"""The higgstables command line interface."""
import argparse
import logging
import sys
from pathlib import Path

import higgstables

from ..config import ConfigFromArgs
from ..handle_root_files import DfFromFiles, TablesFromFiles


def prepare_cli_logging(parser):
    parser.add_argument(
        "--debug",
        help="Debugging level logging.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "--verbose",
        help="Verbose logging.",
        action="store_const",
        dest="loglevel",
        const=logging.INFO,
    )


def set_cli_logging(args):
    FORMAT = "[%(levelname)s:%(name)s] %(message)s"
    logging.basicConfig(format=FORMAT, level=args.loglevel)

    # Additionally log to a logfile at the same level.
    file_handler = logging.FileHandler(args.data_dir / "higgstables.log")
    file_handler.setFormatter(fmt=logging.Formatter(fmt=FORMAT))
    logging.getLogger().addHandler(file_handler)  # Added to the root logger.

    # Do some first logging.
    logger = logging.getLogger(__name__)
    logger.warning(higgstables._version_info)
    logger.warning(f"Rootfiles taken from {args.data_source.absolute()}.")
    logger.debug(f"Arguments as interpreted by the parser: {args=}.")
    logger.debug(f"Python executable used: {sys.executable}.")


def data_to_dir(data_dir):
    """Ensures that the procided data destination is valid."""
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


def main(TablesFromFiles=TablesFromFiles):
    parser = argparse.ArgumentParser(
        description=higgstables.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version", action="version", version=higgstables._version_info
    )
    parser.add_argument(
        "data_source",
        type=Path,
        help="Rootfile with variables from simulated events, or folder thereof.",
    )
    parser.add_argument(
        "-d",
        "--data_dir",
        type=data_to_dir,
        help="Folder to store tables into.",
        default="data",
    )
    parser.add_argument(
        "--config",
        type=str,
        help=(
            "Path to a local configuration file. "
            f"Explicitely set it to `{ConfigFromArgs._default_config_tag}` "
            "to use the default configuration file."
        ),
        default=ConfigFromArgs._default_config_cli,
    )
    parser.add_argument(
        "--no_cs",
        dest="no_cs",
        action="store_true",
        help="Toggle to not build the cross sections column.",
    )
    prepare_cli_logging(parser)
    args = parser.parse_args()

    set_cli_logging(args)
    config = ConfigFromArgs(args).get_config()
    TablesFromFiles(args.data_source, args.data_dir, config)


def make_selected_event_dfs_instead_of_count_tables():
    main(TablesFromFiles=DfFromFiles)


if __name__ == "__main__":
    main()
