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
"""Command line argument parser for pydevc"""

import argparse


def parse_options(argv):
    """Parse command line arguments and return them as namespace."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-s', '--server',
        action='store',
        help='hostname or ip address of the host running pydevd'
    )
    parser.add_argument(
        '-p', '--port',
        action='store',
        type=int,
        help='port number of pydevd'
    )
    parser.add_argument(
        '-f', '--file',
        action='store',
        help='filename of the main script'
    )
    parser.add_argument(
        '--autostart',
        action='store_true',
        help='if true, the script will start automatically when connection has '
        'been made.'
    )
    parser.add_argument(
        '--break-at-start',
        action='store_true',
        help='if true, the script will suspend at first line of the file'
    )

    parser.add_argument(
        '--sync',
        action='store_true'
    )

    return parser.parse_args(argv)
