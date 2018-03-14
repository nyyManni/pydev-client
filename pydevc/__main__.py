#  Copyright (C) 2017 - 2018 Henrik Nyman <henrikjohannesnyman@gmail.com>
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Main entry point to pydevc. """

import logging
import sys

from .cmdargs import parse_options
from .repl import run_repl


def main():
    """Set up logging and start the repl."""

    options = parse_options(sys.argv[1:])

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter('s%(asctime)s %(levelname)s %(name)s %(message)s')

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    if options.debug:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)

    root.addHandler(console)

    run_repl(options)


if __name__ == '__main__':
    main()
