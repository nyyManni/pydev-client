
import logging
import sys

from .cmdargs import parse_options
from .repl import run_repl


def main():
    """Main entry point to pydevc."""

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter('s%(asctime)s %(levelname)s %(name)s %(message)s')

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    root.addHandler(console)

    options = parse_options(sys.argv[1:])
    run_repl(options)


if __name__ == '__main__':
    main()
