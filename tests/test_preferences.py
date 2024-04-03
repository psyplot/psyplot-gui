# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

# -*- coding: utf-8 -*-
"""Script to test the :mod:`psyplot_gui.preferences` module"""
import os
import os.path as osp
import shutil
import tempfile
import unittest
from itertools import islice

import _base_testing as bt
import yaml
from psyplot import rcParams as psy_rcParams

import psyplot_gui.preferences as prefs
from psyplot_gui import rcParams as gui_rcParams
from psyplot_gui.compat.qtcompat import QDialogButtonBox, Qt, QTest, asstring
from psyplot_gui.config.rcsetup import GuiRcParams


class TestRcParamsWidget(bt.PsyPlotGuiTestCase):
    """Test the :class:`psyplot_gui.preferences.RcParamsWidget` class"""

    _created_files = set()

    def setUp(self):
        super(TestRcParamsWidget, self).setUp()
        self._created_files = set()

    def tearDown(self):
        super(TestRcParamsWidget, self).tearDown()
        for f in self._created_files:
            if osp.exists(f) and osp.isdir(f):
                shutil.rmtree(f)
            elif osp.exists(f):
                os.remove(f)
        self._created_files.clear()

    def test_loading(self):
        """Test whether the rcParams are loaded correctly"""
        # create the preferences window
        w = prefs.GuiRcParamsWidget()
        w.initialize()
        items = list(w.tree.top_level_items)
        self.assertEqual(len(items), len(gui_rcParams))
        # test keys
        keys = set(gui_rcParams)
        for item in items:
            keys.remove(asstring(item.text(0)))
        self.assertFalse(keys)

        # test values
        for item in items:
            key = asstring(item.text(0))
            s_val = asstring(w.tree.itemWidget(item.child(0), 2).toPlainText())
            val = yaml.load(s_val, Loader=yaml.Loader)
            self.assertEqual(
                val, gui_rcParams[key], msg="Failed item %s: %s" % (key, s_val)
            )

    def test_changing(self):
        """Test whether the changes are displayed correctly"""
        w = prefs.GuiRcParamsWidget()
        gui_rcParams["console.auto_set_mp"] = True
        w.initialize()
        items = list(w.tree.top_level_items)
        for item in items:
            if item.text(0) == "console.auto_set_mp":
                iw = w.tree.itemWidget(item.child(0), 2)
                iw.setPlainText("f")
        QTest.mouseClick(w.bt_select_changed, Qt.LeftButton)
        selected_rc = dict(w.tree.selected_rc())
        self.assertEqual(len(selected_rc), 1, msg=selected_rc)
        self.assertIn("console.auto_set_mp", selected_rc)
        self.assertEqual(selected_rc["console.auto_set_mp"], False)

        for item in items:
            if item.text(0) == "console.auto_set_mp":
                iw = w.tree.itemWidget(item.child(0), 2)
                iw.setPlainText("t")

        QTest.mouseClick(w.bt_select_none, Qt.LeftButton)
        self.assertFalse(dict(w.tree.selected_rc()))

        QTest.mouseClick(w.bt_select_changed, Qt.LeftButton)
        self.assertFalse(w.tree.selectedItems())

    def test_validation(self):
        """Test whether the validation works correctly"""
        self.window.showMaximized()
        w = prefs.GuiRcParamsWidget()
        w.initialize()

        # choose an item
        for i, item in enumerate(w.tree.top_level_items):
            if asstring(item.text(0)) == "console.auto_set_mp":
                break

        self.assertTrue(w.is_valid, msg=w.tree.valid)
        # set an invalid value
        w.tree.itemWidget(item.child(0), 2).setPlainText("tg")
        self.assertFalse(w.tree.valid[i])
        self.assertFalse(w.is_valid)
        w.tree.itemWidget(item.child(0), 2).setPlainText("t")
        self.assertTrue(w.tree.valid[i])
        self.assertTrue(w.is_valid)

        # set a value that cannot be loaded by yaml
        w.tree.itemWidget(item.child(0), 2).setPlainText('"t')
        self.assertFalse(w.tree.valid[i])
        self.assertFalse(w.is_valid)

    def test_save_01_all(self):
        """Test saving the rcParams"""
        w = prefs.GuiRcParamsWidget()
        w.initialize()

        QTest.mouseClick(w.bt_select_all, Qt.LeftButton)
        self.assertEqual(len(w.tree.selectedItems()), len(gui_rcParams))

        fname = tempfile.NamedTemporaryFile(
            prefix="psyplot_gui_test", suffix=".yml"
        ).name
        self._created_files.add(fname)
        action = w.save_settings_action(target=fname)
        action.trigger()
        self.assertTrue(osp.exists(fname))
        rc = GuiRcParams(defaultParams=gui_rcParams.defaultParams)
        rc.load_from_file(fname)

        self.assertEqual(rc, gui_rcParams)

    def test_save_02_some(self):
        """Test saving some parts the rcParams"""
        w = prefs.GuiRcParamsWidget()
        w.initialize()

        keys = []

        for item in islice(w.tree.top_level_items, 0, None, 2):
            item.setSelected(True)
            keys.append(asstring(item.text(0)))

        self.assertEqual(len(w.tree.selectedItems()), len(keys))

        fname = tempfile.NamedTemporaryFile(
            prefix="psyplot_gui_test", suffix=".yml"
        ).name
        self._created_files.add(fname)
        action = w.save_settings_action(target=fname)
        action.trigger()
        self.assertTrue(osp.exists(fname))
        rc = GuiRcParams(defaultParams=gui_rcParams.defaultParams)
        rc.load_from_file(fname)

        self.assertEqual(dict(rc), {key: gui_rcParams[key] for key in keys})

    def test_update(self):
        """Test updating the rcParams"""
        w = prefs.GuiRcParamsWidget()
        w.initialize()

        fname = tempfile.NamedTemporaryFile(
            prefix="psyplot_gui_test", suffix=".yml"
        ).name
        self._created_files.add(fname)
        gui_rcParams.find_all("console").dump(fname)

        keys = []

        for item in w.tree.top_level_items:
            if asstring(item.text(0)).startswith("help_explorer"):
                item.setSelected(True)
                keys.append(asstring(item.text(0)))

        self.assertEqual(len(w.tree.selectedItems()), len(keys))

        action = w.save_settings_action(update=True, target=fname)
        action.trigger()
        self.assertTrue(osp.exists(fname))
        rc = GuiRcParams(defaultParams=gui_rcParams.defaultParams)
        rc.load_from_file(fname)

        self.assertEqual(
            dict(rc),
            {
                key: gui_rcParams[key]
                for key in gui_rcParams
                if key.startswith("console") or key.startswith("help_explorer")
            },
        )


