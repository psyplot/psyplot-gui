"""Compatibility module for the different versions of PyQt"""

# make sure that the right pyqt version suitable for the IPython console is
# loaded
import six
import sys

try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget
except ImportError:
    pass
try:
    import PyQt5
except ImportError:
    from PyQt4.QtGui import (
        QMainWindow, QDockWidget, QToolBox, QApplication, QListWidget,
        QListWidgetItem, QHBoxLayout, QVBoxLayout, QAbstractItemView,
        QWidget, QPushButton, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem,
        QSizePolicy, QLabel, QLineEdit, QIcon, QToolButton,
        QComboBox as OrigQComboBox,
        QKeyEvent, QSortFilterProxyModel, QStandardItem, QStandardItemModel,
        QCompleter, QStatusBar, QPlainTextEdit, QTextEdit, QToolBar, QMenu,
        QAction, QTextCursor, QMessageBox, QCheckBox, QFileDialog,
        QListView, QDesktopWidget, QValidator, QStyledItemDelegate,
        QTableWidget, QTableWidgetItem, QRegExpValidator, QGridLayout,
        QIntValidator, QErrorMessage, QInputDialog, QTabWidget,
        QDoubleValidator, QGraphicsScene, QGraphicsRectItem, QGraphicsView,
        QKeySequence, QStyleOptionViewItem, QDialog, QDialogButtonBox,
        QStackedWidget, QScrollArea, QTableView, QHeaderView)
    from PyQt4 import QtCore
    from PyQt4.QtCore import Qt
    from PyQt4.QtWebKit import QWebView as QWebEngineView
    from PyQt4.QtTest import QTest
    from PyQt4 import QtGui
    from PyQt4.Qt import PYQT_VERSION_STR as PYQT_VERSION
    from PyQt4.Qt import QT_VERSION_STR as QT_VERSION
    with_qt5 = False
    QSignalSpy = None

    try:
        from PyQt4.QtCore import QString, QByteArray
    except ImportError:
        def isstring(s):
            return isinstance(s, six.string_types)
    else:
        def isstring(s):
            return isinstance(
                s, tuple(list(six.string_types) + [QString, QByteArray]))

    class QComboBox(OrigQComboBox):

        currentTextChanged = QtCore.pyqtSignal(str)

        def __init__(self, *args, **kwargs):
            OrigQComboBox.__init__(self, *args, **kwargs)
            self.currentIndexChanged.connect(self._emit_currentTextChanged)

        def _emit_currentTextChanged(self, i):
            self.currentTextChanged.emit(self.currentText())

        def setCurrentText(self, s):
            idx = self.findText(s)
            if idx == -1:
                self.addItem(s)
                idx = self.findText(s)
            self.setCurrentIndex(idx)

else:
    from PyQt5.QtWidgets import (
        QMainWindow, QDockWidget, QToolBox, QApplication, QListWidget,
        QListWidgetItem, QHBoxLayout, QVBoxLayout, QAbstractItemView,
        QWidget, QPushButton, QFrame, QSplitter, QTreeWidget, QTreeWidgetItem,
        QSizePolicy, QLabel, QLineEdit, QToolButton, QComboBox, QCompleter,
        QStatusBar, QPlainTextEdit, QTextEdit, QToolBar, QMenu,
        QAction, QMessageBox, QCheckBox, QFileDialog, QListView,
        QDesktopWidget, QStyledItemDelegate, QTableWidget, QTableWidgetItem,
        QGridLayout, QErrorMessage, QInputDialog, QTabWidget,
        QGraphicsScene, QGraphicsRectItem, QGraphicsView, QStyleOptionViewItem,
        QDialog, QDialogButtonBox, QStackedWidget, QScrollArea,
        QTableView, QHeaderView)
    from PyQt5.QtGui import (
        QIcon, QKeyEvent, QStandardItem, QStandardItemModel, QTextCursor,
        QValidator, QRegExpValidator, QIntValidator, QDoubleValidator,
        QKeySequence)
    from PyQt5 import QtCore
    from PyQt5.QtCore import Qt, QSortFilterProxyModel
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
    except ImportError:
        from PyQt5.QtWebKitWidgets import QWebView as QWebEngineView
    from PyQt5.QtTest import QTest, QSignalSpy
    from PyQt5 import QtGui
    from PyQt5.Qt import PYQT_VERSION_STR as PYQT_VERSION
    from PyQt5.Qt import QT_VERSION_STR as QT_VERSION
    with_qt5 = True

    def isstring(s):
        return isinstance(s, six.string_types)


def asstring(s):
    return six.text_type(s)


if sys.platform == 'darwin':
    # make sure to register the open file event
    OrigQApplication = QApplication

    class QApplication(OrigQApplication):
        """Reimplemented QApplication with open file event"""

        def event(self, event):
            from psyplot_gui.config.rcsetup import rcParams

            if (rcParams['main.listen_to_port'] and
                    event.type() == QtCore.QEvent.FileOpen):
                from psyplot_gui.main import mainwindow
                if mainwindow is not None:
                    opened = mainwindow.open_files([event.file()])
                    if opened:
                        return True
            return super(QApplication, self).event(event)
