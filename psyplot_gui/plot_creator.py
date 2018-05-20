"""This module contains a widget to create new plots with psyplot

The main class is the :class:`PlotCreator` which is used to handle the
different plotting methods of the :class:`psyplot.project.ProjectPlotter`
class"""
from __future__ import division
import os
import logging
import re
import types
import xarray
from functools import partial
import numpy as np
from collections import defaultdict
from math import floor
from itertools import chain, product, cycle, repeat, starmap
import matplotlib as mpl
import six
from psyplot.utils import _temp_bool_prop
from psyplot.compat.pycompat import map, range, filter, OrderedDict
from psyplot_gui.compat.qtcompat import (
    QWidget, QComboBox, QHBoxLayout, QVBoxLayout, QFileDialog, QToolButton,
    QIcon, Qt, QListView, QtCore, with_qt5, QAbstractItemView, QPushButton,
    QLabel, QValidator, QStyledItemDelegate, QLineEdit, QCheckBox, isstring,
    QTableWidget, QTableWidgetItem, QGridLayout, QIntValidator, QMenu, QAction,
    QInputDialog, QTabWidget, QDoubleValidator, QGraphicsScene, asstring,
    QGraphicsRectItem, QGraphicsView, QDialog, QDialogButtonBox, QSplitter)
from psyplot_gui.common import (get_icon, ListValidator, PyErrorMessage,
                                LoadFromConsoleButton)
from psyplot_gui.preferences import RcParamsTree
import psyplot.project as psy


logger = logging.getLogger(__name__)


class CoordComboBox(QComboBox):
    """Combobox showing coordinate information of a dataset

    This combobox loads its data from the current dataset and allows the
    popups to be left open. It also has a :attr:`leftclick` signal that is
    emitted when the popup is about to be closed because the user clicked on a
    value"""

    close_popups = _temp_bool_prop('close_popups', default=True)
    use_coords = _temp_bool_prop('use_coords', default=False)
    leftclick = QtCore.pyqtSignal(QComboBox)

    def __init__(self, ds_func, dim, parent=None):
        """
        Parameters
        ----------
        ds_func: function
            The function that, when called without arguments, returns the
            xarray.Dataset to use
        dim: str
            The coordinate name for this combobox
        parent: PyQt5.QtWidgets.QWidget
            The parent widget"""
        super(CoordComboBox, self).__init__(parent)
        self.dim = dim
        self._is_empty = True
        self.get_ds = ds_func
        self._changed = False
        self._right_clicked = False

        # modify the view
        view = self.view()
        # We allow the selection of multiple items with a left-click
        view.setSelectionMode(QListView.ExtendedSelection)
        # The following modifications will cause this behaviour:
        #     Left-click:
        #         Case 1: Any of the already existing plot arrays is selected
        #             Add the selected values in the popup to the dimension in
        #             the currently selected plot items
        #         Case 2: No plot arrays are selected or none exists
        #             Create new plot items from the selection in the popup
        #     Right-Click:
        #         Set the currentIndex which will be used when new plot items
        #         are created
        #
        # Therefore we first enable a CustomContextMenu
        view.setContextMenuPolicy(Qt.CustomContextMenu)

        # We have to disable the default MousePressEvent in the views viewport
        # because otherwise the Left-click behaviour would occur as well when
        # hitting the right button
        # Therefore:
        # install an EventFilter such that only the customContextMenuRequested
        # signal of the view is fired and not the pressed signal (which would
        # hide the popup)
        view.viewport().installEventFilter(self)
        view.customContextMenuRequested.connect(self.right_click)
        # Furthermore we implement, that the pop up shall not be closed if the
        # keep open property is True. Therefore we have to track when the
        # index changes
        view.pressed.connect(self.handleItemPressed)
        view.doubleClicked.connect(self.hide_anyway)

    def eventFilter(self, obj, event):
        """Reimplemented to filter right-click events on the view()"""
        ret = ((event.type() == QtCore.QEvent.MouseButtonPress) and
               event.button() == Qt.RightButton)
        return ret

    def handleItemPressed(self, index):
        """Function to be called when an item is pressed to make sure that
        we know whether anything changed before closing the popup"""
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
        self.setCurrentIndex(0)
        self._changed = True

    def right_click(self, point):
        """Function that is called when an item is right_clicked"""
        ind = self.view().indexAt(point).row()
        self.setCurrentIndex(ind)
        self._right_clicked = True
        self._changed = True

    def hide_anyway(self, index=None):
        """Function to hide the popup despite of the :attr:`_changed` attribute
        """
        self._changed = True
        self.hidePopup()

    def hidePopup(self):
        """Reimplemented to only close the popup when the :attr:`close_popup`
        attribute is True or it is clicked outside the window"""
        if not self._right_clicked:
            self.leftclick.emit(self)
        if not self._changed or self.close_popups:
            super(CoordComboBox, self).hidePopup()
        self._changed = False
        self._right_clicked = False

    def mousePressEvent(self, *args, **kwargs):
        """Reimplemented to fill the box with content from the dataset"""
        self.load_coord()
        super(CoordComboBox, self).mousePressEvent(*args, **kwargs)

    def mouseDoubleClickEvent(self, *args, **kwargs):
        """Reimplemented to fill the box with content from the dataset"""
        self.load_coord()
        super(CoordComboBox, self).mouseDoubleClickEvent(*args, **kwargs)

    def load_coord(self):
        """Load the coordinate data from the dataset and fill the combobox with
        it (if it is empty)"""
        if self._is_empty:
            ds = self.get_ds()
            self.addItem('')
            if self.use_coords:
                self.addItems(ds[self.dim].astype(str).values)
            else:
                self.addItems(list(map(str, range(len(ds[self.dim])))))
            self._is_empty = False


class ArrayNameValidator(QValidator):
    """Class to make sure that only those arrays names are inserted that are
    not currently in the main project or the tree"""

    def __init__(self, text, table, *args, **kwargs):
        super(ArrayNameValidator, self).__init__(*args, **kwargs)
        self.table = table
        self.current_text = text
        self.current_names = list(table.current_names)

    def fixup(self, s):
        s = asstring(s)
        if not s:
            return self.table.next_available_name()
        return self.table.next_available_name(s + '_{0}')

    def validate(self, s, pos):
        s = asstring(s)
        if not s:
            return QValidator.Intermediate, s, pos
        elif s == self.current_text:
            pass
        elif s in chain(psy.gcp(True).arr_names, self.current_names):
            return QValidator.Intermediate, s, pos
        return QValidator.Acceptable, s, pos


class ArrayNameItemDelegate(QStyledItemDelegate):
    """Delegate using the :class:`ArrayNameValidator` for validation"""

    def createEditor(self, widget, option, index):
        if not index.isValid():
            return
        editor = QLineEdit(widget)
        item = self.parent().item(index.row(), index.column())
        validator = ArrayNameValidator(item.text() if item else '',
                                       self.parent(), editor)
        editor.setValidator(validator)
        return editor


class VariableItemDelegate(QStyledItemDelegate):
    """Delegate alowing only the variables in the parents dataset.

    The parent must hold a `get_ds` method that returns a dataset when called
    """

    def createEditor(self, widget, option, index):
        if not index.isValid():
            return
        editor = QLineEdit(widget)
        ds = self.parent().get_ds()
        validator = ListValidator(ds.variables.keys(), self.parent().sep,
                                  editor)
        editor.setValidator(validator)
        return editor


class VariablesTable(QTableWidget):
    """Table to display the variables of a dataset"""

    #: The variables in the dataset
    variables = []

    @property
    def selected_variables(self):
        """The currently selected variables"""
        return [
            self.variables[i] for i in map(
                list(map(asstring, self.variables)).index,
                sorted(set(item.text() for item in self.selectedItems()
                           if item.column() == 0)))]

    def __init__(self, get_func, columns=['long_name', 'dims', 'shape'],
                 *args, **kwargs):
        """
        Parameters
        ----------
        get_func: function
            The function that, when called without arguments, returns the
            xarray.Dataset to use
        columns: list of str
            The attribute that will be used as columns for the variables"""
        super(VariablesTable, self).__init__(*args, **kwargs)
        self.variables = []
        self.get_ds = get_func
        self.set_columns(columns)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)

    def set_columns(self, columns=None):
        if columns is None:
            columns = self.column_labels
        else:
            self.column_labels = columns
        self.setColumnCount(len(columns) + 1)
        self.setHorizontalHeaderLabels(['variable'] + columns)

    def fill_from_ds(self, ds=None):
        """Clear the table and insert items from the given `dataset`"""
        self.clear()
        self.set_columns()
        if ds is None:
            ds = self.get_ds()
        if ds is None:
            return
        coords = list(ds.coords)
        self.variables = vnames = [v for v in ds.variables if v not in coords]
        self.setRowCount(len(vnames))
        for i, vname in enumerate(vnames):
            variable = ds.variables[vname]
            self.setItem(i, 0, QTableWidgetItem(asstring(vname)))
            for j, attr in enumerate(self.column_labels, 1):
                if attr == 'dims':
                    self.setItem(i, j, QTableWidgetItem(
                        ', '.join(variable.dims)))
                else:
                    self.setItem(i, j, QTableWidgetItem(
                        str(variable.attrs.get(attr, getattr(
                            variable, attr, '')))))


