"""
ODT input file parser.
"""

import zipfile
import xml.dom
import xml.dom.minidom
from io import StringIO
from .inpf import InputFile
from .. import text


class ODTInputFile(InputFile):
    def __init__(self, filename, cover_image_file):
        InputFile.__init__(self)
        self.odt = parse_file(filename)
        self.cover_image_file = cover_image_file

    def get_metadata(self):
        ret = text.MetaData()
        if self.cover_image_file is not None:
            ret.cover = text.Image(self.cover_image_file)
        
        md = self.odt.meta.properties
        
        if 'Book Author First' in md:
            ret.author_first = md['Book Author First']
        elif 'Book Author' in md:
            names = md['Book Author'].split()
            ret.author_first = " ".join(names[:-1])
        
        if 'Book Author Last' in md:
            ret.author_last = md['Book Author Last']
        elif 'Book Author' in md:
            names = md['Book Author'].split()
            ret.author_last = names[-1]
        
        if 'Publish Year' in md:
            ret.year = md['Publish Year']
        
        if 'title' in md:
            ret.title = md['title']
        
        if 'description' in md:
            ret.description = md['description']
        
        if 'ISBN-10' in md:
            ret.isbn_10 = md['ISBN-10']
        
        if 'ISBN-13' in md:
            ret.isbn_13 = md['ISBN-13']
        
        if 'language' in md:
            ret.language = md['language']
        
        return ret
    
    def sections(self):
        """Iterator to read sections in the input.  Should use 'yield'"""
        for ret in self.odt.content.convert():
            yield ret


def parse_file(filename):
    return parse_zip(zipfile.ZipFile(filename, 'r'))


def parse_contents(contents):
    sfile = StringIO(contents)
    return parse_zip(zipfile.ZipFile(sfile, 'r'))


def parse_zip(zipf):
    return ODT(zipf)


class ODT(object):
    def __init__(self, zipf):
        object.__init__(self)
        self.low = LowODF(zipf)
        assert self.low.has_file(MANIFEST_FILE)
        assert self.low.has_file(CONTENT_FILE)
        assert self.low.has_file(META_FILE)
        self.meta = MetaFile(self.low)
        self.content = ContentFile(self.low)
    

MANIFEST_FILE = "META-INF/manifest.xml"
STYLE_FILE = "styles.xml"
CONTENT_FILE = "content.xml"
META_FILE = "meta.xml"


class LowODF(object):
    def __init__(self, zipf):
        object.__init__(self)
        self.__zip = zipf
        self.__files = {}
        for info in self.__zip.infolist():
            self.__files[info.orig_filename] = info

    def has_file(self, name):
        return name in self.__files.keys()

    def read_file(self, name):
        return self.__zip.read(name)

    def read_dom(self, name):
        return xml.dom.minidom.parseString(self.read_file(name))


class MetaFile(object):
    def __init__(self, lowodf):
        object.__init__(self)
        self.properties = self.parse_meta(
            lowodf.read_dom(META_FILE))

    def parse_meta(self, dom):
        ret = {}
        for metaset in dom.getElementsByTagName("office:meta"):
            for child in metaset.childNodes:
                if child.nodeType == xml.dom.Node.ELEMENT_NODE:
                    if child.tagName[:3] == 'dc:':
                        ret[child.tagName[3:]] = self.get_node_text(child)
                    elif child.tagName == 'meta:user-defined':
                        ret[child.getAttribute("meta:name")] = self.get_node_text(child)
                        pass
                    elif child.tagName == 'meta:document-statistic':
                        # ignore
                        pass
                    elif child.tagName[:5] == 'meta:':
                        ret[child.tagName[5:]] = self.get_node_text(child)
        return ret

    def get_node_text(self, node):
        ret = ""
        for child in node.childNodes:
            if (child.nodeType == xml.dom.Node.TEXT_NODE or 
                    child.nodeType == xml.dom.Node.CDATA_SECTION_NODE):
                ret = ret + child.data
        return ret
        

