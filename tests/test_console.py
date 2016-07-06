# -*- coding: utf-8 -*-
"""Skript to test the InProcessShell that is used in the psyplot gui"""
import re
import six
import unittest
import _base_testing as bt
import psyplot.project as psy
import inspect
from psyplot_gui.compat.qtcompat import QTest


class ConsoleTest(bt.PsyPlotGuiTestCase):
    """A testcase to test the InProcess IPython console of the psyplot GUI"""

    def insert_text(self, text):
        """Convenience method to insert a single line into the console"""
        c = self.window.console
        return c._insert_plain_text(c._get_prompt_cursor(), text)

    def _test_object_docu(self, symbol):
        """Tests whether the documentation of :class:`object` can be displayed

        Parameters
        ----------
        symbol: {'?', '('}
            The symbol to use for displaying the doc

        See Also
        --------
        test_questionmark, test_bracketleft
        """
        from psyplot_gui.help_explorer import signature
        c = self.window.console
        he = self.window.help_explorer
        he.set_viewer('Plain text')
        # we insert the text here otherwise using console _insert_plain_text
        # method because apparently the text is not inserted when using
        # QTest.keyClicks
        self.insert_text('object')
        QTest.keyClicks(c._control, symbol)
        sig = '' if six.PY2 else re.sub(
            '^\(\s*self,\s*', '(', str(signature(object.__init__)))
        header = "object" + sig
        bars = '=' * len(header)
        self.assertEqual(
            he.viewer.editor.toPlainText(),
            '\n'.join([
                bars, header, bars + "\n\n", inspect.getdoc(object),
                "\n" + inspect.getdoc(object.__init__)]))

    @bt.skipOnTravis
    def test_questionmark(self):
        """Test the connection to the help explorer by typing '?'"""
        self._test_object_docu('?')

    @bt.skipOnTravis
    def test_bracketleft(self):
        """Test the connection to the help explorer by typing '?'"""
        self._test_object_docu('(')

#    @bt.skipOnTravis
    def test_current_object(self):
        """Test whether the current object is given correctly"""
        c = self.window.console
        self.insert_text('print(test.anything(object')
        self.assertEqual(c.get_current_object(True), 'object')
        cursor = c._control.textCursor()
        curr = cursor.position()
        self.insert_text(') + 3')
        cursor.movePosition(curr)
        self.assertEqual(c.get_current_object(), 'object')

    def test_command(self):
        self.window.console.kernel_manager.kernel.shell.run_code('a = 4')
        self.assertEqual(self.window.console.get_obj('a')[1], 4)

    def test_mp_sp(self):
        """Test whether the mp and sp variables are set correctly"""
        from xarray import DataArray
        self.assertIs(self.window.console.get_obj('mp')[1], psy.gcp(True))
        self.assertIs(self.window.console.get_obj('sp')[1], psy.gcp())
        sp = psy.plot.lineplot(DataArray([1, 2, 3], name='test').to_dataset())
        self.assertIs(self.window.console.get_obj('mp')[1], psy.gcp(True))
        self.assertIs(self.window.console.get_obj('sp')[1], sp)
        sp.close(True, True)
        self.assertIs(self.window.console.get_obj('mp')[1], psy.gcp(True))
        self.assertIs(self.window.console.get_obj('sp')[1], psy.gcp())


if __name__ == "__main__":
    unittest.main()
