"""Common functions used for the psyplot gui"""
import sys
import traceback as tb
import os.path as osp
from psyplot_gui.compat.qtcompat import (
    QDockWidget, QRegExpValidator, QtCore, QErrorMessage, QDesktopWidget)
import logging
from io import StringIO


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

    def to_dock(self, main, title=None, position=None, docktype='pane', *args,
                **kwargs):
        if title is None:
            title = self.title
        if title is None:
            raise ValueError(
                "No position specified for the %s widget" % (self))
        if position is None:
            position = self.dock_position
        if position is None:
            raise ValueError("No position specified for the %s widget (%s)" % (
                title, self))
        self.dock = self.dock_cls(title, main)
        self.dock.setWidget(self)
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
        s = StringIO()
        tb.print_exc(file=s)
        last_tb = '<p>' + '<br>'.join(s.getvalue().splitlines()) + \
            '</p>'
        header = header + '\n' if header else ''
        self.showMessage(header + last_tb)
        available_width = QDesktopWidget().availableGeometry().width() / 3.
        available_height = QDesktopWidget().availableGeometry().height() / 3.
        width = self.sizeHint().width()
        height = self.sizeHint().height()
        # The plot creator window should cover at least one third of the screen
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
