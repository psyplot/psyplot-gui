"""Preferences widget for psyplot_gui

This module defines the :class:`Preferences` widget that creates an interface
to the rcParams of psyplot and psyplot_gui"""
import yaml
from warnings import warn
from psyplot_gui.compat.qtcompat import (
    QTreeWidget, QTreeWidgetItem, Qt, QMenu, QAction, QTextEdit, QIcon,
    QWidget, QVBoxLayout, QHBoxLayout, QtCore, QDialog, QScrollArea,
    QDialogButtonBox, QStackedWidget, QListWidget, QListView, QSplitter,
    QListWidgetItem, QPushButton, QFileDialog, with_qt5,
    QAbstractItemView, QToolButton, QLabel, QtGui, asstring)
from psyplot_gui.common import get_icon
from psyplot_gui import rcParams as rcParams
from psyplot.config.rcsetup import (
    psyplot_fname, RcParams, rcParams as psy_rcParams)


class ConfigPage(object):
    """An abstract base class for configuration pages"""

    #: A signal that shall be emitted if the validation state changes
    validChanged = QtCore.pyqtSignal(bool)

    #: A signal that is emitted if changes are propsed. The signal should be
    #: emitted with the instance of the page itself
    propose_changes = QtCore.pyqtSignal(object)

    #: The title for the config page
    title = None

    #: The icon of the page
    icon = None

    #: :class:`bool` that is True, if the changes in this ConfigPage are set
    #: immediately
    auto_updates = False

    @property
    def is_valid(self):
        """Check whether the page is valid"""
        raise NotImplementedError

    @property
    def changed(self):
        """Check whether the preferences will change"""
        raise NotImplementedError

    def initialize(self):
        """Initialize the page"""
        raise NotImplementedError

    def apply_changes(self):
        """Apply the planned changes"""
        raise NotImplementedError