class CoordsTable(QTableWidget):
    """A table showing the coordinates of in a dataset via instances of
    :class:`CoordComboBox`"""

    def __init__(self, get_func, *args, **kwargs):
        """
        Parameters
        ----------
        get_func: function
            The function that, when called without arguments, returns the
            xarray.Dataset to use
        ``*args, **kwargs``
            Determined by the :class:`PyQt5.QtWidgets.QTableWidget` class"""
        super(CoordsTable, self).__init__(*args, **kwargs)
        self.get_ds = get_func
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setRowCount(1)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setStretchLastSection(True)

    @property
    def combo_boxes(self):
        """A list of :class:`CoordComboBox` in this table"""
        return list(filter(
            lambda w: w is not None,
            (self.cellWidget(0, i) for i in range(self.columnCount()))))

    def fill_from_ds(self, ds=None):
        """Clear the table and create new comboboxes"""
        for cb in self.combo_boxes:
            cb.blockSignals(True)
        self.clear()
        if ds is None:
            ds = self.get_ds()
        if ds is None:
            return
        coords = list(ds.coords)
        vnames = [v for v in ds.variables if v not in coords]
        self.dims = dims = list(set(
            chain(*(ds.variables[vname].dims for vname in vnames))))
        try:
            dims.sort()
        except TypeError:
            pass
        self.setColumnCount(len(dims))
        for i, dim in enumerate(dims):
            header_item = QTableWidgetItem(dim)
            self.setHorizontalHeaderItem(i, header_item)
            self.setCellWidget(0, i, CoordComboBox(self.get_ds, dim))

    def sizeHint(self):
        """Reimplemented to adjust the heigth based upon the header and the
        first row"""
        return QtCore.QSize(
            super(CoordsTable, self).sizeHint().width(),
            self.horizontalHeader().height() + self.rowHeight(0))


class DragDropTable(QTableWidget):
    """Table that allows to exchange rows via drag and drop

    This class was mainly taken from
    http://stackoverflow.com/questions/26227885/drag-and-drop-rows-within-qtablewidget
    """

    def __init__(self, *args, **kwargs):
        super(DragDropTable, self).__init__(*args, **kwargs)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dropEvent(self, event):
        if event.source() == self and (
                event.dropAction() == Qt.MoveAction or
                self.dragDropMode() == QAbstractItemView.InternalMove):
            self.dropOn(event)

        else:
            super(DragDropTable, self).dropEvent(event)

    def moveRows(self, row, remove=False):
        """Move all selected rows to the given `row`"""
        selRows = sorted({ind.row() for ind in self.selectedIndexes()})
        top = selRows[0]

        dropRow = row
        if dropRow == -1:
            dropRow = self.rowCount()
        offset = dropRow - top

        for i, row in enumerate(selRows):
            r = row + offset
            if r > self.rowCount() or r < 0:
                r = 0
            self.insertRow(r)

        selRows = sorted({ind.row() for ind in self.selectedIndexes()})

        top = selRows[0]
        offset = dropRow - top
        for i, row in enumerate(selRows):
            r = row + offset
            if r > self.rowCount() or r < 0:
                r = 0

            for j in range(self.columnCount()):
                source = QTableWidgetItem(self.item(row, j))
                self.setItem(r, j, source)

        if remove:
            for row in reversed(selRows):
                self.removeRow(row)

    def droppingOnItself(self, event, index):
        dropAction = event.dropAction()

        if self.dragDropMode() == QAbstractItemView.InternalMove:
            dropAction = Qt.MoveAction

        if (event.source() == self and
                event.possibleActions() & Qt.MoveAction and
                dropAction == Qt.MoveAction):
            selectedIndexes = self.selectedIndexes()
            child = index
            while child.isValid() and child != self.rootIndex():
                if child in selectedIndexes:
                    return True
                child = child.parent()

        return False

    def dropOn(self, event):
        if event.isAccepted():
            return False, None, None, None

        index = QtCore.QModelIndex()
        row = -1

        if self.viewport().rect().contains(event.pos()):
            index = self.indexAt(event.pos())
            if not index.isValid() or not self.visualRect(index).contains(
                    event.pos()):
                index = self.rootIndex()

        if self.model().supportedDropActions() & event.dropAction():
            if index != self.rootIndex():
                dropIndicatorPosition = self.position(
                    event.pos(), self.visualRect(index), index)

                if dropIndicatorPosition == QAbstractItemView.AboveItem:
                    row = index.row()
                    # index = index.parent()
                elif dropIndicatorPosition == QAbstractItemView.BelowItem:
                    row = index.row() + 1
                    # index = index.parent()
                else:
                    row = index.row()

            if not self.droppingOnItself(event, index):
                self.moveRows(row, remove=event.source() is None)
                event.accept()

    def position(self, pos, rect, index):
        r = QAbstractItemView.OnViewport
        margin = 2
        if pos.y() - rect.top() < margin:
            r = QAbstractItemView.AboveItem
        elif rect.bottom() - pos.y() < margin:
            r = QAbstractItemView.BelowItem
        elif rect.contains(pos, True):
            r = QAbstractItemView.OnItem

        if r == QAbstractItemView.OnItem and not (
                self.model().flags(index) & Qt.ItemIsDropEnabled):
            if pos.y() < rect.center().y():
                r = QAbstractItemView.AboveItem
            else:
                r = QAbstractItemView.BelowItem
        return r


