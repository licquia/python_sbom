# python_sbom: generate a software bill of materials

Generate a software bill of materials for your Python project in SPDX.
No hassle, no fancy features, just get the job done.

## Installation

At the moment, python_sbom is not in PyPI, which means you'll have to
install it via pip manually.  Additionally, we use a prerelease
version of spdx-tools, which also requires manual installation.  In
the future, we hope to get both problems fixed.

Until then, use pip to get what you need:

    pip install git+https://github.com/spdx/tools-python.git#egg=spdx-tools
    pip install git+https://github.com/licquia/python_sbom.git#egg=python_sbom

Do this in your build environment, using your build tool of choice
and/or your virtualenv of choice.  If you're using an advanced build
tool, you could add those two repositories as development
dependencies, to guarantee they're installed every time.

Long-term, we're hoping you can just run this to install:

    pip install python_sbom

## Simple Usage

Then, simply run the tool:

    python_sbom [name of your project] > sbom.spdx

## API

If you'd prefer, you can generate your SBOM in Python, and do other
interesting things to it.  To do this, follow the installation
instructions above, then do something like this:

    import python_sbom
    spdx_output = python_sbom.generate(my_project_name)

## Limitations

This being an early version of the tool, there are a few details yet
to be handled the best way:

* We don't auto-detect your project name from your source directory.
* Also, if you're running this on a build from a source directory
  (such as in a CI system), we can't pick up on your project's
  information unless the project is itself installed into your
  execution environment.  If you run an install step, this likely
  won't be a problem, but if not, you'll want to install the project
  into your environment in "editable mode", which makes the metadata
  for your project available in the environment itself.  Different
  build tools support doing this in different ways.

## License

* Free software: Apache Software License 2.0

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
