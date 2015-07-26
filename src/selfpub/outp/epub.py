"""
B&N ePub format output

Formatting Guide:
    https://simg1.imagesbn.com/pimages/pubit/support/pubit_epub_formatting_guide.pdf

Previewer:
    http://www.barnesandnoble.com/u/nook-for-pc/379002322/?cds2Pid=35114
    
Checker:
    http://code.google.com/p/epubcheck/
    
    As a library:
        java -jar epubcheck-x.x.x.jar file.epub 
"""


from .output import OutputFile


class EPubOutput(OutputFile):
    def __init__(self, inputfile, outputfile):
        OutputFile.__init__(self)
        self.inputfile = inputfile
        self.outputfile = outputfile