class ArrayTable(DragDropTable):
    """Table that shows the arrays that will be used for plotting

    It contains the following columns:

    1. The variable column which holds the variable names of the arrays.
       multiple variables may be separated by ';;'
    2. The array name. The :attr:`psyplot.data.InteractiveBase.arr_name`
       attribute. Depending on the plot methods
       :attr:`~psyplot.project._PlotterInterface._prefer_list`, multiple
       array names are allowed or not. If this attribute is True,
       arrays with the same array name will be concatenated into one
       :class:`psyplot.data.InteractiveList`
    3. The axes column. Use the right-click context menu to select a
       subplot
    4. The check column. Checks for variable names, array names, axes and
       dimensions via the :meth:`psyplot.project._PlotterInterface.check_data`
       method
    5. Columns containing the dimension informations"""

    #: Pattern to interprete subplots
    subplot_patt = re.compile(r'\((?P<fig>\d+),\s*'  # figure
                              r'(?P<rows>\d+),\s*'   # rows
                              r'(?P<cols>\d+),\s*'   # columns
                              r'(?P<num1>\d+),\s*'   # position
                              r'(?P<num2>\d+)\s*\)'  # end subplot
                              )

    #: pattern to interprete arbitrary axes
    axes_patt = re.compile(r'\((?P<fig>\d+),\s*'     # figure
                           r'(?P<x0>0*\.\d+),\s*'    # lower left x
                           r'(?P<y0>0*\.\d+),\s*'    # lower left y
                           r'(?P<x1>0*\.\d+),\s*'    # upper right x
                           r'(?P<y1>0*\.\d+)\s*\)'   # upper right y
                           )

    #: The separator for variable names
    sep = ';;'

    #: Tool tip for the variable column
    VARIABLE_TT = ("The variables of the array from the dataset. Multiple"
                   "variables for one array may be separated by '%s'" % (
                       sep))

    #: Base tool tip for a dimension column
    DIMS_TT = ("The values for dimension %s."
               " You can use integers either explicit, e.g."
               "<ul>"
               "<li>1, 2, 3, ...,</li>"
               "</ul>"
               "or slices like <em>start:end:step</em>, e.g."
               "<ul>"
               "<li>'1:6:2'</li>"
               "</ul>"
               "where the latter is equivalent to '1, 3, 5'")

    def dropEvent(self, event):
        """Reimplemented to call the :meth:`check_arrays` after the call"""
        # apparently the row deletion occurs after the call of this method.
        # therefore our call of `check_arrays` leads to the (wrong) result
        # of a duplicated entry. We therefore filter them out here and make
        # sure that those arrays are not considered when checking for
        # duplicates
        messages = dict(
            zip(self.current_names, [msg for b, msg in self.check_arrays()]))
        super(ArrayTable, self).dropEvent(event)
        ignores = [arr_name for arr_name, msg in messages.items()
                   if not msg.startswith('Found duplicated entry of')]
        self.check_arrays(ignore_duplicates=ignores)

    @property
    def prefer_list(self):
        """Return the _prefer_list attribute of the plot_method"""
        return self.plot_method and self.plot_method._prefer_list

    @property
    def current_names(self):
        """The names that are currently in use"""
        if self.prefer_list:
            return []
        arr_col = self.arr_col
        return [asstring(item.text()) for item in filter(None, map(
            lambda i: self.item(i, arr_col), range(self.rowCount())))]

    @property
    def vnames(self):
        """The list of variable names per array"""
        var_col = self.var_col
        return [self.item(i, var_col).text().split(';;')
                for i in range(self.rowCount())]

    @property
    def arr_names_dict(self):
        """The final dictionary containing the array names necessary for the
        `arr_names` parameter in the
        :meth:`psyplot.data.ArrayList.from_dataset` method """
        ret = OrderedDict()
        arr_col = self.arr_col
        for irow in range(self.rowCount()):
            arr_name = asstring(self.item(irow, arr_col).text())
            if self.plot_method and self.plot_method._prefer_list:
                d = ret.setdefault(arr_name, defaultdict(list))
                d['name'].append(self._get_variables(irow))
                for key, val in self._get_dims(irow).items():
                    d[key].append(val)
            else:
                ret[arr_name] = d = {'name': self._get_variables(irow)}
                d.update(self._get_dims(irow))

        return ret

    @property
    def axes(self):
        """A list of axes settings corresponding to the arrays in the
        :attr:`arr_names_dict`"""
        ret = []
        d = set()
        arr_col = self.arr_col
        axes_col = self.axes_col
        # get the projection
        pm = self.plot_method
        kwargs = {}
        if pm is not None:
            projection = self.plot_method.plotter_cls._get_sample_projection()
            if projection is not None:
                kwargs['projection'] = projection
        for irow in range(self.rowCount()):
            arr_name = self.item(irow, arr_col).text()
            if arr_name in d:
                continue
            d.add(arr_name)
            axes_type, args = self.axes_info(self.item(irow, axes_col))
            if axes_type == 'subplot':
                ret.append(SubplotCreator.create_subplot(*args, **kwargs))
            elif axes_type == 'axes':
                ret.append(AxesCreator.create_axes(*args, **kwargs))
            else:
                ret.append(None)
        return ret

    @property
    def var_col(self):
        """The index of the variable column"""
        return self.desc_cols.index(self.VARIABLE_LABEL)

    @property
    def arr_col(self):
        """The index of the array name column"""
        return self.desc_cols.index(self.ARRAY_LABEL)

    @property
    def axes_col(self):
        """The index of the axes column"""
        return self.desc_cols.index(self.AXES_LABEL)

    @property
    def check_col(self):
        """The index of the check column"""
        return self.desc_cols.index(self.CHECK_LABEL)

    def __init__(self, get_func, columns=[], *args, **kwargs):
        """
        Parameters
        ----------
        get_func: function
            The function that, when called without arguments, returns the
            xarray.Dataset to use
        columns: list of str
            The coordinates in the dataset"""
        super(ArrayTable, self).__init__(*args, **kwargs)
        self.get_ds = get_func
        self.VARIABLE_LABEL = 'variable'
        self.ARRAY_LABEL = 'array name'
        self.AXES_LABEL = 'axes'
        self.CHECK_LABEL = 'check'
        self.desc_cols = [self.VARIABLE_LABEL, self.ARRAY_LABEL,
                          self.AXES_LABEL, self.CHECK_LABEL]
        self.plot_method = None
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showAxesCreator)
        self.set_columns(columns)
        self.setItemDelegateForColumn(self.var_col, VariableItemDelegate(self))
        self.setItemDelegateForColumn(
            self.arr_col, ArrayNameItemDelegate(self))
        self.itemChanged.connect(self.check_item)
        self.itemChanged.connect(self.update_other_items)

    def set_columns(self, columns):
        """Set the columns of the table

        Parameters
        ----------
        columns: list of str
            The coordinates in the dataset"""
        if columns is None:
            columns = self.column_labels
        else:
            self.column_labels = columns
        self.setColumnCount(len(columns) + len(self.desc_cols))
        self.setHorizontalHeaderLabels(self.desc_cols + columns)
        for i, col in enumerate(columns, len(self.desc_cols)):
            self.horizontalHeaderItem(i).setToolTip(self.DIMS_TT % col)
        self.horizontalHeaderItem(self.var_col).setToolTip(self.VARIABLE_TT)

    def setup_from_ds(self, ds=None, plot_method=None):
        """Fill the table based upon the given dataset.

        Parameters
        ----------
        ds: xarray.Dataset or None
            If None, the dataset from the :attr:`get_ds` function is used
        plot_method: psyplot.project._PlotterInterface or None
            The plot method of the :class:`psyplot.project.ProjectPlotter`
            class or None if no plot shall be made"""
        self.clear()
        self.setRowCount(0)
        if ds is None:
            ds = self.get_ds()
        if plot_method is not None:
            self.set_pm(plot_method)
        if ds is None:
            self.set_columns([])
            return
        coords = list(ds.coords)
        vnames = [v for v in ds.variables if v not in coords]
        self.dims = dims = list(
            set(chain(*(ds.variables[vname].dims for vname in vnames))))
        try:
            dims.sort()
        except TypeError:
            pass
        self.set_columns(dims)

    def next_available_name(self, *args, **kwargs):
        """Gives the next possible name to use"""
        counter = iter(range(1000))
        current_names = self.current_names
        mp = psy.gcp(True)
        while True:
            name = mp.next_available_name(*args, counter=counter, **kwargs)
            if name not in current_names:
                return name

    def insert_array(self, name, check=True, **kwargs):
        """Appends the settings for an array the the list in a new row"""
        dims = set(self.get_ds().variables[name].dims)
        irow = self.rowCount()
        self.setRowCount(irow + 1)
        self.setItem(irow, 0, QTableWidgetItem(asstring(name)))
        self.setItem(irow, 1, QTableWidgetItem(self.next_available_name()))
        self.setItem(irow, 2, QTableWidgetItem(''))
        for dim in dims.intersection(kwargs):
            icol = len(self.desc_cols) + self.dims.index(dim)
            self.setItem(irow, icol, QTableWidgetItem(kwargs[dim]))
        if check:
            self.check_array(irow)

    def remove_arrays(self, selected=True):
        """Remove array rows from the list

        Parameters
        ----------
        selected: bool
            If True, only the selected rows are removed"""
        if selected:
            irows = sorted({ind.row() for ind in self.selectedIndexes()})
        else:
            irows = list(range(self.rowCount()))
        for irow in irows[::-1]:
            self.removeRow(irow)

    def update_selected(self, check=True, dims={}):
        """Updates the dimensions of the selectiond arrays with the given
        `dims`

        Parameters
        ----------
        check: bool
            whether the array shall be checked afterwards
        dims: dict
            a mapping from coordinate names to string values that shall be
            appended to the current text"""
        ds = self.get_ds()
        irows = {item.row() for item in self.selectedItems()}
        var_col = self.desc_cols.index(self.VARIABLE_LABEL)
        for irow in irows:
            vname = asstring(
                self.item(irow, var_col).text()).split(self.sep)[0].strip()
            var_dims = set(ds.variables[vname].dims)
            for dim in var_dims.intersection(dims):
                icol = len(self.desc_cols) + self.dims.index(dim)
                item = self.item(irow, icol)
                curr_text = asstring(item.text())
                if curr_text:
                    curr_text += ', '
                item.setText(curr_text + dims[dim])
        if check:
            for irow in irows:
                self.check_array(irow)

    def add_subplots(self, rows, cols, maxn=None):
        """Add multiple subplots to the selected arrays"""
        import matplotlib.pyplot as plt
        irows = sorted({ind.row() for ind in self.selectedIndexes()})
        irows = irows or list(range(self.rowCount()))
        maxn = maxn or rows * cols
        figs = chain(*(
            [i] * maxn for i in range(1, 1000) if i not in plt.get_fignums()))
        nums = cycle(range(1, maxn + 1))
        seen = set()
        axes_col = self.desc_cols.index(self.AXES_LABEL)
        arr_col = self.desc_cols.index(self.ARRAY_LABEL)
        for irow in irows:
            arr_item = self.item(irow, arr_col)
            if arr_item is None or arr_item.text() in seen:
                continue
            seen.add(arr_item.text())
            num = next(nums)
            text = '(%i, %i, %i, %i, %i)' % (
                next(figs), rows, cols, num, num)
            item = QTableWidgetItem(text)
            self.setItem(irow, axes_col, item)

    def add_single_subplot(self, rows, cols, row, col):
        """Add one subplot to the selected arrays on multiple figures"""
        import matplotlib.pyplot as plt
        irows = sorted({ind.row() for ind in self.selectedIndexes()})
        irows = irows or list(range(self.rowCount()))
        figs = (num for num in range(1, 1000) if num not in plt.get_fignums())
        num = (row - 1) * rows + col
        seen = set()
        axes_col = self.desc_cols.index(self.AXES_LABEL)
        arr_col = self.desc_cols.index(self.ARRAY_LABEL)
        for irow in irows:
            arr_item = self.item(irow, arr_col)
            if arr_item is None or arr_item.text() in seen:
                continue
            seen.add(arr_item.text())
            text = '(%i, %i, %i, %i, %i)' % (
                next(figs), rows, cols, num, num)
            item = QTableWidgetItem(text)
            self.setItem(irow, axes_col, item)

    def showAxesCreator(self, pos):
        """Context menu for right-click on a row"""
        irows = sorted({ind.row() for ind in self.selectedIndexes()})
        if not irows:
            return
        menu = QMenu(self)
        menu.addAction(self.axes_creator_action(irows))
        menu.exec_(self.mapToGlobal(pos))

    def axes_creator_action(self, rows):
        """Action to open a :class:`AxesCreatorCollection` for the selected
        rows"""
        axes_col = self.desc_cols.index(self.AXES_LABEL)
        items = [self.item(row, axes_col) for row in rows]
        action = QAction('Select subplot', self)
        types_and_args = list(
            filter(lambda t: t[0], map(self.axes_info, items)))
        types = [t[0] for t in types_and_args]
        if types and all(t == types[0] for t in types):
            if types[0] == 'subplot':
                creator_kws = ['fig', 'rows', 'cols', 'num1', 'num2']
            elif types[0] == 'axes':
                creator_kws = ['fig', 'x0', 'y0', 'x1', 'y1']
            else:
                creator_kws = []
            func_name = types[0]
            args = [t[1] for t in types_and_args]

            #: the initialization keywords of the :class:`SubplotCreator` class
            kwargs = {}

            if len(items) > 0:
                kwargs['fig'] = ''

            for kw, vals in zip(creator_kws, zip(*args)):
                if all(val == vals[0] for val in vals):
                    kwargs[kw] = vals[0]
        else:
            func_name = None
            kwargs = {}

        action.triggered.connect(
            self._open_axes_creator(items, func_name, kwargs))
        return action

    def _change_axes(self, items, iterator):
        seen = set()
        arr_col = self.desc_cols.index(self.ARRAY_LABEL)
        for item, text in zip(items, iterator):
            arr_name = self.item(item.row(), arr_col).text()
            if arr_name in seen:
                continue
            seen.add(arr_name)
            item.setText(text)

    def _open_axes_creator(self, items, func_name, kwargs):

        def func():
            if hasattr(self, '_axes_creator'):
                self._axes_creator.close()
            self._axes_creator = obj = AxesCreatorCollection(
                func_name, kwargs, parent=self)
            obj.okpressed.connect(partial(self._change_axes, items))
            obj.exec_()
        return func

    def axes_info(self, s):
        """Interpretes an axes information"""
        s = asstring(s) if isstring(s) else asstring(s.text())
        m = self.subplot_patt.match(s)
        if m:
            return 'subplot', list(map(int, m.groups()))
        m = self.axes_patt.match(s)
        if m:
            return 'axes', [int(m.groupdict()['fig'])] + list(map(
                float, m.groups()[1:]))
        return None, None

    def set_pm(self, s):
        """Set the plot method"""
        s = asstring(s)
        self.plot_method = getattr(psy.plot, s, None)
        self.check_arrays()

    def check_item(self, item):
        """Check the array corresponding to the given item"""
        if item.column() == self.desc_cols.index(self.CHECK_LABEL):
            return
        for irow in range(self.rowCount()):
            other_item = self.item(
                irow, self.desc_cols.index(self.ARRAY_LABEL))
            if other_item is not None:
                self.check_array(irow)

    def update_other_items(self, item):
        """Updates the axes information of the other items corresponding
        that have the same array name as the array corresponding to the given
        `item`"""
        axes_col = self.desc_cols.index(self.AXES_LABEL)
        if not self.prefer_list or item.column() != axes_col:
            return
        this_row = item.row()
        arr_col = self.desc_cols.index(self.ARRAY_LABEL)
        arr_item = self.item(this_row, arr_col)
        if arr_item is None:
            return
        arr_name = arr_item.text()
        self.blockSignals(True)
        for row in range(self.rowCount()):
            if row != this_row:
                arr_item2 = self.item(row, arr_col)
                if arr_item2 is not None and arr_item2.text() == arr_name:
                    self.item(row, axes_col).setText(item.text())
        self.blockSignals(False)

    def get_all_rows(self, row):
        """Return all the rows that have the same array name as the given `row`
        """
        def check_item(row):
            item = self.item(row, arr_col)
            return item is not None and item.text() == arr_name

        if self.plot_method is None or not self.plot_method._prefer_list:
            return [row]
        arr_col = self.desc_cols.index(self.ARRAY_LABEL)
        arr_name = self.item(row, arr_col).text()
        return [r for r in range(self.rowCount()) if check_item(r)]

    def check_array(self, row, ignore_duplicates=[]):
        """check whether the array variables are valid, the array name is
        valid, the axes info is valid and the dimensions"""
        def set_check(row, valid, msg):
            check_item = QTableWidgetItem()
            check_item.setFlags(check_item.flags() ^ Qt.ItemIsEditable)
            if valid:
                check_item.setIcon(QIcon(get_icon('valid.png')))
            elif valid is None:
                check_item.setIcon(QIcon(get_icon('warning.png')))
                check_item.setToolTip(msg)
            else:
                check_item.setIcon(QIcon(get_icon('invalid.png')))
                check_item.setToolTip(msg)
            self.setItem(row, check_col, check_item)
            self.resizeColumnToContents(check_col)

        check_col = self.desc_cols.index(self.CHECK_LABEL)
        valid = True
        msg = ''

        # ---------------------------------------------------------------------
        # ----------------- check if a variable is provided -------------------
        # ---------------------------------------------------------------------

        var_item = self.item(row, self.desc_cols.index(self.VARIABLE_LABEL))
        if var_item is not None and not asstring(var_item.text()).strip():
            valid = False
            msg = 'At least one variable name must be provided!'

        # ---------------------------------------------------------------------
        # ----------------- check for duplicates of array names ---------------
        # ---------------------------------------------------------------------

        arr_col = self.desc_cols.index(self.ARRAY_LABEL)
        arr_item = self.item(row, arr_col)
        if valid and arr_item is not None:
            arr_name = arr_item.text()
            if arr_name not in ignore_duplicates:
                if not arr_name:
                    msg = 'An array name must be provided'
                    valid = False
                elif (len([name for name in self.current_names
                          if name == arr_name]) > 1):
                    valid = False
                    msg = "Found duplicated entry of '%s'" % arr_name

        # ---------------------------------------------------------------------
        # ------- check the plotmethod if necessary and set the icon ----------
        # ---------------------------------------------------------------------

        if valid and self.plot_method is not None:
            rows = self.get_all_rows(row)
            checks, messages = self.plot_method.check_data(
                    self.get_ds(),
                    name=list(map(self._get_variables, rows)),
                    dims=list(map(self._get_dims, rows)))
            for row2, valid, msg in zip(rows, checks, messages):
                set_check(row2, valid, msg)
            valid = checks[rows.index(row)]
            msg = messages[rows.index(row)]
        else:
            set_check(row, valid, msg)

        return valid, msg

    def check_arrays(self, **kwargs):
        """Convenience function to check all arrays using the
        :meth:`check_array` method"""
        return list(map(partial(self.check_array, **kwargs),
                        range(self.rowCount())))

    def _str2slice(self, s):
        s = s.strip()
        if not s:
            return []
        s = s.split(':')
        if len(s) > 1:
            return range(*map(int, s[:3]))
        return [int(s[0])]

    def _get_dims(self, row):
        start = len(self.desc_cols)
        ret = {}
        for dim, item in zip(self.dims,
                             map(lambda col: self.item(row, col),
                                 range(start, self.columnCount()))):
            if item:
                text = asstring(item.text())
                if text:
                    slices = list(
                        chain(*map(self._str2slice, text.split(','))))
                    if len(slices) == 1:
                        slices = slices[0]
                    ret[dim] = slices
        return ret

    def _get_variables(self, row):
        var_col = self.desc_cols.index(self.VARIABLE_LABEL)
        ret = [s.strip() for s in asstring(
                   self.item(row, var_col).text()).split(self.sep)]
        ds = self.get_ds()
        for i, name in enumerate(ret):
            ret[i] = next(v for v in ds if asstring(v) == name)
        if len(ret) == 1:
            return ret[0]
        return ret