class RcParamsTree(QTreeWidget):
    """A QTreeWidget that can be used to display a RcParams instance

    This widget is populated by a :class:`psyplot.config.rcsetup.RcParams`
    instance and displays whether the values are valid or not"""

    #: A signal that shall be emitted if the validation state changes
    validChanged = QtCore.pyqtSignal(bool)

    #: A signal that is emitted if changes are propsed. It is either emitted
    #: with the parent of this instance (if this is not None) or with the
    #: instance itself
    propose_changes = QtCore.pyqtSignal(object)

    #: The :class:`~psyplot.config.rcsetup.RcParams` to display
    rc = None

    #: list of :class:`bool`. A boolean for each rcParams key that states
    #: whether the proposed value is valid or not
    valid = []

    value_col = 2

    def __init__(self, rcParams, validators, descriptions, *args, **kwargs):
        """
        Parameters
        ----------
        rcParams: dict
            The dictionary that contains the rcParams
        validators: dict
            A mapping from the `rcParams` key to the validation function for
            the corresponding value
        descriptions: dict
            A mapping from the `rcParams` key to it's description

        See Also
        --------
        psyplot.config.rcsetup.RcParams
        psyplot.config.rcsetup.RcParams.validate
        psyplot.config.rcsetup.RcParams.descriptions
        """
        super(RcParamsTree, self).__init__(*args, **kwargs)
        self.rc = rcParams
        self.validators = validators
        self.descriptions = descriptions
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)
        self.setColumnCount(self.value_col + 1)
        self.setHeaderLabels(['RcParams key', '', 'Value'])

    @property
    def is_valid(self):
        """True if all the proposed values in this tree are valid"""
        return all(self.valid)

    @property
    def top_level_items(self):
        """An iterator over the topLevelItems in this tree"""
        return map(self.topLevelItem, range(self.topLevelItemCount()))

    def initialize(self):
        """Fill the items of the :attr:`rc` into the tree"""
        rcParams = self.rc
        descriptions = self.descriptions
        self.valid = [True] * len(rcParams)
        validators = self.validators
        vcol = self.value_col
        for i, (key, val) in enumerate(sorted(rcParams.items())):
            item = QTreeWidgetItem(0)
            item.setText(0, key)
            item.setToolTip(0, key)
            item.setIcon(1, QIcon(get_icon('valid.png')))
            desc = descriptions.get(key)
            if desc:
                item.setText(vcol, desc)
                item.setToolTip(vcol, desc)
            child = QTreeWidgetItem(0)
            item.addChild(child)
            self.addTopLevelItem(item)
            editor = QTextEdit(self)
            # set maximal height of the editor to 3 rows
            editor.setMaximumHeight(
                4 * QtGui.QFontMetrics(editor.font()).height())
            editor.setPlainText(yaml.dump(val))
            self.setItemWidget(child, vcol, editor)
            editor.textChanged.connect(
                self.set_icon_func(i, item, validators[key]))
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

    def set_icon_func(self, i, item, validator):
        """Create a function to change the icon of one topLevelItem

        This method creates a function that can be called when the value of an
        item changes to display it's valid state. The returned function changes
        the icon of the given topLevelItem depending on
        whether the proposed changes are valid or not and it modifies the
        :attr:`valid` attribute accordingly

        Parameters
        ----------
        i: int
            The index of the topLevelItem
        item: QTreeWidgetItem
            The topLevelItem
        validator: func
            The validation function

        Returns
        -------
        function
            The function that can be called to set the correct icon"""
        def func():
            editor = self.itemWidget(item.child(0), self.value_col)
            s = asstring(editor.toPlainText())
            try:
                val = yaml.load(s)
            except Exception as e:
                item.setIcon(1, QIcon(get_icon('warning.png')))
                item.setToolTip(1, "Could not parse yaml code: %s" % e)
                self.set_valid(i, False)
                return
            try:
                validator(val)
            except Exception as e:
                item.setIcon(1, QIcon(get_icon('invalid.png')))
                item.setToolTip(1, "Wrong value: %s" % e)
                self.set_valid(i, False)
            else:
                item.setIcon(1, QIcon(get_icon('valid.png')))
                self.set_valid(i, True)
            self.propose_changes.emit(self.parent() or self)
        return func

    def set_valid(self, i, b):
        """Set the validation status

        If the validation status changed compared to the old one, the
        :attr:`validChanged` signal is emitted

        Parameters
        ----------
        i: int
            The index of the topLevelItem
        b: bool
            The valid state of the item
        """
        old = self.is_valid
        self.valid[i] = b
        new = self.is_valid
        if new is not old:
            self.validChanged.emit(new)

    def open_menu(self, position):
        """Open a menu to expand and collapse all items in the tree

        Parameters
        ----------
        position: QPosition
            The position where to open the menu"""
        menu = QMenu()
        expand_all_action = QAction('Expand all', self)
        expand_all_action.triggered.connect(self.expandAll)
        menu.addAction(expand_all_action)
        collapse_all_action = QAction('Collapse all', self)
        collapse_all_action.triggered.connect(self.collapseAll)
        menu.addAction(collapse_all_action)
        menu.exec_(self.viewport().mapToGlobal(position))

    def changed_rc(self, use_items=False):
        """Iterate over the changed rcParams

        Parameters
        ----------
        use_items: bool
            If True, the topLevelItems are used instead of the keys

        Yields
        ------
        QTreeWidgetItem or str
            The item identifier
        object
            The proposed value"""
        def equals(item, key, val, orig):
            return val != orig
        for t in self._get_rc(equals):
            yield t[0 if use_items else 1], t[2]

    def selected_rc(self, use_items=False):
        """Iterate over the selected rcParams

        Parameters
        ----------
        use_items: bool
            If True, the topLevelItems are used instead of the keys

        Yields
        ------
        QTreeWidgetItem or str
            The item identifier
        object
            The proposed value"""
        def is_selected(item, key, val, orig):
            return item.isSelected()
        for t in self._get_rc(is_selected):
            yield t[0 if use_items else 1], t[2]

    def _get_rc(self, filter_func=None):
        """Iterate over the rcParams

        This function applies the given `filter_func` to check whether the
        item should be included or not

        Parameters
        ----------
        filter_func: function
            A function that accepts the following arguments:

            item
                The QTreeWidgetItem
            key
                The rcParams key
            val
                The proposed value
            orig
                The current value

        Yields
        ------
        QTreeWidgetItem
            The corresponding topLevelItem
        str
            The rcParams key
        object
            The proposed value
        object
            The current value
        """
        def no_check(item, key, val, orig):
            return True
        rc = self.rc
        filter_func = filter_func or no_check
        for item in self.top_level_items:
            key = asstring(item.text(0))
            editor = self.itemWidget(item.child(0), self.value_col)
            val = yaml.load(asstring(editor.toPlainText()))
            try:
                val = rc.validate[key](val)
            except:
                pass
            try:
                include = filter_func(item, key, val, rc[key])
            except:
                warn('Could not check state for %s key' % key,
                     RuntimeWarning)
            else:
                if include:
                    yield (item, key, val, rc[key])

    def apply_changes(self):
        """Update the :attr:`rc` with the proposed changes"""
        new = dict(self.changed_rc())
        if new != self.rc:
            self.rc.update(new)

    def select_changes(self):
        """Select all the items that changed comparing to the current rcParams
        """
        for item, val in self.changed_rc(True):
            item.setSelected(True)


