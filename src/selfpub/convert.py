"""
Converts an input file to an output file using the given style.
"""


from . import inp, outp, text, stylesheet


def convert(input_file, output_file, style):
    assert isinstance(input_file, inp.InputFile)
    assert isinstance(output_file, outp.OutputFile)
    assert isinstance(style, stylesheet.StyleSheet)
    
    md = input_file.get_metadata()
    output_file.set_metadata(md)

    style.start_parser()
    next_index = 1

    for section in input_file.sections():
        next_section = style.update_section(section)
        if next_section is not None:
            print("Found section {0}".format(next_section))
            next_index = renumber(next_section, next_index)
            output_file.add_section(next_section)
    for section in style.end_parser():
        output_file.add_section(section)

    output_file.write()


def renumber(section, starting_index):
    """Renumbers the index in the section and internal sections, returning the
    next index."""
    
    ret = starting_index
    section.index = ret
    ret += 1
    if hasattr(section, 'divs'):
        for ch in section.divs:
            if isinstance(ch, text.Section):
                ch.index = ret
                ret += 1
    return ret
