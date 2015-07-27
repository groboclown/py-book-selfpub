"""
Cleans up a messy input file.
"""

from .inpf import InputFile
from .. import text

TRANSLATE_CHARACTERS = {
    u'\u201C': '&ldquo;',  # open double quote
    u'\u201D': '&rdquo;',  # close double quote
    u'\u2019': '&rsquo;',  # close single quote
    '&': '&amp;',
    '>': '&gt;',
    '<': '&lt;',
}
UNICODE_SPACES = [
    '\t',       # TAB - usually 5 em.
    u'\u0020',  # SPACE - Depends on font, typically 1/4 em, often adjusted
    u'\u00A0',  # NO-BREAK SPACE - As a space, but often not adjusted
    u'\u1680',  # OGHAM SPACE MARK - Unspecified; usually not really a space but a dash
    u'\u180E',  # MONGOLIAN VOWEL SEPARATOR - No width
    u'\u2000',  # EN QUAD - 1 en (= 1/2 em)
    u'\u2001',  # EM QUAD - 1 em (nominally, the height of the font)
    u'\u2002',  # EN SPACE - 1 en (= 1/2 em)
    u'\u2003',  # EM SPACE - 1 em
    u'\u2004',  # THREE-PER-EM SPACE - 1/3 em
    u'\u2005',  # FOUR-PER-EM SPACE - 1/4 em
    u'\u2006',  # SIX-PER-EM SPACE - 1/6 em
    u'\u2007',  # FIGURE SPACE - "Tabular width", the width of digits
    u'\u2008',  # PUNCTUATION SPACE - The width of a period "."
    u'\u200A',  # HAIR SPACE - Narrower than THIN SPACE
    u'\u2009',  # THIN SPACE - 1/5 em (or sometimes 1/6 em)
    u'\u200B',  # ZERO WIDTH SPACE - Nominally no width, but may expand
    u'\u202F',  # NARROW NO-BREAK SPACE - Narrower than NO-BREAK SPACE (or SPACE)
    u'\u205F',  # MEDIUM MATHEMATICAL SPACE - 4/18 em
    u'\u3000',  # IDEOGRAPHIC SPACE - The width of ideographic (CJK) characters.
    u'\uFEFF',  # ZERO WIDTH NO-BREAK SPACE - No width (the character is invisible)
]
# Need special handling for:
# ' - ': '&nbsp;&ndash; '
# u' \u2013': '&nbsp;&ndash;',  # long dash
# u'\u2013': '&ndash;',  # long dash
# u'\u2018': # open single quote
# " and ' (whether &ldquo; or &lsquo;)


