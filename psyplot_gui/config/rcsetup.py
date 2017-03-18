"""Default management of the psyplot_gui package

This module defines the necessary configuration parts for the psyplot gui"""
import six
from psyplot.config.rcsetup import (
    RcParams, psyplot_fname, validate_bool_maybe_none, validate_stringlist)
from matplotlib.rcsetup import validate_int, validate_bool


def try_and_error(*funcs):
    """Apply multiple validation functions

    Parameters
    ----------
    ``*funcs``
        Validation functions to test

    Returns
    -------
    function"""
    def validate(value):
        exc = None
        for func in funcs:
            try:
                return func(value)
            except (ValueError, TypeError) as e:
                exc = e
        raise exc
    return validate


# -----------------------------------------------------------------------------
# ------------------------- validation functions ------------------------------
# -----------------------------------------------------------------------------


def validate_str(s):
    """Validate a string

    Parameters
    ----------
    s: str

    Returns
    -------
    str

    Raises
    ------
    ValueError"""
    if not isinstance(s, six.string_types):
        raise ValueError("Did not found string!")
    return six.text_type(s)


def validate_none(b):
    """Validate that None is given

    Parameters
    ----------
    b: {None, 'none'}
        None or string (the case is ignored)

    Returns
    -------
    None

    Raises
    ------
    ValueError"""
    if isinstance(b, six.string_types):
        b = b.lower()
    if b is None or b == 'none':
        return None
    else:
        raise ValueError('Could not convert "%s" to None' % b)


def validate_all(v):
    """Test if ``v == 'all'``"""
    if v != 'all':
        raise ValueError("The value must be 'all'")
    return six.text_type(v)


class GuiRcParams(RcParams):

    def load_from_file(self, fname=None):
        """Update rcParams from user-defined settings

        This function updates the instance with what is found in `fname`

        Parameters
        ----------
        fname: str
            Path to the yaml configuration file. Possible keys of the
            dictionary are defined by :data:`config.rcsetup.defaultParams`.
            If None, the :func:`config.rcsetup.psyplot_fname` function is used.

        See Also
        --------
        dump_to_file, psyplot_fname"""
        fname = fname or psyplot_fname(env_key='PSYPLOTGUIRC',
                                       fname='psyplotguirc.yml')
        if fname:
            super(GuiRcParams, self).load_from_file(fname)

#: :class:`dict` with default values and validation functions
defaultParams = {

    # gui settings
    'backend': [
        'psyplot',
        try_and_error(validate_str, validate_none),
        'Backend to use when using the graphical user interface. The current '
        'backend is used and no changes are made. Note that it is usually not '
        'possible to change the backend after importing the psyplot.project '
        'module. The default backend embeds the figures into the '],
    'help_explorer.use_intersphinx': [
        None, validate_bool_maybe_none,
        'Use the intersphinx extension and link to the online documentations '
        'of matplotlib, pyplot, psyplot, numpy, etc. when converting rst '
        'docstrings. The inventories are loaded when the first object is '
        'documented. If None, intersphinx is only used with PyQt5'],
    'help_explorer.render_docs_parallel': [
        True, validate_bool,
        'Boolean whether the html docs are rendered in a separate process'],
    'help_explorer.online': [
        None, validate_bool_maybe_none,
        'Switch that controls whether the online functions of the help '
        'explorer shall be enabled. False implies that '
        'help_explorer.use_intersphinx is set to False'],
    'console.connect_to_help': [
        True, validate_bool,
        'Whether the console shall be connected to the help_explorer or not'],
    'console.auto_set_mp': [
        True, validate_bool,
        "If True, then the 'mp' variable in the console is automatically set "
        "when the current main project changes"],
    'console.auto_set_sp': [
        True, validate_bool,
        "If True, then the 'sp' variable in the console is automatically set "
        "when the current sub project changes"],
    'main.open_files_port': [
        30124, validate_int, "The port number used when new files are opened"],
    'main.listen_to_port': [
        True, validate_bool,
        "If True and the psyplot gui is already running, new files are opened "
        "in that gui"],
    'content.load_tooltips': [
        True, validate_bool,
        "If True, a lazy load is performed on the arrays and data sets and "
        "their string representation is displayed as tool tip. This part of "
        "the data into memory. It is recommended to set this to False for "
        "remote data."],
    'plugins.include': [
        None, try_and_error(validate_none, validate_stringlist),
        "The plugins to load. Can be either None to load all that are not "
        "explicitly excluded by the 'plugins.exclude' key or a list of "
        "plugins to include. List items can be either module names, plugin "
        "names or the module name and widget via '<module_name>:<widget>'"],
    'plugins.exclude': [
        [], try_and_error(validate_all, validate_stringlist),
        "The plugins to exclude from loading. Can be either 'all' to exclude "
        "all plugins or a list like in 'plugins.include'."],
    }

#: :class:`~psyplot.config.rcsetup.RcParams` instance that stores default
#: formatoptions and configuration settings.
rcParams = GuiRcParams(defaultParams=defaultParams)
rcParams.update({key: val[0] for key, val in defaultParams.items()})
rcParams.load_from_file()
