"""Console script for python_sbom."""
import sys
import click

from python_sbom.api import generate


@click.command()
@click.argument('project_name')
def main(project_name):
    """Console script for python_sbom."""

    sys.stdout.write(generate(project_name))
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
