# Test module that defines a plotter
#
# The plotter in this module has been registered by the rcParams in the plugin
# package
from psyplot.plotter import Plotter, Formatoption


class TestFmt(Formatoption):
    """Some documentation"""

    default = None

    name = 'Test formatoption'

    def get_fmt_widget(self, parent, project):
        """Get the formatoption widget to update this formatoption in the GUI
        """
        from psyplot_gui.compat.qtcompat import QPushButton
        button = QPushButton('Test', parent)
        button.clicked.connect(lambda: parent.insert_obj(button.text()))
        return button

    def update(self, value):
        pass


class TestFmt2(TestFmt):
    """Another formatoption to the different types of get_fmt_widget"""

    name = 'Second test formatoption'

    def get_fmt_widget(self, parent, project):
        """Get the formatoption widget to update this formatoption in the GUI
        """
        from psyplot_gui.compat.qtcompat import QPushButton
        button = QPushButton('Test', parent)
        button.clicked.connect(lambda: parent.insert_obj(2))
        return button


class TestPlotter(Plotter):

    fmt1 = TestFmt('fmt1')
    fmt2 = TestFmt2('fmt2')
