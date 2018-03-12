"""A widget to display and edit DataFrames"""
import os
import os.path as osp
import six
from functools import partial
import numpy as np
from psyplot.docstring import docstrings
from psyplot_gui.compat.qtcompat import (
    QWidget, QHBoxLayout, QVBoxLayout, QtCore, QLineEdit,
    QPushButton, Qt, QToolButton, QIcon, QMenu, QLabel, QtGui, QApplication,
    QCheckBox, QFileDialog, with_qt5, QTableView, QHeaderView,
    QDockWidget)
from psyplot_gui.common import (DockMixin, get_icon, LoadFromConsoleButton,
                                PyErrorMessage)
import pandas as pd

if six.PY2:
    try:
        import CStringIO as io
    except ImportError:
        import StringIO as io
else:
    import io


LARGE_SIZE = int(5e5)
LARGE_NROWS = int(1e5)
LARGE_COLS = 60

REAL_NUMBER_TYPES = (float, int, np.int64, np.int32)
COMPLEX_NUMBER_TYPES = (complex, np.complex64, np.complex128)

_bool_false = ['false', '0']


def bool_false_check(value):
    """
    Used to convert bool intrance to false since any string in bool('')
    will return True
    """
    if value.lower() in _bool_false:
        value = ''
    return value


class DataFrameModel(QtCore.QAbstractTableModel):
    """ DataFrame Table Model"""

    ROWS_TO_LOAD = 500
    COLS_TO_LOAD = 40

    _format = '%0.6g'

    @docstrings.get_sectionsf('DataFrameModel')
    @docstrings.dedent
    def __init__(self, df, parent=None, index_editable=True,
                 dtypes_changeable=True):
        """
        Parameters
        ----------
        df: pandas.DataFrame
            The data frame that will be shown by this :class:`DataFrameModel`
            instance
        parent: DataFrameEditor
            The editor for the table
        index_editable: bool
            True if the index should be modifiable by the user
        dtypes_changeable: bool
            True, if the data types should be modifiable by the user
        """
        QtCore.QAbstractTableModel.__init__(self)
        self._parent = parent
        self.df = df
        self.df_index = self.df.index.tolist()
        self.df_header = self.df.columns.tolist()
        self.total_rows = self.df.shape[0]
        self.total_cols = self.df.shape[1]
        size = self.total_rows * self.total_cols
        self.index_editable = index_editable
        self.dtypes_changeable = dtypes_changeable

        # Use paging when the total size, number of rows or number of
        # columns is too large
        if size > LARGE_SIZE:
            self.rows_loaded = self.ROWS_TO_LOAD
            self.cols_loaded = self.COLS_TO_LOAD
        else:
            if self.total_rows > LARGE_NROWS:
                self.rows_loaded = self.ROWS_TO_LOAD
            else:
                self.rows_loaded = self.total_rows
            if self.total_cols > LARGE_COLS:
                self.cols_loaded = self.COLS_TO_LOAD
            else:
                self.cols_loaded = self.total_cols

    def get_format(self):
        """Return current format"""
        # Avoid accessing the private attribute _format from outside
        return self._format

    def set_format(self, format):
        """Change display format"""
        self._format = format
        self.reset()

    def bgcolor(self, state):
        """Toggle backgroundcolor"""
        self.bgcolor_enabled = state > 0
        self.reset()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header data"""
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if section == 0:
                return six.text_type('Index')
            elif isinstance(self.df_header[section-1], six.string_types):
                header = self.df_header[section-1]
                return six.text_type(header)
            else:
                return six.text_type(self.df_header[section-1])
        else:
            return None

    def get_value(self, row, column):
        """Returns the value of the DataFrame"""
        # To increase the performance iat is used but that requires error
        # handling, so fallback uses iloc
        try:
            value = self.df.iat[row, column]
        except AttributeError:
            value = self.df.iloc[row, column]
        return value

    def data(self, index, role=Qt.DisplayRole):
        """Cell content"""
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            column = index.column()
            row = index.row()
            if column == 0:
                return six.text_type(self.df_index[row])
            else:
                value = self.get_value(row, column-1)
                if isinstance(value, float):
                    try:
                        return self._format % value
                    except (ValueError, TypeError):
                        # may happen if format = '%d' and value = NaN;
                        # see issue 4139
                        return DataFrameModel._format % value
                else:
                    return six.text_type(value)

    def sort(self, column, order=Qt.AscendingOrder, return_check=False,
             report=True):
        """Overriding sort method"""
        try:
            ascending = order == Qt.AscendingOrder
            if column > 0:
                try:
                    self.df.sort_values(by=self.df.columns[column-1],
                                        ascending=ascending, inplace=True,
                                        kind='mergesort')
                except AttributeError:
                    # for pandas version < 0.17
                    self.df.sort(columns=self.df.columns[column-1],
                                 ascending=ascending, inplace=True,
                                 kind='mergesort')
                self.update_df_index()
            else:
                self.df.sort_index(inplace=True, ascending=ascending)
                self.update_df_index()
        except TypeError as e:
            if report:
                self._parent.error_msg.showTraceback(
                    "<b>Failed to sort column!</b>")
            return False if return_check else None
        self.reset()
        return True if return_check else None

    def flags(self, index):
        """Set flags"""
        if index.column() == 0 and not self.index_editable:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemFlags(QtCore.QAbstractTableModel.flags(self, index) |
                            Qt.ItemIsEditable)

    def setData(self, index, value, role=Qt.EditRole, change_type=None):
        """Cell content change"""
        column = index.column()
        row = index.row()

        if change_type is not None:
            if not self.dtypes_changeable:
                return False
            try:
                value = current_value = self.data(index, role=Qt.DisplayRole)
                if change_type is bool:
                    value = bool_false_check(value)
                self.df.iloc[row, column - 1] = change_type(value)
            except ValueError:
                self.df.iloc[row, column - 1] = change_type('0')
        else:
            current_value = self.get_value(row, column-1) if column else \
                self.df.index[row]
            if isinstance(current_value, bool):
                value = bool_false_check(value)
            supported_types = (bool,) + REAL_NUMBER_TYPES + \
                COMPLEX_NUMBER_TYPES
            if (isinstance(current_value, supported_types) or
                    isinstance(current_value, six.string_types)):
                if column:
                    try:
                        self.df.iloc[row, column-1] = current_value.__class__(
                            value)
                    except ValueError as e:
                        self._parent.error_msg.showTraceback(
                            "<b>Failed to set value with %r!</b>" % value)
                        return False
                elif self.index_editable:
                    index = self.df.index.values.copy()
                    try:
                        index[row] = value
                    except ValueError as e:
                        self._parent.error_msg.showTraceback(
                            "<b>Failed to set value with %r!</b>" % value)
                        return False
                    self.df.index = pd.Index(index, name=self.df.index.name)
                    self.update_df_index()
                else:
                    return False
            else:
                self._parent.error_msg.showTraceback(
                            "<b>The type of the cell is not a supported type"
                            "</b>")
                return False
        self._parent.cell_edited.emit(row, column, current_value, value)
        return True

    def rowCount(self, index=QtCore.QModelIndex()):
        """DataFrame row number"""
        if self.total_rows <= self.rows_loaded:
            return self.total_rows
        else:
            return self.rows_loaded

    def can_fetch_more(self, rows=False, columns=False):
        if rows:
            if self.total_rows > self.rows_loaded:
                return True
            else:
                return False
        if columns:
            if self.total_cols > self.cols_loaded:
                return True
            else:
                return False

    def fetch_more(self, rows=False, columns=False):
        if self.can_fetch_more(rows=rows):
            reminder = self.total_rows - self.rows_loaded
            items_to_fetch = min(reminder, self.ROWS_TO_LOAD)
            self.beginInsertRows(QtCore.QModelIndex(), self.rows_loaded,
                                 self.rows_loaded + items_to_fetch - 1)
            self.rows_loaded += items_to_fetch
            self.endInsertRows()
        if self.can_fetch_more(columns=columns):
            reminder = self.total_cols - self.cols_loaded
            items_to_fetch = min(reminder, self.COLS_TO_LOAD)
            self.beginInsertColumns(QtCore.QModelIndex(), self.cols_loaded,
                                    self.cols_loaded + items_to_fetch - 1)
            self.cols_loaded += items_to_fetch
            self.endInsertColumns()

    def columnCount(self, index=QtCore.QModelIndex()):
        """DataFrame column number"""
        # This is done to implement series
        if len(self.df.shape) == 1:
            return 2
        elif self.total_cols <= self.cols_loaded:
            return self.total_cols + 1
        else:
            return self.cols_loaded + 1

    def update_df_index(self):
        """"Update the DataFrame index"""
        self.df_index = self.df.index.tolist()

    def reset(self):
        self.beginResetModel()
        self.endResetModel()

    def insertRow(self, irow):
        """Insert one row into the :attr:`df`

        Parameters
        ----------
        irow: int
            The row index. If iRow is equal to the length of the
            :attr:`df`, the new row will be appended."""
        # reimplemented to fall back to the :meth:`insertRows` method
        self.insertRows(irow)

    def insertRows(self, irow, nrows=1):
        """Insert a row into the :attr:`df`

        Parameters
        ----------
        irow: int
            The row index. If `irow` is equal to the length of the
            :attr:`df`, the rows will be appended.
        nrows: int
            The number of rows to insert"""
        df = self.df
        if not irow:
            if not len(df):
                idx = 0
            else:
                idx = df.index.values[0]
        else:
            try:
                idx = df.index.values[irow-1:irow+1].mean()
            except TypeError:
                idx = df.index.values[min(irow, len(df) - 1)]
            else:
                idx = df.index.values[min(irow, len(df) - 1)].__class__(idx)
        # reset the index to sort it correctly
        idx_name = df.index.name
        dtype = df.index.dtype
        df.reset_index(inplace=True)
        new_idx_name = df.columns[0]
        current_len = len(df)
        for i in range(nrows):
            df.loc[current_len + i, new_idx_name] = idx
        df[new_idx_name] = df[new_idx_name].astype(dtype)
        if irow < current_len:
            changed = df.index.values.astype(float)
            changed[current_len:] = irow - 0.5
            df.index = changed
            df.sort_index(inplace=True)
        df.set_index(new_idx_name, inplace=True, drop=True)
        df.index.name = idx_name
        self.update_df_index()
        self.beginInsertRows(QtCore.QModelIndex(), self.rows_loaded,
                             self.rows_loaded + nrows - 1)
        self.total_rows += nrows
        self.rows_loaded += nrows
        self.endInsertRows()
        self._parent.rows_inserted.emit(irow, nrows)