class TestPreferences(bt.PsyPlotGuiTestCase):
    """Test the :class:`psyplot_gui.preferences.Preferences` widget"""

    def setUp(self):
        super(TestPreferences, self).setUp()
        self.window.edit_preferences()
        self.prefs = self.window.preferences

    def tearDown(self):
        # make sure the preferences widget is closed completely
        self.prefs.close()
        del self.prefs
        super(TestPreferences, self).tearDown()

    def test_pages(self):
        """Test whether all pages are loaded"""
        pref_w = self.prefs
        pages = list(pref_w.pages)
        self.assertTrue(pages)
        self.assertTrue(
            any(isinstance(p, prefs.GuiRcParamsWidget) for p in pages),
            msg=pages,
        )
        self.assertTrue(
            any(isinstance(p, prefs.PsyRcParamsWidget) for p in pages),
            msg=pages,
        )

    def test_apply(self):
        """Test the apply button"""
        pref_w = self.prefs
        i, cp = next(
            t
            for t in enumerate(pref_w.pages)
            if isinstance(t[1], prefs.GuiRcParamsWidget)
        )
        pref_w.set_current_index(i)
        self.assertIsInstance(pref_w.get_page(), prefs.GuiRcParamsWidget)
        self.assertFalse(pref_w.bt_apply.isEnabled())

        # change a value
        current = gui_rcParams["console.auto_set_mp"]
        for item in cp.tree.top_level_items:
            if item.text(0) == "console.auto_set_mp":
                break
        cp.tree.itemWidget(item.child(0), 2).setPlainText(
            yaml.dump(not current)
        )
        self.assertTrue(pref_w.bt_apply.isEnabled())

        QTest.mouseClick(pref_w.bt_apply, Qt.LeftButton)
        self.assertEqual(gui_rcParams["console.auto_set_mp"], not current)
        self.assertFalse(pref_w.bt_apply.isEnabled())

        # change the value and the page
        cp.tree.itemWidget(item.child(0), 2).setPlainText(yaml.dump(current))
        self.assertTrue(pref_w.bt_apply.isEnabled())
        j, cp2 = next(
            t
            for t in enumerate(pref_w.pages)
            if isinstance(t[1], prefs.PsyRcParamsWidget)
        )
        pref_w.set_current_index(j)
        self.assertIsInstance(pref_w.get_page(), prefs.PsyRcParamsWidget)
        self.assertFalse(pref_w.bt_apply.isEnabled())
        pref_w.set_current_index(i)
        self.assertTrue(pref_w.bt_apply.isEnabled())

    def test_ok(self):
        """Test the apply button"""
        pref_w = self.prefs
        i, cp = next(
            t
            for t in enumerate(pref_w.pages)
            if isinstance(t[1], prefs.GuiRcParamsWidget)
        )
        pref_w.set_current_index(i)
        self.assertIsInstance(pref_w.get_page(), prefs.GuiRcParamsWidget)
        self.assertFalse(pref_w.bt_apply.isEnabled())

        # change a value
        current = gui_rcParams["console.auto_set_mp"]
        for item in cp.tree.top_level_items:
            if item.text(0) == "console.auto_set_mp":
                break
        cp.tree.itemWidget(item.child(0), 2).setPlainText(
            yaml.dump(not current)
        )
        self.assertTrue(pref_w.bt_apply.isEnabled())

        # change a value in the PsyRcParamsWidget
        i, cp = next(
            t
            for t in enumerate(pref_w.pages)
            if isinstance(t[1], prefs.PsyRcParamsWidget)
        )
        pref_w.set_current_index(i)
        self.assertIsInstance(pref_w.get_page(), prefs.PsyRcParamsWidget)
        self.assertFalse(pref_w.bt_apply.isEnabled())

        # change a value
        for item in cp.tree.top_level_items:
            if item.text(0) == "decoder.x":
                break
        cp.tree.itemWidget(item.child(0), 2).setPlainText(yaml.dump({"test"}))
        self.assertTrue(pref_w.bt_apply.isEnabled())

        QTest.mouseClick(
            pref_w.bbox.button(QDialogButtonBox.Ok), Qt.LeftButton
        )
        self.assertEqual(gui_rcParams["console.auto_set_mp"], not current)
        self.assertEqual(psy_rcParams["decoder.x"], {"test"})

    def test_plugin_pages(self):
        try:
            from psyplot_gui_test.plugin import rcParams
        except ImportError:
            self.skipTest("psyplot_gui_test not installed")
        pref_w = self.prefs
        QTest.mouseClick(pref_w.bt_load_plugins, Qt.LeftButton)
        i, cp = next(
            t
            for t in enumerate(pref_w.pages)
            if isinstance(t[1], prefs.RcParamsWidget)
            and not isinstance(t[1], prefs.PsyRcParamsWidget)
            and "test_plugin"
            in (item.text(0) for item in t[1].tree.top_level_items)
        )
        pref_w.set_current_index(i)
        self.assertEqual(
            len(list(cp.tree.top_level_items)), len(rcParams), msg=cp
        )


if __name__ == "__main__":
    unittest.main()