STYLE_ATTRIBUTES = (
    "text:style-name",
    # "style:data-style-name",
)


class ContentFile(object):
    def __init__(self, lowodf):
        object.__init__(self)
        self.lowodf = lowodf
        self.__content = lowodf.read_dom(CONTENT_FILE)
        self.__styles = OdtStyleSet()
        self.__text = None
        if lowodf.has_file(STYLE_FILE):
            self.__styles.load_from_xml(lowodf.read_dom(STYLE_FILE))
        self.__styles.load_from_xml(self.__content)
        
    def get_text_dom(self):
        """Return a list of all top-level text nodes found in
        <office:body><office:text> parts"""
        
        if self.__text is None:
            self.__text = []
            for section in self.__content.getElementsByTagName("office:text"):
                if section.nodeType == xml.dom.Node.ELEMENT_NODE:
                    for child in section.childNodes:
                        if (child.nodeType == xml.dom.Node.ELEMENT_NODE and
                                child.prefix == "text"):
                            self.__text.append(child)
        return self.__text
    
    def get_style(self, node):
        if isinstance(node, str):
            return self.get_style_by_name(node)
        for attr in STYLE_ATTRIBUTES:
            name = node.getAttribute(attr)
            if name is not None:
                style = self.get_style_by_name(name)
                if style is not None:
                    return style
        return None
    
    def get_style_by_name(self, name):
        return self.__styles.get_style_by_name(name)
    
    def parse_text(self):
        """Iterate over the text nodes, returning BaseText objects."""
        for text_node in self.get_text_dom():
            val = parse_node(text_node, self, [])
            if val is not None:
                for node in val:
                    yield node

    def convert(self):
        """
        Basic conversion from the ODT format into the generic text format.

        :return: iterable of text nodes, which should all be divs.
        """
        for section in self.__content.getElementsByTagName("office:text"):
            if section.nodeType == xml.dom.Node.ELEMENT_NODE:
                for child in section.childNodes:
                    val = None
                    if child.nodeType == xml.dom.Node.ELEMENT_NODE:
                        if child.prefix == "draw" or child.prefix == "text":
                            val = parse_node(child, self)
                        else:
                            print("Unknown child prefix {0}".format(child.toxml()))
                    if val is not None:
                        if isinstance(val, list):
                            for v in val:
                                yield v
                        else:
                            yield val


PARAGRAPH_STYLE_ATTRIBUTES = {
    'fo:margin-left': 'left',  # X.Yin
    'fo:margin-right': 'right',  # X.Yin
    'fo:line-height': 'height',  # X%
    'fo:text-indent': 'indent',  # X.Yin
    'style:auto-text-indent': 'auto-indent',  # true/false
    'style:text-autospace': 'autospace',  # true/false
    'style:master-page-name': 'page-style-name',
    'style:page-layout-name': 'page-layout-name',
}

TEXT_STYLE_ATTRIBUTES = {
    'style:font-name': 'font-name',
    'fo:font-size': 'font-size',
    'style:font-name-asian': 'font-name-asian',
    'style:font-size-asian': 'font-size-asian',
    'style:font-name-complex': 'font-name-complex',
    'style:font-size-complex': 'font-size-complex',
    'fo:font-style': 'font-style',
    'style:font-style-asian': 'font-style-asian',
    'style:font-style-complex': 'font-style-complex',
    'fo:language': 'language',
    'fo:country': 'country',
    'fo:font-weight': 'font-weight',
    'style:font-weight-asian': 'font-weight-asian',
    'style:font-weight-complex': 'font-weight-complex',
}


STYLE_TAGS = (
    "style:style",
    "style:default-style",
    "style:page-layout",
    "style:master-page",
    )
FONT_TAGS = (
    "style:font-face",
    )


