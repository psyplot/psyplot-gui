# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

# -*- coding: utf-8 -*-
"""Skript to test the InProcessShell that is used in the psyplot gui"""
import inspect
import re
import unittest

import _base_testing as bt
import psyplot.project as psy
import six

from psyplot_gui.compat.qtcompat import QTest, with_qt5

travis_qt_msg = "Does not work on Travis with Qt4"


class ConsoleTest(bt.PsyPlotGuiTestCase):
    """A testcase to test the InProcess IPython console of the psyplot GUI"""

    def setUp(self):
        import psyplot_gui.console

        # XXX HACK: Set the _with_prompt attribute to False to tell the
        # ConsoleWidget to use the _prompt_cursor
        psyplot_gui.console._with_prompt = False
        super(ConsoleTest, self).setUp()

    def tearDown(self):
        import psyplot_gui.console

        # XXX HACK: Set the _with_prompt attribute to True again to tell the
        # ConsoleWidget to use the _prompt_cursor
        psyplot_gui.console._with_prompt = True
        super(ConsoleTest, self).tearDown()

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
        he.set_viewer("Plain text")
        # we insert the text here otherwise using console _insert_plain_text
        # method because apparently the text is not inserted when using
        # QTest.keyClicks
        self.insert_text("object")
        QTest.keyClicks(c._control, symbol)
        sig = (
            ""
            if six.PY2
            else re.sub(
                r"^\(\s*self,\s*", "(", str(signature(object.__init__))
            )
        )
        header = "object" + sig
        bars = "=" * len(header)
        self.assertEqual(
            he.viewer.editor.toPlainText(),
            "\n".join(
                [
                    bars,
                    header,
                    bars + "\n\n",
                    inspect.getdoc(object),
                    "\n" + inspect.getdoc(object.__init__),
                ]
            ),
        )

    @unittest.skipIf(bt.on_travis and not with_qt5, travis_qt_msg)
    def test_questionmark(self):
        """Test the connection to the help explorer by typing '?'"""
        self._test_object_docu("?")

    @unittest.skipIf(bt.on_travis and not with_qt5, travis_qt_msg)
    def test_bracketleft(self):
        """Test the connection to the help explorer by typing '?'"""
        self._test_object_docu("(")

    @unittest.skipIf(bt.on_travis and not with_qt5, travis_qt_msg)
    def test_current_object(self):
        """Test whether the current object is given correctly"""
        c = self.window.console
        self.insert_text("print(test.anything(object")
        self.assertEqual(c.get_current_object(True), "object")
        try:  # qtconsole >4.3 uses the _prompt_cursor attribute
            cursor = c._prompt_cursor
        except AttributeError:
            cursor = c._control.textCursor()
        curr = cursor.position()
        self.insert_text(") + 3")
        cursor.setPosition(curr)
        self.assertEqual(c.get_current_object(), "object")

    def test_command(self):
        self.window.console.run_command_in_shell("a = 4")
        self.assertEqual(self.window.console.get_obj("a")[1], 4)

    def test_mp_sp(self):
        """Test whether the mp and sp variables are set correctly"""
        from xarray import DataArray

        psy.Project.oncpchange.emit(psy.gcp(True))
        psy.Project.oncpchange.emit(psy.gcp())
        self.assertIs(self.window.console.get_obj("mp")[1], psy.gcp(True))
        self.assertIs(self.window.console.get_obj("sp")[1], psy.gcp())
        sp = psy.plot.lineplot(DataArray([1, 2, 3], name="test").to_dataset())
        self.assertIs(self.window.console.get_obj("mp")[1], psy.gcp(True))
        self.assertIs(self.window.console.get_obj("sp")[1], sp)
        sp.close(True, True)
        self.assertIs(self.window.console.get_obj("mp")[1], psy.gcp(True))
        self.assertIs(self.window.console.get_obj("sp")[1], psy.gcp())


if __name__ == "__main__":
    unittest.main()
