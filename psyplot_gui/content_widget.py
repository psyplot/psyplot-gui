"""Module containing the project content widget to display the selection

This module redefines the :class:`psyplot.project.Project` class with
additional features for an interactive usage with graphical qt user interface.
There is no need to import this module because the
:class:`GuiProject` class defined here replaces the project class in the
:mod:`psyplot.project` module."""
import six
import os.path as osp
import sip
from itertools import chain
from psyplot_gui.compat.qtcompat import (
    QDockWidget, QToolBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QWidget, QPushButton, QHBoxLayout, QVBoxLayout, Qt, QSplitter, QFrame,
    QTreeWidget, QTreeWidgetItem, QtCore)
from psyplot.compat.pycompat import OrderedDict, map, range
from psyplot.project import scp, gcp, Project
from psyplot.data import _TempBool, ArrayList
from psyplot_gui.common import DockMixin


class ArrayItem(QListWidgetItem):
    """A listwidget item that takes it's informations from a given array"""

    def __init__(self, arr, *args, **kwargs):
        """
        Parameters
        ----------
        arr: :class:`psyplot.data.InteractiveBase` object
            The array to display
        ``*args,**kwargs``
            Are determined by the parent class
        """
        super(ArrayItem, self).__init__(arr._short_info(), **kwargs)
        self.arr = arr
        # make sure that the item is updated when the array changes
        arr.onupdate.connect(self.set_text_from_array)
        self.set_text_from_array()

    def set_text_from_array(self):
        """Set the text and tooltop from the
        :meth:`psyplot.data.InteractiveArray._short_info` and __str__ methods
        """
        if not sip.isdeleted(self):
            self.setText(self.arr._short_info())
            self.setToolTip(str(self.arr))
        else:
            self.disconnect_from_array()

    def disconnect_from_array(self):
        self.arr.onupdate.disconnect(self.set_text_from_array)
        del self.arr


class PlotterList(QListWidget):
    """QListWidget showing multiple ArrayItems of one Plotter class"""

    #: str. The name of the attribute of the :class:`psyplot.project.Project`
    #: class
    project_attribute = None

    #: boolean. True if the current project does not contain any arrays in the
    #: attribute identified by the :attr:`project_attribute`
    is_empty = True

    _no_project_update = _TempBool()

    updated_from_project = QtCore.pyqtSignal(QListWidget)

    # Determine whether the plotter could be loaded
    can_import_plotter = True

    @property
    def arrays(self):
        """List of The InteractiveBase instances in this list"""
        return ArrayList(filter(
            lambda i: i is not None,
            (getattr(item, 'arr', None) for item in self.array_items)))

    @property
    def array_items(self):
        """Iterable of :class:`ArrayItem` items in this list"""
        return filter(lambda i: i is not None,
                      map(self.item, range(self.count())))

    def __init__(self, plotter_type=None, *args, **kwargs):
        """
        Parameters
        ----------
        plotter_type: str or None
            If str, it mus be an attribute name of the
            :class:`psyplot.project.Project` class. Otherwise the full project
            is used
        ``*args,**kwargs``
            Are determined by the parent class

        Notes
        -----
        When initialized, the content of the list is determined by
        ``gcp(True)`` and ``gcp()``"""
        super(PlotterList, self).__init__(*args, **kwargs)
        self.project_attribute = plotter_type
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.itemSelectionChanged.connect(self.update_cp)
        Project.oncpchange.connect(self.update_from_project)
        self.update_from_project(gcp(True))
        self.update_from_project(gcp())

    def update_from_project(self, project):
        """Update the content from the given Project

        Parameters
        ----------
        project: psyplot.project.Project
            If the project is a main project, new items will be added.
            Otherwise only the current selection changes"""
        if self._no_project_update:
            return
        if not self.can_import_plotter or project is None:
            # remove the current items
            for item in self.array_items:
                item.disconnect_from_array()
                self.takeItem(self.indexFromItem(item).row())
            self.is_empty = True
            return
        attr = self.project_attribute
        try:
            arrays = project if not attr else getattr(project, attr)
        except ImportError:  # plotter could not be loaded
            self.is_empty = True
            self.can_import_plotter = False
            return
        self.is_empty = not bool(arrays)
        with self._no_project_update:
            if project is None:
                for item in self.array_items:
                    item.setSelected(False)
            elif project.is_main:
                old_arrays = self.arrays
                # remove outdated items
                i = 0
                for arr in old_arrays:
                    if arr not in arrays:
                        self.takeItem(i)
                    else:
                        i += 1
                # add new items
                for arr in arrays:
                    if arr not in old_arrays:
                        item = ArrayItem(arr, parent=self)
                        self.addItem(item)
            else:
                for item in self.array_items:
                    item.setSelected(item.arr in arrays)
        self.updated_from_project.emit(self)

    def update_cp(self, *args, **kwargs):
        """Update the current project from what is selected in this list"""
        if not self._no_project_update:
            mp = gcp(True)
            sp = gcp()
            selected = [item.arr.arr_name for item in self.selectedItems()]
            other_selected = [
                arr.arr_name for arr in sp if arr not in self.arrays]
            with self._no_project_update:
                scp(mp(arr_name=selected + other_selected))


