"""Core module for the psyplot graphical user interface

This module redefines the :class:`psyplot.project.Project` class with
additional features for an interactive usage with graphical qt user interface.
There is no need to import this module because the
:class:`GuiProject` class defined here replaces the project class in the
:mod:`psyplot.project` module."""
import sys
import six
import socket
import errno
import pickle
import os
from pkg_resources import iter_entry_points
from functools import partial
from collections import defaultdict, OrderedDict
import matplotlib as mpl
from psyplot.compat.pycompat import get_default_value
from psyplot_gui import rcParams
from threading import Thread
import logging

# change backend here before the project module is imported
backend = rcParams['backend']
if backend is not None:
    if backend == 'psyplot':
        backend = 'module://psyplot_gui.backend'
    mpl.use(backend)

from psyplot_gui.console import ConsoleWidget
from psyplot_gui.compat.qtcompat import (
    QMainWindow, QApplication, Qt, QMenu, QAction, QDesktopWidget, QLabel,
    QFileDialog, QKeySequence, QtCore, with_qt5, QMessageBox, QIcon,
    QInputDialog)
from psyplot_gui.content_widget import (
    ProjectContentWidget, DatasetTree, FiguresTree)
from psyplot_gui.plot_creator import PlotCreator
from psyplot_gui.help_explorer import HelpExplorer
from psyplot_gui.dataframeeditor import DataFrameEditor
from psyplot_gui.fmt_widget import FormatoptionWidget
from psyplot_gui.common import PyErrorMessage, get_icon, StreamToLogger
from psyplot_gui.preferences import (
    Prefences, GuiRcParamsWidget, PsyRcParamsWidget)
from psyplot_gui.dependencies import DependenciesDialog

from psyplot.docstring import docstrings
import psyplot.plotter as psyp
import psyplot.project as psy
import psyplot
import psyplot.data as psyd
import psyplot_gui
import xarray as xr


#: The :class:`PyQt5.QtWidgets.QMainWindow` of the graphical user interface
mainwindow = None


def _set_mainwindow(obj):
    global mainwindow
    mainwindow = obj