class OdtStyleSet(object):
    def __init__(self):
        object.__init__(self)
        self.__styles = {}
        self.__fonts = {}
        
    def get_style_by_name(self, name):
        if name in self.__styles:
            ret = self.__styles[name]
            ret.load_parent(self)
            return ret
        return None
    
    def get_font_by_name(self, name):
        if name in self.__fonts:
            return self.__fonts[name]
        return None
    
    def load_from_xml(self, dom):
        for tagname in STYLE_TAGS:
            for style in dom.getElementsByTagName(tagname):
                if style.nodeType == xml.dom.Node.ELEMENT_NODE:
                    styleobj = OdtStyle(style)
                    self.__styles[styleobj.name] = styleobj
        
        for tagname in FONT_TAGS:
            for font in dom.getElementsByTagName(tagname):
                if font.nodeType == xml.dom.Node.ELEMENT_NODE:
                    fontobj = Font(font)
                    self.__fonts[fontobj.name] = fontobj
        

class OdtStyle(object):
    def __init__(self, style_node):
        object.__init__(self)
        
        self.style_node = style_node
        self.parent_style = None
        
        # Default options
        self.name = 'noop'
        self.spans = 'text'
        self.text = {}
        self.paragraph = {}
        if style_node is not None:
            self.name = style_node.getAttribute("style:name")
            self.spans = style_node.getAttribute("style:family")
            
            self.parent_style_name = style_node.getAttribute("style:parent-style-name")
            if self.parent_style_name is not None and (self.parent_style_name == "Standard" or len(self.parent_style_name) <= 0):
                self.parent_style_name = None
            
            for para in style_node.getElementsByTagName("style:paragraph-properties"):
                for key, val in PARAGRAPH_STYLE_ATTRIBUTES.items():
                    attr = para.getAttribute(key)
                    if len(attr) > 0:
                        self.paragraph[val] = attr

            for text_node in style_node.getElementsByTagName("style:text-properties"):
                for key, val in TEXT_STYLE_ATTRIBUTES.items():
                    if text_node.hasAttribute(key):
                        self.text[val] = str(text_node.getAttribute(key))
            
            if style_node.hasAttribute("style:page-layout-name"):
                self.spans = 'page'
                # FIXME page layout description
        
    @property
    def is_paragraph(self):
        return self.spans == "paragraph"
    
    @property
    def is_inner_text(self):
        return self.spans == "text"
    
    @property
    def font_size(self):
        size = "11pt"
        if 'font-size' in self.text:
            size = self.text['font-size']
        return size
    
    @property
    def is_italics(self):
        ret = False
        if 'font-style' in self.text:
            ret = (
                self.text['font-style'] == 'italics' or
                self.text['font-style'] == 'italic')
        return ret
    
    @property
    def is_bold(self):
        ret = False
        if 'font-weight' in self.text:
            ret = self.text['font-weight'] == 'bold'
        return ret
    
    def get_font(self, styleset):
        ret = None
        if 'font-name' in self.text:
            ret = styleset.get_font_by_name(self.text['font-name'])
        return ret
    
    def load_parent(self, styleset):
        if (self.parent_style is None and
                self.parent_style_name is not None and
                self.parent_style_name != self.name):
            self.parent_style = styleset.get_style_by_name(self.parent_style_name)
            if self.parent_style is not None:
                for key, value in self.parent_style.paragraph.items():
                    if key not in self.paragraph:
                        self.paragraph[key] = value
                for key, value in self.parent_style.text.items():
                    if key not in self.text:
                        self.text[key] = value
        
        # FIXME parse self.paragraph['page-style-name'] and
        # self.paragraph['page-layout-name']


class Font(object):
    def __init__(self, font_node):
        object.__init__(self)
        self.font_node = font_node
        
        self.name = 'unknown'
        self.family = 'unknown'
        self.generic_family = 'unknown'
        
        if font_node is not None:
            self.name = font_node.getAttribute("style:name")
            self.family = font_node.getAttribute("svg:font-family")
            self.generic_family = font_node.getAttribute("style:font-family-generic")


