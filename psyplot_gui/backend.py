"""Matplotlib backend to include matplotlib figures as dockwidgets in the
psyplot gui

This backend is based upon matplotlibs qt4agg and qt5agg backends."""
from psyplot_gui.compat.qtcompat import (
    QDockWidget, Qt, QWidget, QVBoxLayout, with_qt5)
from psyplot_gui.common import DockMixin
from matplotlib.backend_bases import FigureManagerBase
from matplotlib.figure import Figure
if with_qt5:
    from matplotlib.backends.backend_qt5agg import (
        show, FigureManagerQT, FigureCanvasQTAgg)
else:
    from matplotlib.backends.backend_qt4agg import (
        show, FigureManagerQT, FigureCanvasQTAgg)


class FiguresDock(QDockWidget):
    """Reimplemented QDockWidget to remove the dock widget when closed
    """

    def close(self, *args, **kwargs):
        """
        Reimplemented to remove the dock widget from the mainwindow when closed
        """
        from psyplot_gui.main import mainwindow
        try:
            mainwindow.figures.remove(self)
        except Exception:
            pass
        try:
            mainwindow.removeDockWidget(self)
        except Exception:
            pass
        return super(FiguresDock, self).close(*args, **kwargs)


class FigureWidget(DockMixin, QWidget):
    """A simple container for figures in the psyplot backend"""

    dock_cls = FiguresDock


def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)
    return new_figure_manager_given_figure(num, thisFig)


def new_figure_manager_given_figure(num, figure):
    """
    Create a new figure manager instance for the given figure.
    """
    canvas = PsyplotCanvas(figure)
    return PsyplotCanvasManager(canvas, num)


class PsyplotCanvasManager(FigureManagerQT):
    """The canvas manager for the psyplot backend interacting with the
    mainwindow of the psyplot gui"""

    toolbar = None

    def __init__(self, canvas, num):
        from psyplot_gui.main import mainwindow
        self.main = mainwindow
        if mainwindow is None:
            return super(PsyplotCanvasManager, self).__init__(canvas, num)
        parent_widget = FigureWidget()
        parent_widget.vbox = vbox = QVBoxLayout()
        self.window = dock = parent_widget.to_dock(
            mainwindow, title="Figure %d" % num, position=Qt.TopDockWidgetArea,
            docktype=None)
        if mainwindow.figures:
            mainwindow.tabifyDockWidget(mainwindow.figures[-1], dock)
        mainwindow.figures.append(dock)
        FigureManagerBase.__init__(self, canvas, num)
        self.canvas = canvas

        self.window.setWindowTitle("Figure %d" % num)

        self.toolbar = self._get_toolbar(canvas, parent_widget)

        # add text label to status bar
        self.statusbar_label = mainwindow.figures_label

        if self.toolbar is not None:
            vbox.addWidget(self.toolbar)
            self.toolbar.message.connect(self.statusbar_label.setText)

        vbox.addWidget(canvas)
        parent_widget.setLayout(vbox)
        self.parent_widget = parent_widget

        # Give the keyboard focus to the figure instead of the
        # manager; StrongFocus accepts both tab and click to focus and
        # will enable the canvas to process event w/o clicking.
        # ClickFocus only takes the focus is the window has been
        # clicked
        # on. http://qt-project.org/doc/qt-4.8/qt.html#FocusPolicy-enum or
        # http://doc.qt.digia.com/qt/qt.html#FocusPolicy-enum
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.setFocus()
        self.window._destroying = False

        self.main.show()

        def notify_axes_change(fig):
            # This will be called whenever the current axes is changed
            if self.toolbar is not None:
                self.toolbar.update()
        self.canvas.figure.add_axobserver(notify_axes_change)

    def statusBar(self, *args, **kwargs):
        if self.main is None:
            return super(PsyplotCanvasManager, self).statusBar(*args, **kwargs)
        return self.main.statusBar(*args, **kwargs)

    def resize(self, width, height):
        self.window.resize(width, height + self.toolbar.sizeHint().height())


class PsyplotCanvas(FigureCanvasQTAgg):
    """The canvas class with reimplemented resizing"""

    def resizeEvent(self, event):
        """Reimplemented to make sure that the figure is only resized for
        events with height and width greater 0"""
        if event.size().width() > 0 and event.size().height() > 0:
            super(PsyplotCanvas, self).resizeEvent(event)


FigureManager = PsyplotCanvasManager
FigureCanvas = PsyplotCanvas
