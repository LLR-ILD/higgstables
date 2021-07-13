"""The higgstables command line interface."""
from pathlib import Path

import higgstables

from ..make_data import save_data

rootfile_help = "The basic file with simulated events."


def main():
    try:
        default_csv_dir = Path(__file__).parents[2] / "data"
    except IndexError:
        # This script might not be that far down in the file hierarchy.
        default_csv_dir = Path("data")
    import argparse

    parser = argparse.ArgumentParser(
        description=higgstables.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version", action="version", version=higgstables._version_info
    )
    parser.add_argument("rootfile", help=rootfile_help)
    parser.add_argument(
        "--data_dir",
        type=str,
        help="Folder to store data into.",
        default=default_csv_dir,
    )
    args = parser.parse_args()
    save_data(args.rootfile, args.data_dir)


if __name__ == "__main__":
    main()
