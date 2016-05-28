"""Core package for the psyplot graphical user interface"""
import os.path as osp
import six
import socket
import atexit
import fasteners
import time
import pickle
import datetime as dt
import logging
import psyplot
from psyplot.main import make_plot
from psyplot_gui.config.rcsetup import rcParams
import psyplot_gui.config as config
from itertools import chain
from psyplot.config.rcsetup import get_configdir
from psyplot.docstring import docstrings
from psyplot.warning import warn
from psyplot.compat.pycompat import map


__version__ = "0.0.3.dev7"
__author__ = "Philipp Sommer (philipp.sommer@unil.ch)"

logger = logging.getLogger(__name__)
logger.debug(
    "%s: Initializing psyplot gui, version %s",
    dt.datetime.now().isoformat(), __version__)
logger.debug("Logging configuration file: %s", config.logcfg_path)
logger.debug("Configuration file: %s", config.config_path)


rcParams.HEADER += "\n\npsyplot gui version: " + __version__


logger = logging.getLogger(__name__)


@docstrings.dedent
def start_app(fnames=[], name=[], dims=None, plot_method=None, backend=False,
              output=None, project=None, engine=None, formatoptions=None,
              tight=False, new_instance=False, rc_file=None, rc_gui_file=None):
    """
    Eventually start the QApplication or only make a plot

    Parameters
    ----------
    %(make_plot.parameters)s
    backend: None or str
        The backend to use. By default, the ``'gui.backend'`` key in the
        :attr:`psyplot.rcParams` dictionary is used. Otherwise it can be None
        to use the standard matplotlib backend or a string identifying the
        backend
    new_instance: bool
        If True/set and the `output` parameter is not set, a new application is
        created
    rc_gui_file: str
        The path to a yaml configuration file that can be used to update  the
        :attr:`psyplot_gui.rcParams`
    """

    if project is not None and (name != [] or dims is not None):
        warn('The `name` and `dims` parameter are ignored if the `project`'
             ' parameter is set!')

    if rc_gui_file is not None:
        rcParams.load_from_file(rc_gui_file)

    if dims is not None and not isinstance(dims, dict):
        dims = dict(chain(*map(six.iteritems, dims)))

    if output is not None:
        return make_plot(
            fnames=fnames, name=name, dims=dims, plot_method=plot_method,
            output=output, project=project, engine=engine,
            formatoptions=formatoptions, tight=tight, rc_file=rc_file)

    # Lock file creation
    lock_file = osp.join(get_configdir(), 'psyplot.lock')
    lock = fasteners.InterProcessLock(lock_file)

    # Try to lock psyplot.lock. If it's *possible* to do it, then
    # there is no previous instance running and we can start a
    # new one. If *not*, then there is an instance already
    # running, which is locking that file
    lock_created = lock.acquire(False)

    if lock_created:
        # Start a new instance
        atexit.register(lock.release)
    elif not new_instance:
        send_files_to_psyplot(fnames, project, engine, plot_method, name, dims)
        return
    elif new_instance:
        rcParams['main.listen_to_port'] = False
    if backend is not False:
        rcParams['backend'] = backend
    from psyplot_gui.main import MainWindow
    MainWindow.run_app(fnames, project, engine, plot_method, name, dims)


def send_files_to_psyplot(fnames, project, *args):
    """
    Simple socket client used to send the args passed to the psyplot
    executable to an already running instance.

    This function has to most parts been taken from spyder
    """
    port = rcParams['main.open_files_port']

    # Wait ~50 secs for the server to be up
    # Taken from http://stackoverflow.com/a/4766598/438386
    for _x in range(200):
        for i, fname in enumerate(fnames):
            fnames[i] = osp.abspath(fname)
        if project is not None:
            project = osp.abspath(project)
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                                   socket.IPPROTO_TCP)
            client.connect(("127.0.0.1", port))

            client.send(pickle.dumps([fnames, project] + list(args)))
            client.close()
        except socket.error:
            time.sleep(0.25)
            continue
        break


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
    from psyplot.main import get_parser
    parser = get_parser(create=False)

    parser.setup_args(start_app)

    gui_grp = parser.add_argument_group(
        'Gui options',
        'Options specific to the graphical user interface')

    parser.update_arg('version', version="psyplot: %s\npsyplot_gui: %s" % (
        psyplot.__version__, __version__))

    parser.update_arg(
        'backend', short='b', const=None, nargs='?', metavar='backend',
        help="""
        The backend to use. By default, the ``'gui.backend'`` key in the
        :attr:`psyplot_gui.rcParams` dictionary is used. If used without
        options, the default matplotlib backend is used.""", group=gui_grp)

    parser.update_arg('new_instance', short='ni', group=gui_grp)

    parser.update_arg('rc_gui_file', short='rc_gui', group=gui_grp)
    parser.pop_key('rc_gui_file', 'metavar')

    parser.set_main(start_app)

    parser.epilog += """

If you omit the ``'-o'`` option, the file is opened in the graphical user
interface"""

    if create:
        parser.create_arguments()

    return parser
