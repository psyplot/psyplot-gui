# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

import os.path as osp
import unittest

# -*- coding: utf-8 -*-
from collections import defaultdict

import _base_testing as bt
import psyplot.data as psyd
import psyplot.project as psy
import xarray as xr

from psyplot_gui.compat.qtcompat import QDialogButtonBox, Qt, QTest, asstring


class ProjectContentTest(bt.PsyPlotGuiTestCase):
    """Test case for testing whether the project content part is updated
    correctly"""

    @property
    def project_content(self):
        return self.window.project_content

    @property
    def content_widget(self):
        return self.project_content.content_widget

    def get_list(self, key):
        return self.content_widget.lists[key]

    def _selected_rows(self, name):
        return list(
            map(lambda ind: ind.row(), self.get_list(name).selectedIndexes())
        )

    def test_content_update(self):
        """Test whether the list is updated correctly"""
        w = self.content_widget
        lists = w.lists
        # currently it should be empty
        self.assertEqual(w.count(), 1)
        self.assertEqual(w.indexOf(lists["All"]), 0)
        self.assertFalse(w.isItemEnabled(0), msg='List "All" is enabled!')

        # create some plots
        sp = psy.plot.plot2d(self.get_file("test-t2m-u-v.nc"), name="t2m")
        sp2 = psy.plot.lineplot(
            self.get_file("test-t2m-u-v.nc"), name="t2m", t=0, x=0, y=0
        )
        d = defaultdict(lambda: 1)
        d["All"] = 2
        d["simple"] = 2
        for name in ["All", "simple", "lineplot", "plot2d"]:
            self.assertIn(name, lists)
            arrays = lists[name]
            i = self.content_widget.indexOf(arrays)
            self.assertNotEqual(i, -1, msg="Missing the list in the widget!")
            self.assertTrue(
                self.content_widget.isItemEnabled(i),
                msg="%s is not enabled!" % name,
            )
            self.assertEqual(
                arrays.count(),
                d[name],
                msg="Wrong number of arrays in %s" % name,
            )
            if name == "plot2d":
                self.assertEqual(
                    asstring(arrays.item(0).text()),
                    sp[0].psy._short_info(),
                    msg="Wrong text in plot2d",
                )
            else:
                self.assertEqual(
                    asstring(arrays.item(d[name] - 1).text()),
                    sp2[0]._short_info(),
                    msg="Wrong text in %s" % name,
                )
        self.assertEqual(
            self._selected_rows("plot2d"),
            [],
            msg="Array in %s is wrongly selected!" % name,
        )
        self.assertEqual(
            self._selected_rows("lineplot"),
            [0],
            msg="Array in %s is not selected!" % name,
        )
        self.assertEqual(
            self._selected_rows("simple"), [1], msg="Wrong selection!"
        )
        self.assertEqual(
            self._selected_rows("All"), [1], msg="Wrong selection!"
        )

        # close the project
        full = sp + sp2
        full.close(True, True, True)
        self.assertEqual(w.count(), 1)
        self.assertEqual(w.indexOf(lists["All"]), 0)
        self.assertFalse(w.isItemEnabled(0), msg='List "All" is enabled!')

    def test_select_all_button(self):
        """Test whether the subproject is changed correctly when selecting all"""
        self.window.showMaximized()
        sp = psy.plot.plot2d(
            self.get_file("test-t2m-u-v.nc"), name="t2m", time=[0, 1]
        )
        psy.scp(None)
        QTest.mouseClick(self.project_content.select_all_button, Qt.LeftButton)
        self.assertIs(
            psy.gcp()[0],
            sp[0],
            msg="actual: %s, expected: %s" % (psy.gcp(), sp),
        )
        self.assertIs(psy.gcp()[1], sp[1])
        self.assertEqual(
            self._selected_rows("All"), [0, 1], msg="Not all arrays selected!"
        )

    def test_unselect_all_button(self):
        """Test whether the subproject is changed cleared when unselecting all"""
        self.window.showMaximized()
        psy.plot.plot2d(
            self.get_file("test-t2m-u-v.nc"), name="t2m", time=[0, 1]
        )
        # test whether the current subproject is not empty
        self.assertTrue(bool(psy.gcp()))
        # unselect all
        QTest.mouseClick(self.project_content.unselect_button, Qt.LeftButton)
        self.assertFalse(bool(psy.gcp()))

    def test_item_selection(self):
        """Test whether the subproject is changed correctly if the selection in
        the list changes"""
        sp = psy.plot.plot2d(
            self.get_file("test-t2m-u-v.nc"), name="t2m", time=[0, 1]
        )
        self.assertIs(psy.gcp()[0], sp[0])
        self.assertIs(psy.gcp()[1], sp[1])
        self.content_widget.lists["All"].item(0).setSelected(False)
        self.assertIs(psy.gcp()[0], sp[1])
        self.content_widget.lists["All"].item(0).setSelected(True)
        self.assertIs(psy.gcp()[0], sp[0], msg="Reselection failed!")
        self.assertIs(psy.gcp()[1], sp[1], msg="Reselection failed!")


