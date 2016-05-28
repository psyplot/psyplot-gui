"""Compatibility module for the different versions of PyQt"""

# make sure that the right pyqt version suitable for the IPython console is
# loaded
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
        QSizePolicy, QLabel, QLineEdit, QIcon, QToolButton, QComboBox,
        QKeyEvent, QSortFilterProxyModel, QStandardItem, QStandardItemModel,
        QCompleter, QStatusBar, QPlainTextEdit, QTextEdit, QToolBar, QMenu,
        QAction, QTextCursor, QMessageBox, QCheckBox, QFileDialog,
        QListView, QDesktopWidget, QValidator, QStyledItemDelegate,
        QTableWidget, QTableWidgetItem, QRegExpValidator, QGridLayout,
        QIntValidator, QErrorMessage, QInputDialog, QTabWidget,
        QDoubleValidator, QGraphicsScene, QGraphicsRectItem, QGraphicsView,
        QKeySequence)
    from PyQt4 import QtCore
    from PyQt4.QtCore import Qt
    from PyQt4.QtWebKit import QWebView
    from PyQt4.QtTest import QTest
    with_qt5 = False
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
        QGraphicsScene, QGraphicsRectItem, QGraphicsView)
    from PyQt5.QtGui import (
        QIcon, QKeyEvent, QStandardItem, QStandardItemModel, QTextCursor,
        QValidator, QRegExpValidator, QIntValidator, QDoubleValidator,
        QKeySequence)
    from PyQt5 import QtCore
    from PyQt5.QtCore import Qt, QSortFilterProxyModel
    from PyQt5.QtWebKitWidgets import QWebView
    from PyQt5.QtTest import QTest
    with_qt5 = True
