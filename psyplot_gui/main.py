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
from functools import partial
from collections import defaultdict
import matplotlib as mpl
from psyplot_gui import rcParams
from threading import Thread

# change backend here before the project module is imported
backend = rcParams['backend']
if backend is not None:
    if backend == 'psyplot':
        backend = 'module://psyplot_gui.backend'
    mpl.use(backend)

from psyplot_gui.console import ConsoleWidget
from psyplot_gui.compat.qtcompat import (
    QMainWindow, QApplication, Qt, QMenu, QAction, QDesktopWidget,
    QFileDialog, QKeySequence, QtCore, with_qt5)
from psyplot_gui.content_widget import (
    ProjectContentWidget, DatasetTree, FiguresTree)
from psyplot_gui.plot_creator import PlotCreator
from psyplot_gui.help_explorer import HelpExplorer
from psyplot_gui.fmt_widget import FormatoptionWidget
from psyplot_gui.common import PyErrorMessage, DockMixin

from psyplot.docstring import docstrings
import psyplot.plotter as psyp
import psyplot.project as psy


#: The :class:`PyQt4.QtGui.QMainWindow` of the graphical user interface
mainwindow = None


def _set_mainwindow(obj):
    global mainwindow
    mainwindow = obj


class MainWindow(QMainWindow):

    open_external = QtCore.pyqtSignal(list)

    def __init__(self):
        super(MainWindow, self).__init__()

        #: list of figures from the psyplot backend
        self.figures = []
        self.error_msg = PyErrorMessage(self)
        self.setDockOptions(
            QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks |
            QMainWindow.AllowTabbedDocks)
        #: Inprocess console
        self.console = ConsoleWidget(parent=self)
        self.project_actions = {}

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
        self.new_plot_action.setShortcut(QKeySequence.New)
        self.new_plot_action.triggered.connect(self.new_plots)
        self.file_menu.addAction(self.new_plot_action)

        # --------------------------- Open project ----------------------------

        self.open_project_menu = QMenu('Open project', self)
        self.file_menu.addMenu(self.open_project_menu)

        self.open_mp_action = QAction('New main project', self)
        self.open_mp_action.setShortcut(QKeySequence.Open)
        self.open_mp_action.setStatusTip('Open a new main project')
        self.open_mp_action.triggered.connect(self.open_mp)
        self.open_project_menu.addAction(self.open_mp_action)

        self.open_sp_action = QAction('Add to current', self)
        self.open_sp_action.setShortcut(QKeySequence(
            'Ctrl+Shift+O', QKeySequence.NativeText))
        self.open_sp_action.setStatusTip(
            'Load a project as a sub project and add it to the current main '
            'project')
        self.open_sp_action.triggered.connect(self.open_sp)
        self.open_project_menu.addAction(self.open_sp_action)

        # ----------------------- Save project --------------------------------

        self.save_project_menu = QMenu('Save project', parent=self)
        self.file_menu.addMenu(self.save_project_menu)

        self.save_mp_action = QAction('All', self)
        self.save_mp_action.setStatusTip(
            'Save the entire project into a pickle file')
        self.save_mp_action.setShortcut(QKeySequence.Save)
        self.save_mp_action.triggered.connect(self.save_mp)
        self.save_project_menu.addAction(self.save_mp_action)

        self.save_sp_action = QAction('Selected', self)
        self.save_sp_action.setStatusTip(
            'Save the selected sub project into a pickle file')
        self.save_sp_action.triggered.connect(self.save_sp)
        self.save_project_menu.addAction(self.save_sp_action)

        # ------------------------ Save project as ----------------------------

        self.save_project_as_menu = QMenu('Save project as', parent=self)
        self.file_menu.addMenu(self.save_project_as_menu)

        self.save_mp_as_action = QAction('All', self)
        self.save_mp_as_action.setStatusTip(
            'Save the entire project into a pickle file')
        self.save_mp_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_mp_as_action.triggered.connect(
            partial(self.save_mp, new_name=True))
        self.save_project_as_menu.addAction(self.save_mp_as_action)

        self.save_sp_as_action = QAction('Selected', self)
        self.save_sp_as_action.setStatusTip(
            'Save the selected sub project into a pickle file')
        self.save_sp_as_action.triggered.connect(
            partial(self.save_sp, new_name=True))
        self.save_project_as_menu.addAction(self.save_sp_as_action)

        # -------------------------- Pack project -----------------------------

        self.pack_project_menu = QMenu('Zip project files', parent=self)
        self.file_menu.addMenu(self.pack_project_menu)

        self.pack_mp_action = QAction('All', self)
        self.pack_mp_action.setStatusTip(
            'Pack all the data of the main project into one folder')
        self.pack_mp_action.triggered.connect(partial(self.save_mp, pack=True))
        self.pack_project_menu.addAction(self.pack_mp_action)

        self.pack_sp_action = QAction('Selected', self)
        self.pack_sp_action.setStatusTip(
            'Pack all the data of the current sub project into one folder')
        self.pack_sp_action.triggered.connect(partial(self.save_sp, pack=True))
        self.pack_project_menu.addAction(self.pack_sp_action)

        # ------------------------ Export figures -----------------------------

        self.export_project_menu = QMenu('Export figures', parent=self)
        self.file_menu.addMenu(self.export_project_menu)

        self.export_mp_action = QAction('All', self)
        self.export_mp_action.setStatusTip(
            'Pack all the data of the main project into one folder')
        self.export_mp_action.triggered.connect(self.export_mp)
        self.export_mp_action.setShortcut(QKeySequence(
            'Ctrl+E', QKeySequence.NativeText))
        self.export_project_menu.addAction(self.export_mp_action)

        self.export_sp_action = QAction('Selected', self)
        self.export_sp_action.setStatusTip(
            'Pack all the data of the current sub project into one folder')
        self.export_sp_action.setShortcut(QKeySequence(
            'Ctrl+Shift+E', QKeySequence.NativeText))
        self.export_sp_action.triggered.connect(self.export_sp)
        self.export_project_menu.addAction(self.export_sp_action)

        # ------------------------ Close project ------------------------------

        self.file_menu.addSeparator()

        self.close_project_menu = QMenu('Close project', parent=self)
        self.file_menu.addMenu(self.close_project_menu)

        self.close_mp_action = QAction('Main project', self)
        self.close_mp_action.setShortcut(QKeySequence(
            'Ctrl+Shift+W', QKeySequence.NativeText))
        self.close_mp_action.setStatusTip(
            'Close the main project and delete all data and plots out of '
            'memory')
        self.close_mp_action.triggered.connect(
            lambda: psy.close(psy.gcp(True).num))
        self.close_project_menu.addAction(self.close_mp_action)

        self.close_sp_action = QAction('Only selected', self)
        self.close_sp_action.setStatusTip(
            'Close the selected arrays project and delete all data and plots '
            'out of memory')
        self.close_sp_action.setShortcut(QKeySequence.Close)
        self.close_sp_action.triggered.connect(
            lambda: psy.gcp().close(True, True))
        self.close_project_menu.addAction(self.close_sp_action)

        # ------------------------ Quit ------------------------------

        if sys.platform != 'darwin':  # mac os makes this anyway
            self.quit_action = QAction('Quit', self)
            self.quit_action.triggered.connect(
                QtCore.QCoreApplication.instance().quit)
            self.quit_action.setShortcut(QKeySequence.Quit)
            self.file_menu.addAction(self.quit_action)

        self.menuBar().addMenu(self.file_menu)

        # ######################## Console menu ###############################

        self.console_menu = QMenu('Console', self)
        self.console_menu.addActions(self.console.actions())
        self.menuBar().addMenu(self.console_menu)

        # ######################## Windows menu ###############################

        self.windows_menu = QMenu('Windows', self)
        self.menuBar().addMenu(self.windows_menu)

        # ---------------------------------------------------------------------
        # -------------------------- Dock windows -----------------------------
        # ---------------------------------------------------------------------
        #: tab widget displaying the arrays in current main and sub project
        self.project_content = ProjectContentWidget(parent=self)
        self.addDockWidget(Qt.LeftDockWidgetArea,
                           self.project_content.to_dock('Plot objects', self),
                           'pane')
        #: tree widget displaying the open datasets
        self.ds_tree = DatasetTree(parent=self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.ds_tree.to_dock(
            'Datasets', self), 'pane')
        #: tree widget displaying the open figures
        self.figures_tree = FiguresTree(parent=self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.figures_tree.to_dock(
            'Figures', self), 'pane')
        #: help explorer
        self.help_explorer = help_explorer = HelpExplorer(parent=self)
        self.addDockWidget(Qt.RightDockWidgetArea, help_explorer.to_dock(
            'Help explorer', self), 'pane')
        #: general formatoptions widget
        self.fmt_widget = FormatoptionWidget(
            parent=self, help_explorer=help_explorer,
            shell=self.console.kernel_client.kernel.shell)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.fmt_widget.to_dock(
            'Formatoptions', self), 'pane')

        self.windows_menu.addSeparator()
        self.add_mp_to_menu()
        psy.Project.oncpchange.connect(self.eventually_add_mp_to_menu)

        # ---------------------------------------------------------------------
        # -------------------------- connections ------------------------------
        # ---------------------------------------------------------------------

        self.console.help_explorer = help_explorer
        psyp.default_print_func = partial(help_explorer.show_rst,
                                          oname='formatoption_docs')
        psy._PlotterInterface._print_func = psyp.default_print_func
        self.setCentralWidget(self.console)

        # make sure that the plots are shown between the project content and
        # the help explorer widget
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)

        # make sure that the formatoption widgets are shown between the
        # project content and the help explorer widget
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        # Server to open external files on a single instance
        self.open_files_server = socket.socket(socket.AF_INET,
                                               socket.SOCK_STREAM,
                                               socket.IPPROTO_TCP)

        self.showMaximized()

        if rcParams['main.listen_to_port']:
            self._file_thread = Thread(target=self.start_open_files_server)
            self._file_thread.setDaemon(True)
            self._file_thread.start()

            self.open_external.connect(self.open_external_files)

        # ---------------------------------------------------------------------
        # ------------------------------ closure ------------------------------
        # ---------------------------------------------------------------------
        self.help_explorer.show_intro(self.console.intro_msg)

    def _save_project(self, p, new_fname=False, *args, **kwargs):
        if new_fname or 'project_file' not in p.attrs:
            fname = QFileDialog.getSaveFileName(
                self, 'Project destination', os.getcwd(),
                'Pickle files (*.pkl);;'
                'All files (*)'
                )
            if not fname:
                return
        else:
            fname = p.attrs['project_file']
        try:
            p.save_project(fname, *args, **kwargs)
        except:
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
            self, 'Project destination', os.getcwd(),
            'Pickle files (*.pkl);;'
            'All files (*)'
            )
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
        if not fname:
            return
        try:
            p.export(fname, *args, **kwargs)
        except:
            self.error_msg.showTraceback(
                '<b>Could not export the figures!</b>')

    def export_mp(self, *args, **kwargs):
        self._export_project(psy.gcp(True), **kwargs)

    def export_sp(self, *args, **kwargs):
        self._export_project(psy.gcp(), **kwargs)

    def new_plots(self):
        if hasattr(self, 'plot_creator'):
            self.plot_creator.close()
        self.plot_creator = PlotCreator(
            self.console.get_obj, help_explorer=self.help_explorer)
        available_width = QDesktopWidget().availableGeometry().width() / 3.
        width = self.plot_creator.sizeHint().width()
        height = self.plot_creator.sizeHint().height()
        # The plot creator window shoul cover at least one third of the screen
        self.plot_creator.resize(max(available_width, width), height)
        self.plot_creator.show()

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
            self.windows_menu.addAction(dockwidget.toggleViewAction())
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
        except:
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
                raise
            l = pickle.loads(req.recv(1024))
            self.open_external.emit(l)
            req.sendall(b' ')

    def open_external_files(self, l):
        fnames, project, engine, plot_method, name, dims = l
        if project is not None:
            fnames = [s.split(',') for s in fnames]
            single_files = (l[0] for l in fnames if len(l) == 1)
            alternative_paths = defaultdict(lambda: next(single_files, None))
            alternative_paths.update(list(l for l in fnames if len(l) == 2))
            psy.Project.load_project(
                project, alternative_paths=alternative_paths,
                engine=engine, main=False)
        else:
            self.new_plots()
            self.plot_creator.open_dataset(fnames, engine=engine)
            self.plot_creator.insert_array(name)
            if dims is not None:
                self.plot_creator.array_table.selectAll()
                self.plot_creator.array_table.update_selected(
                    dims={key: ', '.join(
                        map(str, val)) for key, val in six.iteritems(
                            dims)})

    docstrings.keep_params(
        'make_plot.parameters', 'fnames', 'project', 'engine', 'plot_method',
        'name', 'dims')

    @classmethod
    @docstrings.get_sectionsf('MainWindow.run')
    @docstrings.dedent
    def run(cls, fnames=[], project=None, engine=None, plot_method=None,
            name=None, dims=None):
        """
        Create a mainwindow and open the given files or project

        This class method creates a new mainwindow instance and sets the
        global :attr:`mainwindow` variable.

        Parameters
        ----------
        %(make_plot.parameters.fnames|project|engine|plot_method|name|dims)s

        Notes
        -----
        - There can be only one mainwindow at the time
        - This method does not create a QApplication instance! See
          :meth:`run_app`

        See Also
        --------
        run_app
        """
        mainwindow = cls()
        _set_mainwindow(mainwindow)
        if fnames or project:
            mainwindow.open_external_files(
                [fnames, project, engine, plot_method, name, dims])
        return mainwindow

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

    def close(self, *args, **kwargs):
        _set_mainwindow(None)
        self.open_files_server.close()
        super(MainWindow, self).close(*args, **kwargs)