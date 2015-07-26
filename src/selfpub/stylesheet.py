"""
Defines how the style of the input text is to be parsed into a complete book.

This depends upon the formatting of the input, and needs to be customized
based on the style that it was originally written.
"""


class StyleSheet(object):
    def __init__(self):
        object.__init__(self)

    def update_section(self, section):
        """Updates the style and text in the section pulled from the book.  Returns it as a complete
        section, or """
        raise NotImplementedError()

    def start_parser(self):
        """Signal to start the section parsing."""
        raise NotImplementedError()

    def end_parser(self):
        """End parsing, and return the final elements (list of them)."""
        raise NotImplementedError()


