"""Module for command line interface."""

import argparse
import logging
import sys
from typing import NoReturn, Optional, Sequence

from .core import __issues__, __summary__, __version__
from .dumper import dump

LOG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
logger = logging.getLogger(__name__)


class HelpArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        """Handle error from argparse.ArgumentParser."""
        self.print_help(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def get_parser() -> argparse.ArgumentParser:
    """Prepare ArgumentParser."""
    parser = HelpArgumentParser(
        prog="discord-dumper",
        description=__summary__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s, version {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose mode, enable INFO and DEBUG messages.",
        action="store_true",
        required=False,
    )
    parser.add_argument("path")
    parser.add_argument(
        "--no-pretty",
        dest="pretty",
        action="store_false",
        help="Indent and add space in json file.",
    )
    parser.add_argument(
        "--no-images",
        dest="images",
        action="store_false",
        help="Don't save images.",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch images for best quality.",
    )
    parser.set_defaults(images=True, pretty=True)
    return parser


def setup_logging(verbose: Optional[bool] = None) -> None:
    """Do setup logging."""
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    )


def entrypoint(argv: Optional[Sequence[str]] = None) -> None:
    """Entrypoint for command line interface."""
    try:
        parser = get_parser()
        args = parser.parse_args(argv)
        setup_logging(args.verbose)
        dump(
            args.path,
            pretty=args.pretty,
            images=args.images,
            fetch=args.fetch,
        )
    except Exception as err:  # NoQA: BLE001
        logger.critical("Unexpected error", exc_info=err)
        logger.critical("Please, report this error to %s.", __issues__)
        sys.exit(1)
