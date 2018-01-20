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
