"""
An example of opening up an RichJupyterWidget in a PyQT Application, this can
execute either stand-alone or by importing this file and calling
inprocess_qtconsole.show().
Based on the earlier example in the IPython repository, this has
been updated to use qtconsole.
"""
import re
import sys

try:
    from qtconsole.inprocess import QtInProcessRichJupyterWidget
except ImportError:
    from qtconsole.rich_jupyter_widget import (
        RichJupyterWidget as QtInProcessRichJupyterWidget)

import ipykernel
from tornado import ioloop
from zmq.eventloop import ioloop as zmq_ioloop
from qtconsole.inprocess import QtInProcessKernelManager
from psyplot_gui.compat.qtcompat import (
    with_qt5, QtCore, Qt, QTextEdit, QTextCursor, QKeySequence, asstring)
from psyplot_gui.common import StreamToLogger
import psyplot
import psyplot_gui
from psyplot_gui import rcParams
import psyplot.project as psy
from psyplot.docstring import dedents


import logging

#: HACK: Boolean that is True if the prompt should be used. This unfortunately
#: is necessary for qtconsole >= 4.3 when running the tests
_with_prompt = True


modules2import = [
    ('psyplot.project', 'psy'),
    ('xarray', 'xr'),
    ('pandas', 'pd'),
    ('numpy', 'np')]

symbols_patt = re.compile(r"[^\'\"a-zA-Z0-9_.]")


logger = logging.getLogger(__name__)


class IPythonControl(QTextEdit):
    """A modified control to show the help of objects in the help explorer"""

    def keyPressEvent(self, event):
        """Reimplement Qt Method - Basic keypress event handler"""
        key = event.key()
        if key == Qt.Key_Question or key == Qt.Key_ParenLeft:
            self.parentWidget().show_current_help()
        elif key == Qt.Key_I and (event.modifiers() & Qt.ControlModifier):
            self.parentWidget().show_current_help(True, True)
        # Let the parent widget handle the key press event
        QTextEdit.keyPressEvent(self, event)


