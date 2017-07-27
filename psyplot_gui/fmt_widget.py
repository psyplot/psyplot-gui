# -*- coding: utf-8 -*-
"""Module defining a widget for updating the formatoption of the current
project"""
import six
from functools import partial
from collections import defaultdict
from itertools import chain
import logging
from IPython.core.interactiveshell import ExecutionResult
import psyplot.project as psy
from psyplot.utils import _temp_bool_prop
from psyplot_gui.compat.qtcompat import (
    QWidget, QHBoxLayout, QComboBox, QLineEdit, QVBoxLayout, QToolButton,
    QIcon, QPushButton, QCheckBox)
from psyplot.compat.pycompat import OrderedDict, map
from psyplot_gui.common import DockMixin, get_icon
import psyplot.plotter as psyp


logger = logging.getLogger(__name__)


COORDSGROUP = '__coords'
ALLGROUP = '__all'


class FormatoptionWidget(QWidget, DockMixin):
    """
    Widget to update the formatoptions of the current project

    This widget, mainly made out of a combobox for the formatoption group,
    a combobox for the formatoption, and a one-line text editor, is designed
    for updating the selected formatoptions for the current subproject.

    The widget is connected to the :attr:`psyplot.project.Project.oncpchange`
    signal and refills the comboboxes if the current subproject changes.

    The one-line text editor accepts python code that will be executed in side
    the given `shell`.
    """

    no_fmtos_update = _temp_bool_prop(
        'no_fmtos_update', """update the fmto combo box or not""")

    #: The combobox for the formatoption groups
    group_combo = None

    #: The combobox for the formatoptions
    fmt_combo = None

    #: The help_explorer to display the documentation of the formatoptions
    help_explorer = None

    #: The shell to execute the update of the formatoptions in the current
    #: project
    shell = None

    def __init__(self, *args, **kwargs):
        """
        Parameters
        ----------
        help_explorer: psyplot_gui.help_explorer.HelpExplorer
            The help explorer to show the documentation of one formatoption
        shell: IPython.core.interactiveshell.InteractiveShell
            The shell that can be used to update the current subproject via::

                psy.gcp().update(**kwargs)

            where ``**kwargs`` is defined through the selected formatoption
            in the :attr:`fmt_combo` combobox and the value in the
            :attr:`line_edit` editor
        ``*args, **kwargs``
            Any other keyword for the QWidget class
        """
        help_explorer = kwargs.pop('help_explorer', None)
        shell = kwargs.pop('shell', None)
        super(FormatoptionWidget, self).__init__(*args, **kwargs)
        self.help_explorer = help_explorer
        self.shell = shell

        # ---------------------------------------------------------------------
        # -------------------------- Child widgets ----------------------------
        # ---------------------------------------------------------------------
        self.group_combo = QComboBox(parent=self)
        self.fmt_combo = QComboBox(parent=self)
        self.line_edit = QLineEdit(parent=self)
        self.run_button = QToolButton(parent=self)

        self.keys_button = QPushButton('Formatoption keys', parent=self)
        self.summaries_button = QPushButton('Summaries', parent=self)
        self.docs_button = QPushButton('Docs', parent=self)

        self.grouped_cb = QCheckBox('grouped', parent=self)
        self.all_groups_cb = QCheckBox('all groups', parent=self)
        self.include_links_cb = QCheckBox('include links', parent=self)

        # ---------------------------------------------------------------------
        # -------------------------- Descriptions -----------------------------
        # ---------------------------------------------------------------------

        self.group_combo.setToolTip('Select the formatoption group')
        self.fmt_combo.setToolTip('Select the formatoption to update')
        self.line_edit.setToolTip(
            'Insert the value which what you want to update the selected '
            'formatoption and hit right button. The code is executed in the '
            'main console.')
        self.run_button.setIcon(QIcon(get_icon('run_arrow.png')))
        self.run_button.setToolTip('Update the selected formatoption')
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
        self.run_button.clicked.connect(self.run_code)
        self.line_edit.returnPressed.connect(self.run_button.click)
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
        self.execs.addWidget(self.run_button)

        self.info_box = QHBoxLayout()
        self.info_box.addStretch(0)
        for w in [self.keys_button, self.summaries_button, self.docs_button,
                  self.all_groups_cb, self.grouped_cb, self.include_links_cb]:
            self.info_box.addWidget(w)

        self.vbox = QVBoxLayout()
        self.vbox.addLayout(self.combos)
        self.vbox.addLayout(self.execs)
        self.vbox.addLayout(self.info_box)

        self.setLayout(self.vbox)

        # fill with content
        self.fill_combos_from_project(psy.gcp())
        psy.Project.oncpchange.connect(self.fill_combos_from_project)

    def fill_combos_from_project(self, project):
        """Fill :attr:`group_combo` and :attr:`fmt_combo` from a project

        Parameters
        ----------
        project: psyplot.project.Project
            The project to use"""
        current_text = self.group_combo.currentText()
        with self.no_fmtos_update:
            self.group_combo.clear()
            if project is None or project.is_main or not len(project.plotters):
                self.fmt_combo.clear()
                self.groups = []
                self.fmtos = []
                self.line_edit.setEnabled(False)
                return
            self.line_edit.setEnabled(True)
            # get dimensions
            coords = sorted(project.coords_intersect)
            coords_name = [COORDSGROUP] if coords else []
            coords_verbose = ['Dimensions'] if coords else []
            coords = [coords] if coords else []

            # get formatoptions and group them alphabetically
            grouped_fmts = defaultdict(list)
            for fmto in project._fmtos:
                grouped_fmts[fmto.group].append(fmto)
            for val in six.itervalues(grouped_fmts):
                val.sort(key=self.get_name)
            grouped_fmts = OrderedDict(
                sorted(six.iteritems(grouped_fmts),
                       key=lambda t: psyp.groups.get(t[0], t[0])))
            fmt_groups = list(grouped_fmts.keys())
            # save original names
            self.groups = coords_name + [ALLGROUP] + fmt_groups
            # save verbose group names (which are used in the combo box)
            self.groupnames = coords_verbose + ['All formatoptions'] + list(
                map(lambda s: psyp.groups.get(s, s), fmt_groups))
            # save formatoptions
            fmtos = list(grouped_fmts.values())
            self.fmtos = coords + [sorted(
                chain(*fmtos), key=self.get_name)] + fmtos
            self.group_combo.addItems(self.groupnames)
            ind = self.group_combo.findText(current_text)
            self.group_combo.setCurrentIndex(ind if ind >= 0 else 0)
        self.fill_fmt_combo(self.group_combo.currentIndex())

    def get_name(self, fmto):
        """Get the name of a :class:`psyplot.plotter.Formatoption` instance"""
        if isinstance(fmto, six.string_types):
            return fmto
        return '%s (%s)' % (fmto.name, fmto.key) if fmto.name else fmto.key

    def fill_fmt_combo(self, i):
        """Fill the :attr:`fmt_combo` combobox based on the current group name
        """
        if not self.no_fmtos_update:
            with self.no_fmtos_update:
                current_text = self.fmt_combo.currentText()
                self.fmt_combo.clear()
                self.fmt_combo.addItems(
                    list(map(self.get_name, self.fmtos[i])))
                ind = self.fmt_combo.findText(current_text)
                self.fmt_combo.setCurrentIndex(ind if ind >= 0 else 0)
            self.show_fmt_info(self.fmt_combo.currentIndex())

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
        text = str(self.line_edit.text())
        if not text or not self.fmtos:
            return
        group_ind = self.group_combo.currentIndex()
        if self.groups[group_ind] == COORDSGROUP:
            key = self.fmtos[group_ind][self.fmt_combo.currentIndex()]
            param = 'dims'
        else:
            key = self.fmtos[group_ind][self.fmt_combo.currentIndex()].key
            param = 'fmt'
        e = ExecutionResult()
        self.shell.run_code("psy.gcp().update(%s={'%s': %s})" % (
            param, key, text), e)
        e.raise_error()

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
        if self.all_groups_cb.isChecked():
            fmtos = list(chain(*(
                fmto_group for i, fmto_group in enumerate(self.fmtos)
                if not self.groups[i] in [ALLGROUP, COORDSGROUP])))
        else:
            if self.groups[self.group_combo.currentIndex()] == COORDSGROUP:
                return
            fmtos = self.fmtos[self.group_combo.currentIndex()]
        plotter = fmtos[0].plotter
        getattr(plotter, 'show_' + what)(
            [fmto.key for fmto in fmtos], grouped=self.grouped_cb.isChecked(),
            include_links=self.include_links_cb.isChecked())