class SubplotCreator(QWidget):
    """Select a subplot to which will be created (if not already existing) when
    making the plot"""

    def __init__(self, fig=None, rows=1, cols=1, num1=1, num2=None, *args,
                 **kwargs):
        """
        Parameters
        ----------
        fig: int or None
            The number of the figure
        rows: int
            The number of rows for the gridspec
        cols: int
            The number of columns for the gridspec
        num1: int
            The number of the upper left corner starting from 1
        num2: int or None
            The number of the lower right corner starting from 1. If None,
            `num1` is used"""
        super(SubplotCreator, self).__init__(*args, **kwargs)

        self.fig_label = QLabel('Figure number:', self)
        if fig is None:
            import matplotlib.pyplot as plt
            fig = next(
                num for num in range(1, 1000) if num not in plt.get_fignums())
        self.fig_edit = QLineEdit(str(fig), self)
        self.fig_edit.setValidator(QIntValidator())

        self.rows_label = QLabel('No. of rows:', self)
        self.rows_edit = QLineEdit(str(rows), self)
        self.rows_edit.setValidator(QIntValidator(1, 9999, parent=self))

        self.cols_label = QLabel('No. of columns:', self)
        self.cols_edit = QLineEdit(str(cols), self)
        self.cols_edit.setValidator(QIntValidator(1, 9999, parent=self))

        self.num1_label = QLabel('Subplot number:', self)
        self.num1_edit = QLineEdit(str(num1), self)
        self.num1_edit.setValidator(QIntValidator(
            1,  max(1, (rows or 1)*(cols or 1)), self.num1_edit))

        self.num2_label = QLabel('End of the plot', self)
        self.num2_edit = QLineEdit(str(num2 or num1))
        self.num2_edit.setValidator(QIntValidator(
            num1,  max(1, (rows or 1)*(cols or 1)), self.num2_edit))

        self.table = table = QTableWidget(self)
        table.setSelectionMode(QAbstractItemView.ContiguousSelection)
        table.resizeRowsToContents()
        table.resizeColumnsToContents()
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setup_table()
        self.cols_edit.textChanged.connect(lambda s: self.setup_table())
        self.rows_edit.textChanged.connect(lambda s: self.setup_table())
        self.num1_edit.textChanged.connect(self.set_selected_from_num1)
        self.num1_edit.textChanged.connect(self.set_num2_validator)
        self.num2_edit.textChanged.connect(self.set_selected_from_num2)
        table.itemSelectionChanged.connect(self.update_num_edit)

        layout = QGridLayout()
        layout.addWidget(self.fig_label, 0, 0)
        layout.addWidget(self.fig_edit, 0, 1)
        layout.addWidget(self.rows_label, 1, 0)
        layout.addWidget(self.rows_edit, 1, 1)
        layout.addWidget(self.cols_label, 2, 0)
        layout.addWidget(self.cols_edit, 2, 1)
        layout.addWidget(self.num1_label, 3, 0)
        layout.addWidget(self.num1_edit, 3, 1)
        layout.addWidget(self.num2_label, 4, 0)
        layout.addWidget(self.num2_edit, 4, 1)

        layout.addWidget(self.table, 1, 2, 4, 4)

        self.setLayout(layout)

    @staticmethod
    def create_subplot(fig=None, rows=1, cols=1, num1=1, num2=None, **kwargs):
        """Create a subplot for the given figure

        Parameters
        ----------
        fig: :class:`matplotlib.figure.Figure` or int
            If integer, the :func:`matplotlib.pyplot.figure` function is used
        rows: int
            Number of rows for the gridspec
        cols: int
            Number of columns for the gridspec
        num1: int
            The subplot number of the upper left corner in the grid (starting
            from 1!)
        num2: None or int
            The subplot number of the lower left corner in the grid (starting
            from 1!). If None, `num1` will be used
        ``**kwargs``
            Any other keyword argument for the
            :meth:`matplotlib.figure.Figure.add_subplot` method

        Returns
        -------
        mpl.axes.Subplot
            The new created subplot"""
        if not isinstance(fig, mpl.figure.Figure):
            import matplotlib.pyplot as plt
            fig = plt.figure(fig or next(
                num for num in range(1, 1000) if num not in plt.get_fignums()))
        if num1 == num2:
            num2 = None
        elif num2 is not None:
            num2 = num2 - 1
        num1 = num1 - 1
        # first check if an axes with this specification already exists and if
        # yes, return it
        for ax in fig.axes:
            ss = ax.get_subplotspec()
            if ss.num1 == num1 and (
                    ss.num2 == num2 or (ss.num2 is None and num1 == num2) or
                    (num2 is None and ss.num2 == num1)):
                gs = ss.get_gridspec()
                if gs.get_geometry() == (rows, cols):
                    return ax
        # if it does not exist, create a new one
        gs = mpl.gridspec.GridSpec(rows, cols)
        ss = mpl.gridspec.SubplotSpec(gs, num1, num2)
        return fig.add_subplot(ss, **kwargs)

    def setup_table(self):
        """Set up the table based upon the number of rows and columns in the
        rows and cols line edit"""
        rows = int(self.rows_edit.text() or 0)
        cols = int(self.cols_edit.text() or 0)
        if not rows or not cols:
            return
        self.table.clear()
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        selected = int(self.num1_edit.text() or 0)
        if selected:
            selected = (int(floor(selected / (cols + 1))),
                        ((selected % cols) - 1) % cols)
        else:
            selected = (0, 0)
        for i, (row, col) in enumerate(product(range(rows), range(cols)), 1):
            item = QTableWidgetItem(str(i))
            self.table.setItem(row, col, item)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.num1_edit.validator().setTop(max(1, rows*cols))
        self.set_num2_validator(self.num1_edit.text())
        self.set_selected_from_num1(self.num1_edit.text())

    def set_num2_validator(self, s):
        """Set the validator range for the num2 line edit"""
        num1 = int(s or 1)
        rows = int(self.rows_edit.text() or 0)
        cols = int(self.cols_edit.text() or 0)
        num2 = int(self.num2_edit.text() or num1)
        self.num2_edit.setText(str(max(num1, num2)))
        self.num2_edit.validator().setRange(
            num1, max(1, (rows or 1)*(cols or 1)))

    def set_selected_from_num1(self, s):
        """Update the selection of the table after changes of
        :attr:`num1_edit`"""
        self.table.clearSelection()
        if not s:
            return
        num1 = int(s)
        num2 = int(self.num2_edit.text() or num1)
        self.set_selected(num1, num2)

    def set_selected_from_num2(self, s):
        """Update the selection of the table after changes of :attr:`num2_edit`
        """
        self.table.clearSelection()
        if not s:
            return
        num2 = int(s)
        num1 = int(self.num1_edit.text() or 0)
        if not num1:
            return
        self.set_selected(num1, num2)

    def set_selected(self, num1, num2):
        """Update the selection in the table based upon `num1` and `num2`"""
        self.table.clearSelection()
        rows = int(self.rows_edit.text() or 0)
        cols = int(self.cols_edit.text() or 0)
        if not rows or not cols:
            return
        sel_rows = range(int(floor(num1 / (cols + 1))),
                         int(floor(num2 / (cols + 1))) + 1)
        sel_cols = range(((num1 % cols) - 1) % cols,
                         (((num2 % cols) - 1) % cols) + 1)
        for item in starmap(self.table.item, product(sel_rows, sel_cols)):
            if item:
                self.table.blockSignals(True)
                item.setSelected(True)
                self.table.blockSignals(False)

    def update_num_edit(self):
        """Update the :attr:`num1_edit` and :attr:`num2_edit` after the
        selection of the table changed"""
        items = self.table.selectedItems()
        if not items:
            return
        sel_rows = [item.row() for item in items]
        sel_cols = [item.column() for item in items]
        cols = int(self.cols_edit.text() or 0)
        self.num1_edit.blockSignals(True)
        self.num1_edit.setText(str(min(sel_rows) * cols + min(sel_cols) + 1))
        self.num1_edit.blockSignals(False)
        self.num2_edit.blockSignals(True)
        self.num2_edit.setText(str(max(sel_rows) * cols + max(sel_cols) + 1))
        self.num2_edit.blockSignals(False)

    def get_iter(self):
        """Get the iterator over the axes"""
        fig_text = self.fig_edit.text()
        if fig_text:
            figs = repeat(fig_text)
        else:
            import matplotlib.pyplot as plt
            figs = map(str, (num for num in range(1, 1000)
                             if num not in plt.get_fignums()))
        num1 = self.num1_edit.text() or '1'
        num2 = self.num2_edit.text() or num1
        return ('(%s, %s, %s, %s, %s)' % (
                fig, self.rows_edit.text() or '1',
                self.cols_edit.text() or '1', num1, num2)
                for fig in figs)


