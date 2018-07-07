# -*- coding: utf-8 -*-
"""Module containing the project content widget to display the selection

This module redefines the :class:`psyplot.project.Project` class with
additional features for an interactive usage with graphical qt user interface.
There is no need to import this module because the
:class:`GuiProject` class defined here replaces the project class in the
:mod:`psyplot.project` module."""
import sys
import six
import os.path as osp
import sip
import weakref
from itertools import chain
from psyplot_gui import rcParams
from psyplot_gui.compat.qtcompat import (
    QToolBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QTreeWidget,
    QTreeWidgetItem, QtCore, QMenu, QAction, Qt)
from psyplot.config.rcsetup import safe_list
from psyplot.compat.pycompat import OrderedDict, map, range
from psyplot.project import scp, gcp, Project
from psyplot.data import ArrayList, InteractiveList
from psyplot.utils import _TempBool
from psyplot_gui.common import DockMixin


class ArrayItem(QListWidgetItem):
    """A listwidget item that takes it's informations from a given array"""

    #: The :class:`psyplot.data.InteractiveList` or
    #: :class:`psyplot.data.InteractiveArray` instance
    arr = None

    def __init__(self, ref, *args, **kwargs):
        """
        Parameters
        ----------
        ref: weakref
            The weak reference to the array to display
        ``*args,**kwargs``
            Are determined by the parent class
        """
        arr = ref()
        super(ArrayItem, self).__init__(arr._short_info(), **kwargs)
        self.arr = ref
        # make sure that the item is updated when the array changes
        arr.onupdate.connect(self.set_text_from_array)
        self.set_text_from_array()

    def set_text_from_array(self):
        """Set the text and tooltop from the
        :meth:`psyplot.data.InteractiveArray._short_info` and __str__ methods
        """
        if not sip.isdeleted(self):
            self.setText(self.arr()._short_info())
            if rcParams['content.load_tooltips']:
                if isinstance(self.arr(), InteractiveList):
                    self.setToolTip(str(self.arr()))
                else:
                    self.setToolTip(str(self.arr().arr))
        else:
            self.disconnect_from_array()

    def disconnect_from_array(self):
        arr = self.arr()
        if arr is not None:
            arr.onupdate.disconnect(self.set_text_from_array)
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
        return ArrayList([
            getattr(item.arr(), 'arr', item.arr())
            for item in self.array_items])

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
        if not self.can_import_plotter:
            # remove the current items
            self.disconnect_items()
            return
        attr = self.project_attribute
        # stop if the module of the plotter has not yet been imported
        if attr and Project._registered_plotters[attr][0] not in sys.modules:
            return
        try:
            arrays = project if not attr else getattr(project, attr)
            mp = gcp(True) if project is None else project.main
            main_arrays = mp if not attr else getattr(mp, attr)
        except ImportError:  # plotter could not be loaded
            self.is_empty = True
            self.can_import_plotter = False
            return
        self.is_empty = not bool(main_arrays)
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
                        item = self.takeItem(i)
                        item.disconnect_from_array()
                    else:
                        i += 1
                # add new items
                for arr in arrays:
                    if arr not in old_arrays:
                        item = ArrayItem(weakref.ref(arr.psy), parent=self)
                        self.addItem(item)
                # resort to match the project
                for arr in reversed(main_arrays):
                    for i, item in enumerate(self.array_items):
                        if item.arr() is arr.psy:
                            self.insertItem(0, self.takeItem(i))
            cp = gcp()
            for item in self.array_items:
                item.setSelected(
                    getattr(item.arr(), 'arr', item.arr()) in cp)
        self.updated_from_project.emit(self)

    def update_cp(self, *args, **kwargs):
        """Update the current project from what is selected in this list"""
        if not self._no_project_update:
            mp = gcp(True)
            sp = gcp()
            selected = [item.arr().arr_name for item in self.selectedItems()]
            arrays = self.arrays
            other_selected = [
                arr.psy.arr_name for arr in sp if arr not in arrays]
            with self._no_project_update:
                scp(mp(arr_name=selected + other_selected))

    def disconnect_items(self):
        """Disconnect the items in this list from the arrays"""
        for item in list(self.array_items):
            item.disconnect_from_array()
            self.takeItem(self.indexFromItem(item).row())
        self.is_empty = True


