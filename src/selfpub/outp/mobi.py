"""
Amazon mobi format output

Publishing Guidelines:
    http://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf

Tools:
    http://www.amazon.com/gp/feature.html?ie=UTF8&docId=1000234621
    
    (KindleGen and Kindle Previewer)
"""

from .output import OutputFile
from .. import text
import os
import shutil


OPF_FILENAME = 'book.opf'
NCX_FILENAME = 'book.ncx'
STYLE_FILENAME = 'style.css'
HTML_COVER_FILENAME = 'cover.html'
HTML_END_FILENAME = 'end.html'

SEARCH_ORDER_PRE = 1
SEARCH_ORDER_POST = 2


class MobiOutput(OutputFile):
    def __init__(self, outfile, outdir):
        OutputFile.__init__(self)
        self.sections = {}
        self.metadata = None
        self.toc = None
        self.outfile = outfile
        self.outdir = outdir
        self.section_filenames = {}
        self.css = {}

    def add_section(self, section):
        assert section is not None
        
        self.section_filenames[section.index] = 'chap{0:03d}.html'.format(section.index)
        if section.is_toc:
            assert self.toc is None
            self.toc = section
        self.sections[section.index] = section

    def set_metadata(self, metadata):
        self.metadata = metadata

    def write(self):
        if not os.path.isdir(self.outdir):
            os.makedirs(self.outdir)
        
        opffile = os.path.join(self.outdir, OPF_FILENAME)
        self.write_opf(opffile)
        
        ncxfile = os.path.join(self.outdir, NCX_FILENAME)
        self.write_ncx(ncxfile)
        
        coverhfile = os.path.join(self.outdir, HTML_COVER_FILENAME)
        self.write_html_cover(coverhfile)
        
        coverifile = os.path.join(self.outdir,
            os.path.basename(self.metadata.cover.filename))
        if not os.path.samefile(self.metadata.cover.filename, coverifile):
            shutil.copyfile(self.metadata.cover.filename, coverifile)
        
        if self.toc is not None:
            tocfile = os.path.join(self.outdir, self.section_filenames[self.toc.index])
            self.write_toc(tocfile, False, self.toc)
        
        endfile = os.path.join(self.outdir, HTML_END_FILENAME)
        self.write_html_end(endfile)
        
        # All the sections before the TOC are considered part of the title.
        # So allocate them into a structure, and call the write_toc when the
        # TOC is finally found.
        before_toc = []
        keys = list(self.sections.keys())
        keys.sort()
        for key in keys:
            ch = self.sections[key]
            chfile = os.path.join(self.outdir,
                self.section_filenames[ch.index])
            if before_toc is None:
                self.write_section(chfile, ch)
            elif ch.is_toc:
                self.write_toc(chfile, before_toc, ch)
                before_toc = None
            else:
                before_toc.append(ch)
            
            if hasattr(ch, 'divs'):
                for media in ch.divs:
                    if isinstance(media, text.Media):
                        # FIXME
                        mediafile = os.path.join(self.outdir,
                            os.path.basename(media.filename))
                        if not os.path.samefile(mediafile, media.filename):
                            shutil.copyfile(self.metadata.cover.filename, coverifile)

        cssfile = os.path.join(self.outdir, STYLE_FILENAME)
        self.write_css(cssfile)
        
        # FIXME run mobi converter

    def write_opf(self, outfile):
        
        manifest = self.create_manifest()
        
        spine = self.create_spine()
        
        guide = self.create_guide()
        
        with open(outfile, "w") as f:
            f.write(OPF_TEMPLATE.format(
                manifest=manifest,
                spine=spine,
                guide=guide,
                title=self.metadata.title,
                language=self.metadata.language,
                isbn_10=self.metadata.isbn_10,
                isbn_13=self.metadata.isbn_13,
                author_first=self.metadata.author_first,
                author_last=self.metadata.author_last,
                description=self.metadata.description
                ))
    
    def write_ncx(self, outfile):
        navpoints, last_play_order, maxdepth = self.create_navpoints()
        
        toc_loc = None
        keys = list(self.sections.keys())
        keys.sort()
        for key in keys:
            ch = self.sections[key]
            if ch.is_toc:
                toc_loc = self.section_filenames[ch.index]
                break
        
        with open(outfile, "w") as f:
            f.write(NCX_TEMPLATE.format(
                navpoints=navpoints,
                title=self.metadata.title,
                author_first=self.metadata.author_first,
                author_last=self.metadata.author_last,
                description=self.metadata.description,
                depth=maxdepth,
                toc_loc=toc_loc,
                lastPlayOrder=last_play_order
                ))

    def write_toc(self, outfile, before_toc, toc):
        title_sections = ""
        for ch in before_toc:
            title_sections += self.create_section_text(ch)
        
        toc_title = self.create_div_text(toc.title_div)
        
        toc_divs = ""

        def visit(ch, order, depth):
            raise NotImplementedError()
        
        # FIXME use search_sections
        keys = list(self.sections.keys())
        keys.sort()
        for key in keys:
            ch = self.sections[key]
            chfile = self.section_filenames[ch.index]
            if ch not in before_toc:
                pass
        
        with open(outfile, "w") as f:
            f.write(TOC_TEMPLATE.format(
                title=self.metadata.title,
                cover_loc=os.path.basename(self.metadata.cover.filename),
                title_sections=title_sections,
                toc_title=toc_title,
                toc_divs=toc_divs
                ))
        
        raise NotImplementedError()
    
    def write_html_cover(self, outfile):
        with open(outfile, "w") as f:
            f.write(COVER_TEMPLATE.format(
                loc=os.path.basename(self.metadata.cover.filename),
                title=self.manifest.title
                ))
    
    def write_section(self, outfile, section):
        raise NotImplementedError()

    def write_html_end(self, outfile):
        raise NotImplementedError()

    def write_css(self, outfile):
        raise NotImplementedError()

    def create_section_text(self, section):
        raise NotImplementedError()
    
    def create_div_text(self, div):
        raise NotImplementedError()

    def create_manifest(self):
        found = ['cover-image', 'toc', 'cover-page']
        
        ret = (
            MANIFEST_ENTRY_TEMPLATE.format(
                name='cover-image',
                loc=os.path.basename(self.metadata.cover.filename),
                mimetype=self.metadata.cover.get_mimetype())
            )
        
        # FIXME use search_sections
        keys = list(self.sections.keys())
        keys.sort()
        for key in keys:
            ch = self.sections[key]
            ret += MANIFEST_ENTRY_TEMPLATE.format(
                name=self.section_filenames[ch.index],
                loc=self.section_filenames[ch.index],
                mimetype='application/xhtml+xml'
                )
            if hasattr(ch, 'divs'):
                for media in ch.divs:
                    if isinstance(media, text.Media):
                        ret += MANIFEST_ENTRY_TEMPLATE.format(
                            name=os.path.basename(media.filename),
                            loc=os.path.basename(media.filename),
                            mimetype=media.get_mimetype()
                            )
            
        return ret

    def create_spine(self):
        # NOTE: we hard-code the location of the cover, because that's
        # what's required of us.
        
        ret = ""
        
        keys = list(self.sections.keys())
        keys.sort()
        for key in keys:
            ch = self.sections[key]
            name = self.section_filenames[ch.index],
            ret += SPINE_ENTRY_TEMPLATE.format(name=name)
            
        return ret

    def create_guide(self):
        # Find the actual page name of the TOC and first non-toc section
        first = None
        toc = None
        keys = list(self.sections.keys())
        keys.sort()
        for key in keys:
            ch = self.sections[key]
            if toc is not None and ch.is_toc:
                toc = self.section_filenames[ch.index]
            elif first is not None:
                first = self.section_filenames[ch.index]
            if toc is not None and first is not None:
                break
        return GUIDE_TEMPLATE.format(first_loc=first, toc_loc=toc)

    def create_navpoints(self):
        text_stack = []
        global text_stack

        def visit(ch, order, depth):
            global text_stack
            clazz = ""
            if ch.is_book:
                clazz = 'class="book"'
            
            while depth > len(text_stack):
                text_stack.append("")
            
            if depth + 1 == len(text_stack):
                # Bottom of tree
                text_stack[depth] += NAVPOINT_TEMPLATE.format(
                    name=str(order),
                    order=str(order),
                    title=ch.name,
                    loc=self.section_filenames[ch.index],
                    index=ch.index,
                    navpoints="",
                    clazz=clazz)
            elif depth + 2 == len(text_stack):
                # parent
                children = text_stack[-1]
                text_stack = text_stack[:-1]
                text_stack[depth] += NAVPOINT_TEMPLATE.format(
                    name=str(order),
                    order=str(order),
                    title=ch.name,
                    loc=self.section_filenames[ch.index],
                    index=ch.index,
                    navpoints=children,
                    clazz=clazz)
            else:
                raise Exception("invalid walking: depth {0}, text_stack: {1}".format(depth, text_stack))
                
        play_order, max_depth = self.search_sections(3, SEARCH_ORDER_POST, False, visit)
        return text_stack[0], play_order, max_depth
    
    def search_sections(self, init_index, search_order, visit_toc, visitor):
        max_depth = 0
        play_order = init_index
        keys = list(self.sections.keys())
        keys.sort()
        for key in keys:
            ch = self.sections[key]
            if not ch.is_toc or visit_toc:
                vals = self.__search_sections(
                    ch, play_order, 0, search_order, visitor)
                play_order = vals[0]
                if vals[1] > max_depth:
                    max_depth = vals[1]
        return play_order, max_depth

    def __search_sections(self, ch, index, depth, search_order, visitor):
        ret_play_order = index + 1
        ret_depth = depth
        
        if search_order == SEARCH_ORDER_PRE:
            visitor(ch, index, depth)
        
        if hasattr(ch, 'divs'):
            for sub in ch.divs:
                if isinstance(sub, text.Chapter):
                    vals = self.__create_navpoint(sub, ret_play_order, depth + 1)
                    ret_play_order = vals[0]
                    if vals[1] > ret_depth:
                        ret_depth = vals[1]
        
        if search_order == SEARCH_ORDER_POST:
            visitor(ch, index, depth)
        
        return ret_play_order, ret_depth