class MainWindow(QMainWindow):

    #: A signal that is emmitted when the a signal is received through the
    #: open_files_server
    open_external = QtCore.pyqtSignal(list)

    #: The server to open external files
    open_files_server = None

    #: Inprocess console
    console = None

    #: tree widget displaying the open datasets
    ds_tree = None

    #: list of figures from the psyplot backend
    figures = []

    #: tree widget displaying the open figures
    figures_tree = None

    #: general formatoptions widget
    fmt_widget = None

    #: help explorer
    help_explorer = None

    #: the DataFrameEditor widgets, a widget to show and edit data frames
    dataframeeditors = None

    #: tab widget displaying the arrays in current main and sub project
    project_content = None

    #: The dockwidgets of this instance
    dockwidgets = []

    #: default widths of the dock widgets
    default_widths = {}

    _is_open = False

    #: The keyboard shortcuts of the default layout
    default_shortcuts = []

    #: The current keyboard shortcuts
    current_shortcuts = []

    @property
    def logger(self):
        """The logger of this instance"""
        return logging.getLogger('%s.%s' % (self.__class__.__module__,
                                            self.__class__.__name__))

    @docstrings.get_sectionsf('MainWindow')
    @docstrings.dedent
    def __init__(self, show=True):
        """
        Parameters
        ----------
        show: bool
            If True, the created mainwindow is show
        """
        if sys.stdout is None:
            sys.stdout = StreamToLogger(self.logger)
        if sys.stderr is None:
            sys.stderr = StreamToLogger(self.logger)
        super(MainWindow, self).__init__()
        self.setWindowIcon(QIcon(get_icon('logo.png')))

        #: list of figures from the psyplot backend
        self.figures = []
        self.error_msg = PyErrorMessage(self)
        self.setDockOptions(
            QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks)
        #: Inprocess console
        self.console = ConsoleWidget(self)
        self.project_actions = {}

        self.config_pages = []

        self.open_file_options = OrderedDict([
            ('new psyplot plot from dataset', self.open_external_files),
            ('new psyplot project', partial(self.open_external_files, [])),
            ])

        # ---------------------------------------------------------------------
        # ----------------------------- Menus ---------------------------------
        # ---------------------------------------------------------------------

        # ######################## File menu ##################################

        # --------------------------- New plot --------------------------------

        self.file_menu = QMenu('File', parent=self)
        self.new_plot_action = QAction('New plot', self)
        self.new_plot_action.setStatusTip(
            'Use an existing dataset (or open a new one) to create one or '
            'more plots')
        self.register_shortcut(self.new_plot_action, QKeySequence.New)
        self.new_plot_action.triggered.connect(lambda: self.new_plots(True))
        self.file_menu.addAction(self.new_plot_action)

        # --------------------------- Open project ----------------------------

        self.open_project_menu = QMenu('Open project', self)
        self.file_menu.addMenu(self.open_project_menu)

        self.open_mp_action = QAction('New main project', self)
        self.register_shortcut(self.open_mp_action, QKeySequence.Open)
        self.open_mp_action.setStatusTip('Open a new main project')
        self.open_mp_action.triggered.connect(self.open_mp)
        self.open_project_menu.addAction(self.open_mp_action)

        self.open_sp_action = QAction('Add to current', self)

        self.register_shortcut(
            self.open_sp_action, QKeySequence(
                'Ctrl+Shift+O', QKeySequence.NativeText))
        self.open_sp_action.setStatusTip(
            'Load a project as a sub project and add it to the current main '
            'project')
        self.open_sp_action.triggered.connect(self.open_sp)
        self.open_project_menu.addAction(self.open_sp_action)

        # ----------------------- Save project --------------------------------

        self.save_project_menu = QMenu('Save', parent=self)
        self.file_menu.addMenu(self.save_project_menu)

        self.save_mp_action = QAction('Full psyplot project', self)
        self.save_mp_action.setStatusTip(
            'Save the entire project into a pickle file')
        self.register_shortcut(self.save_mp_action, QKeySequence.Save)
        self.save_mp_action.triggered.connect(self.save_mp)
        self.save_project_menu.addAction(self.save_mp_action)

        self.save_sp_action = QAction('Selected psyplot project', self)
        self.save_sp_action.setStatusTip(
            'Save the selected sub project into a pickle file')
        self.save_sp_action.triggered.connect(self.save_sp)
        self.save_project_menu.addAction(self.save_sp_action)

        # ------------------------ Save project as ----------------------------

        self.save_project_as_menu = QMenu('Save as', parent=self)
        self.file_menu.addMenu(self.save_project_as_menu)

        self.save_mp_as_action = QAction('Full psyplot project', self)
        self.save_mp_as_action.setStatusTip(
            'Save the entire project into a pickle file')
        self.register_shortcut(self.save_mp_as_action,
                                       QKeySequence.SaveAs)
        self.save_mp_as_action.triggered.connect(
            partial(self.save_mp, new_fname=True))
        self.save_project_as_menu.addAction(self.save_mp_as_action)

        self.save_sp_as_action = QAction('Selected psyplot project', self)
        self.save_sp_as_action.setStatusTip(
            'Save the selected sub project into a pickle file')
        self.save_sp_as_action.triggered.connect(
            partial(self.save_sp, new_fname=True))
        self.save_project_as_menu.addAction(self.save_sp_as_action)

        # -------------------------- Pack project -----------------------------

        self.pack_project_menu = QMenu('Zip project files', parent=self)
        self.file_menu.addMenu(self.pack_project_menu)

        self.pack_mp_action = QAction('Full psyplot project', self)
        self.pack_mp_action.setStatusTip(
            'Pack all the data of the main project into one folder')
        self.pack_mp_action.triggered.connect(partial(self.save_mp, pack=True))
        self.pack_project_menu.addAction(self.pack_mp_action)

        self.pack_sp_action = QAction('Selected psyplot project', self)
        self.pack_sp_action.setStatusTip(
            'Pack all the data of the current sub project into one folder')
        self.pack_sp_action.triggered.connect(partial(self.save_sp, pack=True))
        self.pack_project_menu.addAction(self.pack_sp_action)

        # ------------------------ Export figures -----------------------------

        self.export_project_menu = QMenu('Export figures', parent=self)
        self.file_menu.addMenu(self.export_project_menu)

        self.export_mp_action = QAction('Full psyplot project', self)
        self.export_mp_action.setStatusTip(
            'Pack all the data of the main project into one folder')
        self.export_mp_action.triggered.connect(self.export_mp)
        self.register_shortcut(
            self.export_mp_action, QKeySequence(
                'Ctrl+E', QKeySequence.NativeText))
        self.export_project_menu.addAction(self.export_mp_action)

        self.export_sp_action = QAction('Selected psyplot project', self)
        self.export_sp_action.setStatusTip(
            'Pack all the data of the current sub project into one folder')
        self.register_shortcut(
            self.export_sp_action, QKeySequence(
                'Ctrl+Shift+E', QKeySequence.NativeText))
        self.export_sp_action.triggered.connect(self.export_sp)
        self.export_project_menu.addAction(self.export_sp_action)

        # ------------------------ Close project ------------------------------

        self.file_menu.addSeparator()

        self.close_project_menu = QMenu('Close project', parent=self)
        self.file_menu.addMenu(self.close_project_menu)

        self.close_mp_action = QAction('Full psyplot project', self)
        self.register_shortcut(
            self.close_mp_action, QKeySequence(
                'Ctrl+Shift+W', QKeySequence.NativeText))
        self.close_mp_action.setStatusTip(
            'Close the main project and delete all data and plots out of '
            'memory')
        self.close_mp_action.triggered.connect(
            lambda: psy.close(psy.gcp(True).num))
        self.close_project_menu.addAction(self.close_mp_action)

        self.close_sp_action = QAction('Selected psyplot project', self)
        self.close_sp_action.setStatusTip(
            'Close the selected arrays project and delete all data and plots '
            'out of memory')
        self.register_shortcut(self.close_sp_action, QKeySequence.Close)
        self.close_sp_action.triggered.connect(
            lambda: psy.gcp().close(True, True))
        self.close_project_menu.addAction(self.close_sp_action)

        # ----------------------------- Quit ----------------------------------

        if sys.platform != 'darwin':  # mac os makes this anyway
            self.quit_action = QAction('Quit', self)
            self.quit_action.triggered.connect(self.close)
            self.quit_action.triggered.connect(
                QtCore.QCoreApplication.instance().quit)
            self.register_shortcut(
                self.quit_action, QKeySequence.Quit)
            self.file_menu.addAction(self.quit_action)

        self.menuBar().addMenu(self.file_menu)

        # ######################## Console menu ###############################

        self.console_menu = QMenu('Console', self)
        self.console_menu.addActions(self.console.actions())
        self.menuBar().addMenu(self.console_menu)

        # ######################## Windows menu ###############################

        self.windows_menu = QMenu('Windows', self)
        self.menuBar().addMenu(self.windows_menu)

        # ############################ Help menu ##############################

        self.help_menu = QMenu('Help', parent=self)
        self.menuBar().addMenu(self.help_menu)

        # -------------------------- Preferences ------------------------------

        self.help_action = QAction('Preferences', self)
        self.help_action.triggered.connect(lambda: self.edit_preferences(True))
        self.register_shortcut(self.help_action,
                                       QKeySequence.Preferences)
        self.help_menu.addAction(self.help_action)

        # ---------------------------- About ----------------------------------

        self.about_action = QAction('About', self)
        self.about_action.triggered.connect(self.about)
        self.help_menu.addAction(self.about_action)

        # ---------------------------- Dependencies ---------------------------

        self.dependencies_action = QAction('Dependencies', self)
        self.dependencies_action.triggered.connect(
            lambda: self.show_dependencies(True))
        self.help_menu.addAction(self.dependencies_action)

        self.dockwidgets = []

        # ---------------------------------------------------------------------
        # -------------------------- Dock windows -----------------------------
        # ---------------------------------------------------------------------
        #: tab widget displaying the arrays in current main and sub project
        #: tree widget displaying the open datasets
        self.project_content = ProjectContentWidget(parent=self)
        self.ds_tree = DatasetTree(parent=self)
        #: tree widget displaying the open figures
        self.figures_tree = FiguresTree(parent=self)
        #: help explorer
        self.help_explorer = help_explorer = HelpExplorer(parent=self)
        if help_explorer.viewers['HTML help'].sphinx_thread is not None:
            help_explorer.viewers[
                'HTML help'].sphinx_thread.html_ready.connect(
                    self.focus_on_console)
        #: the DataFrameEditor widgets
        self.dataframeeditors = []
        #: general formatoptions widget
        self.fmt_widget = FormatoptionWidget(
            parent=self, help_explorer=help_explorer,
            console=self.console)

        # load plugin widgets
        self.plugins = plugins = OrderedDict([
            ('project_content', self.project_content),
            ('ds_tree', self.ds_tree),
            ('figures_tree', self.figures_tree),
            ('help_explorer', self.help_explorer),
            ('fmt_widget', self.fmt_widget),
            ])
        self.default_plugins = list(plugins)
        for plugin_name, w_class in six.iteritems(rcParams.load_plugins()):
            plugins[plugin_name] = w_class(parent=self)

        self.add_mp_to_menu()
        psy.Project.oncpchange.connect(self.eventually_add_mp_to_menu)
        self.windows_menu.addSeparator()
        self.window_layouts_menu = QMenu('Window layouts', self)
        self.restore_layout_action = QAction('Restore default layout', self)
        self.restore_layout_action.triggered.connect(self.setup_default_layout)
        self.window_layouts_menu.addAction(self.restore_layout_action)
        self.windows_menu.addMenu(self.window_layouts_menu)
        self.panes_menu = QMenu('Panes', self)
        self.windows_menu.addMenu(self.panes_menu)

        self.dataframe_menu = QMenu('DataFrame editors', self)
        self.dataframe_menu.addAction(
            'New Editor', partial(self.new_data_frame_editor, None,
                                  'DataFrame Editor'))
        self.dataframe_menu.addSeparator()
        self.windows_menu.addMenu(self.dataframe_menu)

        # ---------------------------------------------------------------------
        # -------------------------- connections ------------------------------
        # ---------------------------------------------------------------------

        self.console.help_explorer = help_explorer
        psyp.default_print_func = partial(help_explorer.show_rst,
                                          oname='formatoption_docs')
        psy.PlotterInterface._print_func = psyp.default_print_func
        self.setCentralWidget(self.console)

        # make sure that the plots are shown between the project content and
        # the help explorer widget
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)

        # make sure that the formatoption widgets are shown between the
        # project content and the help explorer widget
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        # ---------------------------------------------------------------------
        # ------------------------------ closure ------------------------------
        # ---------------------------------------------------------------------
        if show:
            self.help_explorer.show_intro(self.console.intro_msg)

        # ---------------------------------------------------------------------
        # ------------------------- open_files_server -------------------------
        # ---------------------------------------------------------------------
        self.callbacks = {'new_plot': self.open_external.emit,
                          'change_cwd': self._change_cwd,
                          'run_script': self.console.run_script.emit,
                          'command': self.console.run_command.emit,
                          }

        # Server to open external files on a single instance
        self.open_files_server = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM,
                                               socket.IPPROTO_TCP)

        if rcParams['main.listen_to_port']:
            self._file_thread = Thread(target=self.start_open_files_server)
            self._file_thread.setDaemon(True)
            self._file_thread.start()

            self.open_external.connect(self._open_external_files)

        self.config_pages.extend([GuiRcParamsWidget, PsyRcParamsWidget])

        # display the statusBar
        statusbar = self.statusBar()
        self.figures_label = QLabel()
        statusbar.addWidget(self.figures_label)
        self.plugin_label = QLabel()
        statusbar.addWidget(self.plugin_label)

        self.default_widths = {}

        self.setup_default_layout()

        if show:
            self.showMaximized()

        # save the default widths after they have been shown
        for w in self.plugins.values():
            self.default_widths[w] = w.dock.size().width()

        # hide plugin widgets that should be hidden at startup. Although this
        # has been executed by :meth:`setup_default_layout`, we have to execute
        # it again after the call of showMaximized
        for w in self.plugins.values():
            w.to_dock(self)
            if w.hidden:
                w.hide_plugin()

        self._is_open = True

    def focus_on_console(self, *args, **kwargs):
        """Put focus on the ipython console"""
        self.console._control.setFocus()

    def new_data_frame_editor(self, df=None, title='DataFrame Editor'):
        """Open a new dataframe editor

        Parameters
        ----------
        df: pandas.DataFrame
            The dataframe to display
        title: str
            The title of the dock window

        Returns
        -------
        psyplot_gui.dataframeeditor.DataFrameEditor
            The newly created editor"""
        editor = DataFrameEditor()
        self.dataframeeditors.append(editor)
        editor.to_dock(self, title,
                       Qt.RightDockWidgetArea, docktype='df')
        if df is not None:
            editor.set_df(df)
        editor.show_plugin()
        editor.maybe_tabify()
        editor.raise_()
        return editor

    def setup_default_layout(self):
        """Set up the default window layout"""
        self.project_content.to_dock(self, 'Plot objects',
                                     Qt.LeftDockWidgetArea)
        self.ds_tree.to_dock(self, 'Datasets', Qt.LeftDockWidgetArea)
        self.figures_tree.to_dock(self, 'Figures', Qt.LeftDockWidgetArea)
        self.help_explorer.to_dock(self, 'Help explorer',
                                   Qt.RightDockWidgetArea)
        self.fmt_widget.to_dock(self, 'Formatoptions', Qt.BottomDockWidgetArea)

        modify_widths = bool(self.default_widths)
        for w in map(self.plugins.__getitem__, self.default_plugins):
            w.show_plugin()

            if modify_widths and with_qt5:
                self.resizeDocks([w.dock], [self.default_widths[w]],
                                 Qt.Horizontal)

        # hide plugin widgets that should be hidden at startup
        for w in self.plugins.values():
            w.to_dock(self)
            if w.hidden:
                w.hide_plugin()

        action2shortcut = defaultdict(list)
        for s, a in self.default_shortcuts:
            action2shortcut[a].append(s)

        for a, s in action2shortcut.items():
            self.register_shortcut(a, s)

    def _save_project(self, p, new_fname=False, *args, **kwargs):
        if new_fname or 'project_file' not in p.attrs:
            fname = QFileDialog.getSaveFileName(
                self, 'Project destination', os.getcwd(),
                'Pickle files (*.pkl);;'
                'All files (*)'
                )
            if with_qt5:  # the filter is passed as well
                fname = fname[0]
            if not fname:
                return
        else:
            fname = p.attrs['project_file']
        try:
            p.save_project(fname, *args, **kwargs)
        except Exception:
            self.error_msg.showTraceback('<b>Could not save the project!</b>')
        else:
            p.attrs['project_file'] = fname
            if p.is_main:
                self.update_project_action(p.num)

    def open_mp(self, *args, **kwargs):
        """Open a new main project"""
        self._open_project(main=True)

    def open_sp(self, *args, **kwargs):
        """Open a subproject and add it to the current main project"""
        self._open_project(main=False)

    def _open_project(self, *args, **kwargs):
        fname = QFileDialog.getOpenFileName(
            self, 'Project file', os.getcwd(),
            'Pickle files (*.pkl);;'
            'All files (*)'
            )
        if with_qt5:  # the filter is passed as well
            fname = fname[0]
        if not fname:
            return
        p = psy.Project.load_project(fname, *args, **kwargs)
        p.attrs['project_file'] = fname
        self.update_project_action(p.num)

    def save_mp(self, *args, **kwargs):
        """Save the current main project"""
        self._save_project(psy.gcp(True), **kwargs)

    def save_sp(self, *args, **kwargs):
        """Save the current sub project"""
        self._save_project(psy.gcp(), **kwargs)

    def _export_project(self, p, *args, **kwargs):
        fname = QFileDialog.getSaveFileName(
            self, 'Picture destination', os.getcwd(),
            'PDF files (*.pdf);;'
            'Postscript file (*.ps);;'
            'PNG image (*.png);;'
            'JPG image (*.jpg *.jpeg);;'
            'TIFF image (*.tif *.tiff);;'
            'GIF image (*.gif);;'
            'All files (*)'
            )
        if with_qt5:  # the filter is passed as well
            fname = fname[0]
        if not fname:
            return
        try:
            p.export(fname, *args, **kwargs)
        except Exception:
            self.error_msg.showTraceback(
                '<b>Could not export the figures!</b>')

    def export_mp(self, *args, **kwargs):
        self._export_project(psy.gcp(True), **kwargs)

    def export_sp(self, *args, **kwargs):
        self._export_project(psy.gcp(), **kwargs)

    def new_plots(self, exec_=None):
        if hasattr(self, 'plot_creator'):
            try:
                self.plot_creator.close()
            except RuntimeError:
                pass
        self.plot_creator = PlotCreator(
            help_explorer=self.help_explorer, parent=self)
        available_width = QDesktopWidget().availableGeometry().width() / 3.
        width = self.plot_creator.sizeHint().width()
        height = self.plot_creator.sizeHint().height()
        # The plot creator window should cover at least one third of the screen
        self.plot_creator.resize(max(available_width, width), height)
        if exec_:
            self.plot_creator.exec_()

    def excepthook(self, type, value, traceback):
        """A method to replace the sys.excepthook"""
        self.error_msg.excepthook(type, value, traceback)

    def edit_preferences(self, exec_=None):
        """Edit Spyder preferences"""
        if hasattr(self, 'preferences'):
            try:
                self.preferences.close()
            except RuntimeError:
                pass
        self.preferences = dlg = Prefences(self)
        for PrefPageClass in self.config_pages:
            widget = PrefPageClass(dlg)
            widget.initialize()
            dlg.add_page(widget)
        available_width = 0.667 * QDesktopWidget().availableGeometry().width()
        width = dlg.sizeHint().width()
        height = dlg.sizeHint().height()
        # The preferences window should cover at least one third of the screen
        dlg.resize(max(available_width, width), height)
        if exec_:
            dlg.exec_()

    def about(self):
        """About the tool"""
        versions = {
            key: d['version'] for key, d in psyplot.get_versions(False).items()
            }
        versions.update(psyplot_gui.get_versions()['requirements'])
        versions.update(psyplot._get_versions()['requirements'])
        versions['github'] = 'https://github.com/Chilipp/psyplot'
        versions['author'] = psyplot.__author__
        QMessageBox.about(
            self, "About psyplot",
            u"""<b>psyplot: Interactive data visualization with python</b>
            <br>Copyright &copy; 2017- Philipp Sommer
            <br>Licensed under the terms of the GNU General Public License v2
            (GPLv2)
            <p>Created by %(author)s</p>
            <p>Most of the icons come from the
            <a href="https://www.iconfinder.com/"> iconfinder</a>.</p>
            <p>For bug reports and feature requests, please go
            to our <a href="%(github)s">Github website</a> or contact the
            author via mail.</p>
            <p>This package uses (besides others) the following packages:<br>
            <ul>
                <li>psyplot %(psyplot)s</li>
                <li>Python %(python)s </li>
                <li>numpy %(numpy)s</li>
                <li>xarray %(xarray)s</li>
                <li>pandas %(pandas)s</li>
                <li>psyplot_gui %(psyplot_gui)s</li>
                <li>Qt %(qt)s</li>
                <li>PyQt %(pyqt)s</li>
                <li>qtconsole %(qtconsole)s</li>
            </ul></p>
            <p>For a full list of requirements see the <em>dependencies</em>
            in the <em>Help</em> menu.</p>
            <p>This software is provided "as is", without warranty or support
            of any kind.</p>"""
            % versions)

    def show_dependencies(self, exec_=None):
        """Open a dialog that shows the dependencies"""
        if hasattr(self, 'dependencies'):
            try:
                self.dependencies.close()
            except RuntimeError:
                pass
        self.dependencies = dlg = DependenciesDialog(psyplot.get_versions(),
                                                     parent=self)
        dlg.resize(630, 420)
        if exec_:
            dlg.exec_()

    def reset_rcParams(self):
        rcParams.update_from_defaultParams()
        psy.rcParams.update_from_defaultParams()

    def add_mp_to_menu(self):
        mp = psy.gcp(True)
        action = QAction(os.path.basename(mp.attrs.get(
            'project_file', 'Untitled %s*' % mp.num)), self)
        action.setStatusTip(
            'Make project %s the current project' % mp.num)
        action.triggered.connect(lambda: psy.scp(psy.project(mp.num)))
        self.project_actions[mp.num] = action
        self.windows_menu.addAction(action)

    def update_project_action(self, num):
        action = self.project_actions.get(num)
        p = psy.project(num)
        if action:
            action.setText(os.path.basename(p.attrs.get(
                'project_file', 'Untitled %s*' % num)))

    def eventually_add_mp_to_menu(self, p):
        for num in set(self.project_actions).difference(
                psy.get_project_nums()):
            self.windows_menu.removeAction(self.project_actions.pop(num))
        if p is None or not p.is_main:
            return
        if p.num not in self.project_actions:
            self.add_mp_to_menu()

    def addDockWidget(self, area, dockwidget, docktype=None, *args, **kwargs):
        """Reimplemented to add widgets to the windows menu"""
        ret = super(MainWindow, self).addDockWidget(area, dockwidget, *args,
                                                    **kwargs)
        if docktype == 'pane':
            self.panes_menu.addAction(dockwidget.toggleViewAction())
        elif docktype == 'df':
            self.dataframe_menu.addAction(dockwidget.toggleViewAction())
        return ret

    def start_open_files_server(self):
        """This method listens to the open_files_port and opens the plot
        creator for new files

        This method is inspired and to most parts copied from spyder"""
        self.open_files_server.setsockopt(socket.SOL_SOCKET,
                                          socket.SO_REUSEADDR, 1)
        port = rcParams['main.open_files_port']
        try:
            self.open_files_server.bind(('127.0.0.1', port))
        except Exception:
            return
        self.open_files_server.listen(20)
        while 1:  # 1 is faster than True
            try:
                req, dummy = self.open_files_server.accept()
            except socket.error as e:
                # See Issue 1275 for details on why errno EINTR is
                # silently ignored here.
                eintr = errno.EINTR
                # To avoid a traceback after closing on Windows
                if e.args[0] == eintr:
                    continue
                # handle a connection abort on close error
                enotsock = (errno.WSAENOTSOCK if os.name == 'nt'
                            else errno.ENOTSOCK)
                if e.args[0] in [errno.ECONNABORTED, enotsock]:
                    return
                raise
            args = pickle.loads(req.recv(1024))
            callback = args[0]
            func = self.callbacks[callback]
            self.logger.debug('Emitting %s callback %s', callback, func)
            func(args[1:])
            req.sendall(b' ')

    def change_cwd(self, path):
        """Change the current working directory"""
        import os
        os.chdir(path)

    def _change_cwd(self, args):
        path = args[0][0]
        self.change_cwd(path)

    docstrings.keep_params(
        'make_plot.parameters', 'fnames', 'project', 'engine', 'plot_method',
        'name', 'dims', 'encoding', 'enable_post', 'seaborn_style',
        'concat_dim', 'chname')

    def open_files(self, fnames):
        """Open a file and ask the user how"""
        fnames_s = ', '.join(map(os.path.basename, fnames))
        if len(fnames_s) > 30:
            fnames_s = fnames_s[:27] + '...'
        item, ok = QInputDialog.getItem(
            self, 'Open file...', 'Open %s as...' % fnames_s,
            list(self.open_file_options), current=0, editable=False)
        if ok:
            return self.open_file_options[item](fnames)

    @docstrings.get_sectionsf('MainWindow.open_external_files')
    @docstrings.dedent
    def open_external_files(self, fnames=[], project=None, engine=None,
                            plot_method=None, name=None, dims=None,
                            encoding=None, enable_post=False,
                            seaborn_style=None, concat_dim=get_default_value(
                                xr.open_mfdataset, 'concat_dim'), chname={}):
        """
        Open external files

        Parameters
        ----------
        %(make_plot.parameters.fnames|project|engine|plot_method|name|dims|encoding|enable_post|seaborn_style|concat_dim|chname)s
        """
        if seaborn_style is not None:
            import seaborn as sns
            sns.set_style(seaborn_style)
        if project is not None:
            fnames = [s.split(',') for s in fnames]
            if not isinstance(project, dict):
                project = psyd.safe_list(project)[0]
            single_files = (l[0] for l in fnames if len(l) == 1)
            alternative_paths = defaultdict(lambda: next(single_files, None))
            alternative_paths.update(list(l for l in fnames if len(l) == 2))
            p = psy.Project.load_project(
                project, alternative_paths=alternative_paths,
                engine=engine, main=not psy.gcp(), encoding=encoding,
                enable_post=enable_post, chname=chname)
            if isinstance(project, six.string_types):
                p.attrs.setdefault('project_file', project)
            return True
        else:
            self.new_plots(False)
            self.plot_creator.open_dataset(fnames, engine=engine,
                                           concat_dim=concat_dim)
            if name == 'all':
                ds = self.plot_creator.get_ds()
                name = sorted(set(ds.variables) - set(ds.coords))
            self.plot_creator.insert_array(
                list(filter(None, psy.safe_list(name))))
            if dims is not None:
                ds = self.plot_creator.get_ds()
                dims = {key: ', '.join(
                    map(str, val)) for key, val in six.iteritems(
                        dims)}
                for i, vname in enumerate(
                        self.plot_creator.array_table.vnames):
                    self.plot_creator.array_table.selectRow(i)
                    self.plot_creator.array_table.update_selected(
                        )
                self.plot_creator.array_table.selectAll()
                var = ds[vname[0]]
                self.plot_creator.array_table.update_selected(
                    dims=var.psy.decoder.correct_dims(var, dims.copy()))
            if plot_method:
                self.plot_creator.pm_combo.setCurrentIndex(
                    self.plot_creator.pm_combo.findText(plot_method))
            self.plot_creator.exec_()
            return True

    def _open_external_files(self, args):
        self.open_external_files(*args)

    @classmethod
    @docstrings.get_sectionsf('MainWindow.run')
    @docstrings.dedent
    def run(cls, fnames=[], project=None, engine=None, plot_method=None,
            name=None, dims=None, encoding=None, enable_post=False,
            seaborn_style=None,
            concat_dim=get_default_value(xr.open_mfdataset, 'concat_dim'),
            chname={}, show=True):
        """
        Create a mainwindow and open the given files or project

        This class method creates a new mainwindow instance and sets the
        global :attr:`mainwindow` variable.

        Parameters
        ----------
        %(MainWindow.open_external_files.parameters)s
        %(MainWindow.parameters)s

        Notes
        -----
        - There can be only one mainwindow at the time
        - This method does not create a QApplication instance! See
          :meth:`run_app`

        See Also
        --------
        run_app
        """
        mainwindow = cls(show=show)
        _set_mainwindow(mainwindow)
        if fnames or project:
            mainwindow.open_external_files(
                fnames, project, engine, plot_method, name, dims, encoding,
                enable_post, seaborn_style, concat_dim, chname)
        psyplot.with_gui = True
        return mainwindow

    def register_shortcut(self, action, shortcut,
                          context=Qt.ApplicationShortcut):
        """Register an action for a shortcut"""
        shortcuts = psy.safe_list(shortcut)
        for j, shortcut in enumerate(shortcuts):
            found = False
            for i, (s, a) in enumerate(self.current_shortcuts):
                if s == shortcut:
                    new_shortcuts = [
                        sc for sc in self.current_shortcuts[i][1].shortcuts()
                        if sc != s]
                    a.setShortcut(QKeySequence())
                    if new_shortcuts:
                        a.setShortcuts(new_shortcuts)
                    self.current_shortcuts[i][1] = action
                    found = True
                    break
            if not found:
                self.default_shortcuts.append([shortcut, action])
                self.current_shortcuts.append([shortcut, action])
        action.setShortcuts(shortcuts)
        action.setShortcutContext(context)

    @classmethod
    @docstrings.dedent
    def run_app(cls, *args, **kwargs):
        """
        Create a QApplication, open the given files or project and enter the
        mainloop

        Parameters
        ----------
        %(MainWindow.run.parameters)s

        See Also
        --------
        run
        """
        app = QApplication(sys.argv)
        cls.run(*args, **kwargs)
        sys.exit(app.exec_())

    def closeEvent(self, event):
        """closeEvent reimplementation"""
        if not self._is_open or (self._is_open and self.close()):
            self._is_open = False
            event.accept()

    def close(self):
        _set_mainwindow(None)
        if self.open_files_server is not None:
            self.open_files_server.close()
            del self.open_files_server
        for widget in self.plugins.values():
            widget.close()
        self.plugins.clear()
        return super(MainWindow, self).close()