class AxesViewer(QGraphicsView):
    """Widget to show a rectangle"""

    sizeChanged = QtCore.pyqtSignal(QtCore.QSize)

    def __init__(self, *args, **kwargs):
        super(AxesViewer, self).__init__(*args, **kwargs)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def resizeEvent(self, *args, **kwargs):
        super(AxesViewer, self).resizeEvent(*args, **kwargs)
        self.setSceneRect(
            0, 0, self.frameSize().width(), self.frameSize().height())
        self.sizeChanged.emit(self.size())


class AxesCreator(QWidget):
    """Widget to setup an axes in a arbitrary location"""

    def __init__(self, fig=None, x0=0.125, y0=0.1, x1=0.9, y1=0.9,
                 *args, **kwargs):
        """
        Parameters
        ----------
        fig: int or None
            The figure number. If None, a new figure number will be used
        x0: float
            the x-coordinate of the lower left corner (between 0 and 1)
        y0: float
            the y-coordinate of the lower left corner (between 0 and 1)
        x1: float
            the x-coordinate of the upper right corner (between 0 and 1)
        y1: float
            the y-coordinate of the upper right corner (between 0 and 1)
        """
        super(AxesCreator, self).__init__(*args, **kwargs)
        self.fig_label = QLabel('Figure number:', self)
        if fig is None:
            import matplotlib.pyplot as plt
            fig = next(
                num for num in range(1, 1000) if num not in plt.get_fignums())
        self.fig_edit = QLineEdit(str(fig), self)
        self.fig_edit.setValidator(QIntValidator())

        self.x0_label = QLabel('Lower left x: ', self)
        self.x0_edit = QLineEdit(str(x0), self)
        self.x0_edit.setValidator(QDoubleValidator(0.0, 1.0, 5,
                                                   parent=self))

        self.y0_label = QLabel('Lower left y: ', self)
        self.y0_edit = QLineEdit(str(y0), self)
        self.y0_edit.setValidator(QDoubleValidator(0.0, 1.0, 5,
                                                   parent=self))

        self.x1_label = QLabel('Upper right x: ', self)
        self.x1_edit = QLineEdit(str(x1), self)
        self.x1_edit.setValidator(QDoubleValidator(0.0, 1.0, 5,
                                                   parent=self))

        self.y1_label = QLabel('Upper right y: ', self)
        self.y1_edit = QLineEdit(str(y1), self)
        self.y1_edit.setValidator(QDoubleValidator(0.5, 1.0, 5,
                                                   parent=self))

        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view = AxesViewer(self.graphics_scene)

        size = self.graphics_view.size()
        width = size.width() * float(x1 - x0)
        height = size.height() * float(y1 - y0)
        x0_resized = size.width() * float(x0)
        y0_resized = size.height() * float(y0)

        self.box_widget = QGraphicsRectItem(
            x0_resized, y0_resized, width, height)
        self.graphics_scene.addItem(self.box_widget)
        self.graphics_view.sizeChanged.connect(self.resize_rectangle)

        layout = QGridLayout()
        layout.addWidget(self.fig_label, 0, 0)
        layout.addWidget(self.fig_edit, 0, 1)
        layout.addWidget(self.x0_label, 1, 0)
        layout.addWidget(self.x0_edit, 1, 1)
        layout.addWidget(self.y0_label, 2, 0)
        layout.addWidget(self.y0_edit, 2, 1)
        layout.addWidget(self.x1_label, 3, 0)
        layout.addWidget(self.x1_edit, 3, 1)
        layout.addWidget(self.y1_label, 4, 0)
        layout.addWidget(self.y1_edit, 4, 1)

        layout.addWidget(self.graphics_view, 1, 2, 4, 4)

        for w in [self.x0_edit, self.y0_edit, self.x1_edit, self.y1_edit]:
            w.textChanged.connect(lambda s: self.resize_rectangle(
                self.graphics_view.size()))

        self.setLayout(layout)

    def resize_rectangle(self, size):
        """resize the rectangle after changes of the widget size"""
        coords = [self.x0_edit.text(), self.y0_edit.text(),
                  self.x1_edit.text(), self.y1_edit.text()]
        if any(not c for c in coords):
            return
        x0, y0, x1, y1 = map(float, coords)
        width = size.width() * float(x1 - x0)
        height = size.height() * float(y1 - y0)
        x0_resized = size.width() * float(x0)
        y1_resized = size.height() * float(1.0 - y1)
        self.box_widget.setRect(x0_resized, y1_resized, width, height)

    @staticmethod
    def create_axes(fig, x0, y0, x1, y1, **kwargs):
        """
        Create an axes for the given `fig`

        Parameters
        ----------
        fig: int or None
            The figure number. If None, a new figure number will be used
        x0: float
            the x-coordinate of the lower left corner (between 0 and 1)
        y0: float
            the y-coordinate of the lower left corner (between 0 and 1)
        x1: float
            the x-coordinate of the upper right corner (between 0 and 1)
        y1: float
            the y-coordinate of the upper right corner (between 0 and 1)
        ``**kwargs``
            Any other keyword argument for the
            :meth:`matplotlib.figure.Figure.add_axes` method
        """
        if not isinstance(fig, mpl.figure.Figure):
            import matplotlib.pyplot as plt
            fig = plt.figure(fig or next(
                num for num in range(1, 1000) if num not in plt.get_fignums()))
        x1 = max([x0, x1])
        y1 = max([y0, y1])
        bbox = mpl.transforms.Bbox.from_extents(x0, y0, x1, y1)
        points = np.round(bbox.get_points(), 5)
        for ax in fig.axes:
            if (np.round(ax.get_position().get_points(), 5) == points).all():
                return ax
        return fig.add_axes(bbox, **kwargs)

    def get_iter(self):
        """Get the iterator over the axes"""
        fig_text = self.fig_edit.text()
        if fig_text:
            figs = repeat(fig_text)
        else:
            import matplotlib.pyplot as plt
            figs = map(str, (num for num in range(1, 1000)
                             if num not in plt.get_fignums()))
        left = self.x0_edit.text() or '0.125'
        bottom = self.y0_edit.text() or '0.1'
        width = self.x1_edit.text() or '0.9'
        height = self.y1_edit.text() or '0.9'
        return ('(%s, %s, %s, %s, %s)' % (fig, left, bottom, width, height)
                for fig in figs)


