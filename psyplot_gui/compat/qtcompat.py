"""Compatibility module for the different versions of PyQt"""

# SPDX-FileCopyrightText: 2016-2024 University of Lausanne
# SPDX-FileCopyrightText: 2020-2021 Helmholtz-Zentrum Geesthacht
# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

import sys

# make sure that the right pyqt version suitable for the IPython console is
# loaded
import six

from psyplot_gui.config.rcsetup import rcParams

try:
    from qtconsole.rich_jupyter_widget import RichJupyterWidget  # noqa: F401
except ImportError:
    pass
try:
    import PyQt5  # noqa: F401
except ImportError:
    from PyQt4 import QtCore, QtGui  # noqa: F401
    from PyQt4.Qt import PYQT_VERSION_STR as PYQT_VERSION  # noqa: F401
    from PyQt4.Qt import QT_VERSION_STR as QT_VERSION  # noqa: F401
    from PyQt4.QtCore import Qt  # noqa: F401
    from PyQt4.QtGui import (  # noqa: F401
        QAbstractItemView,
        QAction,
        QActionGroup,
        QApplication,
        QCheckBox,
    )
    from PyQt4.QtGui import QComboBox as OrigQComboBox
    from PyQt4.QtGui import (  # noqa: F401
        QCompleter,
        QDesktopWidget,
        QDialog,
        QDialogButtonBox,
        QDockWidget,
        QDoubleValidator,
        QErrorMessage,
        QFileDialog,
        QFrame,
        QGraphicsRectItem,
        QGraphicsScene,
        QGraphicsView,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QIcon,
        QInputDialog,
        QIntValidator,
        QKeyEvent,
        QKeySequence,
        QLabel,
        QLineEdit,
        QListView,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QRegExpValidator,
        QScrollArea,
        QSizePolicy,
        QSortFilterProxyModel,
        QSplitter,
        QStackedWidget,
        QStandardItem,
        QStandardItemModel,
        QStatusBar,
        QStyledItemDelegate,
        QStyleOptionViewItem,
        QTableView,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextCursor,
        QTextEdit,
        QToolBar,
        QToolBox,
        QToolButton,
        QTreeWidget,
        QTreeWidgetItem,
        QValidator,
        QVBoxLayout,
        QWidget,
    )
    from PyQt4.QtTest import QTest  # noqa: F401
    from PyQt4.QtWebKit import QWebView as QWebEngineView  # noqa: F401

    with_qt5 = False
    QSignalSpy = None

    try:
        from PyQt4.QtCore import QByteArray, QString
    except ImportError:

        def isstring(s):
            return isinstance(s, six.string_types)

    else:

        def isstring(s):
            return isinstance(
                s, tuple(list(six.string_types) + [QString, QByteArray])
            )

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
    from PyQt5 import QtCore
    from PyQt5.QtCore import QSortFilterProxyModel, Qt  # noqa: F401
    from PyQt5.QtGui import (  # noqa: F401
        QDoubleValidator,
        QIcon,
        QIntValidator,
        QKeyEvent,
        QKeySequence,
        QRegExpValidator,
        QStandardItem,
        QStandardItemModel,
        QTextCursor,
        QValidator,
    )
    from PyQt5.QtWidgets import (  # noqa: F401
        QAbstractItemView,
        QAction,
        QActionGroup,
        QApplication,
        QCheckBox,
        QComboBox,
        QCompleter,
        QDesktopWidget,
        QDialog,
        QDialogButtonBox,
        QDockWidget,
        QErrorMessage,
        QFileDialog,
        QFrame,
        QGraphicsRectItem,
        QGraphicsScene,
        QGraphicsView,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QInputDialog,
        QLabel,
        QLineEdit,
        QListView,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMenu,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSplitter,
        QStackedWidget,
        QStatusBar,
        QStyledItemDelegate,
        QStyleOptionViewItem,
        QTableView,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QTextEdit,
        QToolBar,
        QToolBox,
        QToolButton,
        QTreeWidget,
        QTreeWidgetItem,
        QVBoxLayout,
        QWidget,
    )

    if rcParams["help_explorer.use_webengineview"]:
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        except ImportError:
            from PyQt5.QtWebKitWidgets import (  # noqa: F401
                QWebView as QWebEngineView,
            )
    else:
        QWebEngineView = None
    from PyQt5 import QtGui  # noqa: F401
    from PyQt5.Qt import PYQT_VERSION_STR as PYQT_VERSION  # noqa: F401
    from PyQt5.Qt import QT_VERSION_STR as QT_VERSION  # noqa: F401
    from PyQt5.QtTest import QSignalSpy, QTest  # noqa: F401

    with_qt5 = True

    def isstring(s):
        return isinstance(s, six.string_types)


def asstring(s):
    return six.text_type(s)


if sys.platform == "darwin":
    # make sure to register the open file event
    OrigQApplication = QApplication

    class QApplication(OrigQApplication):
        """Reimplemented QApplication with open file event"""

        def event(self, event):
            from psyplot_gui.config.rcsetup import rcParams

            if (
                rcParams["main.listen_to_port"]
                and event.type() == QtCore.QEvent.FileOpen
            ):
                from psyplot_gui.main import mainwindow

                if mainwindow is not None:
                    opened = mainwindow.open_files([event.file()])
                    if opened:
                        return True
            return super(QApplication, self).event(event)