class Cleaner(InputFile):
    def __init__(self, md, proxy):
        InputFile.__init__(self)
        self.__proxy = proxy
        self.__md = md
        self.expect_paragraphs_to_start_with_tab = True

    def sections(self):
        for sec in self.__proxy.sections():
            val = self.clean_section(sec)
            if val is not None:
                yield val

    def get_metadata(self):
        return self.__md

    def clean_section(self, sec):
        print("cleaning {0}".format(sec))
        if isinstance(sec, text.Para):
            val = self.clean_para(sec)
            if not isinstance(val, text.Para):
                return val
            if len(val.spans) <= 0:
                return None
            return val
        elif isinstance(sec, text.Chapter) or isinstance(sec, text.SideBar):
            new_divs = []
            for div in sec.divs:
                val = self.clean_section(div)
                if val is not None:
                    new_divs.append(val)
            sec.divs = new_divs
            return sec
        elif isinstance(sec, text.Text):
            kids = []
            self.clean_text(sec, kids, "")
            if len(kids) == 0:
                return None
            elif len(kids) == 1:
                return kids[0]
            else:
                raise Exception("Section text node ({0}) was cleaned into multiple parts".format(sec))
        else:
            # raise Exception("Unknown section clean {0}".format(sec))
            return sec

    def clean_para(self, para):
        assert isinstance(para, text.Para)
        new_spans = []
        parsed = ""
        first = self.expect_paragraphs_to_start_with_tab
        for span in para.spans:
            if isinstance(span, text.Text):
                if first:
                    first = False
                    if len(span.text) > 0 and span.text[0] != '\t':
                        print("*** Does not start with tab: {0}".format(span.text))
                parsed = self.clean_text(span, new_spans, parsed)
            else:
                new_spans.append(span)
        _strip_trailing_whitespace(new_spans, "")
        para.spans = new_spans
        return self.special_para_handling(para)

    def special_para_handling(self, para):
        contents = para.get_text().strip()
        if len(contents) == 0:
            return None
        if contents.count('*') == len(contents):
            # A row of '*', which indicates a special separator line.
            print("-- turned [{0}] into a line".format(contents))
            ret = text.SeparatorLine()
            ret.source = para.source
            return ret
        return para

    def clean_text(self, text_node, spans, parsed):
        if text_node.text is None or text_node.text == "":
            return parsed
        val = ""
        print("cleaning [{0}]".format(text_node))
        for ch in text_node.text:
            # print("  - [{0}]".format(ord(ch)))
            # if ch == '\t':
            #    # special tab handling; happens before we join the parsed text.
            #
            #    # First, strip off whitespace at the end of the val.
            #    val = _strip_trailing_whitespace(spans, val)
            #
            #    # Then add in the previous value as a node
            #    val = _join_text(spans, text_node, val)
            #
            #    # Add in the tab as a special character
            #    spans.append(_special_text(text_node, ch, "&nbsp;", True))
            #
            #    parsed = parsed.rstrip() + " "
            #    continue

            # Special characters that are whitespace sensitive, before double-whitespace checks
            if ch == '-' or ch == u'\u2013':
                # possible long dash
                if parsed[-1] == " ":
                    # long dash with a leading space
                    # Note that we check "parsed", because we want to replace the previous
                    # whitespace with a non-breaking space.
                    val = _strip_trailing_whitespace(spans, val)
                    parsed = parsed.rstrip() + " -"
                    val = _join_text(spans, text_node, val)
                    spans.append(_special_text(text_node, u" \u2013", "&nbsp;&ndash;", False))
                elif ch == u'\u2013':
                    # explicit long dash in the middle of stand-alone text.
                    val = _join_text(spans, text_node, val)
                    spans.append(_special_text(text_node, ch, "&ndash;", False))
                    parsed += "-"
                else:
                    val = _join_text(spans, text_node, val)
                    spans.append(_special_text(text_node, ch, ch, False))
                    parsed += ch
                continue

            # 201c: open double quote
            # 201d: closed double quote
            if ch in [u'\u201C', u'\u201D', '"']:
                val = _join_text(spans, text_node, val)

                # Check whitespace before hand.  If there is an odd number of previous double quotes,
                # then we want to turn this into an open double quote with an explicit space
                # before it.
                quote_count = parsed.count('"')
                if quote_count % 2 == 1:
                    # Odd number of previously found double quotes.  Make this a closed double quote.
                    if _has_trailing_whitespace(parsed):
                        # Closing double quotes should always be without whitespace before it
                        span = text.Correction(" " + ch)
                        span.style = text_node.style
                        spans.append(span)
                        val = _strip_trailing_whitespace(spans, val)
                        parsed = parsed.rstrip()
                    elif ch != u'\u201D':
                        span = text.Correction(ch)
                        span.style = text_node.style
                        spans.append(span)
                    spans.append(_special_text(text_node, u'\u201D', '&rdquo;', False))
                else:
                    # Even number of previously found double quotes.  Make this an open double quote.
                    if not _has_trailing_whitespace(parsed):
                        # Open double quotes should always have leading whitespace.  Note that an empty
                        # parsed string (beginning of paragraph) is marked as whitespace, so this won't insert
                        # whitespace at the start.
                        span = text.Correction(ch)
                        span.style = text_node.style
                        spans.append(span)
                    elif ch != u'\u201C':
                        span = text.Correction(ch)
                        span.style = text_node.style
                        spans.append(span)
                    spans.append(_special_text(text_node, u'\u201C', '&ldquo;', False))

                # Mark in the parsed as a normal double quote
                parsed += '"'
                continue

            # u'\u2018' close open quote
            # u'\u2019' close single quote
            if ch in [u'\u2018', u'\u2019', "'"]:
                val = _join_text(spans, text_node, val)

                # Single quotes are more difficult to handle.  If there is whitespace before it, then we consider
                # it to be an open quote.  In all other cases (including contractions and possessives), it's
                # a closed quote.
                if _has_trailing_whitespace(parsed):
                    if ch != '\u2018':
                        span = text.Correction(ch)
                        span.style = text_node.style
                        spans.append(span)
                    spans.append(_special_text(text_node, '\u2018', '&lsquo;', False))
                else:
                    if ch != u'\u2019':
                        span = text.Correction(ch)
                        span.style = text_node.style
                        spans.append(span)
                    spans.append(_special_text(text_node, '\u2019', '&rsquo;', False))

                # Mark in the parsed as a normal single quote
                parsed += "'"
                continue

            # Check if we have multiple whitespace
            if ch.isspace() or ch in UNICODE_SPACES:
                # Convert any other whitespace character to a simple space.
                if len(parsed) <= 0 or parsed[-1] == " ":
                    # already have a previous white space.  Ignore.
                    continue
                ch = " "

            parsed += ch
            val += ch
        _join_text(spans, text_node, val)
        return parsed


def _clone_text(text_node, new_text):
    t = text.Text()
    t.style = text_node.style
    t.text = new_text
    return t


def _special_text(text_node, new_text, html, is_whitespace):
    t = text.SpecialCharacter()
    t.style = text_node.style
    t.text = new_text
    t.html = html
    t.is_whitespace = is_whitespace
    return t


def _join_text(ret, text_node, val):
    if len(val) > 0:
        ret.append(_clone_text(text_node, val))
    return ""


def _has_trailing_whitespace(parsed):
    if len(parsed) <= 0:
        return True
    return parsed[-1].isspace()


def _strip_trailing_whitespace(spans, val):
    if val.rstrip() == "" and len(spans) > 0:
        while len(spans) > 0:
            # Need to check the previous text node
            prev = spans[-1]
            if isinstance(prev, text.SpecialCharacter) and prev.is_whitespace:
                # Explicit whitespace
                break
            else:
                prev.text = prev.text.rstrip()
                if len(prev.text) <= 0:
                    del spans[-1]
                else:
                    break
    return val.rstrip()
