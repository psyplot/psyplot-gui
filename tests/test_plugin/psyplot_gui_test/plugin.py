from psyplot_gui.common import DockMixin
from psyplot_gui.compat.qtcompat import QWidget, Qt


class W1(QWidget, DockMixin):
    title = 'w1'
    dock_position = Qt.LeftDockWidgetArea


class W2(QWidget, DockMixin):
    title = 'w2'
    dock_position = Qt.BottomDockWidgetArea
