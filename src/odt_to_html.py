#!/usr/bin/python3

import selfpub
import os
import sys
import datetime
import re


CHAPTER_TEXT = re.compile(r"^\s*Chapter\s+(\d+)\s*$", re.I)


class ExampleStyleSheet(selfpub.stylesheet.StyleSheet):
    """
    Simple style sheet.
    """

    def __init__(self):
        object.__init__(self)
        self.chapter_div = None
        self.chapter_count = 0

    def start_parser(self):
        self.chapter_div = None
        self.chapter_count = 0

    def update_section(self, section):
        m = CHAPTER_TEXT.match(section.get_text())
        if m is not None:
            # Chapter start
            ret = self.chapter_div
            self.chapter_count += 1
            self.chapter_div = selfpub.text.Chapter(m.group(1), self.chapter_count)
            return ret
        elif self.chapter_div is not None and isinstance(section, selfpub.text.Div):
            if isinstance(section, selfpub.text.Chapter):
                raise Exception("chapter found in input")
            self.chapter_div.add_div(section)
        else:
            print("simple stylesheet: Ignoring [{0}|{1}]".format(section, section.get_text()))

        return None

    def end_parser(self):
        if self.chapter_div is None:
            ret = []
        else:
            ret = [self.chapter_div]
        self.chapter_div = None
        self.chapter_count = 0
        return ret


if __name__ == '__main__':
    (inp, out, title, author_first, author_last) = sys.argv[1:]

    metadata = selfpub.text.MetaData()
    metadata.title = title
    metadata.author_first = author_first
    metadata.author_last = author_last
    metadata.year = datetime.date.today().year

    in_file = selfpub.inp.Cleaner(metadata, selfpub.inp.ODTInputFile(inp, None))
    out_file = selfpub.outp.HtmlOutput(out, os.path.split(out)[0] or ".")
    style = ExampleStyleSheet()

    selfpub.convert.convert(in_file, out_file, style)
