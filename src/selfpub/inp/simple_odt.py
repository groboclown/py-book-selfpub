
"""
A simple ODT file parser.  It creates section breaks (chapters) with the text "Chapter (number)".
"""


from .inpf import InputFile
from .. import text
from .odt import parse_file, ODT
import re

CHAPTER_TEXT = re.compile(r"^\s*Chapter\s+(\d+)\s*$", re.I)

FIRST_SET = 0
FIRST_PARAGRAPH = 1
NOT_FIRST = 2


class SimpleODT(InputFile):
    def __init__(self, filename, metadata):
        InputFile.__init__(self)
        self.odt = parse_file(filename)
        assert isinstance(self.odt, ODT)
        self.metadata = metadata

    def get_metadata(self):
        return self.metadata

    def sections(self):
        index = 0
        chapter_name = None
        current = []
        for tx in self.odt.content.convert():
            print("Node {0}".format(tx))
            match = CHAPTER_TEXT.match(tx.get_text())
            if match:
                if len(current) > 0:
                    r = self.parse_chapter(index, chapter_name, current)
                    if r is not None:
                        yield r
                chapter_name = match.group(1)
                index += 1
                # Don't include the chapter text
                current = []
            else:
                current.append(tx)
        if len(current) > 0:
            r = self.parse_chapter(index, chapter_name, current)
            if r is not None:
                yield r

    def parse_chapter(self, index, chapter_name, text_nodes):
        """
        FIXME this should be in the stylesheet.

        :param index:
        :param chapter_name:
        :param text_nodes:
        :return:
        """
        if index <= 0:
            return None
        ret = text.Chapter(chapter_name, index)
        ret.name = "Chapter {0}".format(chapter_name)

        count = 0
        for node in text_nodes:
            count += 1
            if node.style is None:
                print("Node {0} style is None: {1}".format(count, node.node.toxml()))
                raise Exception()
            ret.add_div(node)
        return ret