class FrozenTableView(QTableView):
    """This class implements a table with its first column frozen
    For more information please see:
    http://doc.qt.io/qt-5/qtwidgets-itemviews-frozencolumn-example.html"""
    def __init__(self, parent):
        """Constructor."""
        QTableView.__init__(self, parent)
        self.parent = parent
        self.setModel(parent.model())
        self.setFocusPolicy(Qt.NoFocus)
        self.verticalHeader().hide()
        if with_qt5:
            self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        else:
            self.horizontalHeader().setResizeMode(QHeaderView.Fixed)

        parent.viewport().stackUnder(self)

        self.setSelectionModel(parent.selectionModel())
        for col in range(1, parent.model().columnCount()):
            self.setColumnHidden(col, True)

        self.setColumnWidth(0, parent.columnWidth(0))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.show()
        self.setVerticalScrollMode(QTableView.ScrollPerPixel)

        self.verticalScrollBar().valueChanged.connect(
            parent.verticalScrollBar().setValue)
        parent.verticalScrollBar().valueChanged.connect(
            self.verticalScrollBar().setValue)

    def update_geometry(self):
        """Update the frozen column size when an update occurs in its parent
        table"""
        self.setGeometry(self.parent.verticalHeader().width() +
                         self.parent.frameWidth(),
                         self.parent.frameWidth(),
                         self.parent.columnWidth(0),
                         self.parent.viewport().height() +
                         self.parent.horizontalHeader().height())

    def contextMenuEvent(self, event):
        """Show the context Menu

        Reimplemented to show the use the contextMenuEvent of the parent"""
        self.parent.contextMenuEvent(event)