class AxesSelector(QWidget):
    """Widget to select an already created axes

    Click the button, select your axes and click the button again"""

    def __init__(self, *args, **kwargs):
        super(AxesSelector, self).__init__(*args, **kwargs)
        self.bt_choose = QPushButton('Click to select axes', self)
        self.bt_choose.setCheckable(True)
        self.msg_label = QLabel('', self)

        self.result_label = QLabel('', self)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.bt_choose)
        self.layout.addWidget(self.msg_label)
        self.layout.addWidget(self.result_label)

        self.setLayout(self.layout)

        self.bt_choose.clicked.connect(self.change_pickers)

    def change_pickers(self, b):
        """Change the pickers of the axes instances

        If the push button is clicked, we replace the existing pickers of the
        axes in order to select the plots. Otherwise we restore them"""
        if self.bt_choose.isChecked():
            self.bt_choose.setText('Click when finished')
            self.msg_label.setText('Select an existing axes')
            self.result_label.setText('')
            self.allow_axes_select()
        else:
            self.bt_choose.setText('Select an axes')
            self.msg_label.setText('')
            self.restore_pickers()

    def unclick(self):
        """Restore the original pickers"""
        if self.bt_choose.isChecked():
            self.bt_choose.click()

    def allow_axes_select(self):
        """Replace make all axes pickable"""
        import matplotlib.pyplot as plt
        self.fig_events = d = {}
        self.pickers = pickers = defaultdict(dict)
        for num in plt.get_fignums():
            fig = plt.figure(num)
            d[num] = fig.canvas.mpl_connect('pick_event', self.get_picked_ax)
            for ax in fig.axes:
                pickers[num][ax] = ax.get_picker()
                ax.set_picker(True)

    def restore_pickers(self):
        """Restore the original pickers of the existing axes instances"""
        import matplotlib.pyplot as plt
        for num, cid in self.fig_events.items():
            plt.figure(num).canvas.mpl_disconnect(cid)
            for artist, picker in self.pickers[num].items():
                artist.set_picker(picker)
        self.fig_events.clear()
        self.pickers.clear()

    def get_picked_ax(self, event):
        """Function to be called when an axes is picked"""
        try:
            ax = event.artist.axes
        except AttributeError:
            ax = event.artist.get_axes()
        text = self.result_label.text()
        if text:
            text += ';;'
        self.result_label.setText(
            text + self.inspect_axes(ax))

    def inspect_axes(self, ax):
        """Inspect the given axes and get the right string for making a plot
        with it"""
        from matplotlib.axes import SubplotBase
        if isinstance(ax, SubplotBase):
            ss = ax.get_subplotspec()
            gs = ss.get_gridspec()
            rows, cols = gs.get_geometry()
            return '(%i, %i, %i, %i, %i)' % (
                ax.get_figure().number, rows, cols, ss.num1 + 1,
                (ss.num2 or ss.num1) + 1)
        else:
            box = ax.get_position()
            points = np.round(box.get_points().ravel(), 5).tolist()
            return '(%i, %1.5f, %1.5f, %1.5f, %1.5f)' % tuple(
                [ax.get_figure().number] + points)

    def setVisible(self, b):
        """Reimplemented to restore the pickers if the widget is made invisible
        """
        super(AxesSelector, self).setVisible(b)
        if not self.isVisible():
            self.unclick()

    def close(self):
        """Reimplemented to restore the pickers if the widget is closed
        """
        self.unclick()
        return super(AxesSelector, self).close()

    def get_iter(self):
        """Get the iterator over the axes"""
        return (txt for txt in cycle(self.result_label.text().split(';;')))


class AxesCreatorCollection(QDialog):
    """Wrapper for a QToolBox that holds the different possibilities to select
    an axes

    When the user finished, the :attr:`okpressed` symbol is emitted with an
    infinite iterator of strings. Possible widgets for the toolbox are
    determined by the :attr:`widgets` attribute"""

    #: signal that is emitted when the 'Ok' pushbutton is pressed and the user
    #: finished the selection
    okpressed = QtCore.pyqtSignal(types.GeneratorType)

    #: key, title and class fot the widget that is used to create an
    #: axes
    widgets = [('subplot', 'Subplot in a grid', SubplotCreator),
               ('axes', 'Arbitray position', AxesCreator),
               ('choose', 'Existing subplot', AxesSelector)]

    def __init__(self, key=None, func_kwargs={}, *args, **kwargs):
        """
        Parameters
        ----------
        key: str or None
            if string, it must be one of the keys in the :attr:`widgets`
            attribute
        func_kwargs: dict
            a dictionary that is passed to the class constructor determined by
            the `key` parameter if `key` is not None
        ``*args,**kwargs``
            Determined by the QWidget class"""
        super(AxesCreatorCollection, self).__init__(*args, **kwargs)
        self.bt_cancel = QPushButton('Cancel', self)
        self.bt_ok = QPushButton('Ok', self)

        self.tb = QTabWidget(self)
        self.tb.setTabPosition(QTabWidget.West)
        current = 0
        for i, (func_name, title, cls) in enumerate(self.widgets):
            if func_name == key:
                current = i
                w = cls(**func_kwargs)
            else:
                w = cls()
            self.tb.addTab(w, title)

        self.tb.setCurrentIndex(current)

        self.bt_ok.clicked.connect(self.create_subplot)
        self.bt_ok.clicked.connect(self.close)
        self.bt_cancel.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.tb)

        hbox = QHBoxLayout()
        hbox.addStretch(0)
        hbox.addWidget(self.bt_cancel)
        hbox.addWidget(self.bt_ok)
        layout.addLayout(hbox)

        self.setLayout(layout)

    def create_subplot(self):
        """Method that is called whenn the ok button is pressed.

        It emits the :attr:`okpressed` signal with the iterator of the current
        widget in the toolbox"""
        it = self.tb.currentWidget().get_iter()
        self.okpressed.emit(it)

    def close(self):
        """reimplemented to make sure that all widgets are closed when this one
        is closed"""
        for w in map(self.tb.widget, range(len(self.widgets))):
            w.close()
        return super(AxesCreatorCollection, self).close()


