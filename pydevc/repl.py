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
"""Implements the main command line interface. """

import cmd
import functools
import inspect
import re
import sys
import threading
import time
import select

from .client import PyDevClient, State


CONSOLE_PROMPT = '(pydevc) '


class ArgumentError(TypeError):
    """Raised when incorrect argument given to splitter."""


def split_args(*types, split_char=' '):
    """Decorator for splitting and typeconverting user input for the function.
    """
    def _decorator(f):

        @functools.wraps(f)
        def _wrapper(self, arg):

            s = inspect.signature(f)
            defaults = [p.default for p in s.parameters.values()][1:]

            if not arg:
                args = []
            elif split_char:
                args = arg.split(split_char)
            else:
                args = [arg]

            try:
                for i, val in enumerate(args):
                    defaults[i] = val
            except IndexError:
                raise ArgumentError('Too many arguments provided')

            if inspect.Parameter.empty in defaults:
                raise ArgumentError('Wrong number of arguments')
            args = defaults

            # Support split_args([type]) -notation for specifying variable
            # number of typed arguments.
            nonlocal types
            _types = types
            if _types and isinstance(_types[0], list):
                _types = [_types[0][0]] * len(args)

            if len(_types) != len(args):
                raise ArgumentError('Wrong number of arguments')
            try:
                typed_args = [t(s) if s is not None else None
                              for t, s in zip(_types, args)]
            except TypeError as e:
                raise ArgumentError(str(e)) from None
            return f(self, *typed_args)
        return _wrapper
    return _decorator


def parse_breakpoint(s):
    """Parse breakpoint from user input.
    Examples:
    - file.py:32
    - /path/to/file.py:15, n = 32
    - file.py:func_name
    """

    match = re.compile(r'^([^:]+):(?:(\d+)|([^,]+))(?:, ?(.*))?$').match(s)
    filename = match.group(1)
    lineno = int(match.group(2) or 'None')
    scope = match.group(3) or 'None'
    expression = match.group(4) or 'None'

    return filename, lineno, scope, expression


