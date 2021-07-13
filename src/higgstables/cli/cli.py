"""The higgstables command line interface."""
import argparse
from pathlib import Path

import higgstables

from ..make_data import save_data

rootfile_help = "The basic file with simulated events."


def data_to_dir(data_dir):
    data_dir = Path(data_dir)
    if data_dir.is_dir():
        is_empty = not any(data_dir.iterdir())
        if is_empty:
            return data_dir
        else:
            raise FileExistsError(
                f"{data_dir.absolute()} already exists and is non-empty. "
                "Please provide a new path for data output through `-d new_dir`."
            )
    data_dir.mkdir(parents=True)
    return data_dir


def main():
    parser = argparse.ArgumentParser(
        description=higgstables.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version", action="version", version=higgstables._version_info
    )
    parser.add_argument("rootfile", help=rootfile_help)
    parser.add_argument(
        "-d",
        "--data_dir",
        type=data_to_dir,
        help="Folder to store tables into.",
        default="data",
    )
    args = parser.parse_args()
    save_data(args.rootfile, args.data_dir)


if __name__ == "__main__":
    main()
