"""Core package for the psyplot graphical user interface"""
import sys
import os
import os.path as osp
import six
import socket
import atexit
import fasteners
import time
import pickle
import datetime as dt
import logging
import argparse
import xarray as xr
import psyplot
from psyplot.__main__ import make_plot
from psyplot_gui.config.rcsetup import rcParams
import psyplot_gui.config as config
from itertools import chain
from psyplot.config.rcsetup import get_configdir, safe_list
from psyplot.docstring import docstrings
from psyplot.warning import warn
from psyplot.compat.pycompat import map
from psyplot_gui.version import __version__

from psyplot.compat.pycompat import get_default_value

__author__ = "Philipp Sommer (philipp.sommer@unil.ch)"

logger = logging.getLogger(__name__)
logger.debug(
    "%s: Initializing psyplot gui, version %s",
    dt.datetime.now().isoformat(), __version__)
logger.debug("psyplot version: %s", psyplot.__version__)
logger.debug("Logging configuration file: %s", config.logcfg_path)
logger.debug("Configuration file: %s", config.config_path)


rcParams.HEADER += "\n\npsyplot gui version: " + __version__


logger = logging.getLogger(__name__)


def get_versions(requirements=True):
    ret = {'version': __version__}
    if requirements:
        req = ret['requirements'] = {}
        try:
            import qtconsole
        except Exception:
            logger.error('Could not load qtconsole!', exc_info=True)
        else:
            req['qtconsole'] = qtconsole.__version__
        try:
            from psyplot_gui.compat.qtcompat import PYQT_VERSION, QT_VERSION
        except Exception:
            logger.error('Could not load qt and pyqt!', exc_info=True)
        else:
            req['qt'] = QT_VERSION
            req['pyqt'] = PYQT_VERSION
    return ret


