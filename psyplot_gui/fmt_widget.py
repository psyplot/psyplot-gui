# -*- coding: utf-8 -*-
"""Module defining a widget for updating the formatoption of the current
project"""
import six
import yaml
from functools import partial
from collections import defaultdict
from itertools import chain
import logging
from warnings import warn
from IPython.core.interactiveshell import ExecutionResult
import psyplot.project as psy
from psyplot.utils import _temp_bool_prop, unique_everseen
from psyplot_gui.compat.qtcompat import (
    QWidget, QHBoxLayout, QComboBox, QLineEdit, QVBoxLayout, QToolButton,
    QIcon, QPushButton, QCheckBox, QTextEdit, QListView, QCompleter, Qt,
    QStandardItemModel, QStandardItem, with_qt5)
from psyplot_gui.plot_creator import CoordComboBox
from psyplot_gui.config.rcsetup import rcParams
from psyplot.compat.pycompat import OrderedDict, map
from psyplot_gui.common import DockMixin, get_icon, PyErrorMessage
from psyplot.data import safe_list
import psyplot.plotter as psyp
from psyplot.data import isstring

try:
    from IPython.core.interactiveshell import ExecutionInfo
except ImportError:
    ExecutionInfo = None


logger = logging.getLogger(__name__)


COORDSGROUP = '__coords'
ALLGROUP = '__all'


class DimensionsWidget(QWidget):
    """A widget for updating the dimensions"""

    def __init__(self, parent, dim=None):
        super(DimensionsWidget, self).__init__(parent)
        self.coord_combo = CoordComboBox(self.get_ds, dim)
        self.cb_use_coord = QCheckBox('show coordinates')
        self.cb_close_popups = QCheckBox('close dropdowns')
        self.cb_close_popups.setChecked(True)
        self.toggle_close_popup()
        self._single_selection = False

        self.dim = dim
        hbox = QHBoxLayout()
        hbox.addWidget(self.cb_close_popups)
        hbox.addWidget(self.cb_use_coord)
        hbox.addWidget(self.coord_combo)
        self.setLayout(hbox)
        self.cb_use_coord.stateChanged.connect(self.reset_combobox)
        self.cb_close_popups.stateChanged.connect(self.toggle_close_popup)
        self.coord_combo.leftclick.connect(self.insert_from_combo)

    def set_dim(self, dim):
        self.dim = self.coord_combo.dim = dim

    def slice2list(self, sl):
        if not isinstance(sl, slice):
            return sl
        return list(range(*sl.indices(self.coord_combo.count() - 1)))

    def reset_combobox(self):
        """Clear all comboboxes"""
        self.coord_combo.use_coords = self.cb_use_coord.isChecked()
        self.coord_combo.clear()
        self.coord_combo._is_empty = True

    def toggle_close_popup(self):
        self.coord_combo.close_popups = self.cb_close_popups.isChecked()

    def insert_from_combo(self):
        cb = self.coord_combo
        inserts = list(
            ind.row() - 1
            for ind in cb.view().selectionModel().selectedIndexes()
            if ind.row() > 0)
        if not inserts:
            return
        elif not self._single_selection:
            try:
                current = yaml.load(self.parent().get_text())
            except Exception:
                pass
            else:
                if current:
                    current = self.slice2list(current)
                    inserts = sorted(set(chain(inserts, safe_list(current))))
        else:
            inserts = inserts[0]

        self.parent().set_obj(inserts)

    def get_ds(self):
        import psyplot.project as psy
        project = psy.gcp()
        datasets = project.datasets
        dim = self.dim
        dims = {ds.coords[dim].shape[0]: ds for ds in datasets.values()}
        if len(dims) > 1:
            warn("Datasets have differing dimensions lengths for the "
                 "%s dimension!" % dim)
        return min(dims.items())[1]

    def set_single_selection(self, yes=True):
        self._single_selection = yes
        if yes:
            self.coord_combo.view().setSelectionMode(
                QListView.SingleSelection)
        else:
            self.coord_combo.view().setSelectionMode(
                QListView.ExtendedSelection)


