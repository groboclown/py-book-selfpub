"""
Generic interchange document structures.
"""


STYLE_TYPE_INT = 'int'
STYLE_TYPE_FLOAT = 'float'
STYLE_TYPE_CDATA = 'cdata'
STYLE_TYPE_BOOLEAN = 'boolean'
STYLE_TYPES = (
    STYLE_TYPE_INT,
    STYLE_TYPE_FLOAT,
    STYLE_TYPE_CDATA,
    STYLE_TYPE_BOOLEAN
)


class Style(object):
    def __init__(self, types):
        object.__init__(self)
        self.name = None
        self.source = None
        self.__settings = {}
        self.__types = types
        for key, val in types.items():
            assert (isinstance(key, str)
                ), "key '{0}' not string".format(key)
            if isinstance(val, str):
                assert (val in STYLE_TYPES
                    ), "key '{0}' type '{1}' not valid".format(key, val)
            else:
                assert (hasattr(val, '__iter__') and callable(getattr(val, '__iter__'))
                    ), "key '{0}' type '{1}' not list".format(key, val)
                # FIXME Assert entries in type are strings

    def get_setting(self, name):
        if name in self.__settings:
            return self.__settings[name]
        if name in self.__types:
            return None
        raise Exception("bad setting name: {0}".format(str(name)))

    def set_setting(self, name, value):
        if name in self.__types:
            t = self.__types[name]
            if t == STYLE_TYPE_INT:
                value = int(value)
            elif t == STYLE_TYPE_FLOAT:
                value = float(value)
            elif t == STYLE_TYPE_CDATA:
                value = str(value)
            elif t == STYLE_TYPE_BOOLEAN:
                value = bool(value)
            else:
                value = str(value).lower()
                if value not in t:
                    raise Exception("Bad setting value for name {0}: {1}".format(
                        str(name), value))
            self.__settings[name] = value
        raise Exception("bad setting name: {0}".format(str(name)))

    def defaults(self, default_settings):
        for key, val in default_settings.iteritems():
            self.set_setting(key, val)

    def keys(self):
        return self.__types.keys()

    def __getitem__(self, key):
        return self.get_setting(key)
    
    def __setitem__(self, name, value):
        self.set_setting(name, value)
    
    def __str__(self):
        return "Style({0}: {1})".format(self.name, self.__settings)


class BlockStyle(Style):
    def __init__(self):
        # All size measurements in mm
        Style.__init__(self, {
            'margin-left': STYLE_TYPE_FLOAT,
            'margin-right': STYLE_TYPE_FLOAT,
            'margin-top': STYLE_TYPE_FLOAT,
            'margin-bottom': STYLE_TYPE_FLOAT,
            'page-break': STYLE_TYPE_BOOLEAN,
            'h-align': ["center", "left", "right", "justify"],
            'border-left-width': STYLE_TYPE_INT,
            'border-right-width': STYLE_TYPE_INT,
            'border-top-width': STYLE_TYPE_INT,
            'border-bottom-width': STYLE_TYPE_INT
        })


class TextStyle(Style):
    def __init__(self):
        Style.__init__(self, {
            'italic': STYLE_TYPE_BOOLEAN,
            'bold': STYLE_TYPE_BOOLEAN,
            'underline': STYLE_TYPE_BOOLEAN,
            'strikethrough': STYLE_TYPE_BOOLEAN,
            'all-caps': STYLE_TYPE_BOOLEAN,
            'small-caps': STYLE_TYPE_BOOLEAN,
            'v-align': ['sup', 'sub', 'normal'],
            'size': STYLE_TYPE_INT,
            'font': ['sans', 'serif', 'mono', 'normal'],
            'color': STYLE_TYPE_CDATA,
            'background-color': STYLE_TYPE_CDATA
        })


class ContentObj(object):
    def __init__(self):
        object.__init__(self)
        self.source = None

    def get_text(self):
        raise NotImplementedError()


class Div(ContentObj):
    """A block spacing object."""
    def __init__(self):
        ContentObj.__init__(self)
        self.style = BlockStyle()
        self.is_section = False

    def get_children(self):
        raise NotImplementedError()

    def get_text(self):
        ret = ""
        for ch in self.get_children():
            ret += ch.get_text()
        return ret


class SideBar(Div):
    """A side section of content."""
    def __init__(self):
        Div.__init__(self)
        self.divs = []

    def get_children(self):
        return self.divs


class SeparatorLine(Div):
    """A single line separating parts of a chapter."""
    def __init__(self):
        Div.__init__(self)

    def get_children(self):
        return []


class Para(Div):
    def __init__(self):
        Div.__init__(self)
        self.spans = []

    def add_span(self, span):
        assert isinstance(span, Span), "not a span: {0}".format(span)
        self.spans.append(span)

    def get_children(self):
        return self.spans

    def __str__(self):
        spanstxt = u"["
        visited = False
        for spn in self.spans:
            if visited:
                spanstxt += u", "
            else:
                visited = True
            spanstxt += repr(spn)
        spanstxt += u"]"
        return u"Para(Style: {0}; spans: {1})".format(
            self.style, spanstxt)