OPF_TEMPLATE = """<?xml version="1.0"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{title}</dc:title>
    <dc:language>{language}</dc:language>
    <dc:identifier id="BookId" opf:scheme="ISBN">{isbn_10}</dc:identifier>
    <dc:creator opf:file-as="{author_last}, {author_first}" opf:role="aut">{author_first} {author_last}</dc:creator>
    <dc:description>
{description}
    </dc:description>
    <meta name="cover" content="cover-image" />
  </metadata>
  
  <manifest>
    <item id="toc" href="book.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="cover-page" href="cover.html" media-type="application/xhtml+xml"/>
{manifest}
  </manifest>
 
  <spine toc="toc">
    <itemref idref="cover-page" linear="no" />
    <itemref idref="toc" />
{spine}
  </spine>
 
  <guide>
    <reference type="cover" title="Cover Image" href="cover.html" />
{guide}
  </guide>
 
</package>
"""

MANIFEST_ENTRY_TEMPLATE = """    <item id="{name}" href="{loc}" media-type="{mimetype}"/>
"""
SPINE_ENTRY_TEMPLATE = """    <itemref idref="{name}" />
"""
GUIDE_TEMPLATE = """    <reference type="start" title="Start" href="{first_loc}%23start" />
    <reference type="toc" title="Table of Contents" href="{toc_loc}%23toc" />
"""


