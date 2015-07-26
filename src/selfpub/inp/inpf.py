"""
Generic input parsing class
"""

from .. import text


class InputFile(object):
    def __init__(self):
        object.__init__(self)

    def get_metadata(self):
        raise NotImplementedError()

    def sections(self):
        """Iterator to read sections in the input.  Should use 'yield'"""
        raise NotImplementedError()
        

class InputVisitor(InputFile):
    """
    Visitor pattern for consuming the raw div/span format of the input document,
    and converting it to the deep section level input required by the
    outp module.
    """
    def __init__(self, raw):
        assert isinstance(raw, InputFile)
        
        InputFile.__init__(self)
        self.raw = raw
        self.digested = []
    
    def get_metadata(self):
        return self.raw.get_metadata()

    def sections(self):
        self.enter_doc()
        for inps in self.raw.sections():
            self.process_input(inps, 0)
            r = self.next_digested_section()
            while r is not None:
                yield r
                r = self.next_digested_section()
        self.exit_doc()
        r = self.next_digested_section()
        while r is not None:
            yield r
            r = self.next_digested_section()

    def next_digested_section(self):
        if len(self.digested) > 0:
            return self.digested.pop(0)
        return None
    
    def digest_section(self, sec):
        assert isinstance(sec, text.Div)
        
        self.digested.append(sec)

    def enter_doc(self):
        pass

    def enter_div(self, div, depth):
        pass

    def exit_div(self, div, depth):
        pass

    def enter_span(self, span, parent):
        pass

    def exit_span(self, span, parent):
        pass

    def exit_doc(self):
        pass

    def process_input(self, sec, depth):
        if isinstance(sec, text.Para):
            self.enter_div(sec, depth)
            for span in sec.spans:
                self.enter_span(span, sec)
                self.exit_span(span, sec)
            self.exit_div(sec, depth)
        elif isinstance(sec, text.Table):
            self.enter_div(sec, depth)
            if sec.header is not None:
                self.process_input(sec.header, depth + 1)
            for row in sec.rows:
                self.process_input(row, depth + 1)
            self.exit_div(sec, depth)
        elif isinstance(sec, text.TableRow):
            self.enter_div(sec, depth)
            for cell in sec.cells:
                self.process_input(cell, depth + 1)
            self.exit_div(sec, depth)
        elif isinstance(sec, text.Media):
            self.enter_div(sec, depth)
            self.exit_div(sec, depth)
        elif isinstance(sec, text.Text):
            div = text.Para()
            div.spans.append(sec)
            self.enter_div(div, depth)
            self.enter_span(sec, div)
            self.exit_span(sec, div)
            self.exit_div(div, depth)
        else:
            raise Exception("Invalid raw section: {0}".format(sec))