# pylint: disable=locally-disabled, too-many-public-methods
class DebuggerConsole(cmd.Cmd):
    """REPL console for PyDev debugger."""

    def __init__(self, host, port, stdin=sys.stdin, stdout=sys.stdout,
                 autostart=False, filename=None, break_at_start=False):
        super().__init__(stdin=stdin, stdout=stdout)
        self.session = PyDevClient(host, port)

        self.session.callbacks = {
            PyDevClient.EVENT_THREAD_SUSPEND: self.on_suspend,
            PyDevClient.EVENT_SERVER_EXIT: self.on_exit,
            PyDevClient.EVENT_SET_BREAKPOINT: self.on_breakpoint_create,
            PyDevClient.EVENT_REMOVE_BREAKPOINT: self.on_breakpoint_remove,
        }
        self.prompt = CONSOLE_PROMPT

        self._prompt_lock = threading.Lock()
        self._prompt_sleeping = False

        self._quit = False
        self.filename = filename
        self.break_at_start = break_at_start
        self.autostart = autostart

        self.opt_list_context = 7

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        """

        self.preloop()
        if intro is not None:
            self.intro = intro
        if self.intro:
            self.stdout.write(str(self.intro) + "\n")

        self._quit = False
        while not self._quit:

            self.stdout.write(self.prompt)
            self.stdout.flush()
            while not self._quit:

                # Non-blocking user input with select
                read, _write, _error = select.select([sys.stdin], [], [], 0.1)

                if read:
                    line = sys.stdin.readline()
                    if not line:
                        line = 'EOF'
                    else:
                        line = line.rstrip('\r\n')

                    line = self.precmd(line)
                    self._quit = self.onecmd(line)
                    self._quit = self.postcmd(self._quit, line)
                    break

        self.postloop()

    def postloop(self):
        self.stdout.write('Leaving\npydevc: That\'s all, folks...\n')
        self.stdout.flush()

    def __prompt_sleep(self, t):
        """Give the session t seconds to output async event.
        If the event arrives during the wait time, no prompt will be printed
        by the event.
        """
        try:
            with self._prompt_lock:
                self._prompt_sleeping = True
            time.sleep(t)
        finally:
            with self._prompt_lock:
                self._prompt_sleeping = False

    def on_suspend(self, filename, line_no, function):
        """A thread stopped at a breakpoint.
        """
        msg = '({}:{}): {}\n'.format(filename, line_no, function)

        # Asynchronous operation, print a new prompt after the message.
        with self._prompt_lock:
            if self._prompt_sleeping:
                self.stdout.write(msg)
            else:
                self.stdout.write('\n{}{}'.format(msg, self.prompt))

    def on_exit(self):
        """The server has finished execution, the client is free to exit.
        """
        # The callback is called from another thread, sys.exit doesn't work here
        self._quit = True

    def on_breakpoint_create(self, breakpoint):
        """Breakpoint was created.
        """
        if not breakpoint['temporary']:
            self.stdout.write('Breakpoint {id} set at line {line} of file'
                              ' {filename}\n'.format(**breakpoint))

    def on_breakpoint_remove(self, breakpoint):
        """Breakpoint was remove.
        """
        if not breakpoint['temporary']:
            self.stdout.write('Deleted breakpoint {id}\n'.format(**breakpoint))

    def onecmd(self, line):
        try:
            return super().onecmd(line)
        except RuntimeError as e:
            self.stdout.write(str(e) + '\n')

    def preloop(self):
        """Connect to debugger process and initialize the session.
        """
        self.session.connect()
        self.session.start()

        server_version = self.session.init('1.0')

        if self.autostart:
            if self.filename and self.break_at_start:
                self.session.start_debugger(filename=self.filename)

        self.stdout.write('PyDev v{}\n'.format(server_version))

    @split_args()
    def do_start(self):
        """Start the debugger.

        Usage:
            start
        """
        self.session.start_debugger()
        self.__prompt_sleep(0.1)

    @split_args(parse_breakpoint)
    def do_break(self, breakpoint):
        """Add a breakpoint to the debugged program.

        Usage:
            break <filename>:(<lineno>|<scope>)[, <expression>]

            filename:   The name of the file where to insert breakpoint. Either
                        an absolute path or relative to debuggee's work
                        directory. Filename is a required argument.
            lineno:     The line number of the breakpoint. Either lineno or
                        scope must be given.
            scope:      A scope qualifier (e.g. a function name) where to add
                        the breakpoint. Either lineno or scope must be given.
            expression: Expression that will be evaluated when the breakpoint is
                        hit. Only when the expression returns True the program
                        will stop at the breakpoint.
        """
        filename, lineno, scope, expression = breakpoint
        self.session.add_breakpoint(filename=filename, line_number=lineno,
                                    function=scope, condition=None,
                                    expression=expression)
    do_b = do_break

    @split_args([int])
    def do_enable(self, *ids):
        """Enable breakpoint(s)

        Usage:
            enable <id1> <id2>...<idN>

            id:   The id of the breakpoint to enable.
        """

    do_e = do_enable

    @split_args([int])
    def do_disable(self, *ids):
        """Disable breakpoint(s)

        Usage:
            disable <id1> <id2>...<idN>

            id:   The id of the breakpoint to disable.
        """

    do_d = do_disable

    @split_args([int])
    def do_delete(self, ids):
        """Delete breakpoint(s)

        Usage:
            delete <id1> <id2>...<idN>

            id:   The id of the breakpoint to delete.
        """
        for breakpoint_id in ids:
            self.session.remove_breakpoint(breakpoint_id)

    @split_args(str)
    def do_step(self, thread=None):
        """Step through an event.

        Behaves similar to `next`, except it will step "into" functions.

        Usage:
            step [thread name or id]

            thread: Name or id of the thread to progress. Defaults to currently
                    active thread.
        """
        self.session.step_into(thread)
        self.__prompt_sleep(0.1)

    do_s = do_step

    @split_args(str)
    def do_next(self, thread=None):
        """Step over a line of code.

        Usage:
            next [thread name or id]

            thread: Name or id of the thread to progress. Defaults to currently
                    active thread.
        """
        self.session.step_over(thread)
        self.__prompt_sleep(0.1)

    do_n = do_next

    @split_args(str)
    def do_return(self, thread=None):
        """Continue execution until the end of the current function.

        Usage:
            return [thread name or id]

            thread: Name or id of the thread to progress. Defaults to currently
                    active thread.
        """
        self.session.step_return(thread)
        self.__prompt_sleep(0.1)

    do_r = do_return

    @split_args(str)
    def do_continue(self, thread=None):
        """Continue execution from a stopped state.

        The execution will continue until a breakpoint is hit or stop command
        is given.

        Usage:
            continue [thread name or id]

            thread: Name or id of the thread to progress. Defaults to currently
                    active thread.
        """

        self.session.continue_thread(thread)
        self.__prompt_sleep(0.1)

    do_c = do_continue

    @split_args(int)
    def do_jump(self, lineno):
        """Jump to a line on current file.

        Usage:
            jump <lineno>

            lineno: Line number to jump to.

        The debugger has to be in a stopped state to execute this command.
        """

    do_j = do_jump

    @split_args()
    def do_up(self):
        """Go up a frame.

        Go up one stack frame, for example return from a function.

        Usage:
            up

        The debugger has to be in a stopped state to go up a frame.
        """

    @split_args()
    def do_down(self):
        """Go down a frame.

        Go down one stack frame, for example go back to the called function
        after an exception has been caught.

        Usage:
            up

        The debugger has to be in a stopped state to go up a frame.
        """

    @split_args(str)
    def do_exec(self, expression):
        """Execute expression in debuggee's context.

        Execute will modify the state of the debugged script and can possibly
        deadlock the debugger.

        Usage:
            exec <expression>
        """

    def do_eval(self, expression):
        """Evaluate expression in debuggee's context.

        Eval command does not alter the state of the debuggee, so for example
        assignments are not allowed.

        Usage:
            eval <expression>
        """
        value = self.session.evaluate(expression)
        self.stdout.write(value + '\n')

    do_e = do_eval

    @split_args(str)
    def do_help(self, command=None):  # pylint: disable=locally-disabled, arguments-differ
        """Print list of commands.

        Usage:
            help
        """
        if command:
            doc = getattr(self, 'do_{}'.format(command)).__doc__
            if doc:
                self.stdout.write('{}\n'.format(inspect.cleandoc(doc)))
            else:
                self.stdout.write('Not documented\n')
            self.stdout.write('\n')
            return

        commands = []
        for attr in dir(self):
            if attr.startswith('do_'):
                m = getattr(self, attr)
                if m not in commands and attr != 'do_EOF':
                    commands.append(m)
        helps = []
        for c in sorted(commands, key=lambda f: f.__name__):
            command = c.__name__.replace('do_', '')
            doc = (c.__doc__ or '').split('\n')[0]

            helps.append((command, doc))

        # Lenght of the longest command defined.
        l = len(max(helps, key=lambda x: len(x[0]))[0])

        self.stdout.write('\nCommands (use help <command> for more info):\n\n')
        for c, h in helps:
            self.stdout.write(('{:>%d} -- {}\n' % l).format(c, h))
        self.stdout.write('\n')

    @split_args(str)
    def do_list(self, thread=None):
        """List the contents of the source file.

        Listing is done at the position of the given thread or active thread.

        Usage:
            list [thread name or id]
        """
        filename, line_number, _function = self.session.get_position(thread)

        with open(filename, 'rt', encoding='utf-8') as f:
            lines = f.readlines()

        range_begin = max(0, line_number - self.opt_list_context)
        range_end = line_number + self.opt_list_context
        for index, line in enumerate(lines[range_begin:range_end]):
            _lineno = index + 1

            linum_width = len(str(range_end + 1))
            fmt = ' {number:>{w}}  {current} {line}'.format(
                number=_lineno,
                w=linum_width,
                current='->' if _lineno == line_number else '  ',
                line=line
            )

            self.stdout.write(fmt)

    do_l = do_list

    @split_args()
    def do_exit(self):
        """Exit the debugging session.

        Usage:
            exit
        """
        self.session.kill_debugger()
        return True

    do_quit = do_exit
    do_EOF = do_exit

    @split_args(str, str)
    def do_set(self, option, value):
        """Set debugger options.

        Usage:
            set <option> <value>
        """

        attr = 'opt_{}'.format(option.lower().replace('-', '_'))
        if hasattr(self, attr):
            setattr(self, attr, int(value))
        else:
            raise RuntimeError('Unkwnown option: {}'.format(option))

    @split_args(int)
    def do_thread(self, thread_id=None):
        """List current threads or set active thread.

        Usage:
            thread [id]
        """
        # TODO: Check if the order stays the same between calls
        for index, thread in enumerate(self.session.threads.values()):
            if index == thread_id:
                self.session._active_thread = thread['id']
            else:
                fmt = '  {active} {id:<3} | {name:<15} | {running}\n'.format(
                    active='*' if thread['id'] == self.session._active_thread else ' ',
                    id=index,
                    name=thread['name'],
                    running=('SUSPENDED' if thread['state'] == State.SUSPENDED else 'RUNNING')
                )
                self.stdout.write(fmt)

    do_t = do_thread

    def emptyline(self):
        pass


def run_repl(options):
    """Start the REPL.
    """

    c = DebuggerConsole(host=options.server, port=options.port,
                        autostart=options.autostart,
                        filename=options.file,
                        break_at_start=options.break_at_start)
    c.cmdloop()