class FormatoptionWidget(QWidget, DockMixin):
    """
    Widget to update the formatoptions of the current project

    This widget, mainly made out of a combobox for the formatoption group,
    a combobox for the formatoption, and a text editor, is designed
    for updating the selected formatoptions for the current subproject.

    The widget is connected to the :attr:`psyplot.project.Project.oncpchange`
    signal and refills the comboboxes if the current subproject changes.

    The text editor either accepts python code that will be executed by the
    given `console`, or yaml code.
    """

    no_fmtos_update = _temp_bool_prop(
        'no_fmtos_update', """update the fmto combo box or not""")

    #: The combobox for the formatoption groups
    group_combo = None

    #: The combobox for the formatoptions
    fmt_combo = None

    #: The help_explorer to display the documentation of the formatoptions
    help_explorer = None

    #: The formatoption specific widget that is loaded from the formatoption
    fmt_widget = None

    #: A line edit for updating the formatoptions
    line_edit = None

    #: A multiline text editor for updating the formatoptions
    text_edit = None

    #: A button to switch between :attr:`line_edit` and :attr:`text_edit`
    multiline_button = None

    @property
    def shell(self):
        """The shell to execute the update of the formatoptions in the current
        project"""
        return self.console.kernel_manager.kernel.shell

    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        help_explorer: psyplot_gui.help_explorer.HelpExplorer
            The help explorer to show the documentation of one formatoption
        console: psyplot_gui.console.ConsoleWidget
            The console that can be used to update the current subproject via::

                psy.gcp().update(**kwargs)

            where ``**kwargs`` is defined through the selected formatoption
            in the :attr:`fmt_combo` combobox and the value in the
            :attr:`line_edit` editor
        ``*args, **kwargs``
            Any other keyword for the QWidget class
        """
        help_explorer = kwargs.pop('help_explorer', None)
        console = kwargs.pop('console', None)
        super(FormatoptionWidget, self).__init__(*args, **kwargs)
        self.help_explorer = help_explorer
        self.console = console
        self.error_msg = PyErrorMessage(self)

        # ---------------------------------------------------------------------
        # -------------------------- Child widgets ----------------------------
        # ---------------------------------------------------------------------
        self.group_combo = QComboBox(parent=self)
        self.fmt_combo = QComboBox(parent=self)
        self.line_edit = QLineEdit(parent=self)
        self.text_edit = QTextEdit(parent=self)
        self.run_button = QToolButton(parent=self)

        # completer for the fmto widget
        self.fmt_combo.setEditable(True)
        self.fmt_combo.setInsertPolicy(QComboBox.NoInsert)
        self.fmto_completer = completer = QCompleter(
            ['time', 'lat', 'lon', 'lev'])
        completer.setCompletionMode(
            QCompleter.PopupCompletion)
        completer.activated[str].connect(self.set_fmto)
        if with_qt5:
            completer.setFilterMode(Qt.MatchContains)
        completer.setModel(QStandardItemModel())
        self.fmt_combo.setCompleter(completer)

        self.dim_widget = DimensionsWidget(parent=self)
        self.dim_widget.setVisible(False)

        self.multiline_button = QPushButton('Multiline', parent=self)
        self.multiline_button.setCheckable(True)

        self.yaml_cb = QCheckBox('Yaml syntax')
        self.yaml_cb.setChecked(True)

        self.keys_button = QPushButton('Keys', parent=self)
        self.summaries_button = QPushButton('Summaries', parent=self)
        self.docs_button = QPushButton('Docs', parent=self)

        self.grouped_cb = QCheckBox('grouped', parent=self)
        self.all_groups_cb = QCheckBox('all groups', parent=self)
        self.include_links_cb = QCheckBox('include links', parent=self)

        self.text_edit.setVisible(False)

        # ---------------------------------------------------------------------
        # -------------------------- Descriptions -----------------------------
        # ---------------------------------------------------------------------

        self.group_combo.setToolTip('Select the formatoption group')
        self.fmt_combo.setToolTip('Select the formatoption to update')
        self.line_edit.setToolTip(
            'Insert the value which what you want to update the selected '
            'formatoption and hit right button. The code is executed in the '
            'main console.')
        self.yaml_cb.setToolTip(
            "Use the yaml syntax for the values inserted in the above cell. "
            "Otherwise the content there is evaluated as a python expression "
            "in the terminal")
        self.text_edit.setToolTip(self.line_edit.toolTip())
        self.run_button.setIcon(QIcon(get_icon('run_arrow.png')))
        self.run_button.setToolTip('Update the selected formatoption')
        self.multiline_button.setToolTip(
            'Allow linebreaks in the text editor line above.')
        self.keys_button.setToolTip(
            'Show the formatoption keys in this group (or in all '
            'groups) in the help explorer')
        self.summaries_button.setToolTip(
            'Show the formatoption summaries in this group (or in all '
            'groups) in the help explorer')
        self.docs_button.setToolTip(
            'Show the formatoption documentations in this group (or in all '
            'groups) in the help explorer')
        self.grouped_cb.setToolTip(
            'Group the formatoptions before displaying them in the help '
            'explorer')
        self.all_groups_cb.setToolTip('Use all groups when displaying the '
                                      'keys, docs or summaries')
        self.include_links_cb.setToolTip(
            'Include links to remote documentations when showing the '
            'keys, docs and summaries in the help explorer (requires '
            'intersphinx)')

        # ---------------------------------------------------------------------
        # -------------------------- Connections ------------------------------
        # ---------------------------------------------------------------------
        self.group_combo.currentIndexChanged[int].connect(self.fill_fmt_combo)
        self.fmt_combo.currentIndexChanged[int].connect(self.show_fmt_info)
        self.fmt_combo.currentIndexChanged[int].connect(self.load_fmt_widget)
        self.fmt_combo.currentIndexChanged[int].connect(
            self.set_current_fmt_value)
        self.run_button.clicked.connect(self.run_code)
        self.line_edit.returnPressed.connect(self.run_button.click)
        self.multiline_button.clicked.connect(self.toggle_line_edit)
        self.keys_button.clicked.connect(
            partial(self.show_all_fmt_info, 'keys'))
        self.summaries_button.clicked.connect(
            partial(self.show_all_fmt_info, 'summaries'))
        self.docs_button.clicked.connect(
            partial(self.show_all_fmt_info, 'docs'))

        # ---------------------------------------------------------------------
        # ------------------------------ Layouts ------------------------------
        # ---------------------------------------------------------------------
        self.combos = QHBoxLayout()
        self.combos.addWidget(self.group_combo)
        self.combos.addWidget(self.fmt_combo)

        self.execs = QHBoxLayout()
        self.execs.addWidget(self.line_edit)
        self.execs.addWidget(self.text_edit)
        self.execs.addWidget(self.run_button)

        self.info_box = QHBoxLayout()
        self.info_box.addWidget(self.multiline_button)
        self.info_box.addWidget(self.yaml_cb)
        self.info_box.addStretch(0)
        for w in [self.keys_button, self.summaries_button, self.docs_button,
                  self.all_groups_cb, self.grouped_cb, self.include_links_cb]:
            self.info_box.addWidget(w)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.combos)
        self.vbox.addWidget(self.dim_widget)
        self.vbox.addLayout(self.execs)
        self.vbox.addLayout(self.info_box)

        self.vbox.setSpacing(0)

        self.setLayout(self.vbox)

        # fill with content
        self.fill_combos_from_project(psy.gcp())
        psy.Project.oncpchange.connect(self.fill_combos_from_project)
        rcParams.connect('fmt.sort_by_key', self.refill_from_rc)

    def refill_from_rc(self, sort_by_key):
        from psyplot.project import gcp
        self.fill_combos_from_project(gcp())

    def fill_combos_from_project(self, project):
        """Fill :attr:`group_combo` and :attr:`fmt_combo` from a project

        Parameters
        ----------
        project: psyplot.project.Project
            The project to use"""
        if rcParams['fmt.sort_by_key']:
            def sorter(fmto):
                return fmto.key
        else:
            sorter = self.get_name

        current_text = self.group_combo.currentText()
        with self.no_fmtos_update:
            self.group_combo.clear()
            if project is None or project.is_main or not len(project):
                self.fmt_combo.clear()
                self.groups = []
                self.fmtos = []
                self.line_edit.setEnabled(False)
                return
            self.line_edit.setEnabled(True)
            # get dimensions
            it_vars = chain.from_iterable(
                arr.psy.iter_base_variables for arr in project.arrays)
            dims = next(it_vars).dims
            sdims = set(dims)
            for var in it_vars:
                sdims.intersection_update(var.dims)
            coords = [d for d in dims if d in sdims]
            coords_name = [COORDSGROUP] if coords else []
            coords_verbose = ['Dimensions'] if coords else []
            coords = [coords] if coords else []

            if len(project.plotters):
                # get formatoptions and group them alphabetically
                grouped_fmts = defaultdict(list)
                for fmto in project._fmtos:
                    grouped_fmts[fmto.group].append(fmto)
                for val in six.itervalues(grouped_fmts):
                    val.sort(key=sorter)
                grouped_fmts = OrderedDict(
                    sorted(six.iteritems(grouped_fmts),
                           key=lambda t: psyp.groups.get(t[0], t[0])))
                fmt_groups = list(grouped_fmts.keys())
                # save original names
                self.groups = coords_name + [ALLGROUP] + fmt_groups
                # save verbose group names (which are used in the combo box)
                self.groupnames = (
                    coords_verbose + ['All formatoptions'] + list(
                        map(lambda s: psyp.groups.get(s, s), fmt_groups)))
                # save formatoptions
                fmtos = list(grouped_fmts.values())
                self.fmtos = coords + [sorted(
                    chain(*fmtos), key=sorter)] + fmtos
            else:
                self.groups = coords_name
                self.groupnames = coords_verbose
                self.fmtos = coords
            self.group_combo.addItems(self.groupnames)
            ind = self.group_combo.findText(current_text)
            self.group_combo.setCurrentIndex(ind if ind >= 0 else 0)
        self.fill_fmt_combo(self.group_combo.currentIndex())

    def get_name(self, fmto):
        """Get the name of a :class:`psyplot.plotter.Formatoption` instance"""
        if isinstance(fmto, six.string_types):
            return fmto
        return '%s (%s)' % (fmto.name, fmto.key) if fmto.name else fmto.key

    @property
    def fmto(self):
        return self.fmtos[self.group_combo.currentIndex()][
            self.fmt_combo.currentIndex()]

    @fmto.setter
    def fmto(self, value):
        name = self.get_name(value)
        for i, fmtos in enumerate(self.fmtos):
            if i == 1:  # all formatoptions
                continue
            if name in map(self.get_name, fmtos):
                with self.no_fmtos_update:
                    self.group_combo.setCurrentIndex(i)
                self.fill_fmt_combo(i, name)
                return

    def toggle_line_edit(self):
        """Switch between the :attr:`line_edit` and :attr:`text_edit`

        This method is called when the :attr:`multiline_button` is clicked
        and switches between the single line :attr:``line_edit` and the
        multiline :attr:`text_edit`
        """
        # switch to multiline text edit
        if (self.multiline_button.isChecked() and
                not self.text_edit.isVisible()):
            self.line_edit.setVisible(False)
            self.text_edit.setVisible(True)
            self.text_edit.setPlainText(self.line_edit.text())
        elif (not self.multiline_button.isChecked() and
              not self.line_edit.isVisible()):
            self.line_edit.setVisible(True)
            self.text_edit.setVisible(False)
            self.line_edit.setText(self.text_edit.toPlainText())

    def fill_fmt_combo(self, i, current_text=None):
        """Fill the :attr:`fmt_combo` combobox based on the current group name
        """
        if not self.no_fmtos_update:
            with self.no_fmtos_update:
                if current_text is None:
                    current_text = self.fmt_combo.currentText()
                self.fmt_combo.clear()
                self.fmt_combo.addItems(
                    list(map(self.get_name, self.fmtos[i])))
                ind = self.fmt_combo.findText(current_text)
                self.fmt_combo.setCurrentIndex(ind if ind >= 0 else 0)
                # update completer model
                self.setup_fmt_completion_model()
            idx = self.fmt_combo.currentIndex()
            self.show_fmt_info(idx)
            self.load_fmt_widget(idx)
            self.set_current_fmt_value(idx)

    def set_fmto(self, name):
        self.fmto = name

    def setup_fmt_completion_model(self):
        fmtos = list(unique_everseen(map(
            self.get_name, chain.from_iterable(self.fmtos))))
        model = self.fmto_completer.model()
        model.setRowCount(len(fmtos))
        for i, name in enumerate(fmtos):
            model.setItem(i, QStandardItem(name))

    def load_fmt_widget(self, i):
        """Load the formatoption specific widget

        This method loads the formatoption specific widget from the
        :meth:`psyplot.plotter.Formatoption.get_fmt_widget` method and
        displays it above the :attr:`line_edit`

        Parameters
        ----------
        i: int
            The index of the current formatoption"""
        self.remove_fmt_widget()
        group_ind = self.group_combo.currentIndex()
        if not self.no_fmtos_update:
            from psyplot.project import gcp
            if self.groups[group_ind] == COORDSGROUP:
                dim = self.fmtos[group_ind][i]
                self.fmt_widget = self.dim_widget
                self.dim_widget.set_dim(dim)
                self.dim_widget.set_single_selection(
                    dim not in gcp()[0].dims)
                self.dim_widget.setVisible(True)
            else:
                fmto = self.fmtos[group_ind][i]
                self.fmt_widget = fmto.get_fmt_widget(self, gcp())
                if self.fmt_widget is not None:
                    self.vbox.insertWidget(2, self.fmt_widget)

    def reset_fmt_widget(self):
        idx = self.fmt_combo.currentIndex()
        self.load_fmt_widget(idx)
        self.set_current_fmt_value(idx)

    def remove_fmt_widget(self):
        if self.fmt_widget is not None:
            self.fmt_widget.hide()
            if self.fmt_widget is self.dim_widget:
                self.fmt_widget.reset_combobox()
            else:
                self.vbox.removeWidget(self.fmt_widget)
                self.fmt_widget.close()
            del self.fmt_widget

    def set_current_fmt_value(self, i):
        """Add the value of the current formatoption to the line text"""
        group_ind = self.group_combo.currentIndex()
        if not self.no_fmtos_update:
            if self.groups[group_ind] == COORDSGROUP:
                from psyplot.project import gcp
                dim = self.fmtos[group_ind][i]
                self.set_obj(gcp().arrays[0].psy.idims[dim])
            else:
                fmto = self.fmtos[group_ind][i]
                self.set_obj(fmto.value)

    def show_fmt_info(self, i):
        """Show the documentation of the formatoption in the help explorer
        """
        group_ind = self.group_combo.currentIndex()
        if (not self.no_fmtos_update and
                self.groups[group_ind] != COORDSGROUP):
            fmto = self.fmtos[self.group_combo.currentIndex()][i]
            fmto.plotter.show_docs(
                fmto.key, include_links=self.include_links_cb.isChecked())

    def run_code(self):
        """Run the update of the project inside the :attr:`shell`"""
        if self.line_edit.isVisible():
            text = str(self.line_edit.text())
        else:
            text = str(self.text_edit.toPlainText())
        if not text or not self.fmtos:
            return
        group_ind = self.group_combo.currentIndex()
        if self.groups[group_ind] == COORDSGROUP:
            key = self.fmtos[group_ind][self.fmt_combo.currentIndex()]
            param = 'dims'
        else:
            key = self.fmtos[group_ind][self.fmt_combo.currentIndex()].key
            param = 'fmt'
        if self.yaml_cb.isChecked():
            import psyplot.project as psy
            psy.gcp().update(**{key: yaml.load(text)})
        else:
            code = "psy.gcp().update(%s={'%s': %s})" % (param, key, text)
            if ExecutionInfo is not None:
                info = ExecutionInfo(raw_cell=code, store_history=False,
                                     silent=True, shell_futures=False)
                e = ExecutionResult(info)
            else:
                e = ExecutionResult()
            self.console.run_command_in_shell(code, e)
            try:
                e.raise_error()
            except Exception:  # reset the console and clear the error message
                raise
            finally:
                self.console.reset()

    def get_text(self):
        """Get the current update text"""
        if self.line_edit.isVisible():
            return self.line_edit.text()
        else:
            return self.text_edit.toPlainText()

    def get_obj(self):
        """Get the current update text"""
        if self.line_edit.isVisible():
            txt = self.line_edit.text()
        else:
            txt = self.text_edit.toPlainText()
        try:
            obj = yaml.load(txt)
        except Exception:
            self.error_msg.showTraceback("Could not load %s" % txt)
        else:
            return obj

    def insert_obj(self, obj):
        """Add a string to the formatoption widget"""
        current = self.get_text()
        use_yaml = self.yaml_cb.isChecked()
        use_line_edit = self.line_edit.isVisible()
        # strings are treated separately such that we consider quotation marks
        # at the borders
        if isstring(obj) and current:
            if use_line_edit:
                pos = self.line_edit.cursorPosition()
            else:
                pos = self.text_edit.textCursor().position()
            if pos not in [0, len(current)]:
                s = obj
            else:
                if current[0] in ['"', "'"]:
                    current = current[1:-1]
                self.clear_text()
                if pos == 0:
                    s = '"' + obj + current + '"'
                else:
                    s = '"' + current + obj + '"'
                current = ''
        elif isstring(obj):  # add quotation marks
            s = '"' + obj + '"'
        elif not use_yaml:
            s = repr(obj)
        else:
            s = yaml.dump(obj).strip()
            if s.endswith('\n...'):
                s = s[:-4]
        if use_line_edit:
            self.line_edit.insert(s)
        else:
            self.text_edit.insertPlainText(s)

    def clear_text(self):
        if self.line_edit.isVisible():
            self.line_edit.clear()
        else:
            self.text_edit.clear()

    def set_obj(self, obj):
        self.clear_text()
        self.insert_obj(obj)

    def show_all_fmt_info(self, what):
        """Show the keys, summaries or docs of the formatoptions

        Calling this function let's the help browser show the documentation
        etc. of all docs or only the selected group determined by the state of
        the :attr:`grouped_cb` and :attr:`all_groups_cb` checkboxes

        Parameters
        ----------
        what: {'keys', 'summaries', 'docs'}
            Determines what to show"""
        if not self.fmtos:
            return
        if (self.all_groups_cb.isChecked() or
                self.group_combo.currentIndex() < 2):
            fmtos = list(chain.from_iterable(
                fmto_group for i, fmto_group in enumerate(self.fmtos)
                if self.groups[i] not in [ALLGROUP, COORDSGROUP]))
        else:
            fmtos = self.fmtos[self.group_combo.currentIndex()]
        plotter = fmtos[0].plotter
        getattr(plotter, 'show_' + what)(
            [fmto.key for fmto in fmtos], grouped=self.grouped_cb.isChecked(),
            include_links=self.include_links_cb.isChecked())
