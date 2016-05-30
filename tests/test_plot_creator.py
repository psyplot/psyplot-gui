# -*- coding: utf-8 -*-
"""Skript to test the InProcessShell that is used in the psyplot gui"""
import unittest
from itertools import chain, cycle
import _base_testing as bt
import psyplot.project as psy
from psyplot.compat.pycompat import range
from psyplot_gui.compat.qtcompat import QTest, Qt


class PlotCreatorTest(bt.PsyPlotGuiTestCase):
    """Tests concerning the plot creator"""

    def setUp(self):
        super(PlotCreatorTest, self).setUp()
        self.window.new_plots()
        self.pc = self.window.plot_creator

    def tearDown(self):
        if getattr(self.pc, 'ds', None) is not None:
            self.pc.ds.close()
        super(PlotCreatorTest, self).tearDown()

    def test_load_external_file(self):
        """Test whether an external netCDF file can be loaded"""
        fname = self.get_file('test-t2m-u-v.nc')
        self.pc.open_dataset([fname])
        vtab = self.pc.variables_table
        ds = psy.open_dataset(fname)
        self.assertRegexpMatches(self.pc.ds_combo.currentText(),
                                 '.*:\s*%s' % fname)
        self.assertEqual(
            {vtab.item(irow, 0).text() for irow in range(vtab.rowCount())},
            set(ds.variables) - set(ds.coords))
        ds.close()

    def test_load_from_console(self):
        """Test whether a dataset can be loaded that is defined in the
        console"""
        self.window.console.execute(
            "ds = psy.open_dataset('%s')" % self.get_file('test-t2m-u-v.nc'))
        vtab = self.pc.variables_table
        ds = psy.open_dataset(self.get_file('test-t2m-u-v.nc'))
        self.pc.get_ds_from_shell('ds')
        self.assertRegexpMatches(self.pc.ds_combo.currentText(),
                                 '.*:\s*ds')
        self.assertEqual(
            {vtab.item(irow, 0).text() for irow in range(vtab.rowCount())},
            set(ds.variables) - set(ds.coords))
        ds.close()

    def test_plusplus(self):
        """Test the add all button"""
        # loag a dataset
        self.test_load_external_file()
        QTest.mouseClick(self.pc.bt_add_all, Qt.LeftButton)
        atab = self.pc.array_table
        vtab = self.pc.variables_table
        self.assertEqual(
            [atab.item(irow, 0).text() for irow in range(atab.rowCount())],
            [vtab.item(irow, 0).text() for irow in range(vtab.rowCount())])

    def test_minusminus(self):
        """Test the remove all button"""
        self.test_plusplus()
        QTest.mouseClick(self.pc.bt_remove_all, Qt.LeftButton)
        self.assertEqual(self.pc.array_table.rowCount(), 0)

    def test_plus(self):
        """Test the add button"""
        self.test_load_external_file()
        vtab = self.pc.variables_table
        atab = self.pc.array_table
        nvar = vtab.rowCount()
        rows = [nvar - 2, nvar - 1]
        for row in rows:
            vtab.item(row, 0).setSelected(True)
        QTest.mouseClick(self.pc.bt_add, Qt.LeftButton)
        self.assertEqual(
            [atab.item(irow, 0).text() for irow in range(atab.rowCount())],
            [vtab.item(irow, 0).text() for irow in rows])

    def test_minus(self):
        """Test the minus button"""
        self.test_plusplus()
        vtab = self.pc.variables_table
        atab = self.pc.array_table
        nvar = atab.rowCount()
        rows = [nvar - 2, nvar - 1]
        for row in rows:
            atab.item(row, 0).setSelected(True)
        QTest.mouseClick(self.pc.bt_remove, Qt.LeftButton)
        variables = [vtab.item(row, 0).text() for row in range(vtab.rowCount())
                     if row not in rows]
        self.assertEqual(
            [atab.item(irow, 0).text() for irow in range(atab.rowCount())],
            variables)

    def test_add_subplots(self):
        """Test the add subplots button"""
        from math import ceil
        import matplotlib.pyplot as plt
        self.test_load_external_file()
        self.test_plusplus()
        self.pc.cols_axis_edit.setText('2')
        self.pc.rows_axis_edit.setText('2')
        self.pc.max_axis_edit.setText('3')
        QTest.mouseClick(self.pc.bt_add_axes, Qt.LeftButton)
        nvar = self.pc.array_table.rowCount()
        nfigs = int(ceil(nvar / 3.))
        # create the subplots
        axes = self.pc.array_table.axes
        self.assertEqual([ax.numCols for ax in axes], [2] * nvar)
        self.assertEqual([ax.numRows for ax in axes], [2] * nvar)
        rows = [0, 0, 1] * nfigs
        cols = [0, 1, 0] * nfigs
        self.assertEqual([ax.rowNum for ax in axes], rows)
        self.assertEqual([ax.colNum for ax in axes], cols)
        fig_nums = list(chain(*([i] * 3 for i in range(1, nfigs + 1))))
        self.assertEqual([ax.get_figure().number for ax in axes], fig_nums)
        plt.close('all')

    def test_add_single_subplots(self):
        """Test the add single subplot button"""
        import matplotlib.pyplot as plt
        self.test_load_external_file()
        self.test_plusplus()
        self.pc.cols_axis_edit.setText('2')
        self.pc.rows_axis_edit.setText('2')
        self.pc.row_axis_edit.setText('1')
        self.pc.col_axis_edit.setText('2')
        self.pc.array_table.selectAll()
        QTest.mouseClick(self.pc.bt_add_single_axes, Qt.LeftButton)
        nvar = self.pc.array_table.rowCount()
        # create the subplots
        axes = self.pc.array_table.axes
        # test rows, cols and figure numbers
        self.assertEqual([ax.numCols for ax in axes], [2] * nvar)
        self.assertEqual([ax.numRows for ax in axes], [2] * nvar)
        self.assertEqual([ax.rowNum for ax in axes], [0] * nvar)
        self.assertEqual([ax.colNum for ax in axes], [1] * nvar)
        self.assertEqual([ax.get_figure().number for ax in axes], list(
            range(1, nvar + 1)))
        plt.close('all')

    def test_axescreator_subplots(self):
        """Test the :class:`psyplot_gui.plot_creator.SubplotCreator`"""
        import matplotlib.pyplot as plt
        from psyplot_gui.plot_creator import AxesCreatorCollection
        # load dataset
        self.test_load_external_file()
        # create arrays
        self.test_plusplus()
        # use all items
        atab = self.pc.array_table
        items = [atab.item(i, atab.axes_col) for i in range(atab.rowCount())]
        # create the widget to select the subplots
        ac = AxesCreatorCollection('subplot')
        w = ac.tb.currentWidget()
        w.fig_edit.setText('')
        w.cols_edit.setText('2')
        w.rows_edit.setText('2')
        w.num1_edit.setText('2')
        w.num2_edit.setText('2')
        ac.okpressed.connect(lambda it: atab._change_axes(items, it))
        QTest.mouseClick(ac.bt_ok, Qt.LeftButton)
        nvar = self.pc.array_table.rowCount()
        # create the subplots
        axes = self.pc.array_table.axes
        # test rows, cols and figure numbers
        self.assertEqual([ax.numCols for ax in axes], [2] * nvar)
        self.assertEqual([ax.numRows for ax in axes], [2] * nvar)
        self.assertEqual([ax.rowNum for ax in axes], [0] * nvar)
        self.assertEqual([ax.colNum for ax in axes], [1] * nvar)
        self.assertEqual([ax.get_figure().number for ax in axes], list(
            range(1, nvar + 1)))
        # close figures
        plt.close('all')

    def test_axescreator_axes(self):
        """Test the :class:`psyplot_gui.plot_creator.AxesCreator`"""
        import matplotlib.pyplot as plt
        from psyplot_gui.plot_creator import AxesCreatorCollection
        # load dataset
        self.test_load_external_file()
        # create arrays
        self.test_plusplus()
        # use all items
        atab = self.pc.array_table
        items = [atab.item(i, atab.axes_col) for i in range(atab.rowCount())]
        # create the widget to select the subplots
        ac = AxesCreatorCollection('axes')
        w = ac.tb.currentWidget()
        w.fig_edit.setText('')
        w.x0_edit.setText('0.3')
        w.y0_edit.setText('0.4')
        w.x1_edit.setText('0.7')
        w.y1_edit.setText('0.8')
        ac.okpressed.connect(lambda it: atab._change_axes(items, it))
        QTest.mouseClick(ac.bt_ok, Qt.LeftButton)
        nvar = self.pc.array_table.rowCount()
        # create the subplots
        axes = self.pc.array_table.axes
        boxes = [ax.get_position() for ax in axes]
        # test rows, cols and figure numbers
        self.assertEqual([box.x0 for box in boxes], [0.3] * nvar)
        self.assertEqual([box.y0 for box in boxes], [0.4] * nvar)
        self.assertEqual([box.x1 for box in boxes], [0.7] * nvar)
        self.assertEqual([box.y1 for box in boxes], [0.8] * nvar)
        self.assertEqual([ax.get_figure().number for ax in axes], list(
            range(1, nvar + 1)))
        # close figures
        plt.close('all')

    def test_axescreator_select(self):
        """Test the :class:`psyplot_gui.plot_creator.AxesSelector`"""
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.backend_bases import MouseEvent, PickEvent
        from psyplot_gui.plot_creator import AxesCreatorCollection
        # load dataset
        self.test_load_external_file()
        # create arrays
        self.test_plusplus()
        # use all items
        atab = self.pc.array_table
        items = [atab.item(i, atab.axes_col) for i in range(2)]
        # create the widget to select the subplots
        ax1 = plt.axes([0.3, 0.4, 0.6, 0.3])
        plt.figure()
        ax2 = plt.subplot(211)
        ac = AxesCreatorCollection('choose')
        w = ac.tb.currentWidget()
        fig = ax1.get_figure()
        mouseevent1 = MouseEvent(
            'button_release_event', fig.canvas,
            *np.mean(ax1.get_position().get_points().T, axis=1))
        w.get_picked_ax(PickEvent('pick', fig.canvas, mouseevent1, artist=ax1))
        fig = ax2.get_figure()
        mouseevent2 = MouseEvent(
            'button_release_event', ax2.get_figure().canvas,
            *np.mean(ax2.get_position().get_points().T, axis=1))
        w.get_picked_ax(PickEvent('pick', fig.canvas, mouseevent2, artist=ax2))

        ac.okpressed.connect(lambda it: atab._change_axes(items, it))
        QTest.mouseClick(ac.bt_ok, Qt.LeftButton)
        # create the subplots
        axes = self.pc.array_table.axes
        # check them
        self.assertIs(axes[0], ax1)
        self.assertIs(axes[1], ax2)
        # close figures
        plt.close('all')


if __name__ == '__main__':
    unittest.main()