class RcParamsWidget(ConfigPage, QWidget):
    """A configuration page for RcParams instances

    This page displays the :class:`psyplot.config.rcsetup.RcParams` instance in
    the :attr:`rc` attribute and let's the user modify it.

    Notes
    -----
    After the initialization, you have to call the :meth:`initialize` method"""

    #: the rcParams to use (must be implemented by subclasses)
    rc = None

    #: the :class:`RcParamsTree` that is used to display the rcParams
    tree = None

    @property
    def propose_changes(self):
        """A signal that is emitted if the user changes the values in the
        rcParams"""
        return self.tree.propose_changes

    @property
    def validChanged(self):
        """A signal that is emitted if the user changes the valid state of this
        page"""
        return self.tree.validChanged

    @property
    def changed(self):
        """True if any changes are proposed by this config page"""
        return bool(next(self.tree.changed_rc(), None))

    @property
    def is_valid(self):
        """True if all the settings are valid"""
        return self.tree.is_valid

    @property
    def icon(self):
        """The icon of this instance in the :class:`Preferences` dialog"""
        return QIcon(get_icon('rcParams.png'))

    def __init__(self, *args, **kwargs):
        super(RcParamsWidget, self).__init__(*args, **kwargs)
        self.vbox = vbox = QVBoxLayout()

        self.description = QLabel(
            '<p>Modify the rcParams for your need. Changes will not be applied'
            ' until you click the Apply or Ok button.</p>'
            '<p>Values must be entered in yaml syntax</p>', parent=self)
        vbox.addWidget(self.description)
        self.tree = tree = RcParamsTree(
            self.rc, getattr(self.rc, 'validate', None),
            getattr(self.rc, 'descriptions', None), parent=self)
        tree.setSelectionMode(QAbstractItemView.MultiSelection)
        vbox.addWidget(self.tree)

        self.bt_select_all = QPushButton('Select All', self)
        self.bt_select_changed = QPushButton('Select changes', self)
        self.bt_select_none = QPushButton('Clear Selection', self)
        self.bt_export = QToolButton(self)
        self.bt_export.setText('Export Selection...')
        self.bt_export.setToolTip('Export the selected rcParams to a file')
        self.bt_export.setPopupMode(QToolButton.InstantPopup)
        self.export_menu = export_menu = QMenu(self)
        export_menu.addAction(self.save_settings_action())
        export_menu.addAction(self.save_settings_action(True))
        self.bt_export.setMenu(export_menu)
        hbox = QHBoxLayout()
        hbox.addWidget(self.bt_select_all)
        hbox.addWidget(self.bt_select_changed)
        hbox.addWidget(self.bt_select_none)
        hbox.addStretch(1)
        hbox.addWidget(self.bt_export)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.bt_select_all.clicked.connect(self.tree.selectAll)
        self.bt_select_none.clicked.connect(self.tree.clearSelection)
        self.bt_select_changed.clicked.connect(self.tree.select_changes)

    def save_settings_action(self, update=False, target=None):
        """Create an action to save the selected settings in the :attr:`tree`

        Parameters
        ----------
        update: bool
            If True, it is expected that the file already exists and it will be
            updated. Otherwise, existing files will be overwritten
        """
        def func():
            if update:
                meth = QFileDialog.getOpenFileName
            else:
                meth = QFileDialog.getSaveFileName
            if target is None:
                fname = meth(
                    self, 'Select a file to %s' % (
                        'update' if update else 'create'),
                    self.default_path,
                    'YAML files (*.yml);;'
                    'All files (*)'
                    )
                if with_qt5:  # the filter is passed as well
                    fname = fname[0]
            else:
                fname = target
            if not fname:
                return
            if update:
                rc = self.rc.__class__(defaultParams=self.rc.defaultParams)
                rc.load_from_file(fname)
                old_keys = list(rc)
                selected = dict(self.tree.selected_rc())
                new_keys = list(selected)
                rc.update(selected)
                rc.dump(fname, include_keys=old_keys + new_keys,
                        exclude_keys=[])
            else:
                rc = self.rc.__class__(self.tree.selected_rc(),
                                       defaultParams=self.rc.defaultParams)
                rc.dump(fname, exclude_keys=[])

        action = QAction('Update...' if update else 'Overwrite...', self)
        action.triggered.connect(func)
        return action

    def initialize(self, rcParams=None, validators=None, descriptions=None):
        """Initialize the config page

        Parameters
        ----------
        rcParams: dict
            The rcParams to use. If None, the :attr:`rc` attribute of this
            instance is used
        validators: dict
            A mapping from the `rcParams` key to the corresponding validation
            function for the value. If None, the
            :attr:`~psyplot.config.rcsetup.RcParams.validate` attribute of the
            :attr:`rc` attribute is used
        descriptions: dict
            A mapping from the `rcParams` key to it's description. If None, the
            :attr:`~psyplot.config.rcsetup.RcParams.descriptions` attribute of
            the :attr:`rc` attribute is used"""
        if rcParams is not None:
            self.rc = rcParams
            self.tree.rc = rcParams
        if validators is not None:
            self.tree.validators = validators
        if descriptions is not None:
            self.tree.descriptions = descriptions
        self.tree.initialize()

    def apply_changes(self):
        """Apply the changes in the config page"""
        self.tree.apply_changes()


