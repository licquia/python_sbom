"""Internals for python_sbom.  This code does not have a stable API; use the
code in python_sbom.api (or just python_sbom) instead."""

import os
import re
import json
import hashlib
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


def get_tool_version():
    import python_sbom  # noqa
    return python_sbom.__version__


def get_checksum_from_module_info(module_info):
    result = hashlib.sha1(module_info['name'].encode())
    checksum = spdx.checksum.Algorithm(identifier='SHA1',
                                       value=result.hexdigest())
    # Todo ...
    # when spdx starts the support more algorithm enable below code
    # if 'digests' in module_info:
    #     checksum.identifier = 'SHA256'
    #     checksum.value = module_info['digests']['sha256']

    return checksum


def get_supplier_from_module_info(module_info):
    AuthorAnOrganizationKeywords = [
        "authority", "team", "developers", "services", "foundation", "software"
    ]

    def check_supplier_is_organization(supplier):
        for key in AuthorAnOrganizationKeywords:
            if key in supplier.name.lower():
                return True
        return False

    name = module_info.get('author', {}).get('name')
    email = module_info.get('author', {}).get('email')

    supplier = spdx.creationinfo.Person(name, email)
    if check_supplier_is_organization(supplier):
        supplier = spdx.creationinfo.Organization(name, email)
    return supplier


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
        if module_cache[module_name].get('author', {}).get('name', None) is None:
            module_cache[module_name]['author'] = {
                'name': parsed['info']['maintainer'],
                'email': parsed['info']['maintainer_email']
            }

        if 'package_url' not in module_cache[module_name]:
            module_cache[module_name]['package_url'] = \
                parsed['info']['package_url']

        if 'release_url' not in module_cache[module_name]:
            module_cache[module_name]['release_url'] = \
                "{0}/{1}".format(module_cache[module_name]['package_url'],
                                 module_cache[module_name]['version'])

        if 'project_url' not in module_cache[module_name]:
            module_cache[module_name]['project_url'] = \
                parsed['info']['project_url']

        if 'home_page' not in module_cache[module_name]:
            module_cache[module_name]['home_page'] = \
                parsed['info']['home_page']
            if len(module_cache[module_name]['home_page']) == 0:
                module_cache[module_name]['home_page'] = \
                    module_cache[module_name]['release_url']

        module_info = module_cache[module_name]
        release_info = parsed['releases'][module_info['version']]
        sdist = [x for x in release_info if x['packagetype'] == 'sdist']
        sdist_info = sdist[0] if len(sdist) > 0 else {}
        for field in ['url', 'digests', 'size', 'filename']:
            if field not in module_info:
                module_info[field] = sdist_info.get(field)


def get_module_info(module_name, module_cache={}):
    if module_name in module_cache:
        return module_cache
    module_cache[module_name] = {}
    try:
        dist = importlib_metadata.distribution(module_name)
    except importlib_metadata.PackageNotFoundError:
        dist = None
    if dist is not None:
        module_cache[module_name]['name'] = module_name
        module_cache[module_name]['version'] = dist.version
        module_cache[module_name]['license'] = \
            detect_license(dist.metadata['License'])
        module_cache[module_name]['author'] = {
            'name': dist.metadata['Author'],
            'email': dist.metadata['Author-email']
        }
        module_cache[module_name]['home_page'] = dist.metadata['Home-page']
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
        f'{toplevel_module_name}-{module_info.get("version")}'
    d.spdx_id = 'SPDXRef-DOCUMENT'
    d.name = f'{toplevel_module_name}-{module_info.get("version")}'
    d.version = spdx.version.Version(2, 2)
    d.data_license = spdx.document.License.from_identifier('CC0-1.0')
    d.creation_info.add_creator(spdx.creationinfo.Tool(
        'python_sbom ' + get_tool_version()
    ))
    d.creation_info.set_created_now()

    return d


def spdx_from_module(module_name, module_info):
    if 'version' not in module_info or 'seen' in module_info:
        return None
    p = spdx.package.Package()
    p.spdx_id = f'SPDXRef-Package-{module_name}'
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

    if module_info.get('url', None) is not None:
        p.download_location = module_info['url']
    elif module_info.get('home_page', None) is not None:
        p.download_location = module_info['home_page']
    else:
        p.download_location = spdx.utils.NoAssert()

    p.files_analyzed = False

    p.supplier = get_supplier_from_module_info(module_info)

    module_info['seen'] = True

    p.homepage = module_info['home_page']

    p.check_sum = get_checksum_from_module_info(module_info)

    return p


def spdx_from_module_deps(module_name, module_cache):
    module_info = module_cache[module_name]
    for dep in module_info['requires']:
        pkg = spdx_from_module(dep, module_cache[dep])
        if pkg is not None:
            rel_desc = f'SPDXRef-Package-{module_name} DEPENDS_ON SPDXRef-Package-{dep}'
            rel = spdx.relationship.Relationship(rel_desc)
            yield (pkg, rel)
            for (subpkg, subrel) in spdx_from_module_deps(dep, module_cache):
                if subpkg is not None:
                    yield (subpkg, subrel)