class ProjectContent(QToolBox):
    """Display the content in the current project

    This toolbox contains several :class:`PlotterList` that show the content
    of the current main and subproject"""

    #: :class:`OrderedDict` containing the :class:`PlotterList` instances
    #: of the different selection attributes
    lists = OrderedDict()

    def __init__(self, *args, **kwargs):
        super(ProjectContent, self).__init__(*args, **kwargs)
        for attr in chain(['All'], sorted(Project._registered_plotters)):
            self.add_plotterlist(attr)
        self.currentChanged.connect(self.update_current_list)

    def enable_list(self, list_widget):
        """Enable a given list widget based upon whether it is empty or not"""
        self.setItemEnabled(
            self.indexOf(list_widget), not list_widget.is_empty)

    def add_plotterlist(self, identifier):
        """Create a :class:`PlotterList` from an identifier from the
        :class:`psyplot.project.Project` class"""
        attr = identifier if identifier != 'All' else None
        item = PlotterList(attr)
        if not item.can_import_plotter:
            return
        item.setParent(self)
        self.lists[identifier] = item
        item.updated_from_project.connect(self.enable_list)
        self.addItem(item, identifier)
        self.setItemEnabled(len(self.lists) - 1, not item.is_empty)

    def update_current_list(self):
        """Update the current list from the current main and sub project"""
        self.currentWidget().update_from_project(gcp(True))
        self.currentWidget().update_from_project(gcp())


class SelectAllButton(QPushButton):
    """A button to select all data objects in the current main project"""

    def __init__(self, *args, **kwargs):
        super(SelectAllButton, self).__init__(*args, **kwargs)
        self.setToolTip(
            'Click to select all data arrays in the entire project')
        self.clicked.connect(self.select_all)
        Project.oncpchange.connect(self.enable_from_project)

    def select_all(self):
        """Select all arrays"""
        scp(gcp(True)[:])

    def enable_from_project(self, project):
        """Enable the button if the given project is not empty"""
        self.setEnabled(bool(project))


class SelectNoneButton(QPushButton):
    """A button to select no data objects in the current main project"""

    def __init__(self, *args, **kwargs):
        super(SelectNoneButton, self).__init__(*args, **kwargs)
        self.setToolTip('Click to deselect all data arrays')
        self.clicked.connect(self.select_none)
        Project.oncpchange.connect(self.enable_from_project)

    def select_none(self):
        """Clear current subproject"""
        scp(gcp(True)[:0])

    def enable_from_project(self, project):
        """Enable the button if the given project is not empty"""
        self.setEnabled(bool(project))


class ProjectContentWidget(QWidget, DockMixin):
    """A combination of selection buttons and the ProjectContent"""

    def __init__(self, *args, **kwargs):
        super(ProjectContentWidget, self).__init__(*args, **kwargs)
        vbox = QVBoxLayout()
        # create buttons for unselecting and selecting all arrays
        self.unselect_button = SelectNoneButton('Unselect all', parent=self)
        self.select_all_button = SelectAllButton('Select all', parent=self)
        button_hbox = QHBoxLayout()
        button_hbox.addWidget(self.unselect_button)
        button_hbox.addWidget(self.select_all_button)
        sp = gcp(True)
        self.unselect_button.setEnabled(bool(sp))
        self.select_all_button.setEnabled(bool(sp))
        # create widget showing the content of the current project
        self.content_widget = ProjectContent(parent=self)
        vbox.addLayout(button_hbox)
        vbox.addWidget(self.content_widget)
        self.setLayout(vbox)


