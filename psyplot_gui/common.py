"""Common functions used for the psyplot gui"""
import sys
import traceback as tb
import os.path as osp
from psyplot_gui.compat.qtcompat import (
    QDockWidget, QRegExpValidator, QtCore, QErrorMessage)


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
        last_tb = '<p>' + ''.join(tb.format_exception(*sys.exc_info())) + \
            '</p>'
        header = header + '\n' if header else ''
        self.showMessage(header + last_tb)
