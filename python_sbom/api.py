"""Main module."""


import io
import spdx.writers.tagvalue

from python_sbom import private


def generate(toplevel_package_name):
    """Given the toplevel package name, return a string containing a
    SPDX software bill of materials."""

    module_info = private.get_module_info(toplevel_package_name)
    module_doc = private.spdx_document(toplevel_package_name,
                                       module_info[toplevel_package_name])
    pkg = private.spdx_from_module(toplevel_package_name,
                                   module_info[toplevel_package_name])
    module_doc.add_package(pkg)

    for (dep, rel) in private.spdx_from_module_deps(toplevel_package_name,
                                                    module_info):
        module_doc.add_package(dep)
        module_doc.add_relationships(rel)

    with io.StringIO() as outbuf:
        spdx.writers.tagvalue.write_document(module_doc, outbuf)
        outstr = outbuf.getvalue()
    return outstr