class DatasetTreeItem(QTreeWidgetItem):
    """A QTreeWidgetItem showing informations on one dataset in the main
    project"""

    def __init__(self, ds, columns=[], *args, **kwargs):
        super(DatasetTreeItem, self).__init__(*args, **kwargs)
        variables = QTreeWidgetItem(0)
        variables.setText(0, 'variables')
        coords = QTreeWidgetItem(0)
        coords.setText(0, 'coords')
        self.addChildren([variables, coords])
        self.addChild(variables)
        for vname, variable in six.iteritems(ds.variables):
            item = QTreeWidgetItem(0)
            item.setText(0, vname)
            for i, attr in enumerate(columns, 1):
                if attr == 'dims':
                    item.setText(i, ', '.join(variable.dims))
                else:
                    item.setText(i, str(variable.attrs.get(attr, getattr(
                        variable, attr, ''))))
            if vname in ds.coords:
                coords.addChild(item)
            else:
                variables.addChild(item)
            item.setToolTip(0, str(variable))


class DatasetTree(QTreeWidget, DockMixin):
    """A QTreeWidget showing informations on all datasets in the main project
    """

    def __init__(self, *args, **kwargs):
        super(DatasetTree, self).__init__(*args, **kwargs)
        self.create_dataset_tree()
        Project.oncpchange.connect(self.add_datasets_from_cp)

    def create_dataset_tree(self):
        """Set up the columns and insert the :class:`DatasetTreeItem`
        instances from the current project"""
        self.set_columns()
        self.add_datasets_from_cp(gcp())

    def set_columns(self, columns=['long_name', 'dims', 'shape']):
        """Set up the columns in the DatasetTree.

        Parameters
        ----------
        columns: list of str
            A list of netCDF attributes that shall be shown in columns"""
        self.setColumnCount(len(columns) + 1)
        self.setHeaderLabels(['Dataset'] + list(columns))
        self.attr_columns = columns

    def add_datasets_from_cp(self, project):
        """Clear the tree and add the datasets based upon the given `project`

        Parameters
        ----------
        project: psyplot.project.Project
            The project containing the data array. If the project is not a main
            project, it's main project is used.
        """
        if project is None:
            project = gcp(True)
            sp_arrs = ArrayList().arrays
        elif project.is_main:
            sp_arrs = gcp().arrays
        else:
            sp_arrs = project.arrays
            project = project.main
        # remove items from the tree
        self.clear()
        for i, ds_desc in six.iteritems(project._get_ds_descriptions(
                project.array_info(ds_description='all'))):
            top_item = DatasetTreeItem(ds_desc['ds'], self.attr_columns, 0)
            if ds_desc['fname'] is not None:
                ds_desc['fname'] = osp.basename(ds_desc['fname'])
            top_item.setText(0, '%s%i: %s' % (
                '*' if any(arr in sp_arrs for arr in ds_desc['arr']) else '',
                i, ds_desc['fname']))
            top_item.setToolTip(0, str(ds_desc['ds']))
            for arr in ds_desc['arr']:
                arr.onbasechange.connect(self.add_datasets_from_cp)
            self.addTopLevelItem(top_item)


class FiguresTreeItem(QTreeWidgetItem):
    """An item displaying the information on a data object in one figure"""

    def __init__(self, arr, *args, **kwargs):
        """
        Parameters
        ----------
        arr: psyplot.data.InteractiveBase
            The array containing the data"""
        super(FiguresTreeItem, self).__init__(*args, **kwargs)
        self.arr = arr
        self.set_text_from_array()
        arr.onupdate.connect(self.set_text_from_array)

    def set_text_from_array(self):
        """Set the text and tooltop from the
        :meth:`psyplot.data.InteractiveArray._short_info` and __str__ methods
        """
        self.setText(0, self.arr._short_info())
        self.setToolTip(0, str(self.arr))

    def disconnect_from_array(self):
        """Disconect this item from the corresponding array"""
        self.arr.onupdate.disconnect(self.set_text_from_array)
        del self.arr


class FiguresTree(QTreeWidget, DockMixin):
    """A tree widget sorting the arrays by their figure

    This widget uses the current sub and main project to show the open figures
    """

    def __init__(self, *args, **kwargs):
        super(FiguresTree, self).__init__(*args, **kwargs)
        self.setHeaderLabel('Figure')
        Project.oncpchange.connect(self.add_figures_from_cp)
        self.add_figures_from_cp(gcp(True))

    def add_figures_from_cp(self, project):
        """Add the items in this tree based upon the figures in the given
        project"""
        if project is None or not project.is_main:
            return
        for item in map(self.takeTopLevelItem, [0] * self.topLevelItemCount()):
            for child in item.takeChildren():
                child.disconnect_from_array()
        for fig, arrays in six.iteritems(project.figs):
            item = QTreeWidgetItem(0)
            item.setText(0, fig.canvas.get_window_title())
            item.addChildren([FiguresTreeItem(arr, 0) for arr in arrays])
            self.addTopLevelItem(item)