@docstrings.get_sectionsf('psyplot_gui.start_app')
@docstrings.dedent
def start_app(fnames=[], name=[], dims=None, plot_method=None,
              output=None, project=None, engine=None, formatoptions=None,
              tight=False, encoding=None, enable_post=False,
              seaborn_style=None, output_project=None,
              concat_dim=get_default_value(xr.open_mfdataset, 'concat_dim'),
              chname={},
              backend=False, new_instance=False, rc_file=None,
              rc_gui_file=None, include_plugins=rcParams['plugins.include'],
              exclude_plugins=rcParams['plugins.exclude'], offline=False,
              pwd=None, script=None, command=None, exec_=True, use_all=False,
              callback=None):
    """
    Eventually start the QApplication or only make a plot

    Parameters
    ----------
    %(make_plot.parameters)s
    backend: None or str
        The backend to use. By default, the ``'gui.backend'`` key in the
        :attr:`~psyplot_gui.config.rcsetup.rcParams` dictionary is used.
        Otherwise it can be None to use the standard matplotlib backend or a
        string identifying the backend
    new_instance: bool
        If True/set and the `output` parameter is not set, a new application is
        created
    rc_gui_file: str
        The path to a yaml configuration file that can be used to update  the
        :attr:`~psyplot_gui.config.rcsetup.rcParams`
    include_plugins: list of str
        The plugin widget to include. Can be either None to load all that are
        not explicitly excluded by `exclude_plugins` or a list of
        plugins to include. List items can be either module names, plugin
        names or the module name and widget via ``'<module_name>:<widget>'``
    exclude_plugins: list of str
        The plugin widgets to exclude. Can be either ``'all'`` to exclude
        all plugins or a list like in `include_plugins`.
    offline: bool
        If True/set, psyplot will be started in offline mode without
        intersphinx and remote access for the help explorer
    pwd: str
        The path to the working directory to use. Note if you do not provide
        any `fnames` or `project`, but set the `pwd`, it will switch the
        `pwd` of the current GUI.
    script: str
        The path to a python script that shall be run in the GUI. If the GUI
        is already running, the commands will be executed in this GUI.
    command: str
        Python commands that shall be run in the GUI. If the GUI is already
        running, the commands will be executed in this GUI
    use_all: bool
        If True, use all variables. Note that this is the default if the
        `output` is specified and not `name`
    exec_: bool
        If True, the main loop is entered.
    callback: str
        A unique identifier for the method that should be used if psyplot is
        already running. Set this parameter to None to avoid sending

    Returns
    -------
    None or :class:`psyplot_gui.main.MainWindow`
        ``None`` if `exec_` is True, otherwise the created
        :class:`~psyplot_gui.main.MainWindow` instance
    """
    if pwd is not None:
        os.chdir(pwd)
    if script is not None:
        script = osp.abspath(script)

    if project is not None and (name != [] or dims is not None):
        warn('The `name` and `dims` parameter are ignored if the `project`'
             ' parameter is set!')

    # load rcParams from file
    if rc_gui_file is not None:
        rcParams.load_from_file(rc_gui_file)

    # set plugins
    rcParams['plugins.include'] = include_plugins
    rcParams['plugins.exclude'] = exclude_plugins

    if offline:
        rcParams['help_explorer.online'] = False
        rcParams['help_explorer.use_intersphinx'] = False

    if dims is not None and not isinstance(dims, dict):
        dims = dict(chain(*map(six.iteritems, dims)))

    if output is not None:
        return make_plot(
            fnames=fnames, name=name, dims=dims, plot_method=plot_method,
            output=output, project=project, engine=engine,
            formatoptions=formatoptions, tight=tight, rc_file=rc_file,
            encoding=encoding, enable_post=enable_post,
            seaborn_style=seaborn_style, output_project=output_project,
            concat_dim=concat_dim, chname=chname)
    if use_all:
        name = 'all'
    else:
        name = safe_list(name)

    # Lock file creation
    lock_file = osp.join(get_configdir(), 'psyplot.lock')
    lock = fasteners.InterProcessLock(lock_file)

    # Try to lock psyplot.lock. If it's *possible* to do it, then
    # there is no previous instance running and we can start a
    # new one. If *not*, then there is an instance already
    # running, which is locking that file
    lock_created = lock.acquire(False)

    chname = dict(chname)

    if lock_created:
        # Start a new instance
        atexit.register(lock.release)
    elif not new_instance:
        if callback is None:
            if fnames or project:
                callback = 'new_plot'
            elif pwd is not None:
                callback = 'change_cwd'
                fnames = [pwd]
            elif script is not None:
                callback = 'run_script'
                fnames = [script]
            elif command is not None:
                callback = 'command'
                engine = command
        if callback:
            send_files_to_psyplot(
                callback, fnames, project, engine, plot_method, name, dims,
                encoding, enable_post, seaborn_style, concat_dim, chname)
        return
    elif new_instance:
        rcParams['main.listen_to_port'] = False
    if backend is not False:
        rcParams['backend'] = backend
    from psyplot_gui.main import MainWindow
    fnames = _get_abs_names(fnames)
    if project is not None:
        project = _get_abs_names([project])[0]
    if exec_:
        from psyplot_gui.compat.qtcompat import QApplication
        app = QApplication(sys.argv)
    mainwindow = MainWindow.run(fnames, project, engine, plot_method, name,
                                dims, encoding, enable_post, seaborn_style,
                                concat_dim, chname)
    if script is not None:
        mainwindow.console.run_script_in_shell(script)
    if command is not None:
        mainwindow.console.run_command_in_shell(command)
    if exec_:
        sys.excepthook = mainwindow.excepthook
        sys.exit(app.exec_())
    else:
        return mainwindow


def send_files_to_psyplot(callback, fnames, project, *args):
    """
    Simple socket client used to send the args passed to the psyplot
    executable to an already running instance.

    This function has to most parts been taken from spyder
    """
    port = rcParams['main.open_files_port']

    # Wait ~50 secs for the server to be up
    # Taken from http://stackoverflow.com/a/4766598/438386
    for _x in range(200):
        fnames = _get_abs_names(fnames)
        if project is not None:
            project = _get_abs_names([project])[0]
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                   socket.IPPROTO_TCP)
            client.connect(("127.0.0.1", port))
            client.send(pickle.dumps([callback, fnames, project] + list(args)))
            client.close()
        except socket.error:
            time.sleep(0.25)
            continue
        break


