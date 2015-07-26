"""
Generic interfaces for output to different reader formats.
"""


class OutputFile(object):
    def __init__(self):
        object.__init__(self)
    
    def add_section(self, section):
        raise NotImplementedError()
    
    def set_metadata(self, metadata):
        raise NotImplementedError()

    def add_toc(self, toc):
        raise NotImplementedError()

    def write(self):
        raise NotImplementedError()
    
    def preview(self):
        raise NotImplementedError()
