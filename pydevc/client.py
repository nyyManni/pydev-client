
import time
import os
import socket
import threading
import urllib.parse
import logging
import xml.etree.ElementTree as ET
import functools
import html
import re
import enum
import signal

from _pydevd_bundle.pydevd_comm import (
    CMD_RUN,
    CMD_VERSION,
    CMD_SET_BREAK,
    CMD_REMOVE_BREAK,
    CMD_THREAD_CREATE,
    CMD_THREAD_SUSPEND,
    CMD_THREAD_KILL,
    CMD_THREAD_RUN,
    CMD_STEP_OVER,
    CMD_STEP_INTO,
    CMD_STEP_RETURN,
    CMD_SMART_STEP_INTO,
    CMD_LIST_THREADS,
    CMD_EVALUATE_EXPRESSION
)


class State(enum.Enum):
    RUNNING = 0
    SUSPENDED = 1


MAX_BREAKPOINTS = 1024
PYDEV_INTERNAL_THREADS = [
    'pydevd.Writer',
    'pydevd.CommandThread"',
    'pydevd.Reader'
]

logger = logging.getLogger(__name__)


class PyDevClient(threading.Thread):

    EVENT_THREAD_CREATE = 'thread_create'
    EVENT_THREAD_KILL = 'thread_kill'
    EVENT_THREAD_SUSPEND = 'thread_suspend'
    EVENT_SET_BREAKPOINT = 'breakpoint_set'
    EVENT_REMOVE_BREAKPOINT = 'breakpoint_remove'
    EVENT_SERVER_EXIT = 'server_exit'

    def __init__(self, host, port):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.stopped = False
        self.msg_id = 1
        self.conn = None
        self.pid = None

        self.reply_lock = threading.Lock()
        self.reply_queue = {}

        self.breakpoints = {}

        self.thread_lock = threading.Lock()
        self.threads = {}

        self.callbacks = {}
        self._active_thread = None
        self._active_frames = []

        self.write_lock = threading.Lock()

    def connect(self, timeout=5):
        """Connect to the remote debugger."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((self.host, self.port))
                break
            except socket.error:
                time.sleep(0.1)
                continue
        else:
            raise TimeoutError('Connection timed out')

    def __get_breakpoint_id(self):
        for i in range(MAX_BREAKPOINTS):
            if i not in self.breakpoints:

                # Set a placeholder so that the id gets taken.
                self.breakpoints[i] = None
                return i
        raise RuntimeError('Breakpoint limit ({}) reached'
                           .format(MAX_BREAKPOINTS))

    def __send(self, *args):

        # Even when there are no args, the final separator is required.
        if len(args) < 2:
            args += ('',)

        # Inject message id. Client uses odd ids while server uses even ids.
        _id = self.msg_id
        self.msg_id += 2
        msg = args[:1] + (_id,) + args[1:]

        msg = '\t'.join([str(m) for m in msg]) + '\n'

        logger.debug('>>> ' + msg)
        with self.write_lock:
            self.conn.send(msg.encode('utf-8'))
        return _id

    def __run_callback(self, key, *args):
        if key in self.callbacks:
            self.callbacks[key](*args)

    def __event(self, cmd, msg_id, args):
        if cmd == CMD_THREAD_CREATE:

            # XML seems to always contain just one thread, but prepare for N.
            for thread in ET.fromstring(args[0]):

                thread_id = thread.attrib['id']
                thread_name = thread.attrib['name']

                with self.thread_lock:
                    if self._active_thread is None:
                        self._active_thread = thread_id
                        self.threads[thread_id] = {
                            'id': thread_id,
                            'name': thread_name,
                            'state': State.RUNNING,
                            'file': None,
                            'line': None,
                            'funciotn': None
                        }

                self.__run_callback(PyDevClient.EVENT_THREAD_CREATE,
                                    thread_id, thread_name)

        if cmd == CMD_THREAD_KILL:
            thread_id = args[0]
            try:
                thread_name = self.threads[thread_id]['name']
            except KeyError:
                # Seems that sometimes pydevd does not correctly report about
                # created threads
                logger.debug('Killed nonexistent thread: %s', thread_id)
                # TODO: Maybe callbacks here still?
                return
            with self.thread_lock:
                del self.threads[thread_id]
                if self._active_thread == thread_id:
                    if not self.threads:
                        self._active_thread = None
                    else:
                        # Just pick the first available thread as the active
                        # one.
                        self._active_thread = list(self.threads.keys())[0]
            self.__run_callback(PyDevClient.EVENT_THREAD_CREATE,
                                thread_id, thread_name)

        if cmd == CMD_THREAD_SUSPEND:
            for thread in ET.fromstring(args[0]):
                thread_id = thread.attrib['id']

                self.__delete_if_temporary_breakpoint_hit(thread)

                frame = thread[0]
                self._active_frames = [f.attrib['id'] for f in thread]

                # TODO: Seems that we need to unquote the string twice, figure
                #       out why.
                filename = unquote(unquote(frame.attrib['file']))
                line_no = frame.attrib['line']
                function = unquote(frame.attrib['name'])

                with self.thread_lock:
                    self._active_thread = thread_id

                    if thread_id not in self.threads:
                        self.threads[thread_id] = {}

                    self.threads[thread_id].update(dict(
                        state=State.SUSPENDED,
                        file=filename,
                        line=line_no,
                        function=function
                    ))

                self.__run_callback(PyDevClient.EVENT_THREAD_SUSPEND,
                                    filename, line_no, function)

    def __process(self, message):
        logger.debug('<<< ' + message)
        cmd, msg_id, *args = message.split('\t')
        msg_id = int(msg_id)
        cmd = int(cmd)

        if int(msg_id) % 2 == 1:
            # A reply to a message from us, put it to the queue.
            with self.reply_lock:
                self.reply_queue[msg_id] = args
        else:
            # A spontaneous event.
            self.__event(cmd, msg_id, args)

    def __wait_for_reply(self, msg_id, timeout=5):
        t0 = time.time()

        while time.time() - t0 < timeout:
            with self.reply_lock:
                if msg_id in self.reply_queue:
                    reply = self.reply_queue[msg_id]
                    del self.reply_queue[msg_id]
                    return reply
            time.sleep(0.01)

        raise TimeoutError('No reply from server received')

    def run(self):
        self.stopped = False
        buf = ''
        while not self.stopped:
            d = self.conn.recv(1024).decode('utf-8')
            if not d:
                logger.debug('server closed the socket')
                self.__run_callback(PyDevClient.EVENT_SERVER_EXIT)
                return

            d = buf + d

            # The messages are split by a newline.
            while '\n' in d:
                msg, d = d.split('\n', maxsplit=1)
                self.__process(msg)
            buf = d

    def init(self, version, os_type=('WINDOWS' if os.name == 'nt' else 'UNIX'),
             breakpoint_method='ID'):
        """Initialize debugger.

        Initialize session by specifying version of the client, type of the
        operating system and what kind of breakpoint system the client supports.

        (Because PyCharm does not store id's for its breakpoints, PyDev defaults
        to using line numbers as breakpoint ids. This client is not designed to
        be used with other tools and ids are a better way to keep up with break-
        points, thus we default to ids. To use line numbers as the ids set
        breakpoint_method='LINE')
        """
        msg_id = self.__send(CMD_VERSION, version, os_type, breakpoint_method)

        server_version, *_ = self.__wait_for_reply(msg_id)
        server_version = urllib.parse.unquote(server_version)
        logger.debug('pydevd version: %s', server_version)
        return server_version

    def add_breakpoint(self, filename='', line_number='', function=None,
                       condition=None, expression=None, _temporary=False):
        """Set a breakpoint into the debugged program.
        """
        breakpoint_id = self.__get_breakpoint_id()
        self.__send(CMD_SET_BREAK, breakpoint_id, 'python-line', filename,
                    line_number, function, condition, expression)
        self.breakpoints[breakpoint_id] = {
            'id': breakpoint_id,
            'filename': filename,
            'line': line_number,
            'function': function,
            'temporary': _temporary,
            'enabled': True
        }

        self.__run_callback(PyDevClient.EVENT_SET_BREAKPOINT,
                            self.breakpoints[breakpoint_id])
        return breakpoint_id

    def remove_breakpoint(self, breakpoint_id):
        """Remove a breakpoint from the debugged program.
        """
        bp = self.breakpoints[breakpoint_id]
        self.__send(CMD_REMOVE_BREAK, 'python-line', bp['filename'],
                    breakpoint_id)
        del self.breakpoints[breakpoint_id]
        self.__run_callback(PyDevClient.EVENT_REMOVE_BREAKPOINT, bp)

    def start_debugger(self, filename=None, line_number=None):
        """Start the debugger.

        If a filename is given, add a temporary breakpoint to the given line in
        the script, and start the debugger. If no line number is given, figure
        out the first statement in the file and add the breakpoint there.
        """
        if filename:
            if not line_number:
                line_number = find_first_statement(filename)
            self.add_breakpoint(filename=filename,
                                line_number=line_number,
                                _temporary=True)

        msg_id = self.__send(CMD_LIST_THREADS)
        threads, = self.__wait_for_reply(msg_id)

        # Figure out the PID of the project
        for thread in ET.fromstring(threads):
            thread_id = thread.attrib['id']
            self.pid = int(thread_id.split('_')[1])
            break

        self.__send(CMD_RUN)

    def kill_debugger(self):
        """Kill the debugger"""

        # CMD_EXIT and CMD_THREAD_KILL * seem to not be working with the current
        # version of PyDev. However, we can get the PID of the process fromt the
        # thread id of the MainThread, and thus can send a SIGTERM to it.
        if self.pid is None:
            raise RuntimeError('Debugger not yet running')

        os.kill(self.pid, signal.SIGTERM)

    def thread_info(self):
        """Get information on the threads of the debugged process. """
        msg_id = self.__send(CMD_LIST_THREADS)
        threads, = self.__wait_for_reply(msg_id)
        for thread in ET.fromstring(threads):
            name = unquote(thread.attrib['name'])
            thread_id = unquote(thread.attrib['id'])
            if name in PYDEV_INTERNAL_THREADS:
                continue
            if thread_id not in self.threads:
                self.threads[thread_id] = {}

            self.threads[thread_id]['name'] = name
            self.threads[thread_id]['id'] = thread_id
        return self.threads

    # pylint: disable=locally-disabled, no-self-argument
    def thread_arg(f):
        """A decorator for a command that takes an optional thread-name. """
        @functools.wraps(f)
        def _decorator(self, thread=None):

            # pylint: disable=locally-disabled, protected-access
            if thread is None and self._active_thread is None:
                raise RuntimeError('No thread specified')

            for tid, t in self.threads.items():
                if t.get('name') == thread:
                    thread_id = tid
                    break
            else:
                thread_id = self._active_thread
            # pylint: disable=locally-disabled, not-callable
            return f(self, thread_id)

        return _decorator

    # def _progress_thread(command):
    #     @thread_arg
    #     def _func(self, thread_id):
    #         self.__send(command, thread_id)
    #         self.threads[thread_id]['state'] = State.RUNNING
    #     return _func

    # step_over = _progress_thread(CMD_STEP_OVER)
    # step_into = _progress_thread(CMD_STEP_INTO)
    # step_return = _progress_thread(CMD_STEP_RETURN)
    # step_continue = _progress_thread(CMD_THREAD_RUN)

    @thread_arg
    def get_position(self, thread_id):
        thread = self.threads[thread_id]

        if thread['state'] == State.RUNNING:
            raise RuntimeError('Cannot get position of running thread.')

        return (thread.get('file'), int(thread.get('line')), thread.get('function'))

    @thread_arg
    def step_over(self, thread_id):
        self.__send(CMD_STEP_OVER, thread_id)
        self.threads[thread_id]['state'] = State.RUNNING
        self._active_frames = []

    @thread_arg
    def step_into(self, thread_id, my_code=False):
        self.__send(CMD_SMART_STEP_INTO if my_code else CMD_STEP_INTO, thread_id)
        self.threads[thread_id]['state'] = State.RUNNING
        self._active_frames = []

    @thread_arg
    def step_return(self, thread_id):
        self.__send(CMD_STEP_RETURN, thread_id)
        self.threads[thread_id]['state'] = State.RUNNING
        self._active_frames = []

    @thread_arg
    def continue_thread(self, thread_id):
        self.__send(CMD_THREAD_RUN, thread_id)
        self.threads[thread_id]['state'] = State.RUNNING
        self._active_frames = []

    def __delete_if_temporary_breakpoint_hit(self, thread):
        if not thread.attrib['stop_reason'] == str(CMD_SET_BREAK):
            return

        frame = thread[0]

        # Find the breakpoint we had on that line
        for breakpoint in self.breakpoints.values():
            if (unquote(frame.attrib['file']) == breakpoint['filename']
                    and frame.attrib['line'] == breakpoint['line']
                    and breakpoint['temporary']):
                self.remove_breakpoint(breakpoint['id'])
                break

    def evaluate(self, expression):
        """Evaluate expression in current context. """

        # NOTE: Evaluation can be done in other frames as well, but we need some
        #       intuitive way to the user to select the evaluation context.
        if not self._active_frames:
            raise RuntimeError('No active frame')

        msg_id = self.__send(CMD_EVALUATE_EXPRESSION, self._active_thread,
                             self._active_frames[0], None, expression, 1)
        reply = self.__wait_for_reply(msg_id, timeout=10)

        result = ET.fromstring(reply[0])
        return unquote(unquote(result[0].attrib['value']))


def unquote(string):
    """Remove html escaping and urlencoding. """
    return html.unescape(urllib.parse.unquote(string))


def find_first_statement(filename):
    """Finds the line number of the first statement in the file.

    The statement is either a regular statement, class or function definition
    or a module docstring. The line number returned for the docstring is the
    end of the docstring since that is the line which will accept a breakpoint.
    """

    with open(filename, 'rt', encoding='utf-8') as f:
        lines = f.readlines()

    empty = re.compile(r'^\s*$')
    comment = re.compile(r'^\s*#.*')

    docstr_1 = re.compile(r'^\s*""".*')
    docstr_1_end = re.compile(r'.*""".*')
    docstr_1_matched = False
    docstr_2 = re.compile(r'^\s*\'\'\'.*')
    docstr_2_end = re.compile(r'.*\'\'\'.*')
    docstr_2_matched = False

    for index, line in enumerate(lines):
        if empty.match(line) or comment.match(line):
            continue

        if docstr_1_matched and docstr_1_end.match(line):
            return index + 1

        if docstr_2_matched and docstr_2_end.match(line):
            return index + 1

        if not docstr_1_matched and docstr_1.match(line):
            if docstr_1_end.match(line.replace('"""', '', 1)):
                return index + 1

            docstr_1_matched = True
            continue

        if not docstr_2_matched and docstr_2.match(line):
            if docstr_2_end.match(line.replace('\'\'\'', '', 1)):
                return index + 1

            docstr_2_matched = True
            continue

        if docstr_1_matched or docstr_2_matched:
            continue

        # First line not matching anything is assumed to be a statement
        return index + 1