def parse_style(odt_style_list, text_style):
    if isinstance(text_style, text.BlockStyle):
        parse_block_style(odt_style_list, text_style)
    elif isinstance(text_style, text.TextStyle):
        parse_span_style(odt_style_list, text_style)
    else:
        raise Exception("Not valid style: {0}".format(text_style))
    text_style.source = odt_style_list

    
def parse_block_style(odt_style_list, text_style):
    """Convert the internal style object into a text.Style object."""
    styles = list(odt_style_list)
    styles.reverse()
    for style in styles:
        if style.name is not None and len(style.name) > 0:
            text_style.name = style.name

            # FIXME

            break
    pass


def parse_span_style(odt_style_list, text_style):
    """Convert the internal style object into a text.Style object."""
    styles = list(odt_style_list)
    styles.reverse()
    for style in styles:
        if style.name is not None and len(style.name) > 0:
            text_style.name = style.name
            break
    pass


def _convert_units(self, val):
    """
    Convert the text value into a common unit.  In this case, we're converting to mm.

    :param val:
    :return:
    """
    val = str(val)
    if val[-2:] == "mm":
        # As-is
        return val[:-2]
    elif val[-2:] == "cm":
        return str(float(val[:-2]) * 10.0)
    elif val[-2:] == "m":
        return str(float(val[:-2]) * 1000.0)
    elif val[-2:] == "in":
        return str(float(val[:-2]) * 25.4)
    else:
        return val


CONTROL_CONTAINER_TAGS = (
    'text:list',
    'text:list-header',
    )
PARA_TAGS = (
    'text:p',
    'text:h',
    )
SPAN_TAGS = (
    'text:span',
    )
DATA_TAGS = (
    'text:user-defined',
    'text:title',
    'text:description',
    )
MEDIA_CONTAINER_TAGS = (
    'draw:frame',
    )
IMAGE_TAGS = (
    'draw:image',
    )
WHITESPACE_DIV_TAGS = (
    'text:line-break',
)
WHITESPACE_SPAN_TAGS = (
    'text:s',
    'text:soft-page-break',
    )
TAB_TAGS = (
    'text:tab',
    )
CONTROL_TAGS = (
    'text:sequence-decls',
    'office:forms',
    )

HREF_ATTR = "xlink:href"


