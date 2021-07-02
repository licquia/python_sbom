"""Console script for python_sbom."""
import sys
import click

from python_sbom.api import generate


@click.command()
@click.argument('project_name')
def main(project_name):
    """Console script for python_sbom."""

    try:
        sys.stdout.write(generate(project_name))
        return 0
    except ValueError as e:
        sys.stderr.write(f'error: could not generate: {str(e)}\n')
        return 1


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