class FiguresTreeTest(bt.PsyPlotGuiTestCase):
    """Test to check whether the figures tree behaves correctly"""

    @property
    def tree(self):
        return self.window.figures_tree

    def test_toplevel(self):
        """Test whether the figures are updated correctly"""

        def check_figs(msg=None):
            figs = iter(sp.figs)
            for item in map(
                self.tree.topLevelItem, range(self.tree.topLevelItemCount())
            ):
                self.assertEqual(
                    asstring(item.text(0)),
                    next(figs).canvas.manager.get_window_title(),
                    msg=msg,
                )

        sp = psy.plot.plot2d(
            self.get_file("test-t2m-u-v.nc"), name="t2m", time=[0, 1]
        )
        check_figs()
        sp[1:].close(True, True)
        check_figs("Figures not updated correctly!")

    def test_sublevel(self):
        """Test whether the arrays are updated correctly"""

        def check_figs(msg=None):
            arrays = iter(sp)
            for i, (fig, val) in enumerate(sp.figs.items()):
                top = self.tree.topLevelItem(i)
                self.assertEqual(
                    asstring(top.text(0)),
                    fig.canvas.manager.get_window_title(),
                )
                for child in map(top.child, range(top.childCount())):
                    self.assertEqual(
                        asstring(child.text(0)),
                        next(arrays).psy._short_info(),
                        msg=msg,
                    )

        sp = psy.plot.plot2d(
            self.get_file("test-t2m-u-v.nc"),
            name="t2m",
            time=[0, 1, 2],
            ax=(1, 2),
        )
        check_figs()
        sp[1:2].close(False, True)
        sp = sp[0::2]
        check_figs("Arrays not updated correctly!")
        sp.close(True, True)
        self.assertEqual(self.tree.topLevelItemCount(), 0)


