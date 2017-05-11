"""
An example of opening up an RichJupyterWidget in a PyQT Application, this can
execute either stand-alone or by importing this file and calling
inprocess_qtconsole.show().
Based on the earlier example in the IPython repository, this has
been updated to use qtconsole.
"""
import re
import sys

from qtconsole.rich_jupyter_widget import RichJupyterWidget
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
            self.parentWidget().show_current_help(True)
        # Let the parent widget handle the key press event
        QTextEdit.keyPressEvent(self, event)


class ConsoleWidget(RichJupyterWidget):
    """A console widget to access an inprocess shell"""

    custom_control = IPythonControl

    rc = rcParams.find_and_replace(
        'console.', pattern_base='console\.')

    intro_msg = ''

    def __init__(self, *args, **kwargs):
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
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        kernel = kernel_manager.kernel
        kernel.gui = 'qt4' if not with_qt5 else 'qt'

        kernel_client = kernel_manager.client()
        kernel_client.start_channels()

        self.help_explorer = kwargs.pop('help_explorer', None)

        super(ConsoleWidget, self).__init__(*args, **kwargs)

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

        self.kernel_manager.kernel.shell.run_code(
            '\n'.join('import %s as %s' % t for t in modules2import))
        self.exit_requested.connect(QtCore.QCoreApplication.instance().quit)

        # we overwrite the short cut here because the 'Ctrl+S' shortcut is
        # reserved for mainwindows save action
        self.export_action.setShortcut(QKeySequence(
            'Ctrl+Alt+S', QKeySequence.NativeText))

        psy.Project.oncpchange.connect(self.update_mp)
        psy.Project.oncpchange.connect(self.update_sp)

    def update_mp(self, project):
        """Update the `mp` variable in the shell is
        ``rcParams['console.auto_set_mp']`` with a main project"""
        if self.rc['auto_set_mp'] and project is not None and project.is_main:
            self.kernel_manager.kernel.shell.run_code('mp = psy.gcp(True)')

    def update_sp(self, project):
        """Update the `sp` variable in the shell is
        ``rcParams['console.auto_set_sp']`` with a sub project"""
        if self.rc['auto_set_sp'] and (project is None or not project.is_main):
            self.kernel_manager.kernel.shell.run_code('sp = psy.gcp()')

    def show_current_help(self, to_end=False):
        """Show the help of the object at the cursor position if
        ``rcParams['console.connect_to_help']`` is set"""
        if not self.rc['connect_to_help']:
            return
        obj_text = self.get_current_object(to_end)
        if obj_text is not None and self.help_explorer is not None:
            found, obj = self.get_obj(obj_text)
            if found:
                self.help_explorer.show_help(obj, obj_text)

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