class GuiRcParamsWidget(RcParamsWidget):
    """The config page for the :class:`psyplot_gui.config.rcsetup.rcParams`"""

    rc = rcParams

    title = 'GUI defaults'

    default_path = psyplot_fname('PSYPLOTGUIRC', 'psyplotguirc.yml',
                                 if_exists=False)


class PsyRcParamsWidget(RcParamsWidget):
    """The config page for the :class:`psyplot.config.rcsetup.rcParams`"""

    rc = psy_rcParams

    title = 'psyplot defaults'

    default_path = psyplot_fname(if_exists=False)


class Prefences(QDialog):
    """Preferences dialog"""

    @property
    def bt_apply(self):
        return self.bbox.button(QDialogButtonBox.Apply)

    @property
    def pages(self):
        return map(self.get_page, range(self.pages_widget.count()))

    def __init__(self, main=None):
        super(Prefences, self).__init__(parent=main)
        self.setWindowTitle('Preferences')

        # Widgets
        self.pages_widget = QStackedWidget()
        self.contents_widget = QListWidget()
        self.bt_reset = QPushButton('Reset to defaults')
        self.bt_load_plugins = QPushButton('Load plugin pages')
        self.bt_load_plugins.setToolTip(
            'Load the rcParams for the plugins in separate pages')

        self.bbox = bbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Apply |
            QDialogButtonBox.Cancel)

        # Widgets setup
        # Destroying the C++ object right after closing the dialog box,
        # otherwise it may be garbage-collected in another QThread
        # (e.g. the editor's analysis thread in Spyder), thus leading to
        # a segmentation fault on UNIX or an application crash on Windows
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle('Preferences')
        self.contents_widget.setMovement(QListView.Static)
        self.contents_widget.setSpacing(1)
        self.contents_widget.setCurrentRow(0)

        # Layout
        hsplitter = QSplitter()
        hsplitter.addWidget(self.contents_widget)
        hsplitter.addWidget(self.pages_widget)
        hsplitter.setStretchFactor(1, 1)

        btnlayout = QHBoxLayout()
        btnlayout.addWidget(self.bt_reset)
        btnlayout.addWidget(self.bt_load_plugins)
        btnlayout.addStretch(1)
        btnlayout.addWidget(bbox)

        vlayout = QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        # Signals and slots
        if main is not None:
            self.bt_reset.clicked.connect(main.reset_rcParams)
        self.bt_load_plugins.clicked.connect(self.load_plugin_pages)
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(
            self.pages_widget.setCurrentIndex)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        self.bt_apply.clicked.connect(self.apply_clicked)
        self.bt_apply.setEnabled(False)

    def set_current_index(self, index):
        """Set current page index"""
        self.contents_widget.setCurrentRow(index)

    def current_page_changed(self, index):
        configpage = self.get_page(index)
        self.bt_apply.setVisible(not configpage.auto_updates)
        self.check_changes(configpage)

    def get_page(self, index=None):
        """Return page widget"""
        if index is None:
            widget = self.pages_widget.currentWidget()
        else:
            widget = self.pages_widget.widget(index)
        return widget.widget()

    def accept(self):
        """Reimplement Qt method"""
        for configpage in self.pages:
            if not configpage.is_valid:
                continue
            configpage.apply_changes()
        QDialog.accept(self)

    def apply_clicked(self):
        # Apply button was clicked
        configpage = self.get_page()
        if configpage.is_valid:
            configpage.apply_changes()
        self.check_changes(configpage)

    def add_page(self, widget):
        """Add a new page to the preferences dialog

        Parameters
        ----------
        widget: ConfigPage
            The page to add"""
        widget.validChanged.connect(self.bt_apply.setEnabled)
        widget.validChanged.connect(
            self.bbox.button(QDialogButtonBox.Ok).setEnabled)
        scrollarea = QScrollArea(self)
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(widget)
        self.pages_widget.addWidget(scrollarea)
        item = QListWidgetItem(self.contents_widget)
        try:
            item.setIcon(widget.icon)
        except TypeError:
            pass
        item.setText(widget.title)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item.setSizeHint(QtCore.QSize(0, 25))
        widget.propose_changes.connect(self.check_changes)

    def check_changes(self, configpage):
        """Enable the apply button if there are changes to the settings"""
        if configpage != self.get_page():
            return
        self.bt_apply.setEnabled(
            not configpage.auto_updates and configpage.is_valid and
            configpage.changed)

    def load_plugin_pages(self):
        """Load the rcParams for the plugins in separate pages"""
        validators = psy_rcParams.validate
        descriptions = psy_rcParams.descriptions
        for ep in psy_rcParams._load_plugin_entrypoints():
            plugin = ep.load()
            rc = getattr(plugin, 'rcParams', None)
            if rc is None:
                rc = RcParams()
            w = RcParamsWidget(parent=self)
            w.title = 'rcParams of ' + ep.module_name
            w.default_path = PsyRcParamsWidget.default_path
            w.initialize(rcParams=rc, validators=validators,
                         descriptions=descriptions)
            # use the full rcParams after initialization
            w.rc = psy_rcParams
            self.add_page(w)
