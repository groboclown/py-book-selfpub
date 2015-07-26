"""
Simple HTML output.  Useful for checking the conversion.
"""


from .output import OutputFile
from .. import text
import os


class HtmlOutput(OutputFile):

    def __init__(self, outfile, outdir=None):
        OutputFile.__init__(self)
        self.__metadata = None
        self.__outfile = outfile
        self.__outdir = outdir
        self.__chapter_titles = []
        self.__title_stuff = []
        self.__chapters = []

    def add_section(self, section):
        if isinstance(section, text.Chapter):
            self.__chapter_titles.append(section.name)
            self.__chapters.append(section)
        elif len(self.__chapters) <= 0:
            self.__title_stuff.append(section)
        else:
            raise Exception("Only top-level chapters are allowed")

    def set_metadata(self, metadata):
        assert isinstance(metadata, text.MetaData)
        self.__metadata = metadata

    def write(self):
        with open(self.__outfile, "w") as out:
            if self.__metadata is not None:
                write_metadata(self.__metadata, out)
            else:
                write_generic_header(out)
            for sec in self.__title_stuff:
                write_part(sec, out)
            write_toc(self.__chapter_titles, out)

            for sec in self.__chapters:
                write_chapter(sec, out, self.__outdir)

            write_footer(out)


def write_metadata(metadata, out):
    assert isinstance(metadata, text.MetaData)

    # Ignore cover image

    out.writelines("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>{title}</title>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  </head>
  <body>
    <h1>{title}</h1>
    <h2>By {author_first} {author_last}</h2>
    <h2>{description}</h2>
    <h3>&copy; {year} {isbn_10} / {isbn_13}</h3>
""".format(**metadata.as_dict()))


def write_generic_header(out):
    out.writelines("""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>A Book</title>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  </head>
  <body>
    <h1>A Book</h1>
""")


def write_toc(titles, out):
    out.write("    <h4>Table of Contents</h4>\n    <ol>\n")
    for name in titles:
        out.write("      <li><a href='#{0}'>{0}</a></li>\n".format(name))
    out.write("    </ol>\n")


def write_chapter(sec, out, outdir):
    assert isinstance(sec, text.Chapter)
    out.write("    <h4><a name='{0}'>{0}</a></h4>\n".format(sec.name))
    for part in sec.get_children():
        write_part(part, out, outdir)


def write_part(sec, out, outdir, pref=">"):
    if isinstance(sec, text.Image):
        print(pref+" image")
        if outdir is not None:
            fname = os.path.join(outdir, sec.filename)
            dirname = os.path.split(fname)[0]
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with open(fname, "wb") as f:
                sec.save_as(f)
        out.write("    <img src='{0}'>\n".format(sec.filename))
    elif isinstance(sec, text.Para):
        print(pref+" para")
        out.write("    <p>")
        for span in sec.get_children():
            write_part(span, out, outdir, pref+">")
        out.write("</p>\n")
    elif isinstance(sec, text.Text):
        # italics and so on
        x = sec.text
        if isinstance(sec, text.SpecialCharacter):
            x = sec.html
        else:
            x = x.replace("<","&lt;").replace(">","&gt;").replace("&","&amp;")
        print(pref+" text[{0}]".format(x))
        out.write("<span>{0}</span>".format(x))
    elif isinstance(sec, text.SeparatorLine):
        out.write("    <center>* * *</center>\n")
    elif isinstance(sec, text.Correction):
        # ignore
        print("Correction: was originally [{0}]".format(sec.original))
        pass
    else:
        raise Exception("unknown part {0}".format(sec))


def write_footer(out):
    out.writelines("""
  </body>
</html>
    """)
