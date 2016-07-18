# -*- coding: utf-8 -*-
from collections import defaultdict
import os.path as osp
import unittest
import _base_testing as bt
import xarray as xr
import psyplot.data as psyd
import psyplot.project as psy
from psyplot_gui.compat.qtcompat import QTest, Qt


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
        return self.project_content.content_widget.lists[key]

    def _selected_rows(self, name):
        return list(map(lambda ind: ind.row(),
                        self.get_list(name).selectedIndexes()))

    def test_content_update(self):
        """Test whether the list is updated correctly"""
        sp = psy.plot.mapplot(self.get_file('test-t2m-u-v.nc'), name='t2m')
        sp2 = psy.plot.lineplot(self.get_file('test-t2m-u-v.nc'), name='t2m',
                                t=0, x=0, y=0)
        d = defaultdict(lambda: 1)
        d['All'] = 2
        for name in ['All', 'mapplot', 'maps', 'simple', 'lineplot']:
            l = self.get_list(name)
            i = self.content_widget.indexOf(l)
            self.assertTrue(self.content_widget.isItemEnabled(i),
                            msg='%s is not enabled!' % name)
            self.assertEqual(l.count(), d[name],
                             msg='Wrong number of arrays in %s' % name)
            if name in ['All', 'maps', 'mapplot']:
                self.assertEqual(l.item(0).text(), sp[0]._short_info(),
                                 msg='Wrong text in %s' % name)
            if name in ['All', 'simple', 'lineplot']:
                self.assertEqual(
                    l.item(d[name] - 1).text(), sp2[0]._short_info(),
                    msg='Wrong text in %s' % name)
        for name in ['maps', 'mapplot']:
            self.assertEqual(self._selected_rows(name), [],
                             msg='Array in %s is wrongly selected!' % name)
        for name in ['simple', 'lineplot']:
            self.assertEqual(self._selected_rows(name), [0],
                             msg='Array in %s is not selected!' % name)
        self.assertEqual(self._selected_rows('All'), [1],
                         msg='Wrong selection!')

    def test_select_all_button(self):
        """Test whether the subproject is changed correctly when selecting all
        """
        sp = psy.plot.mapplot(self.get_file('test-t2m-u-v.nc'), name='t2m',
                              time=[0, 1])
        psy.scp(None)
        QTest.mouseClick(self.project_content.select_all_button, Qt.LeftButton)
        self.assertIs(psy.gcp()[0], sp[0])
        self.assertIs(psy.gcp()[1], sp[1])
        self.assertEqual(self._selected_rows('All'), [0, 1],
                         msg='Not all arrays selected!')

    def test_unselect_all_button(self):
        """Test whether the subproject is changed cleared when unselecting all
        """
        psy.plot.mapplot(self.get_file('test-t2m-u-v.nc'), name='t2m',
                         time=[0, 1])
        # test whether the current subproject is not empty
        self.assertTrue(bool(psy.gcp()))
        # unselect all
        QTest.mouseClick(self.project_content.unselect_button, Qt.LeftButton)
        self.assertFalse(bool(psy.gcp()))

    def test_item_selection(self):
        """Test whether the subproject is changed correctly if the selection in
        the list changes"""
        sp = psy.plot.mapplot(self.get_file('test-t2m-u-v.nc'), name='t2m',
                              time=[0, 1])
        self.assertIs(psy.gcp()[0], sp[0])
        self.assertIs(psy.gcp()[1], sp[1])
        self.content_widget.lists['All'].item(0).setSelected(False)
        self.assertIs(psy.gcp()[0], sp[1])
        self.content_widget.lists['All'].item(0).setSelected(True)
        self.assertIs(psy.gcp()[0], sp[0], msg='Reselection failed!')
        self.assertIs(psy.gcp()[1], sp[1], msg='Reselection failed!')


class FiguresTreeTest(bt.PsyPlotGuiTestCase):
    """Test to check whether the figures tree behaves correctly"""

    @property
    def tree(self):
        return self.window.figures_tree

    def test_toplevel(self):
        """Test whether the figures are updated correctly"""
        def check_figs(msg=None):
            figs = iter(sp.figs)
            for item in map(self.tree.topLevelItem,
                            range(self.tree.topLevelItemCount())):
                self.assertEqual(item.text(0),
                                 next(figs).canvas.get_window_title(), msg=msg)
        sp = psy.plot.mapplot(self.get_file('test-t2m-u-v.nc'), name='t2m',
                              time=[0, 1])
        check_figs()
        sp[1:].close(True, True)
        check_figs('Figures not updated correctly!')

    def test_sublevel(self):
        """Test whether the arrays are updated correctly"""
        def check_figs(msg=None):
            arrays = iter(sp)
            for i, (fig, val) in enumerate(sp.figs.items()):
                top = self.tree.topLevelItem(i)
                self.assertEqual(top.text(0),
                                 fig.canvas.get_window_title())
                for child in map(top.child, range(top.childCount())):
                    self.assertEqual(child.text(0), next(arrays)._short_info(),
                                     msg=msg)
        sp = psy.plot.mapplot(self.get_file('test-t2m-u-v.nc'), name='t2m',
                              time=[0, 1, 2], ax=(1, 2))
        check_figs()
        sp[1:2].close(False, True)
        sp = sp[0::2]
        check_figs('Arrays not updated correctly!')
        sp.close(True, True)
        self.assertEqual(self.tree.topLevelItemCount(), 0)


