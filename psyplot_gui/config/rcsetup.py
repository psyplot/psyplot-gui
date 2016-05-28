"""Default management of the psyplot_gui package

This module defines the necessary configuration parts for the psyplot gui"""
import os.path as osp
from psyplot.config.rcsetup import (
    RcParams, try_and_error, validate_str, validate_none, validate_int,
    validate_bool, validate_bool_maybe_none, psyplot_fname)


def psyplot_gui_fname():
    """
    Get the location of the config file.

    The file location is determined by the
    :func:`psyplot.config.rcsetup.psyplot_fname` function"""
    psyplot_file = psyplot_fname()
    if psyplot_file:
        return osp.join(osp.dirname(psyplot_file), 'psyplotguirc.yaml')
    return None


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
        fname = fname or psyplot_gui_fname()
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
        False, validate_bool_maybe_none,
        'Use the intersphinx extension and link to the online documentations '
        'of matplotlib, pyplot, psyplot, numpy, etc. when converting rst '
        'docstrings. The inventories are loaded when the first object is '
        'documented. If None, intersphinx is only used with PyQt5'],
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
        "in that gui"]
    }

#: :class:`~psyplot.config.rcsetup.RcParams` instance that stores default
#: formatoptions and configuration settings.
rcParams = RcParams()
rcParams.defaultParams = defaultParams
rcParams.update({key: val[0] for key, val in defaultParams.items()})
rcParams.load_from_file()