class DataFrameView(QTableView):
    """Data Frame view class"""

    @property
    def filled(self):
        """True if the table is filled with content"""
        return bool(self.model().rows_loaded)

    @docstrings.dedent
    def __init__(self, df, parent, *args, **kwargs):
        """
        Parameters
        ----------
        %(DataFrameModel.parameters)s
        """
        QTableView.__init__(self, parent)
        model = DataFrameModel(df, parent, *args, **kwargs)
        self.setModel(model)
        self.menu = self.setup_menu()

        self.frozen_table_view = FrozenTableView(self)
        self.frozen_table_view.update_geometry()

        self.setHorizontalScrollMode(1)
        self.setVerticalScrollMode(1)

        self.horizontalHeader().sectionResized.connect(
            self.update_section_width)
        self.verticalHeader().sectionResized.connect(
            self.update_section_height)

        self.sort_old = [None]
        self.header_class = self.horizontalHeader()
        self.header_class.sectionClicked.connect(self.sortByColumn)
        self.frozen_table_view.horizontalHeader().sectionClicked.connect(
            self.sortByColumn)
        self.horizontalScrollBar().valueChanged.connect(
                        lambda val: self.load_more_data(val, columns=True))
        self.verticalScrollBar().valueChanged.connect(
                        lambda val: self.load_more_data(val, rows=True))

    def update_section_width(self, logical_index, old_size, new_size):
        """Update the horizontal width of the frozen column when a
        change takes place in the first column of the table"""
        if logical_index == 0:
            self.frozen_table_view.setColumnWidth(0, new_size)
            self.frozen_table_view.update_geometry()

    def update_section_height(self, logical_index, old_size, new_size):
        """Update the vertical width of the frozen column when a
        change takes place on any of the rows"""
        self.frozen_table_view.setRowHeight(logical_index, new_size)

    def resizeEvent(self, event):
        """Update the frozen column dimensions.

        Updates takes place when the enclosing window of this
        table reports a dimension change
        """
        QTableView.resizeEvent(self, event)
        self.frozen_table_view.update_geometry()

    def moveCursor(self, cursor_action, modifiers):
        """Update the table position.

        Updates the position along with the frozen column
        when the cursor (selector) changes its position
        """
        current = QTableView.moveCursor(self, cursor_action, modifiers)

        col_width = (self.columnWidth(0) +
                     self.columnWidth(1))
        topleft_x = self.visualRect(current).topLeft().x()

        overflow = self.MoveLeft and current.column() > 1
        overflow = overflow and topleft_x < col_width

        if cursor_action == overflow:
            new_value = (self.horizontalScrollBar().value() +
                         topleft_x - col_width)
            self.horizontalScrollBar().setValue(new_value)
        return current

    def scrollTo(self, index, hint):
        """Scroll the table.

        It is necessary to ensure that the item at index is visible.
        The view will try to position the item according to the
        given hint. This method does not takes effect only if
        the frozen column is scrolled.
        """
        if index.column() > 1:
            QTableView.scrollTo(self, index, hint)

    def load_more_data(self, value, rows=False, columns=False):
        if rows and value == self.verticalScrollBar().maximum():
            self.model().fetch_more(rows=rows)
        if columns and value == self.horizontalScrollBar().maximum():
            self.model().fetch_more(columns=columns)

    def sortByColumn(self, index):
        """ Implement a Column sort """
        frozen_header = self.frozen_table_view.horizontalHeader()
        if not self.isSortingEnabled():
            self.header_class.setSortIndicatorShown(False)
            frozen_header.setSortIndicatorShown(False)
            return
        if self.sort_old == [None]:
            self.header_class.setSortIndicatorShown(True)
        frozen_header.setSortIndicatorShown(index == 0)
        if index == 0:
            sort_order = frozen_header.sortIndicatorOrder()
        else:
            sort_order = self.header_class.sortIndicatorOrder()
        if not self.model().sort(index, sort_order, True):
            if len(self.sort_old) != 2:
                self.header_class.setSortIndicatorShown(False)
                frozen_header.setSortIndicatorShown(False)
            else:
                self.header_class.setSortIndicator(self.sort_old[0],
                                                   self.sort_old[1])
                if index == 0:
                    frozen_header.setSortIndicator(self.sort_old[0],
                                                   self.sort_old[1])
            return
        self.sort_old = [index, self.header_class.sortIndicatorOrder()]

    def change_type(self, func):
        """A function that changes types of cells"""
        model = self.model()
        index_list = self.selectedIndexes()
        [model.setData(i, '', change_type=func) for i in index_list]

    def insert_row_above_selection(self):
        """Insert rows above the selection

        The number of rows inserted depends on the number of selected rows"""
        rows, cols = self._selected_rows_and_cols()
        model = self.model()
        if not model.rowCount():
            model.insertRows(0, 1)
        elif not rows and not cols:
            return
        else:
            min_row = min(rows)
            nrows = len(set(rows))
            model.insertRows(min_row, nrows)

    def insert_row_below_selection(self):
        """Insert rows below the selection

        The number of rows inserted depends on the number of selected rows"""
        rows, cols = self._selected_rows_and_cols()
        model = self.model()
        if not model.rowCount():
            model.insertRows(0, 1)
        elif not rows and not cols:
            return
        else:
            max_row = max(rows)
            nrows = len(set(rows))
            model.insertRows(max_row + 1, nrows)

    def _selected_rows_and_cols(self):
        index_list = self.selectedIndexes()
        if not index_list:
            return [], []
        return list(zip(*[(i.row(), i.column()) for i in index_list]))

    docstrings.delete_params('DataFrameModel.parameters', 'parent')

    @docstrings.dedent
    def set_df(self, df, *args, **kwargs):
        """
        Set the :class:`~pandas.DataFrame` for this table

        Parameters
        ----------
        %(DataFrameModel.parameters.no_parent)s
        """
        model = DataFrameModel(df, self.parent(), *args, **kwargs)
        self.setModel(model)
        self.frozen_table_view.setModel(model)

    def reset_model(self):
        self.model().reset()

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        model = self.model()
        for a in self.dtype_actions.values():
            a.setEnabled(model.dtypes_changeable)
        nrows = max(len(set(self._selected_rows_and_cols()[0])), 1)
        self.insert_row_above_action.setText('Insert %i row%s above' % (
            nrows, 's' if nrows - 1 else ''))
        self.insert_row_below_action.setText('Insert %i row%s below' % (
            nrows, 's' if nrows - 1 else ''))
        self.insert_row_above_action.setEnabled(model.index_editable)
        self.insert_row_below_action.setEnabled(model.index_editable)
        self.menu.popup(event.globalPos())
        event.accept()

    def setup_menu(self):
        """Setup context menu"""
        menu = QMenu(self)
        menu.addAction('Copy', self.copy, QtGui.QKeySequence.Copy)
        menu.addSeparator()
        functions = (("To bool", bool), ("To complex", complex),
                     ("To int", int), ("To float", float),
                     ("To str", six.text_type))
        self.dtype_actions = {
            name: menu.addAction(name, partial(self.change_type, func))
            for name, func in functions}
        menu.addSeparator()
        self.insert_row_above_action = menu.addAction(
            'Insert rows above', self.insert_row_above_selection)
        self.insert_row_below_action = menu.addAction(
            'Insert rows below', self.insert_row_below_selection)
        menu.addSeparator()
        self.set_index_action = menu.addAction(
            'Set as index', partial(self.set_index, False))
        self.append_index_action = menu.addAction(
            'Append to as index', partial(self.set_index, True))
        return menu

    def set_index(self, append=False):
        """Set the index from the selected columns"""
        model = self.model()
        df = model.df
        args = [model.dtypes_changeable, model.index_editable]
        cols = np.unique(self._selected_rows_and_cols()[1])
        if not append:
            cols += len(df.index.names) - 1
            df.reset_index(inplace=True)
        else:
            cols -= 1
        cols = cols.tolist()
        if len(cols) == 1:
            df.set_index(df.columns[cols[0]], inplace=True, append=append)
        else:
            df.set_index(df.columns[cols].tolist(), inplace=True,
                         append=append)
        self.set_df(df, *args)

    def copy(self):
        """Copy text to clipboard"""
        rows, cols = self._selected_rows_and_cols()
        if not rows and not cols:
            return
        row_min, row_max = min(rows), max(rows)
        col_min, col_max = min(cols), max(cols)
        index = header = False
        if col_min == 0:
            col_min = 1
            index = True
        df = self.model().df
        if col_max == 0:  # To copy indices
            contents = '\n'.join(map(str, df.index.tolist()[slice(row_min,
                                                            row_max+1)]))
        else:  # To copy DataFrame
            if (col_min == 0 or col_min == 1) and (df.shape[1] == col_max):
                header = True
            obj = df.iloc[slice(row_min, row_max+1), slice(col_min-1, col_max)]
            output = io.StringIO()
            obj.to_csv(output, sep='\t', index=index, header=header)
            if not six.PY2:
                contents = output.getvalue()
            else:
                contents = output.getvalue().decode('utf-8')
            output.close()
        clipboard = QApplication.clipboard()
        clipboard.setText(contents)