class DatasetTreeTest(bt.PsyPlotGuiTestCase):
    """Test to check whether the dataset tree behaves correctly"""

    @property
    def tree(self):
        return self.window.ds_tree

    def test_toplevel(self):
        """Test whether the toplevel items are shown correctly"""
        fname = self.get_file('test-t2m-u-v.nc')
        sp1 = psy.plot.mapplot(fname, name='t2m')
        sp2 = psy.plot.mapplot(fname, name='t2m')
        count = next(psyd._ds_counter) - 1
        fname = osp.basename(fname)
        ds1 = sp1[0].base
        ds2 = sp2[0].base

        self.assertEqual(self.tree.topLevelItemCount(), 2)
        self.assertEqual(self._get_toplevel_item(ds1).text(0), '%i: %s' % (
                             count - 1, fname))
        self.assertEqual(self._get_toplevel_item(ds2).text(0), '*%i: %s' % (
                             count, fname))
        psy.scp(sp1)
        self.assertEqual(self._get_toplevel_item(ds1).text(0), '*%i: %s' % (
                             count - 1, fname))
        self.assertEqual(self._get_toplevel_item(ds2).text(0), '%i: %s' % (
                             count, fname))
        sp2.close(True, True)
        self.assertEqual(self._get_toplevel_item(ds1).text(0), '*%i: %s' % (
                             count - 1, fname))
        self.assertEqual(self.tree.topLevelItemCount(), 1)

    def _get_toplevel_item(self, ds):
        toplevel = None
        for item in map(self.tree.topLevelItem,
                        range(self.tree.topLevelItemCount())):
            if item.ds() is ds:
                toplevel = item
                break
        self.assertIsNotNone(
            toplevel, msg='No item found that corresponds to %s' % ds)
        return toplevel

    def _test_ds_representation(self, ds):
        toplevel = self._get_toplevel_item(ds)
        coords = set(ds.coords)
        variables = set(ds.variables) - coords
        for child in map(toplevel.variables.child,
                         range(toplevel.variables.childCount())):
            variables.remove(child.text(0))
        self.assertEqual(len(variables), 0, msg='Variables not found: %s' % (
            variables))
        for child in map(toplevel.coords.child,
                         range(toplevel.coords.childCount())):
            coords.remove(child.text(0))
        self.assertEqual(len(coords), 0, msg='Coordinates not found: %s' % (
            coords))

    def test_sublevel(self):
        """Test whether the variables and coordinates are displayed correctly
        """
        sp = psy.plot.mapplot(self.get_file('test-t2m-u-v.nc'), name='t2m')
        ds = sp[0].base
        self._test_ds_representation(ds)

    def test_refresh(self):
        """Test the refreshing of a dataset"""
        fname = self.get_file('test-t2m-u-v.nc')
        sp1 = psy.plot.mapplot(fname, name='t2m')
        sp2 = psy.plot.mapplot(fname, name='t2m')
        ds = sp1[0].base
        ds['test'] = xr.Variable(('testdim', ), list(range(5)))
        item = self.tree.topLevelItem(0)
        self.tree.refresh_items(item)
        self._test_ds_representation(ds)
        self._test_ds_representation(sp2[0].base)

    def test_refresh_all(self):
        """Test the refreshing of a dataset"""
        fname = self.get_file('test-t2m-u-v.nc')
        sp1 = psy.plot.mapplot(fname, name='t2m')
        sp2 = psy.plot.mapplot(fname, name='t2m')
        ds = sp1[0].base
        ds['test'] = xr.Variable(('testdim', ), list(range(5)))
        ds2 = sp2[0].base
        ds2['test2'] = list(range(10))
        self.tree.refresh_items()
        self._test_ds_representation(ds)
        self._test_ds_representation(ds2)

    def test_make_plot(self):
        """Test the making of plots"""
        fname = self.get_file('test-t2m-u-v.nc')
        sp1 = psy.plot.mapplot(fname, name='t2m')
        # to make sure, have in the mean time another dataset in the current
        # subproject, we create a second plot
        psy.plot.mapplot(fname, name='t2m')
        ds = sp1[0].base
        name = 't2m'
        self.tree.make_plot(ds, name)
        try:
            self.window.plot_creator.pm_combo.setCurrentText('mapplot')
        except AttributeError:
            self.window.plot_creator.pm_combo.setEditText('mapplot')
        QTest.mouseClick(self.window.plot_creator.bt_create, Qt.LeftButton)
        self.assertIs(ds, psy.gcp()[0].base)


if __name__ == '__main__':
    unittest.main()
