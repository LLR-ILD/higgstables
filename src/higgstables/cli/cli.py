"""The higgstables command line interface."""
import argparse
import logging
from pathlib import Path

import higgstables

from ..config.load_config import ConfigFromArgs
from ..make_data import save_data


def prepare_cli_logging(parser):
    parser.add_argument(
        "--debug",
        help="Debugging level logging",
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
    logger = logging.getLogger(__name__)

    logger.debug(higgstables._version_info)
    logger.debug(f"Arguments as interpreted by the parser: {args=}.")


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
    parser.add_argument("data_source", help=rootfile_help)
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
    prepare_cli_logging(parser)
    args = parser.parse_args()

    set_cli_logging(args)
    config = ConfigFromArgs(args).get_config()
    print(config)
    save_data(args.data_source, args.data_dir)


if __name__ == "__main__":
    main()