def _get_abs_names(fnames):
    """Return the absolute paths of the given filenames"""
    if fnames is None:
        return
    for i, fname in enumerate(fnames):
        if fname:
            fnames[i] = ','.join(map(osp.abspath, fname.split(',')))
    return fnames


def get_parser(create=True):
    """Return a parser to make that can be used to make plots or open files
    from the command line

    Returns
    -------
    psyplot.parser.FuncArgParser
        The :class:`argparse.ArgumentParser` instance

    See Also
    --------
    psyplot.main.get_parser
    psyplot.parser.FuncArgParser
    psyplot.main.main"""
    from psyplot.__main__ import get_parser
    parser = get_parser(create=False)

    parser.setup_args(start_app)

    gui_grp = parser.add_argument_group(
        'Gui options',
        'Options specific to the graphical user interface')

    parser.update_arg(
        'backend', short='b', const=None, nargs='?', metavar='backend',
        help="""
        The backend to use. By default, the ``'gui.backend'`` key in the
        :attr:`~psyplot_gui.config.rcsetup.rcParams` dictionary is used. If
        used without options, the default matplotlib backend is used.""",
        group=gui_grp)

    parser.update_arg('new_instance', short='ni', group=gui_grp)

    parser.update_arg('rc_gui_file', short='rc-gui', group=gui_grp)
    parser.pop_key('rc_gui_file', 'metavar')
    parser.update_arg('include_plugins', short='inc', group=gui_grp,
                      default=rcParams['plugins.include'])
    parser.append2help('include_plugins', '. Default: %(default)s')
    parser.update_arg('exclude_plugins', short='exc', group=gui_grp,
                      default=rcParams['plugins.exclude'])
    parser.append2help('exclude_plugins', '. Default: %(default)s')

    parser.update_arg('offline', group=gui_grp)
    parser.update_arg('pwd', group=gui_grp)
    parser.update_arg('script', short='s', group=gui_grp)
    parser.update_arg('command', short='c', group=gui_grp)
    # add an action to display the GUI plugins
    info_grp = parser.unfinished_arguments['list_plugins'].get('group')
    parser.update_arg(
        'list_gui_plugins', short='lgp', long='list-gui-plugins',
        action=ListGuiPluginsAction, if_existent=False,
        help=("Print the names of the GUI plugins and exit. Note that the "
              "displayed plugins are not affected by the `include-plugins` "
              "and `exclude-plugins` options"))
    if info_grp is not None:
        parser.unfinished_arguments['list_gui_plugins']['group'] = info_grp

    parser.pop_key('offline', 'short')

    parser.append2help('output_project',
                       '. This option has only an effect if the `output` '
                       ' option is set.')

    parser.update_arg('use_all', short='a')

    parser.pop_arg('exec_')
    parser.pop_arg('callback')

    if psyplot.__version__ < '1.0':
        parser.set_main(start_app)

    parser.epilog += """

If you omit the ``'-o'`` option, the file is opened in the graphical user
interface and if you run::

    $ psyplot -pwd .

It will switch the directory of the already running GUI (if existent) to the
current working directory in your terminal. Additionally,::

    $ psyplot -s myscript.py

will run the file ``'myscript.py'`` in the GUI and::

    $ psyplot -c 'print("Hello World!")'

will execute ``print("Hello World")`` in the GUI. The output, of the `-s` and
`-c` options, will, however, be shown in the terminal."""

    if create:
        parser.create_arguments()

    return parser


#: Disable the default for the ListGuiPluginsAction on RTD, because it looks
#: better in the docs
_on_rtd = os.environ.get('READTHEDOCS', None) == 'True'


class ListGuiPluginsAction(argparse.Action):

    def __init__(self, option_strings, dest=argparse.SUPPRESS, nargs=None,
                 default=argparse.SUPPRESS, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        if not _on_rtd:
            kwargs['default'] = default
        super(ListGuiPluginsAction, self).__init__(
            option_strings, nargs=0, dest=dest,
            **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        import yaml
        if not rcParams._plugins:
            list(rcParams._load_plugin_entrypoints())
        print(yaml.dump(rcParams._plugins, default_flow_style=False))
        sys.exit(0)