class ProjectContent(QToolBox):
    """Display the content in the current project

    This toolbox contains several :class:`PlotterList` that show the content
    of the current main and subproject"""

    #: :class:`OrderedDict` containing the :class:`PlotterList` instances
    #: of the different selection attributes
    lists = OrderedDict()

    @property
    def current_names(self):
        return [self.itemText(i) for i in range(self.count())]

    def __init__(self, *args, **kwargs):
        super(ProjectContent, self).__init__(*args, **kwargs)
        self.lists = OrderedDict()
        for attr in chain(['All'], sorted(Project._registered_plotters)):
            item = self.add_plotterlist(attr, force=(attr == 'All'))
            self.lists[attr] = item
        self.currentChanged.connect(self.update_current_list)
        Project.oncpchange.connect(self.update_lists)

    def enable_list(self, list_widget):
        """Enable a given list widget based upon whether it is empty or not"""
        i = self.indexOf(list_widget)
        if i != -1:
            self.setItemEnabled(i, not list_widget.is_empty)

    def add_plotterlist(self, identifier, force=False):
        """Create a :class:`PlotterList` from an identifier from the
        :class:`psyplot.project.Project` class"""
        attr = identifier if identifier != 'All' else None
        item = PlotterList(attr)
        if not item.can_import_plotter:
            return item
        if force or not item.is_empty:
            item.setParent(self)
            item.updated_from_project.connect(self.enable_list)
            self.addItem(item, identifier)
            i = self.indexOf(item)
            self.setItemEnabled(i, not item.is_empty)
        return item

    def update_current_list(self):
        """Update the current list from the current main and sub project"""
        self.currentWidget().update_from_project(gcp(True))
        self.currentWidget().update_from_project(gcp())

    def update_lists(self, p):
        # check new lists
        current_items = self.current_names
        for name, l in self.lists.items():
            if not p.is_main:
                l.update_from_project(p.main)
            l.update_from_project(p)
            if l.is_empty:
                l.disconnect_items()
            if name != 'All' and l.is_empty:
                i = self.indexOf(l)
                self.removeItem(i)
            elif not l.is_empty and name not in current_items:
                self.addItem(l, name)


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
        self.setEnabled(bool(project.main if project is not None else gcp(1)))


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
        mp = gcp(True)
        self.unselect_button.setEnabled(bool(mp))
        self.select_all_button.setEnabled(bool(mp))
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
        self.variables = variables = QTreeWidgetItem(0)
        self.columns = columns
        variables.setText(0, 'variables')
        self.coords = coords = QTreeWidgetItem(0)
        coords.setText(0, 'coords')
        self.addChildren([variables, coords])
        self.addChild(variables)
        self.add_variables(ds)

    def add_variables(self, ds=None):
        """Add children of variables and coords to this TreeWidgetItem"""
        if ds is None:
            ds = self.ds()
            self.variables.takeChildren()
            self.coords.takeChildren()
        else:
            self.ds = weakref.ref(ds)
        columns = self.columns
        variables = self.variables
        coords = self.coords
        for vname, variable in six.iteritems(ds.variables):
            item = QTreeWidgetItem(0)
            item.setText(0, str(vname))
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
            if rcParams['content.load_tooltips']:
                item.setToolTip(0, str(variable))