class DatasetTreeTest(bt.PsyPlotGuiTestCase):
    """Test to check whether the dataset tree behaves correctly"""

    @property
    def tree(self):
        return self.window.ds_tree

    def test_toplevel(self):
        """Test whether the toplevel items are shown correctly"""
        fname = self.get_file("test-t2m-u-v.nc")
        sp1 = psy.plot.plot2d(fname, name="t2m")
        sp2 = psy.plot.plot2d(fname, name="t2m")
        count = next(psyd._ds_counter) - 1
        fname = osp.basename(fname)
        ds1 = sp1[0].psy.base
        ds2 = sp2[0].psy.base

        self.assertEqual(self.tree.topLevelItemCount(), 2)
        self.assertEqual(
            asstring(self._get_toplevel_item(ds1).text(0)),
            "%i: %s" % (count - 1, fname),
        )
        self.assertEqual(
            asstring(self._get_toplevel_item(ds2).text(0)),
            "*%i: %s" % (count, fname),
        )
        psy.scp(sp1)
        self.assertEqual(
            asstring(self._get_toplevel_item(ds1).text(0)),
            "*%i: %s" % (count - 1, fname),
        )
        self.assertEqual(
            asstring(self._get_toplevel_item(ds2).text(0)),
            "%i: %s" % (count, fname),
        )
        sp2.close(True, True)
        self.assertEqual(
            asstring(self._get_toplevel_item(ds1).text(0)),
            "*%i: %s" % (count - 1, fname),
        )
        self.assertEqual(self.tree.topLevelItemCount(), 1)

    def _get_toplevel_item(self, ds):
        toplevel = None
        for item in map(
            self.tree.topLevelItem, range(self.tree.topLevelItemCount())
        ):
            if item.ds() is ds:
                toplevel = item
                break
        self.assertIsNotNone(
            toplevel, msg="No item found that corresponds to %s" % ds
        )
        return toplevel

    def _test_ds_representation(self, ds):
        toplevel = self._get_toplevel_item(ds)
        coords = set(ds.coords)
        variables = set(ds.variables) - coords
        for child in map(
            toplevel.variables.child, range(toplevel.variables.childCount())
        ):
            variables.remove(asstring(child.text(0)))
        self.assertEqual(
            len(variables), 0, msg="Variables not found: %s" % (variables)
        )
        for child in map(
            toplevel.coords.child, range(toplevel.coords.childCount())
        ):
            coords.remove(asstring(child.text(0)))
        self.assertEqual(
            len(coords), 0, msg="Coordinates not found: %s" % (coords)
        )

    def test_sublevel(self):
        """Test whether the variables and coordinates are displayed correctly"""
        sp = psy.plot.plot2d(self.get_file("test-t2m-u-v.nc"), name="t2m")
        ds = sp[0].psy.base
        self._test_ds_representation(ds)

    def test_refresh(self):
        """Test the refreshing of a dataset"""
        fname = self.get_file("test-t2m-u-v.nc")
        sp1 = psy.plot.plot2d(fname, name="t2m")
        sp2 = psy.plot.plot2d(fname, name="t2m")
        ds = sp1[0].psy.base
        ds["test"] = xr.Variable(("testdim",), list(range(5)))
        item = self.tree.topLevelItem(0)
        self.tree.refresh_items(item)
        self._test_ds_representation(ds)
        self._test_ds_representation(sp2[0].psy.base)

    def test_refresh_all(self):
        """Test the refreshing of a dataset"""
        fname = self.get_file("test-t2m-u-v.nc")
        sp1 = psy.plot.plot2d(fname, name="t2m")
        sp2 = psy.plot.plot2d(fname, name="t2m")
        ds = sp1[0].psy.base
        ds["test"] = xr.Variable(("testdim",), list(range(5)))
        ds2 = sp2[0].psy.base
        ds2["test2"] = list(range(10))
        self.tree.refresh_items()
        self._test_ds_representation(ds)
        self._test_ds_representation(ds2)

    def test_expansion_reset(self):
        """Test whether the expansion state is recovered"""
        fname = self.get_file("test-t2m-u-v.nc")
        psy.plot.plot2d(fname, name="t2m")
        self.tree.expandItem(self.tree.topLevelItem(0))
        self.tree.expandItem(self.tree.topLevelItem(0).child(1))

        # trigger an update
        psy.plot.plot2d(fname, name="t2m")
        self.assertTrue(self.tree.topLevelItem(0).isExpanded())
        self.assertFalse(self.tree.topLevelItem(0).child(0).isExpanded())
        self.assertTrue(self.tree.topLevelItem(0).child(1).isExpanded())
        self.assertFalse(self.tree.topLevelItem(0).child(2).isExpanded())

    def test_make_plot(self):
        """Test the making of plots"""
        fname = self.get_file("test-t2m-u-v.nc")
        sp1 = psy.plot.plot2d(fname, name="t2m")
        # to make sure, have in the mean time another dataset in the current
        # subproject, we create a second plot
        psy.plot.plot2d(fname, name="t2m")
        ds = sp1[0].psy.base
        name = "t2m"
        self.tree.make_plot(ds, name)
        try:
            self.window.plot_creator.pm_combo.setCurrentText("plot2d")
        except AttributeError:
            self.window.plot_creator.pm_combo.setEditText("plot2d")
        QTest.mouseClick(
            self.window.plot_creator.bbox.button(QDialogButtonBox.Ok),
            Qt.LeftButton,
        )
        self.assertIs(ds, psy.gcp()[0].psy.base)


if __name__ == "__main__":
    unittest.main()