class PlotCreator(QDialog):
    """
    Widget to extract data from a dataset and eventually create a plot"""

    #: Tooltip for not making a plot
    NO_PM_TT = 'Choose a plot method (or choose none to only extract the data)'

    def __init__(self, *args, **kwargs):
        self.help_explorer = kwargs.pop('help_explorer', None)
        super(PlotCreator, self).__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle('Create plots')
        self.error_msg = PyErrorMessage(self)
        mp = psy.gcp(True)

        self.splitter = splitter = QSplitter(Qt.Vertical, parent=self)
        self.w = w = QWidget(self)
        self.fmt_tree_widget = QWidget(self)

        # ---------------------------------------------------------------------
        # -------------------------- children ---------------------------------
        # ---------------------------------------------------------------------

        self.ds_combo = QComboBox(parent=w)
        self.ds_combo.setToolTip('The data source to use the data from')
        self.fill_ds_combo(mp)
        self.bt_open_file = QToolButton(parent=w)
        self.bt_open_file.setIcon(QIcon(get_icon('run_arrow.png')))
        self.bt_open_file.setToolTip('Open a new dataset from the hard disk')
        self.bt_get_ds = LoadFromConsoleButton(xarray.Dataset, parent=w)
        self.bt_get_ds.setToolTip(
            'Use a dataset already defined in the console')

        self.pm_label = QLabel('Plot method: ', w)
        self.pm_combo = QComboBox(w)
        self.fill_plot_method_combo()
        self.pm_info = QToolButton(w)
        self.pm_info.setIcon(QIcon(get_icon('info.png')))
        self.pm_info.setToolTip('Show information in the help explorer')

        self.variables_table = VariablesTable(self.get_ds, parent=w)
        self.variables_table.fill_from_ds()

        self.coords_table = CoordsTable(self.get_ds, parent=w)
        self.coords_table.fill_from_ds()

        self.array_table = ArrayTable(self.get_ds, parent=w)
        self.array_table.setup_from_ds(plot_method=self.pm_combo.currentText())

        self.cbox_load = QCheckBox('load')
        self.cbox_load.setToolTip(
            'Load the selected data arrays into memory when clicking on '
            '<em>Ok</em>. Note that this might cause problems for large '
            'arrays!')

        self.cbox_close_popups = QCheckBox('close dropdowns', w)
        self.cbox_close_popups.setChecked(True)
        self.cbox_close_popups.setToolTip(
            'Close drop down menues after selecting indices to plot')
        self.cbox_use_coords = QCheckBox('show coordinates', w)
        self.cbox_use_coords.setChecked(False)
        self.cbox_use_coords.setToolTip(
            'Show the real coordinates instead of the indices in the drop '
            'down menues')
        self.bt_remove_all = QToolButton(w)
        self.bt_remove_all.setIcon(QIcon(get_icon('minusminus.png')))
        self.bt_remove_all.setToolTip('Remove all arrays')
        self.bt_remove = QToolButton(w)
        self.bt_remove.setIcon(QIcon(get_icon('minus.png')))
        self.bt_remove.setToolTip('Remove selected arrays')
        self.bt_add = QToolButton(w)
        self.bt_add.setIcon(QIcon(get_icon('plus.png')))
        self.bt_add.setToolTip('Add arrays for the selected variables')
        self.bt_add_all = QToolButton(w)
        self.bt_add_all.setIcon(QIcon(get_icon('plusplus.png')))
        self.bt_add_all.setToolTip(
            'Add arrays for all variables in the dataset')

        self.rows_axis_label = QLabel('No. of rows', w)
        self.rows_axis_edit = QLineEdit(w)
        self.rows_axis_edit.setText('1')
        self.cols_axis_label = QLabel('No. sof columns', w)
        self.cols_axis_edit = QLineEdit(w)
        self.cols_axis_edit.setText('1')
        self.max_axis_label = QLabel('No. of axes per figure', w)
        self.max_axis_edit = QLineEdit(w)
        self.bt_add_axes = QPushButton('Add new subplots', w)
        self.bt_add_axes.setToolTip(
            'Adds subplots for the selected arrays based the specified number '
            'of rows and columns')

        self.row_axis_label = QLabel('Row number:', w)
        self.row_axis_edit = QLineEdit(w)
        self.row_axis_edit.setText('1')
        self.col_axis_label = QLabel('Column number', w)
        self.col_axis_edit = QLineEdit(w)
        self.col_axis_edit.setText('1')
        self.bt_add_single_axes = QPushButton('Add one subplot', w)
        self.bt_add_single_axes.setToolTip(
            'Add one subplot for the specified row and column')

        self.fmt_tree_label = QLabel(
            "Modify the formatoptions of the newly created plots."
            "Values must be entered in yaml syntax",
            parent=self.fmt_tree_widget)

        self.fmt_tree = RcParamsTree(None, None, None,
                                     parent=self.fmt_tree_widget)
        self.fmt_tree.value_col = 3
        self.fmt_tree.setColumnCount(4)
        self.fmt_tree.setHeaderLabels(['Formatoption', '', '', 'Value'])

        # ---------------------------------------------------------------------
        # ---------------------------- connections ----------------------------
        # ---------------------------------------------------------------------

        # ----------------- dataset combo connections ------------------------
        self.bt_open_file.clicked.connect(lambda: self.open_dataset())
        self.bt_get_ds.object_loaded.connect(self.add_new_ds)
        self.ds_combo.currentIndexChanged[int].connect(self.set_ds)

        self.ds_combo.currentIndexChanged[int].connect(
            lambda i: self.variables_table.fill_from_ds())
        self.ds_combo.currentIndexChanged[int].connect(
            lambda i: self.coords_table.fill_from_ds())
        self.ds_combo.currentIndexChanged[int].connect(
            lambda i: self.array_table.setup_from_ds())
        self.ds_combo.currentIndexChanged[int].connect(
            lambda i: self.connect_combo_boxes())

        # ------------------- plot method connections -------------------------
        self.pm_combo.currentIndexChanged[str].connect(
            lambda s: self.pm_combo.setToolTip(
                getattr(psy.plot, s)._summary) if s else self.NO_PM_TT)
        self.pm_info.clicked.connect(self.show_pm_info)
        self.pm_combo.currentIndexChanged[str].connect(self.array_table.set_pm)
        self.pm_combo.currentIndexChanged[str].connect(self.fill_fmt_tree)

        # --------------------- Combo box connections -------------------------
        self.cbox_close_popups.clicked.connect(self.toggle_close_popups)
        self.cbox_use_coords.clicked.connect(self.reset_comboboxes)
        # connect leftclick of combo boxes to create new arrays or update the
        # selected
        self.connect_combo_boxes()

        # ----------------- add and remove button connections -----------------
        self.bt_add.clicked.connect(lambda b: self.insert_array(
            variables=self.variables_table.selected_variables))
        self.bt_add_all.clicked.connect(
            lambda b: self.insert_array(
                variables=self.variables_table.variables))
        self.bt_remove_all.clicked.connect(
            lambda b: self.array_table.remove_arrays(False))
        self.bt_remove.clicked.connect(
            lambda b: self.array_table.remove_arrays(True))

        # ------------- axes creation connections -----------------------------
        self.rows_axis_edit.returnPressed.connect(self.bt_add_axes.click)
        self.cols_axis_edit.returnPressed.connect(self.bt_add_axes.click)
        self.max_axis_edit.returnPressed.connect(self.bt_add_axes.click)
        self.bt_add_axes.clicked.connect(self.setup_subplots)
        self.row_axis_edit.returnPressed.connect(self.bt_add_single_axes.click)
        self.col_axis_edit.returnPressed.connect(self.bt_add_single_axes.click)
        self.bt_add_single_axes.clicked.connect(self.setup_subplot)

        # -------------------- create and cancel connections ------------------
        self.bbox = bbox = QDialogButtonBox(QDialogButtonBox.Ok |
                                            QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.create_plots)
        bbox.rejected.connect(self.reject)

        # -------------------- other connections ------------------------------
        # allow only to select either variables or newly created arrays in
        # order to control the behaviour of the combo box left click in
        # self.insert_array_from_combo
        self.array_table.itemSelectionChanged.connect(
            self.variables_table.clearSelection)
        self.variables_table.itemSelectionChanged.connect(
            self.array_table.clearSelection)

        # ---------------------------------------------------------------------
        # ---------------------------- layouts --------------------------------
        # ---------------------------------------------------------------------

        self.ds_box = QHBoxLayout()
        self.ds_box.addWidget(self.ds_combo)
        self.ds_box.addWidget(self.bt_open_file)
        self.ds_box.addWidget(self.bt_get_ds)

        self.pm_box = QHBoxLayout()
        self.pm_box.addStretch(0)
        self.pm_box.addWidget(self.pm_label)
        self.pm_box.addWidget(self.pm_combo)
        self.pm_box.addWidget(self.pm_info)

        self.tree_box = QHBoxLayout()
        self.tree_box.addStretch(0)
        self.tree_box.addWidget(self.cbox_load)
        self.tree_box.addWidget(self.cbox_close_popups)
        self.tree_box.addWidget(self.cbox_use_coords)
        self.tree_box.addWidget(self.bt_remove_all)
        self.tree_box.addWidget(self.bt_remove)
        self.tree_box.addWidget(self.bt_add)
        self.tree_box.addWidget(self.bt_add_all)

        self.axes_box = QGridLayout()
        self.axes_box.addWidget(self.max_axis_label, 0, 0)
        self.axes_box.addWidget(self.max_axis_edit, 0, 1)
        self.axes_box.addWidget(self.rows_axis_label, 0, 2)
        self.axes_box.addWidget(self.rows_axis_edit, 0, 3)
        self.axes_box.addWidget(self.cols_axis_label, 0, 4)
        self.axes_box.addWidget(self.cols_axis_edit, 0, 5)
        self.axes_box.addWidget(self.bt_add_axes, 0, 6)
        self.axes_box.addWidget(self.row_axis_label, 1, 2)
        self.axes_box.addWidget(self.row_axis_edit, 1, 3)
        self.axes_box.addWidget(self.col_axis_label, 1, 4)
        self.axes_box.addWidget(self.col_axis_edit, 1, 5)
        self.axes_box.addWidget(self.bt_add_single_axes, 1, 6)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.ds_box)
        self.vbox.addLayout(self.pm_box)
        self.vbox.addLayout(self.tree_box)
        self.vbox.addWidget(self.variables_table)
        self.vbox.addWidget(self.coords_table)
        self.vbox.addWidget(self.array_table)
        self.vbox.addLayout(self.axes_box)
        self.vbox.addWidget(self.bbox)

        w.setLayout(self.vbox)

        fmt_tree_layout = QVBoxLayout()
        fmt_tree_layout.addWidget(self.fmt_tree_label)
        fmt_tree_layout.addWidget(self.fmt_tree)
        self.fmt_tree_widget.setLayout(fmt_tree_layout)

        splitter.addWidget(w)

        splitter.addWidget(self.fmt_tree_widget)

        hbox = QHBoxLayout(self)
        hbox.addWidget(splitter)
        self.setLayout(hbox)
        self.fill_fmt_tree(self.pm_combo.currentText())

    def toggle_close_popups(self):
        """Change the automatic closing of popups"""
        close_popups = self.cbox_close_popups.isChecked()
        for cb in self.coords_table.combo_boxes:
            cb.close_popups = close_popups

    def reset_comboboxes(self):
        """Clear all comboboxes"""
        use_coords = self.cbox_use_coords.isChecked()
        for cb in self.coords_table.combo_boxes:
            cb.use_coords = use_coords
            cb.clear()
            cb._is_empty = True

    def fill_fmt_tree(self, pm):
        self.fmt_tree.clear()
        if not pm:
            self.fmt_tree_widget.setVisible(False)
        else:
            pm = getattr(psy.plot, pm)
            plotter = pm.plotter_cls()
            self.fmt_tree.rc = plotter
            self.fmt_tree.validators = {
                key: getattr(plotter, key).validate for key in plotter}
            self.fmt_tree.descriptions = {
                key: getattr(plotter, key).name for key in plotter}
            self.fmt_tree.initialize()
            icon = QIcon(get_icon('info.png'))
            docs_funcs = {
                key: partial(plotter.show_docs, key) for key in plotter}
            for item in self.fmt_tree.top_level_items:
                key = item.text(0)
                bt = QToolButton()
                bt.setIcon(icon)
                bt.clicked.connect(docs_funcs[key])
                self.fmt_tree.setItemWidget(item, 2, bt)
            self.fmt_tree.resizeColumnToContents(2)
            self.fmt_tree_widget.setVisible(True)

    def setup_subplots(self):
        """Method to be emitted to setup the subplots for the selected arrays
        on new figures"""
        rows = int(self.rows_axis_edit.text())
        cols = int(self.cols_axis_edit.text())
        maxn = int(self.max_axis_edit.text() or 0)
        self.array_table.add_subplots(rows, cols, maxn)

    def setup_subplot(self):
        """Method to be emitted to setup one subplot at a specific location
        for each of the selected arrays on separate (new) figures"""
        rows = int(self.rows_axis_edit.text())
        cols = int(self.cols_axis_edit.text())
        row = int(self.row_axis_edit.text())
        col = int(self.col_axis_edit.text())
        self.array_table.add_single_subplot(rows, cols, row, col)

    def show_pm_info(self):
        """Shows info on the current plotting method in the help explorer"""
        if self.help_explorer is None:
            return
        pm_name = self.pm_combo.currentText()
        if pm_name:
            self.help_explorer.show_help(getattr(psy.plot, pm_name),
                                         'psyplot.project.plot.' + pm_name)
        else:
            self.help_explorer.show_rst("""
            No plot
            =======
            No plot will be created, only the data is extracted""", 'no_plot')

    def connect_combo_boxes(self):
        for cb in self.coords_table.combo_boxes:
            cb.leftclick.connect(self.insert_array_from_combo)

    def fill_plot_method_combo(self):
        """Takes the names of the plotting methods in the current project"""
        self.pm_combo.addItems([''] + sorted(psy.plot._plot_methods))
        self.pm_combo.setToolTip(self.NO_PM_TT)

    def set_pm(self, plot_method):
        self.pm_combo.setCurrentIndex(
            self.pm_combo.findText(plot_method or ''))

    def create_plots(self):
        """Method to be called when the `Create plot` button is pressed

        This method reads the data from the :attr:`array_table` attribute and
        makes the plot (or extracts the data) based upon the
        :attr:`plot_method` attribute"""
        import matplotlib.pyplot as plt
        names = self.array_table.arr_names_dict
        pm = self.pm_combo.currentText()
        if pm:
            pm = getattr(psy.plot, pm)
            for d, (default_dim, default_slice) in product(
                    six.itervalues(names), six.iteritems(pm._default_dims)):
                d.setdefault(default_dim, default_slice)
            kwargs = {'ax': self.array_table.axes,
                      'fmt': {t[1]: t[2] for t in self.fmt_tree._get_rc()}}
        else:
            pm = self.open_data
            kwargs = {}
        fig_nums = plt.get_fignums()[:]
        try:
            pm(self.ds, arr_names=names, load=self.cbox_load.isChecked(),
               **kwargs)
        except Exception:
            for num in set(plt.get_fignums()).difference(fig_nums):
                plt.close(num)
            self.error_msg.showTraceback('<b>Failed to create the plots!</b>')
            logger.debug('Error while creating the plots with %s!',
                         names, exc_info=True)
        else:
            self.close()

    def open_dataset(self, fnames=None, *args, **kwargs):
        """Opens a file dialog and the dataset that has been inserted"""

        def open_ds():
            if len(fnames) == 1:
                kwargs.pop('concat_dim', None)
                return psy.open_dataset(fnames[0], *args, **kwargs)
            else:
                return psy.open_mfdataset(fnames, *args, **kwargs)

        if fnames is None:
            fnames = QFileDialog.getOpenFileNames(
                self, 'Open dataset', os.getcwd(),
                'NetCDF files (*.nc *.nc4);;'
                'Shape files (*.shp);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fnames = fnames[0]
        if isinstance(fnames, xarray.Dataset):
            ds = fnames
            self.add_new_ds('ds', ds)
        elif not fnames:
            return
        else:
            try:
                ds = open_ds()
            except Exception:
                kwargs['decode_times'] = False
                try:
                    ds = open_ds()
                except Exception:
                    self.error_msg.showTraceback(
                        '<b>Could not open dataset %s</b>' % (fnames, ))
                    return
            fnames_str = ', '.join(fnames)
            self.add_new_ds(fnames_str, ds, fnames_str)

    def add_new_ds(self, oname, ds, fname=None):
        d = {'ds': ds}
        if fname:
            d['fname'] = fname
        self.ds_descs.insert(0, d)
        self.ds_combo.insertItem(0, 'New: ' + oname)
        self.ds_combo.setCurrentIndex(0)

    def set_ds(self, i):
        """Set the current dataset"""
        self.ds = self.ds_descs[i]['ds']

    def fill_ds_combo(self, project):
        """fill the dataset combobox with datasets of the current main project
        """
        self.ds_combo.clear()
        self.ds_combo.setInsertPolicy(QComboBox.InsertAtBottom)
        ds_descs = project._get_ds_descriptions(
            project.array_info(ds_description='all'))
        self.ds_combo.addItems(
            ['%i: %s' % (i, ds_desc['fname']) for i, ds_desc in six.iteritems(
                ds_descs)])
        self.ds_descs = list(ds_descs.values())
        if len(self.ds_descs):
            self.set_ds(0)

    def insert_array_from_combo(self, cb, variables=None):
        """Insert new arrays into the dataset when the combobox is left-clicked
        """
        if variables is None:
            variables = self.variables_table.selected_variables
        dims = {}
        for other_cb in self.coords_table.combo_boxes:
            ind = other_cb.currentIndex()
            dims[other_cb.dim] = str((ind - 1) if ind not in [-1, 0] else '')
        dim = cb.dim
        inserts = list(
            str(ind.row() - 1)
            for ind in cb.view().selectionModel().selectedIndexes()
            if ind.row() > 0)
        dims.pop(dim)
        for name, val in product(variables, inserts):
            dims[dim] = val
            self.array_table.insert_array(name, check=False, **dims)
        if len(inserts) > 1:
            inserts = '%s:%s' % (min(inserts), max(inserts))
        elif inserts:
            inserts = inserts[0]
        else:
            return
        self.array_table.update_selected(check=False, dims={dim: inserts})
        self.array_table.check_arrays()

    def insert_array(self, variables=None):
        """Inserts an array for the given variables (or the ones selected in
        the :attr:`variable_table` if `variables` is None)
        """
        if variables is None:
            variables = self.variables_table.selected_variables
        dims = {}
        for other_cb in self.coords_table.combo_boxes:
            ind = other_cb.currentIndex()
            dims[other_cb.dim] = str((ind - 1) if ind not in [-1, 0] else '')
        for name in variables:
            self.array_table.insert_array(name, check=False, **dims)
        self.array_table.check_arrays()

    def get_ds(self, i=None):
        """Get the dataset

        Parameters
        ----------
        i: int or None
            If None, the dataset of the current index in the `ds_combo` is
            returned. Otherwise it specifies the locdation of the dictionary in
            the :attr:`ds_descs` attribute

        Returns
        -------
        xarray.Dataset
            The requested dataset"""
        if i is None:
            i = self.ds_combo.currentIndex()
        if not len(self.ds_descs):
            return
        return self.ds_descs[i]['ds']

    def close(self, *args, **kwargs):
        """Reimplemented to make sure that the data sets are deleted"""
        super(PlotCreator, self).close(*args, **kwargs)
        if hasattr(self, 'ds_descs'):
            del self.ds_descs

    def open_data(self, *args, **kwargs):
        """Convenience method to create a sub project without a plotter

        This method is used when the :attr:`pm_combo` is empty"""
        p = psy.Project.from_dataset(*args, main=psy.gcp(True), **kwargs)
        psy.scp(p)

    def switch2ds(self, ds):
        """Switch to the given dataset

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset to use. It is assumed that this dataset is already
            in the dataset combobox"""
        for i, desc in enumerate(self.ds_descs):
            if desc['ds'] is ds:
                self.ds_combo.setCurrentIndex(i)
                return

    def keyPressEvent(self, e):
        """Reimplemented to close the window when escape is hitted"""
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        else:
            super(PlotCreator, self).keyPressEvent(e)