class ConsoleWidget(QtInProcessRichJupyterWidget):
    """A console widget to access an inprocess shell"""

    custom_control = IPythonControl

    rc = rcParams.find_and_replace(
        'console.', pattern_base='console\.')

    intro_msg = ''

    run_script = QtCore.pyqtSignal(list)

    run_command = QtCore.pyqtSignal(list)

    def __init__(self, main, *args, **kwargs):
        """
        Parameters
        ----------
        help_explorer: psyplot_gui.help_explorer.HelpExplorer or None
            A widget that can be used to show the documentation of an object
        ``*args,**kwargs``
            Any other keyword argument for the
            :class:`qtconsole.rich_jupyter_widget.RichJupyterWidget`
        """
        kernel_manager = QtInProcessKernelManager()
        # on windows, sys.stdout may be None when using pythonw.exe. Therefore
        # we just us a StringIO for security
        orig_stdout = sys.stdout
        if sys.stdout is None:
            sys.stdout = StreamToLogger(logger)
        orig_stderr = sys.stderr
        if sys.stderr is None:
            sys.stderr = StreamToLogger(logger)
        kernel_manager.start_kernel(show_banner=False)
        if ipykernel.__version__ < '5.1.1':
            # monkey patch to fix
            # https://github.com/ipython/ipykernel/issues/370
            def _abort_queues(kernel):
                pass
            kernel_manager.kernel._abort_queues = _abort_queues
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        kernel = kernel_manager.kernel
        kernel.gui = 'qt4' if not with_qt5 else 'qt'

        kernel_client = kernel_manager.client()
        if rcParams['console.start_channels']:
            kernel_client.start_channels()

        self.help_explorer = kwargs.pop('help_explorer', None)

        super(ConsoleWidget, self).__init__(*args, parent=main, **kwargs)

        self.intro_msg = dedents("""
        psyplot version: %s

        gui version: %s

        The console provides you the full access to the current project and
        plots.
        To make your life easier, the following modules have been imported

            - %s

        Furthermore, each time you change the selection or the content in the
        plot objects viewer, the `sp` (the selection) and `mp` (all arrays)
        variables in the console are adjusted. To disable this behaviour, set::

            >>> import psyplot_gui
            >>> psyplot_gui.rcParams['console.auto_set_mp'] = False
            >>> psyplot_gui.rcParams['console.auto_set_sp'] = False

        To inspect and object in the console and display it's documentation in
        the help explorer, type 'Ctrl + I' or a '?' after the object""") % (
                psyplot.__version__, psyplot_gui.__version__,
                '\n    - '.join('%s as %s' % t for t in modules2import))

        self.kernel_manager = kernel_manager
        self.kernel_client = kernel_client

        self.run_command_in_shell(
            '\n'.join('import %s as %s' % t for t in modules2import))
        self.exit_requested.connect(self._close_mainwindow)
        self.exit_requested.connect(QtCore.QCoreApplication.instance().quit)

        # we overwrite the short cut here because the 'Ctrl+S' shortcut is
        # reserved for mainwindows save action
        try:
            main.register_shortcut(
                self.export_action, QKeySequence(
                    'Ctrl+Alt+S', QKeySequence.NativeText))
        except AttributeError:
            pass

        psy.Project.oncpchange.connect(self.update_mp)
        psy.Project.oncpchange.connect(self.update_sp)

        self.run_script.connect(self._run_script_in_shell)
        self.run_command.connect(self._run_command_in_shell)

        # HACK: we set the IOloop for the InProcessKernel here manually without
        # starting it (not necessary because QApplication has a blocking
        # IOLoop). However, we need this because the ZMQInteractiveShell wants
        # to call
        #     loop = self.kernel.io_loop
        #     loop.call_later(0.1, loop.stop)``
        zmq_ioloop.install()
        self.kernel_manager.kernel.io_loop = ioloop.IOLoop.current()

    def update_mp(self, project):
        """Update the `mp` variable in the shell is
        ``rcParams['console.auto_set_mp']`` with a main project"""
        if self.rc['auto_set_mp'] and project is not None and project.is_main:
            self.run_command_in_shell('mp = psy.gcp(True)')

    def update_sp(self, project):
        """Update the `sp` variable in the shell is
        ``rcParams['console.auto_set_sp']`` with a sub project"""
        if self.rc['auto_set_sp'] and (project is None or not project.is_main):
            self.run_command_in_shell('sp = psy.gcp()')

    def show_current_help(self, to_end=False, force=False):
        """Show the help of the object at the cursor position if
        ``rcParams['console.connect_to_help']`` is set"""
        if not force and not self.rc['connect_to_help']:
            return
        obj_text = self.get_current_object(to_end)
        if obj_text is not None and self.help_explorer is not None:
            found, obj = self.get_obj(obj_text)
            if found:
                self.help_explorer.show_help(obj, obj_text)
                self._control.setFocus()

    def get_obj(self, obj_text):
        """
        Get the object from the shell specified by `obj_text`

        Parameters
        ----------
        obj_text: str
            The name of the variable as it is stored in the shell

        Returns
        -------
        bool
            True, if the object could be found
        object or None
            The requested object or None if it could not be found"""
        info = self.kernel_manager.kernel.shell._object_find(
            obj_text)
        if info.found:
            return True, info.obj
        else:
            return False, None

    def get_current_object(self, to_end=False):
        """Get the name of the object at cursor position"""
        c = self._control
        if not _with_prompt:
            try:  # qtconsole >4.3 uses the _prompt_cursor attribute
                cursor = self._prompt_cursor
            except AttributeError:
                cursor = c.textCursor()
        else:
            cursor = c.textCursor()
        curr = cursor.position()
        start = curr - cursor.positionInBlock()
        txt = c.toPlainText()[start:curr]
        eol = ''
        if to_end:
            cursor.movePosition(QTextCursor.EndOfBlock)
            end = cursor.position()
            if end > curr:
                eol = c.toPlainText()[curr:end]
                m = symbols_patt.search(eol)
                if m:
                    eol = eol[:m.start()]

        if not txt:
            return txt
        txt = asstring(txt)
        txt = txt.rsplit('\n', 1)[-1]
        txt_end = ""
        for startchar, endchar in ["[]", "()"]:
            if txt.endswith(endchar):
                pos = txt.rfind(startchar)
                if pos:
                    txt_end = txt[pos:]
                    txt = txt[:pos]
        tokens = symbols_patt.split(txt)
        token = None
        try:
            while token is None or symbols_patt.match(token):
                token = tokens.pop()
            if token.endswith('.'):
                token = token[:-1]
            if token.startswith('.'):
                # Invalid object name
                return None
            token += txt_end
            if token:
                return token + eol
        except IndexError:
            return None

    def _run_script_in_shell(self, args):
        self.run_script_in_shell(args[0][0])

    def run_script_in_shell(self, script):
        """Run a script in the shell"""
        self.kernel_manager.kernel.shell.run_line_magic('run', script)

    def _run_command_in_shell(self, args):
        # 0: filenames
        # 1: project
        # 2: command
        self.run_command_in_shell(args[2])

    def run_command_in_shell(self, code, *args, **kwargs):
        """Run a script in the shell"""
        ret = self.kernel_manager.kernel.shell.run_code(code, *args, **kwargs)
        import IPython
        if IPython.__version__ < '7.0':  # run_code is an asyncio.coroutine
            return ret
        else:
            import asyncio
            gathered = asyncio.gather(ret)
            loop = asyncio.get_event_loop()
            ret = loop.run_until_complete(gathered)
            return ret[0]

    def _close_mainwindow(self):
        from psyplot_gui.main import mainwindow
        if mainwindow is not None:
            mainwindow.close()
        else:
            self.close()

    def close(self):
        if self.kernel_client.channels_running:
            self.kernel_client.stop_channels()
        return super(ConsoleWidget, self).close()
