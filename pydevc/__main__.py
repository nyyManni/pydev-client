
import logging
import sys

from .cmdargs import parse_options
from .repl import run_repl


def main():
    """Main entry point to pydevc."""

    # readline_test()
    # sys.exit()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter('s%(asctime)s %(levelname)s %(name)s %(message)s')

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    root.addHandler(console)

    options = parse_options(sys.argv[1:])
    run_repl(options)


def readline_test():
    import select
    import pipes
    import threading

    p = pipes.Template()

    _quit = False

    def f():
        nonlocal _quit
        import time
        time.sleep(10)
        _quit = True

    threading.Thread(target=f).start()

    while not _quit:
        read, _write, _error = select.select([sys.stdin], [], [], 0.1)

        if read:
            print(sys.stdin.readline())
        else:
            print('nothing to read...')
    print('out')

    print(read)
    if read:
        print('reading already')
        print(sys.stdin.readline())


if __name__ == '__main__':
    main()