NCX_TEMPLATE = """<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/"
version="2005-1" xml:lang="en-US">

<head>
<meta name="dtb:uid" content="uid"/>
<meta name="dtb:depth" content="{depth}"/>
<meta name="dtb:totalPageCount" content="0"/>
<meta name="dtb:maxPageNumber" content="0"/>
</head>

<docTitle><text>{title}</text></docTitle>
<docAuthor><text>{author_first} {author_last}</text></docAuthor>

<navMap>
    <navPoint class="titlepage" id="TitlePage" playOrder="1">
        <navLabel><text>Title Page</text></navLabel>
        <content src="{toc_loc}#Title Page" />
    </navPoint>
    
    <navPoint id="toc" playOrder="2">
        <navLabel><text>Table of Contents</text></navLabel>
        <content src="{toc_loc}#toc" />
    </navPoint>
    
    {navpoints}
    
    <navPoint id="Copyright" playOrder="{lastPlayOrder}">
        <navLabel><text>Copyright Notice</text></navLabel>
        <content src="{toc_loc}#copyright" />
    </navPoint>
</navMap>

</ncx>
"""

NAVPOINT_TEMPLATE = """    <navPoint {clazz} id="{name}" playOrder="{order}">
        <navLabel><text>{title}</text></navLabel>
        <content src="{loc}#{index}" />
        {navpoints}
    </navPoint>
"""


COVER_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8"/>
        <title>{title}</title>
        <meta name="cover" content="{loc}" />
        <link rel="StyleSheet" href="style.css" type="text/css" media="screen, print" />
    </head>
<body>
    <a name="Cover"></a>
    <mbp:section>
    <img src="{loc}" name="{title}" />
    </mbp:section>
</body>
</html>"""


TOC_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8"/>
        <title>{title}</title>
        <meta name="cover" content="{cover_loc}" />
        <link rel="StyleSheet" href="style.css" type="text/css" media="screen, print" />
    </head>
<body>
    <!-- ********************* TITLE PAGE ******************************** -->
    <a name="Title Page"></a>
    {title_sections}
    
    
    <!-- ********************* TABLE OF CONTENTS ******************************** -->
    <a name="toc"></a>
    <mbp:section>
    <h1 class="chapter">Table of Contents</h1>
    <div><a href="#Title Page">Title Page</a></div>
    {toc_divs}
    <div><a href="end.html#copyright">Copyright Notice</a></div>
    </mbp:section>
</body>
</html>"""
