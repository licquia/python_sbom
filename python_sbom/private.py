"""Internals for python_sbom.  This code does not have a stable API; use the
code in python_sbom.api (or just python_sbom) instead."""


import sys
import os
import re
import json
import urllib.request
import urllib.error

import spdx.document
import spdx.version
import spdx.creationinfo
import spdx.review
import spdx.package
import spdx.file
import spdx.checksum
import spdx.utils
import spdx.relationship

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata


def get_module_name_from_dep(dep):
    name_chars = re.compile(r'[\[<>= ]')
    bare_dep = dep.split(';')[0].strip()
    return name_chars.split(bare_dep, 1)[0]


def detect_license(license_identifier):
    # The following uses internal information from spdx-tools, which
    # should be replaced with explicit support for the license list.
    license_json_path = os.path.dirname(spdx.document.__file__)
    with open(os.path.join(license_json_path, 'licenses.json')) as f:
        licenses = json.load(f)

    identifiers = [x['licenseId'] for x in licenses['licenses']]
    if license_identifier in identifiers:
        return license_identifier
    else:
        return 'NOASSERTION'


def get_module_info_from_pypi(module_name, module_cache):
    url = f'https://pypi.org/pypi/{module_name}/json'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            raw_data = resp.read()
        data = raw_data.decode('utf-8')
        parsed = json.loads(data)
    except urllib.error.HTTPError:
        parsed = None

    if parsed is not None:
        module_info = module_cache[module_name]
        release_info = parsed['releases'][module_info['version']]
        sdist_info = [x for x in release_info
                      if x['packagetype'] == 'sdist'][0]
        for field in ['url', 'digests', 'size', 'filename']:
            if field not in module_info:
                module_info[field] = sdist_info[field]


def get_module_info(module_name, module_cache={}):
    if module_name in module_cache:
        return module_cache
    module_cache[module_name] = {}
    try:
        dist = importlib_metadata.distribution(module_name)
    except importlib_metadata.PackageNotFoundError:
        dist = None
    if dist is not None:
        module_cache[module_name]['version'] = dist.version
        module_cache[module_name]['license'] = \
            detect_license(dist.metadata['License'])
        module_cache[module_name]['author'] = {
            'name': dist.metadata['Author'],
            'email': dist.metadata['Author-email']
        }
        get_module_info_from_pypi(module_name, module_cache)
        if dist.requires is None:
            dep_names = []
        else:
            dep_names = [get_module_name_from_dep(x)
                         for x in dist.requires]
        for dep_name in dep_names:
            if dep_name not in module_cache:
                module_cache = get_module_info(dep_name, module_cache)
        module_cache[module_name]['requires'] = dep_names
    return module_cache


def spdx_document(toplevel_module_name, module_info):
    d = spdx.document.Document()
    d.namespace = f'http://spdx.org/spdxpackages/' \
        f'{toplevel_module_name}-{module_info["version"]}'
    d.spdx_id = 'SPDXRef-DOCUMENT'
    d.name = f'{toplevel_module_name}-{module_info["version"]}'
    d.version = spdx.version.Version(2, 2)
    d.data_license = spdx.document.License.from_identifier('CC0-1.0')
    d.creation_info.add_creator(spdx.creationinfo.Person(
        module_info['author']['name'], module_info['author']['email']
    ))
    d.creation_info.set_created_now()

    return d


def spdx_from_module(module_name, module_info):
    if 'version' not in module_info or 'seen' in module_info:
        return None
    p = spdx.package.Package()
    p.spdx_id = f'SPDXREF-Package-{module_name}'
    p.name = module_name
    p.version = module_info['version']
    if module_info['license'] == 'NOASSERTION':
        p.license_declared = spdx.utils.NoAssert()
    else:
        p.license_declared = \
            spdx.document.License.from_identifier(module_info['license'])
    p.conc_lics = p.license_declared
    p.licenses_from_files = [spdx.utils.NoAssert()]
    p.cr_text = spdx.utils.NoAssert()
    if 'url' in module_info:
        p.download_location = module_info['url']
    else:
        p.download_location = spdx.utils.NoAssert()
    p.files_analyzed = False

    module_info['seen'] = True
    return p


def spdx_from_module_deps(module_name, module_cache):
    module_info = module_cache[module_name]
    for dep in module_info['requires']:
        pkg = spdx_from_module(dep, module_cache[dep])
        if pkg is not None:
            rel_desc = f'SPDXREF-Package-{module_name} DEPENDS_ON SPDXRef-Package-{dep}'
            rel = spdx.relationship.Relationship(rel_desc)
            yield (pkg, rel)
            for (subpkg, subrel) in spdx_from_module_deps(dep, module_cache):
                if subpkg is not None:
                    yield (subpkg, subrel)