def parse_node(node, content, parent_style_list=None):
    if parent_style_list is None:
        parent_style_list = []
    tag = node.tagName
    print("Parsing {0}".format(tag))
    style = content.get_style(node)
    style_list = list(parent_style_list)
    style_list.append(style)
    if tag in CONTROL_CONTAINER_TAGS:
        # FIXME recheck how to deal with control tags

        children = []
        for child in node.childNodes:
            ntype = child.nodeType
            if ntype == xml.dom.Node.ELEMENT_NODE:
                children.append(parse_node(child, content, style_list))
            elif (ntype == xml.dom.Node.TEXT_NODE or
                    ntype == xml.dom.Node.CDATA_SECTION_NODE):
                raise Exception("Text element in control {0}".format(node.toxml()))
            else:
                # Ignore non elements and text nodes
                pass
        if len(children) == 1:
            return children[0]
        # elif len(children) <= 0:
        #    return TextWhitespace(style, node)
        # else:
        #    return TextContainer(children[0].style, children, node)
        else:
            raise Exception("Unknown parsing for control tag {0}".format(node.toxml()))
    
    elif tag in PARA_TAGS:
        ret_list = []
        ret = text.Para()
        parse_style(style_list, ret.style)
        for child in node.childNodes:
            ntype = child.nodeType
            if (ntype == xml.dom.Node.ELEMENT_NODE and
                    child.tagName in DATA_TAGS):
                child = child.childNodes[0]
                ntype = child.nodeType
            
            if ntype == xml.dom.Node.ELEMENT_NODE:
                pchild = parse_node(child, content, style_list)
                if not isinstance(pchild, list):
                    pchild = [pchild]
                if isinstance(pchild, list):
                    for ch in pchild:
                        if isinstance(ch, text.Div):
                            # A new top-level div inside this one.  Break it apart
                            # so that the returned paragraphs only have spans.
                            prev_style = ret.style
                            ret_list.append(ret)
                            ret_list.append(ch)
                            ret = text.Para()
                            ret.style = prev_style
                        else:
                            ret.add_span(ch)
            elif (ntype == xml.dom.Node.TEXT_NODE or
                    ntype == xml.dom.Node.CDATA_SECTION_NODE):
                pchild = text.Text()
                pchild.text = child.data
                pchild.source = node
                parse_style(style_list, pchild.style)
                ret.add_span(pchild)
            else:
                # Ignore non elements and text nodes
                pass
        ret_list.append(ret)
        return ret_list

    elif tag in SPAN_TAGS:
        ret = []
        for child in node.childNodes:
            ntype = child.nodeType
            if (ntype == xml.dom.Node.ELEMENT_NODE and
                    child.tagName in DATA_TAGS):
                child = child.childNodes[0]
                ntype = child.nodeType
            
            if ntype == xml.dom.Node.ELEMENT_NODE:
                pchild = parse_node(child, content, style_list)
                if isinstance(pchild, list):
                    ret.extend(pchild)
                else:
                    ret.append(pchild)
            elif (ntype == xml.dom.Node.TEXT_NODE or
                    ntype == xml.dom.Node.CDATA_SECTION_NODE):
                pchild = text.Text()
                pchild.text = child.data
                pchild.source = node
                parse_style(style_list, pchild.style)
                ret.append(pchild)
            else:
                # Ignore non elements and text nodes
                pass
        return ret

    elif tag in TAB_TAGS:
        ret = text.Text()
        parse_style(style_list, ret.style)
        ret.text = "\t"
        return ret

    elif tag in WHITESPACE_SPAN_TAGS:
        ret = text.Text()
        parse_style(style_list, ret.style)
        return ret

    elif tag in WHITESPACE_DIV_TAGS or tag in CONTROL_TAGS:
        # This indicates a new paragraph.  However, it's a stand-alone tag.
        ret = text.Para()
        parse_style(style_list, ret.style)
        return ret

    elif tag in DATA_TAGS:
        print("Unexpected data tag at top level: {0}".format(node.toxml()))

    elif tag in MEDIA_CONTAINER_TAGS:
        ret = text.SideBar()
        kid_list = list(parent_style_list)
        kid_list.append(ret.style)
        parse_block_style(kid_list, ret.style)
        for child in node.childNodes:
            pchild = parse_node(child, content, kid_list)
            if isinstance(pchild, list):
                ret.divs.extend(pchild)
            else:
                ret.divs.append(pchild)
        return ret

    elif tag in IMAGE_TAGS:
        if node.hasAttribute(HREF_ATTR):
            ret = OdtImage(node.getAttribute(HREF_ATTR), content.lowodf)
            kid_list = list(parent_style_list)
            kid_list.append(ret.style)
            parse_block_style(kid_list, ret.style)
            return ret
        else:
            raise Exception("No href tag in image {0}".format(node.toxml()))

    else:
        raise Exception("Unknown text node: {0}".format(node.toxml()))


class OdtImage(text.Image):
    def __init__(self, rel_name, low):
        assert isinstance(low, LowODF)
        assert low.has_file(rel_name), "ODT has no file {0}".format(rel_name)
        text.Image.__init__(self, rel_name)
        self.__low = low

    def save_as(self, dest_file_stream):
        inp = self.__low.read_file(self.filename)
        try:
            dest_file_stream.write(inp.read())
        finally:
            inp.close()
