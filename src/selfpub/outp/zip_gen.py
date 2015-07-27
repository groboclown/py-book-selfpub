
"""
Uses template files to generate an ODT document.
"""

from .output import OutputFile
import os
import zipfile
from .. import text

class ZipGenOutput(OutputFile):
    def __init__(self, template_dir, output_file):
        OutputFile.__init__(self)
        self.output_file = output_file
        self.template_dir = template_dir
        assert os.path.isdir(os.path.join(template_dir, "copy"))
        assert os.path.isdir(os.path.join(template_dir, "template"))
        self.__chapters = []
        self.__toc = None
        self.__md = None

    def write(self):
        out = zipfile.ZipFile(self.output_file, mode="w", compression=zipfile.ZIP_DEFLATED)
        try:
            _copy_tree_to_zip(out, os.path.join(self.template_dir, "copy"))
            data = self.populate_data()
            _template_tree_to_zip(out, os.path.join(self.template_dir, "template"), data)
        finally:
            out.close()

    def set_metadata(self, metadata):
        self.__md = metadata

    def add_section(self, section):
        if isinstance(section, text.Chapter):
            self.__chapters.append(section)
        else:
            raise Exception("Only top-level chapters are allowed")

    def add_toc(self, toc):
        self.__toc = toc

    def preview(self):
        pass

    def populate_data(self):
        data = {
            "metadata": self.__md,
            "toc": self.__toc,
            "chapters": self.__chapters,
            "Chapter": text.Chapter,
            "SeparatorLine": text.SeparatorLine,
            "Para": text.Para,
            "Text": text.Text,
        }
        return data


def _copy_tree_to_zip(zip_out, base_dir):
    dirs = [[]]
    while len(dirs) > 0:
        current_path_list = dirs[0]
        del dirs[0]
        path = os.path.join(base_dir, *current_path_list)
        print("Tree Copy {0}".format(path))
        for name in os.listdir(path):
            next_path_list = list(current_path_list)
            next_path_list.append(name)
            filename = os.path.join(path, name)
            print("   - {0}".format(filename))
            if os.path.isdir(filename):
                dirs.append(next_path_list)
                _add_empty_dir_to_zip("/".join(next_path_list), zip_out)
            elif os.path.isfile(filename):
                zip_out.write(filename, "/".join(next_path_list), zipfile.ZIP_DEFLATED)


def _template_tree_to_zip(zip_out, base_dir, data):
    engine = _create_template_engine()
    dirs = [[]]
    while len(dirs) > 0:
        current_path_list = dirs[0]
        del dirs[0]
        path = os.path.join(base_dir, *current_path_list)
        print("Template tree search: {0}".format(path))
        for name in os.listdir(path):
            next_path_list = list(current_path_list)
            next_path_list.append(name)
            filename = os.path.join(path, name)
            print("   - {0}".format(filename))
            if os.path.isdir(filename):
                dirs.append(next_path_list)
                _add_empty_dir_to_zip("/".join(next_path_list), zip_out)
            elif os.path.isfile(filename):
                _add_data_to_zip("/".join(next_path_list), zip_out, _template_file(engine, filename, data))


def _template_file(engine, filename, data):
    print("Rendering template {0}".format(filename))
    ret = engine.render(filename, data)
    if os.path.isfile(filename + ".cache"):
        os.unlink(filename + ".cache")
    return ret


def _create_template_engine():
    properties = {}
    from .template import tenjin
    from tenjin.helpers import *
    return tenjin.Engine(**properties)


def _add_data_to_zip(file_name, zip_out, data):
    print("  adding data to zip file {0}".format(file_name))
    assert isinstance(zip_out, zipfile.ZipFile)
    info = zipfile.ZipInfo()
    info.filename = file_name
    if len(data) == 0:
        info.compress_type = zipfile.ZIP_STORED
    else:
        info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.create_version = 30
    # info.external_attr = 1106051088
    info.internal_attr = 0
    zip_out.writestr(info, data)


def _add_empty_dir_to_zip(dir_name, zip_out):
    print("  adding empty directory to zip {0}".format(dir_name))
    assert isinstance(zip_out, zipfile.ZipFile)
    info = zipfile.ZipInfo()
    info.filename = dir_name + "/"
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.create_version = 30
    info.external_attr = 1106051088
    info.internal_attr = 0
    zip_out.writestr(info, "")