class DatasetTree(QTreeWidget, DockMixin):
    """A QTreeWidget showing informations on all datasets in the main project
    """

    tooltips = {
        'Refresh': 'Refresh the selected dataset',
        'Refresh all': 'Refresh all datasets',
        'Add to project': ('Add this variable or a plot of it to the current '
                           'project')}

    def __init__(self, *args, **kwargs):
        super(DatasetTree, self).__init__(*args, **kwargs)
        self.create_dataset_tree()
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)
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

    def add_datasets_from_cp(self, project=None):
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
            if ds_desc['fname'] is not None and not all(
                    s is None for s in ds_desc['fname']):
                ds_desc['fname'] = ', '.join(map(osp.basename,
                                                 safe_list(ds_desc['fname'])))
            else:
                ds_desc['fname'] = None
            top_item.setText(0, '%s%i: %s' % (
                '*' if any(any(arr is arr2 for arr2 in sp_arrs)
                           for arr in ds_desc['arr']) else '',
                i, ds_desc['fname']))
            for arr in ds_desc['arr']:
                arr.psy.onbasechange.connect(self.add_datasets_from_cp)
            self.addTopLevelItem(top_item)

    def open_menu(self, pos):
        menu = QMenu()
        item = self.itemAt(pos)
        parent, item_type = self._get_toplevel_item(item)
        # ---- Refresh the selected item action
        refresh_action = QAction('Refresh', self)
        refresh_action.setToolTip(self.tooltips['Refresh'])
        refresh_action.triggered.connect(lambda: self.refresh_items(parent))

        # ---- Refresh all items action
        refresh_all_action = QAction('Refresh all', self)
        refresh_all_action.setToolTip(self.tooltips['Refresh all'])
        refresh_all_action.triggered.connect(lambda: self.refresh_items())

        # ---- add refresh actions
        menu.addActions([refresh_action, refresh_all_action])

        # ---- add plot option
        if item_type == 'variable':
            add2p_action = QAction('Add to project', self)
            add2p_action.setToolTip(self.tooltips['Add to project'])
            add2p_action.triggered.connect(lambda: self.make_plot(
                parent.ds(), item.text(0), True))
            menu.addSeparator()
            menu.addAction(add2p_action)

        # ---- show menu
        menu.exec_(self.mapToGlobal(pos))
        return menu

    def refresh_items(self, item=None):
        if item is not None:
            item.add_variables()
        else:
            for item in map(self.topLevelItem,
                            range(self.topLevelItemCount())):
                item.add_variables()

    def make_plot(self, ds, name, exec_=None):
        from psyplot_gui.main import mainwindow
        mainwindow.new_plots()
        mainwindow.plot_creator.switch2ds(ds)
        mainwindow.plot_creator.insert_array(safe_list(name))
        if exec_:
            mainwindow.plot_creator.exec_()

    def _get_toplevel_item(self, item):
        if item is None:
            parent = None
        else:
            parent = item.parent()
        item_type = None
        while parent is not None:
            if parent.text(0) == 'variables':
                item_type = 'variable'
            elif parent.text(0) == 'coords':
                item_type = 'coord'
            item = item.parent()
            parent = item.parent()
        return item, item_type


class FiguresTreeItem(QTreeWidgetItem):
    """An item displaying the information on a data object in one figure"""

    def __init__(self, ref, *args, **kwargs):
        """
        Parameters
        ----------
        ref: weakref
            The weak reference to the array containing the data"""
        super(FiguresTreeItem, self).__init__(*args, **kwargs)
        self.arr = ref
        self.set_text_from_array()
        ref().psy.onupdate.connect(self.set_text_from_array)

    def set_text_from_array(self):
        """Set the text and tooltop from the
        :meth:`psyplot.data.InteractiveArray._short_info` and __str__ methods
        """
        self.setText(0, self.arr().psy._short_info())
        if rcParams['content.load_tooltips']:
            self.setToolTip(0, str(self.arr()))

    def disconnect_from_array(self):
        """Disconect this item from the corresponding array"""
        arr = self.arr()
        if arr is not None:
            arr.psy.onupdate.disconnect(self.set_text_from_array)
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
            item.addChildren(
                [FiguresTreeItem(weakref.ref(arr), 0) for arr in arrays])
            self.addTopLevelItem(item)
