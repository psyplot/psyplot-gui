"""Dependencies widget of the psyplot package

This module defines the :class:`DependenciesWidget` that shows the versions of
of psyplot, psyplot_gui, psyplot plugins and their requirements"""
from psyplot_gui.compat.qtcompat import (
    QDialog, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QLabel, QMenu, QAction,
    Qt, QApplication, QMessageBox, QPushButton, QHBoxLayout, QAbstractItemView,
    QDialogButtonBox, QtCore)
from psyplot.docstring import docstrings


class DependenciesTree(QTreeWidget):
    """A tree widget to display dependencies

    This widget uses a dictionary as created through the
    :func:`psyplot.get_versions` function to display the requirements and
    versions."""

    @docstrings.get_sectionsf('DependenciesTree')
    def __init__(self, versions, *args, **kwargs):
        """
        Parameters
        ----------
        versions: dict
            The dictionary that contains the version information

        See Also
        --------
        psyplot.get_versions
        """
        super(DependenciesTree, self).__init__(*args, **kwargs)
        self.resizeColumnToContents(0)
        self.setColumnCount(2)
        self.setHeaderLabels(['Package', 'installed version'])
        self.add_dependencies(versions)
        self.expandAll()
        self.resizeColumnToContents(0)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)

    @docstrings.dedent
    def add_dependencies(self, versions, parent=None):
        """
        Add the version informations to the tree

        This method creates an QTreeWidgetItem for each package in `versions`
        and adds it to this tree.

        Parameters
        ----------
        %(DependenciesTree.parameters)s
        parent: QTreeWidgetItem
            The parent of the newly created items for the packages in
            `versions`. If None, the newly created items are inserted as
            top level items into the tree
        """
        for pkg, pkg_d in versions.items():
            new_item = QTreeWidgetItem(0)
            new_item.setText(0, pkg)
            if isinstance(pkg_d, dict):
                new_item.setText(1, pkg_d['version'])
            else:
                new_item.setText(1, pkg_d)
            if parent is None:
                self.addTopLevelItem(new_item)
            else:
                parent.addChild(new_item)
            if 'requirements' in pkg_d:
                self.add_dependencies(pkg_d['requirements'], new_item)

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


class DependenciesDialog(QDialog):
    """A dialog for displaying the dependencies"""

    #: description label
    label = None

    #: the QVBoxLayout containing all the widgets
    vbox = None

    #: The :class:`DependenciesTree` that contains the package infos
    tree = None

    #: The QPushButton used for copying selected packages to the clipboard
    bt_copy = None

    #: A simple info label for info messages
    info_label = None

    #: A QTimer that clears the :attr:`info_label` after some time
    timer = None

    @docstrings.dedent
    def __init__(self, versions, *args, **kwargs):
        """
        Parameters
        ----------
        %(DependenciesTree.parameters)s
        """
        super(DependenciesDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle('Dependencies')
        self.versions = versions
        self.vbox = layout = QVBoxLayout()

        self.label = QLabel("""
            psyplot and the plugins depend on several python libraries. The
            tree widget below lists the versions of the plugins and the
            requirements. You can select the items in the tree and copy them to
            clipboard.""", parent=self)

        layout.addWidget(self.label)

        self.tree = DependenciesTree(versions, parent=self)
        self.tree.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.tree)

        # copy button
        self.bt_copy = QPushButton('Copy selection to clipboard')
        self.bt_copy.setToolTip(
            'Copy the selected packages in the above table to the clipboard.')
        self.bt_copy.clicked.connect(lambda: self.copy_selected())

        self.bbox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.bbox.accepted.connect(self.accept)

        hbox = QHBoxLayout()
        hbox.addWidget(self.bt_copy)
        hbox.addStretch(1)
        hbox.addWidget(self.bbox)
        layout.addLayout(hbox)

        #: A label for simple status update
        self.info_label = QLabel('', self)
        layout.addWidget(self.info_label)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.clear_label)

        self.setLayout(layout)

    def copy_selected(self, label=None):
        """Copy the selected versions and items to the clipboard"""
        d = {}
        items = self.tree.selectedItems()
        if not items:
            QMessageBox.warning(self, "No packages selected!",
                                "Please select packages in the tree!")
            return
        for item in items:
            d[item.text(0)] = item.text(1)
        if label is None:
            label = QApplication.clipboard()
        label.setText("\n".join(
            '%s: %s' % t for t in d.items()))
        self.info_label.setText('Packages copied to clipboard.')
        self.timer.start(3000)

    def clear_label(self):
        """Clear the info label"""
        self.info_label.setText('')