class DataFrameDock(QDockWidget):
    """The QDockWidget for the :class:`DataFrameEditor"""

    def close(self):
        """
        Reimplemented to remove the dock widget from the mainwindow when closed
        """
        mainwindow = self.parent()
        try:
            mainwindow.dataframeeditors.remove(self.widget())
        except Exception:
            pass
        try:
            mainwindow.removeDockWidget(self)
        except Exception:
            pass
        return super(DataFrameDock, self).close()


class DataFrameEditor(DockMixin, QWidget):
    """An editor for data frames"""

    dock_cls = DataFrameDock

    #: A signal that is emitted, if the table is cleared
    cleared = QtCore.pyqtSignal()

    #: A signal that is emitted when a cell has been changed. The argument
    #: is a tuple of two integers and one float:
    #: the row index, the column index and the new value
    cell_edited = QtCore.pyqtSignal(int, int, object, object)

    #: A signal that is emitted, if rows have been inserted into the dataframe.
    #: The first value is the integer of the (original) position of the row,
    #: the second one is the number of rows
    rows_inserted = QtCore.pyqtSignal(int, int)

    @property
    def hidden(self):
        return not self.table.filled

    def __init__(self, *args, **kwargs):
        super(DataFrameEditor, self).__init__(*args, **kwargs)
        self.error_msg = PyErrorMessage(self)

        # Label for displaying the DataFrame size
        self.lbl_size = QLabel()

        # A Checkbox for enabling and disabling the editability of the index
        self.cb_index_editable = QCheckBox('Index editable')

        # A checkbox for enabling and disabling the change of data types
        self.cb_dtypes_changeable = QCheckBox('Datatypes changeable')

        # A checkbox for enabling and disabling sorting
        self.cb_enable_sort = QCheckBox('Enable sorting')

        # A button to open a dataframe from the file
        self.btn_open_df = QToolButton(parent=self)
        self.btn_open_df.setIcon(QIcon(get_icon('run_arrow.png')))
        self.btn_open_df.setToolTip('Open a DataFrame from your disk')

        self.btn_from_console = LoadFromConsoleButton(pd.DataFrame)
        self.btn_from_console.setToolTip('Show a DataFrame from the console')

        # The table to display the DataFrame
        self.table = DataFrameView(pd.DataFrame(), self)

        # format line edit
        self.format_editor = QLineEdit()
        self.format_editor.setText(self.table.model()._format)

        # format update button
        self.btn_change_format = QPushButton('Update')
        self.btn_change_format.setEnabled(False)

        # table clearing button
        self.btn_clear = QPushButton('Clear')
        self.btn_clear.setToolTip(
            'Clear the table and disconnect from the DataFrame')

        # refresh button
        self.btn_refresh = QToolButton()
        self.btn_refresh.setIcon(QIcon(get_icon('refresh.png')))
        self.btn_refresh.setToolTip('Refresh the table')

        # close button
        self.btn_close = QPushButton('Close')
        self.btn_close.setToolTip('Close this widget permanentely')

        # ---------------------------------------------------------------------
        # ------------------------ layout --------------------------------
        # ---------------------------------------------------------------------
        vbox = QVBoxLayout()
        self.top_hbox = hbox = QHBoxLayout()
        hbox.addWidget(self.cb_index_editable)
        hbox.addWidget(self.cb_dtypes_changeable)
        hbox.addWidget(self.cb_enable_sort)
        hbox.addWidget(self.lbl_size)
        hbox.addStretch(0)
        hbox.addWidget(self.btn_open_df)
        hbox.addWidget(self.btn_from_console)
        vbox.addLayout(hbox)
        vbox.addWidget(self.table)
        self.bottom_hbox = hbox = QHBoxLayout()
        hbox.addWidget(self.format_editor)
        hbox.addWidget(self.btn_change_format)
        hbox.addStretch(0)
        hbox.addWidget(self.btn_clear)
        hbox.addWidget(self.btn_close)
        hbox.addWidget(self.btn_refresh)
        vbox.addLayout(hbox)
        self.setLayout(vbox)

        # ---------------------------------------------------------------------
        # ------------------------ Connections --------------------------------
        # ---------------------------------------------------------------------
        self.cb_dtypes_changeable.stateChanged.connect(
            self.set_dtypes_changeable)
        self.cb_index_editable.stateChanged.connect(self.set_index_editable)
        self.btn_from_console.object_loaded.connect(self._open_ds_from_console)
        self.rows_inserted.connect(lambda i, n: self.set_lbl_size_text())
        self.format_editor.textChanged.connect(self.toggle_fmt_button)
        self.btn_change_format.clicked.connect(self.update_format)
        self.btn_clear.clicked.connect(self.clear_table)
        self.btn_close.clicked.connect(self.clear_table)
        self.btn_close.clicked.connect(lambda: self.close())
        self.btn_refresh.clicked.connect(self.table.reset_model)
        self.btn_open_df.clicked.connect(self._open_dataframe)
        self.table.set_index_action.triggered.connect(
            self.update_index_editable)
        self.table.append_index_action.triggered.connect(
            self.update_index_editable)
        self.cb_enable_sort.stateChanged.connect(
            self.table.setSortingEnabled)

    def update_index_editable(self):
        model = self.table.model()
        if len(model.df.index.names) > 1:
            model.index_editable = False
            self.cb_index_editable.setEnabled(False)
        self.cb_index_editable.setChecked(model.index_editable)

    def set_lbl_size_text(self, nrows=None, ncols=None):
        """Set the text of the :attr:`lbl_size` label to display the size"""
        model = self.table.model()
        nrows = nrows if nrows is not None else model.rowCount()
        ncols = ncols if ncols is not None else model.columnCount()
        if not nrows and not ncols:
            self.lbl_size.setText('')
        else:
            self.lbl_size.setText('Rows: %i, Columns: %i' % (nrows, ncols))

    def clear_table(self):
        """Clear the table and emit the :attr:`cleared` signal"""
        df = pd.DataFrame()
        self.set_df(df, show=False)

    def _open_ds_from_console(self, oname, df):
        self.set_df(df)

    @docstrings.dedent
    def set_df(self, df, *args, **kwargs):
        """
        Fill the table from a :class:`~pandas.DataFrame`

        Parameters
        ----------
        %(DataFrameModel.parameters.no_parent)s
        show: bool
            If True (default), show and raise_ the editor
        """
        show = kwargs.pop('show', True)
        self.table.set_df(df, *args, **kwargs)
        self.set_lbl_size_text(*df.shape)
        model = self.table.model()
        self.cb_dtypes_changeable.setChecked(model.dtypes_changeable)

        if len(model.df.index.names) > 1:
            model.index_editable = False
            self.cb_index_editable.setEnabled(False)
        else:
            self.cb_index_editable.setEnabled(True)
        self.cb_index_editable.setChecked(model.index_editable)
        self.cleared.emit()
        if show:
            self.show_plugin()
            self.dock.raise_()

    def set_index_editable(self, state):
        """Set the :attr:`DataFrameModel.index_editable` attribute"""
        self.table.model().index_editable = state == Qt.Checked

    def set_dtypes_changeable(self, state):
        """Set the :attr:`DataFrameModel.dtypes_changeable` attribute"""
        self.table.model().dtypes_changeable = state == Qt.Checked

    def toggle_fmt_button(self, text):
        try:
            text % 1.1
        except (TypeError, ValueError):
            self.btn_change_format.setEnabled(False)
        else:
            self.btn_change_format.setEnabled(
                text.strip() != self.table.model()._format)

    def update_format(self):
        """Update the format of the table"""
        self.table.model().set_format(self.format_editor.text().strip())

    def to_dock(self, main, *args, **kwargs):
        connect = self.dock is None
        super(DataFrameEditor, self).to_dock(main, *args, **kwargs)
        if connect:
            self.dock.toggleViewAction().triggered.connect(self.maybe_tabify)

    def maybe_tabify(self):
        main = self.dock.parent()
        if self.is_shown and main.dockWidgetArea(
                main.help_explorer.dock) == main.dockWidgetArea(self.dock):
            main.tabifyDockWidget(main.help_explorer.dock, self.dock)

    def _open_dataframe(self):
        self.open_dataframe()

    def open_dataframe(self, fname=None, *args, **kwargs):
        """Opens a file dialog and the dataset that has been inserted"""
        if fname is None:
            fname = QFileDialog.getOpenFileName(
                self, 'Open dataset', os.getcwd(),
                'Comma separated files (*.csv);;'
                'Excel files (*.xls *.xlsx);;'
                'JSON files (*.json);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
        if isinstance(fname, pd.DataFrame):
            self.set_df(fname)
        elif not fname:
            return
        else:
            ext = osp.splitext(fname)[1]
            open_funcs = {
                '.xls': pd.read_excel, '.xlsx': pd.read_excel,
                '.json': pd.read_json,
                '.tab': partial(pd.read_csv, delimiter='\t'),
                '.dat': partial(pd.read_csv, delim_whitespace=True),
                }
            open_func = open_funcs.get(ext, pd.read_csv)
            try:
                df = open_func(fname)
            except Exception:
                self.error_msg.showTraceback(
                    '<b>Could not open DataFrame %s with %s</b>' % (
                        fname, open_func))
                return
            self.set_df(df)

    def close(self, *args, **kwargs):
        if self.dock is not None:
            self.dock.close(*args, **kwargs)  # removes the dock window
            del self.dock
        return super(DataFrameEditor, self).close(*args, **kwargs)