class TableRow(Div):
    def __init__(self):
        Div.__init__(self)
        self.cells = []
    
    def add_cell(self, cell):
        assert isinstance(cell, Div)
        self.cells.append(cell)

    def get_children(self):
        return self.cells


class Table(Div):
    def __init__(self):
        Div.__init__(self)
        self.header = None
        self.rows = []

    def set_header(self, header):
        assert header is None or isinstance(header, TableRow)
        self.header = header

    def add_row(self, row):
        assert isinstance(row, TableRow)
        self.rows.append(row)

    def get_children(self):
        ret = [self.header]
        ret.extend(self.rows)
        return ret


class Span(ContentObj):
    """A inline object.  Contained in a Div"""
    def __init__(self):
        ContentObj.__init__(self)
        self.style = TextStyle()

    def get_text(self):
        return ""


class Text(Span):
    def __init__(self):
        Span.__init__(self)
        self.text = ""

    def get_text(self):
        return self.text

    def __str__(self):
        return u"Text(Style: {0}, text: '{1}')".format(
            self.style, self.text)


class SpecialCharacter(Text):
    def __init__(self):
        Text.__init__(self)
        self.html = ""
        self.is_whitespace = False


class Correction(Span):
    def __init__(self, original):
        Span.__init__(self)
        self.original = original
        self.text = ""


class Media(Span):
    def __init__(self, filename):
        Span.__init__(self)
        assert filename.find('.') >= 0
        self.filename = filename
        self.ext = filename[filename.rindex('.')+1:]

    def get_mimetype(self):
        raise NotImplementedError()

    def save_as(self, dest_stream):
        raise NotImplementedError()


class Image(Media):
    def __init__(self, filename):
        Media.__init__(self, filename)
        assert filename.find('.') >= 0
        self.filename = filename
        self.ext = filename[filename.rindex('.')+1:]

    def get_mimetype(self):
        return "image/{0}".format(self.ext)

    def save_as(self, dest_stream):
        raise NotImplementedError()


class Section(Div):
    def __init__(self, index):
        Div.__init__(self)
        self.is_section = True
        self.index = index
        self.is_toc = False
        self.is_book = False

    def get_children(self):
        raise NotImplementedError()


class Chapter(Section):
    def __init__(self, name, index):
        Section.__init__(self, index)
        self.name = name
        self.divs = []

    def add_div(self, div):
        assert isinstance(div, Div)
        self.divs.append(div)

    def get_children(self):
        return self.divs


class TOC(Section):
    def __init__(self, index, depth_index_func):
        Section.__init__(self, index)
        self.is_toc = True
        self.title_div = None
        if depth_index_func is not None:
            assert callable(depth_index_func)
        self.depth_index_func = depth_index_func
        
        # Should be a list of block styles,
        # one per depth of the TOC
        self.line_div_styles = []

        # A list of nodes
        self.section_tree = []

    def get_children(self):
        ret = []
        if self.title_div is not None:
            ret.append(self.title_div)

        ret.extend(self.section_tree)

        return ret

    def set_chapters(self, chapters):
        self.section_tree = self.__chapter_builder(chapters, 0)

    def __chapter_builder(self, sections, depth):
        order = []
        index = 0
        for ch in sections:
            if isinstance(ch, Chapter):
                index += 1
                order.append(self.__create_entry(ch, depth, index))
                kids = self.__chapter_builder(ch.get_children(), depth + 1)
                if len(kids) > 0:
                    order.extend(kids)
        return order

    def __create_entry(self, ch, depth, index):
        assert isinstance(ch, Chapter)
        prefix = None
        if self.depth_index_func is not None:
            prefix = self.depth_index_func(depth, index)
        d = TocRow(ch, depth, index, prefix)
        if depth > len(self.line_div_styles):
            d.style = self.line_div_styles[-1]
        else:
            d.style = self.line_div_styles[depth]
        return d


class TocRow(Div):
    def __init__(self, chapter, depth, index, prefix):
        Div.__init__(self)
        self.name = chapter.name
        self.prefix = prefix or ""
        self.depth = depth
        self.index = index

        self.text = Text()
        self.text.text = self.prefix + self.name

    def get_children(self):
        return [self.text]


class MetaData(object):
    def __init__(self):
        object.__init__(self)
        self.author_first = ""  # (includes middle name / initial)
        self.author_last = ""
        self.year = ""
        self.cover = None  # Image
        self.title = ""
        self.description = ""
        self.isbn_10 = ""
        self.isbn_13 = ""
        self.language = "en"
        self.subtitles = []
    
    def set_cover(self, cover):
        assert isinstance(cover, Image)
        self.cover = cover

    def as_dict(self):
        return {
            "author_first": self.author_first,
            "author_last": self.author_last,
            "year": self.year,
            "title": self.title,
            "description": self.description,
            "isbn_10": self.isbn_10,
            "isbn_13": self.isbn_13,
            "language": self.language,
            "subtitles": self.subtitles
        }
