#!/usr/bin/env python

"""Run higgstables without installing it.

You should (pip) install higgstables into your python environment.
If for some reason you refuse to do that,
the CLI can be accessed through this script.
Of course this still means that you need to have all dependencies installed
in the python environment that you are using.
"""


def get_higgstables_cli():
    import sys
    from pathlib import Path

    module_path = Path(__file__).absolute().parents[1] / "src"
    sys.path.insert(0, str(module_path))

    try:
        from higgstables.cli import cli
    except ModuleNotFoundError as e:
        print("Prepending to path was not successful...")
        print(f"{sys.path=}")
        raise e
    return cli


if __name__ == "__main__":
    cli = get_higgstables_cli()
    cli()
