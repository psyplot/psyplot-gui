"""Common functions used for the psyplot gui"""
import sys
import six
import inspect
import traceback as tb
from functools import partial
import os.path as osp
from psyplot_gui.compat.qtcompat import (
    QDockWidget, QRegExpValidator, QtCore, QErrorMessage, QDesktopWidget,
    QToolButton, QInputDialog, QIcon)
import logging

if six.PY2:
    try:
        import CStringIO as io
    except ImportError:
        import StringIO as io
else:
    import io


def get_module_path(modname):
    """Return module `modname` base path"""

    return osp.abspath(osp.dirname(sys.modules[modname].__file__))


def get_icon(name):
    """Get the path to an icon in the icons directory"""
    return osp.join(get_module_path('psyplot_gui'), 'icons', name)


class DockMixin(object):
    """A mixin class to define psyplot_gui plugins

    Notes
    -----
    Each external plugin should set the :attr:`dock_position` and the
    :attr:`title` attribute!
    """

    #: The position of the plugin
    dock_position = None

    #: The title of the plugin
    title = None

    #: The class to use for the DockWidget
    dock_cls = QDockWidget

    #: The config page for this widget. Should inherit the
    #: :class:`psyplot_gui.preferences.ConfigPage` widget
    config_page = None

    #: Boolean that is True if the dock widget should be hidden automatically
    #: after startup
    hidden = False

    #: The instance of :class:`QDockWidget` of this plugin
    dock = None

    @property
    def is_shown(self):
        """Boolean that is True, if the dock widget is shown"""
        return (self.dock is not None and
                self.dock.toggleViewAction().isChecked())

    def to_dock(self, main, title=None, position=None, docktype='pane', *args,
                **kwargs):
        if title is None:
            title = self.title
        if title is None:
            raise ValueError(
                "No title specified for the %s widget" % (self))
        if position is None:
            position = self.dock_position
        if position is None:
            raise ValueError("No position specified for the %s widget (%s)" % (
                title, self))
        self.title = title
        self.dock_position = position
        if self.dock is None:
            self.dock = self.dock_cls(title, main)
            self.dock.setWidget(self)
            main.dockwidgets.append(self.dock)
        main.addDockWidget(position, self.dock, docktype, *args, **kwargs)
        config_page = self.config_page
        if config_page is not None:
            main.config_pages.append(config_page)
        return self.dock

    def show_plugin(self):
        """Show the plugin widget"""
        a = self.dock.toggleViewAction()
        if not a.isChecked():
            a.trigger()

    def hide_plugin(self):
        """Hide the plugin widget"""
        a = self.dock.toggleViewAction()
        if a.isChecked():
            a.trigger()

    def show_status_message(self, msg):
        """Show a status message"""
        try:
            self.dock.parent().plugin_label.setText(msg)
        except AttributeError:
            pass


class LoadFromConsoleButton(QToolButton):
    """A toolbutton to load an object from the console"""

    #: The signal that is emitted when an object has been loaded. The first
    #: argument is the object name, the second the object itself
    object_loaded = QtCore.pyqtSignal(str, object)

    @property
    def instances2check_str(self):
        return ', '.join('%s.%s' % (cls.__module__, cls.__name__)
                         for cls in self._instances2check)

    @property
    def potential_object_names(self):
        from ipykernel.inprocess.ipkernel import InProcessInteractiveShell
        shell = InProcessInteractiveShell.instance()
        return sorted(name for name, obj in shell.user_global_ns.items()
                      if not name.startswith('_') and self.check(obj))

    def __init__(self, instances=None, *args, **kwargs):
        """
        Parameters
        ----------
        instances: class or tuple of classes
            The classes that should be used for an instance check
        """
        super(LoadFromConsoleButton, self).__init__(*args, **kwargs)
        self.setIcon(QIcon(get_icon('console-go.png')))
        if instances is not None and inspect.isclass(instances):
            instances = (instances, )
        self._instances2check = instances
        self.error_msg = PyErrorMessage(self)
        self.clicked.connect(partial(self.get_from_shell, None))

    def check(self, obj):
        return True if not self._instances2check else isinstance(
            obj, self._instances2check)

    def get_from_shell(self, oname=None):
        """Open an input dialog, receive an object and emit the
        :attr:`object_loaded` signal"""
        if oname is None:
            oname, ok = QInputDialog.getItem(
                self, 'Select variable',
                'Select a variable to import from the console',
                self.potential_object_names)
            if not ok:
                return
        if self.check(oname) and (self._instances2check or
                                  not isinstance(oname, six.string_types)):
            obj = oname
            oname = 'object'
        else:
            found, obj = self.get_obj(oname.strip())
            if found:
                if not self.check(obj):
                    self.error_msg.showMessage(
                        'Object must be an instance of %r, not %r' % (
                            self.instances2check_str,
                            '%s.%s' % (type(obj).__module__,
                                       type(obj).__name__)))
                    return
            else:
                if not oname.strip():
                    msg = 'The variable name must not be empty!'
                else:
                    msg = 'Could not find object ' + oname
                self.error_msg.showMessage(msg)
                return
        self.object_loaded.emit(oname, obj)

    def get_obj(self, oname):
        """Load an object from the current shell"""
        from psyplot_gui.main import mainwindow
        return mainwindow.console.get_obj(oname)


class ListValidator(QRegExpValidator):
    """A validator class to validate that a string consists of strings in a
    list of strings"""

    def __init__(self, valid, sep=',', *args, **kwargs):
        """
        Parameters
        ----------
        valid: list of str
            The possible choices
        sep: str, optional
            The separation pattern
        ``*args,**kwargs``
            Determined by PyQt5.QtGui.QValidator
        """
        patt = QtCore.QRegExp('^((%s)(;;)?)+$' % '|'.join(valid))
        super(QRegExpValidator, self).__init__(patt, *args, **kwargs)


class PyErrorMessage(QErrorMessage):
    """Widget designed to display python errors via the :meth:`showTraceback`
    method"""

    def showTraceback(self, header=None):
        s = io.StringIO()
        tb.print_exc(file=s)
        last_tb = '<p>' + '<br>'.join(s.getvalue().splitlines()) + \
            '</p>'
        header = header + '\n' if header else ''
        self.showMessage(header + last_tb)
        available_width = QDesktopWidget().availableGeometry().width() / 3.
        available_height = QDesktopWidget().availableGeometry().height() / 3.
        width = self.sizeHint().width()
        height = self.sizeHint().height()
        # The message window should cover at least one third of the screen
        self.resize(max(available_width, width), max(available_height, height))

    def excepthook(self, type, value, traceback):
        s = io.StringIO()
        tb.print_exception(type, value, traceback, file=s)
        last_tb = '<p>' + '<br>'.join(s.getvalue().splitlines()) + \
            '</p>'
        header = value.message if six.PY2 else str(value)
        self.showMessage(header + '\n' + last_tb)
        available_width = QDesktopWidget().availableGeometry().width() / 3.
        available_height = QDesktopWidget().availableGeometry().height() / 3.
        width = self.sizeHint().width()
        height = self.sizeHint().height()
        # The message window should cover at least one third of the screen
        self.resize(max(available_width, width), max(available_height, height))


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass
