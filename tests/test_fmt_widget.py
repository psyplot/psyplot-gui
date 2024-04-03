# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

"""Test module for the psyplot_gui.fmt_widget module"""
import _base_testing as bt
import yaml

from psyplot_gui.compat.qtcompat import (
    QPushButton,
    Qt,
    QtCore,
    QTest,
    QtGui,
    with_qt5,
)

if with_qt5:
    ClearAndSelect = QtCore.QItemSelectionModel.ClearAndSelect
else:
    ClearAndSelect = QtGui.QItemSelectionModel.ClearAndSelect


class FormatoptionWidgetTest(bt.PsyPlotGuiTestCase):
    """Test case for the :class:`psyplot_gui.fmt_widget.FormatoptionWidget`"""

    @property
    def fmt_widget(self):
        return self.window.fmt_widget

    def setUp(self):
        import psyplot.project as psy

        super(FormatoptionWidgetTest, self).setUp()
        self.project = psy.plot.gui_test_plotter(
            self.get_file("test-t2m-u-v.nc"), name="t2m"
        )

    def tearDown(self):
        import psyplot.project as psy

        super(FormatoptionWidgetTest, self).tearDown()
        psy.close("all")
        del self.project

    def test_fmto_groups(self):
        """Test whether the group combo is filled correctly"""
        fmt_w = self.fmt_widget
        # test groups
        self.assertEqual(
            list(
                map(
                    fmt_w.group_combo.itemText,
                    range(fmt_w.group_combo.count()),
                )
            ),
            [
                "Dimensions",
                "All formatoptions",
                "Miscallaneous formatoptions",
                "Post processing formatoptions",
            ],
        )

    def test_dims(self):
        """Test whether the fmto combo for dimensions is filled correctly"""
        fmt_w = self.fmt_widget
        # test groups
        self.assertEqual(
            list(
                map(fmt_w.fmt_combo.itemText, range(fmt_w.fmt_combo.count()))
            ),
            list(self.project[0].psy.base["t2m"].dims),
        )

    def test_dim_widget(self):
        """Test the :class:`psyplot_gui.fmt_widget.DimensionsWidget`"""
        fmt_w = self.fmt_widget
        fmt_w.clear_text()
        self.assertTrue(fmt_w.dim_widget.isVisible())
        fmt_w.dim_widget.coord_combo.load_coord()
        model = fmt_w.dim_widget.coord_combo.model()
        selection_model = fmt_w.dim_widget.coord_combo.view().selectionModel()
        item = model.item(2)
        selection_model.select(model.indexFromItem(item), ClearAndSelect)
        fmt_w.dim_widget.insert_from_combo()
        self.assertEqual(fmt_w.get_text(), "[1]")
        # select a second item
        item = model.item(3)
        selection_model.select(model.indexFromItem(item), ClearAndSelect)
        fmt_w.dim_widget.insert_from_combo()
        self.assertEqual(fmt_w.get_text(), "[1, 2]")

        # change to single selection
        fmt_w.dim_widget.set_single_selection(True)
        fmt_w.dim_widget.insert_from_combo()
        self.assertEqual(fmt_w.get_text(), "2")

    def test_fmtos(self):
        """Test whether the fmto combo for formatoptions is filled correctly"""
        fmt_w = self.fmt_widget
        fmt_w.group_combo.setCurrentIndex(
            fmt_w.group_combo.findText("Miscallaneous formatoptions")
        )
        # test groups
        self.assertEqual(
            list(
                map(fmt_w.fmt_combo.itemText, range(fmt_w.fmt_combo.count()))
            ),
            ["Test formatoption (fmt1)", "Second test formatoption (fmt2)"],
        )

    def test_toggle_multiline(self):
        """Test toggle the multiline text editor"""
        fmt_w = self.fmt_widget
        self.assertTrue(fmt_w.line_edit.isVisible())
        self.assertFalse(fmt_w.text_edit.isVisible())
        fmt_w.set_obj("test")
        self.assertEqual(fmt_w.line_edit.text()[1:-1], "test")

        # now toggle the button
        QTest.mouseClick(fmt_w.multiline_button, Qt.LeftButton)
        self.assertFalse(fmt_w.line_edit.isVisible())
        self.assertTrue(fmt_w.text_edit.isVisible())
        self.assertEqual(fmt_w.text_edit.toPlainText()[1:-1], "test")
        fmt_w.insert_obj("test")
        self.assertEqual(fmt_w.text_edit.toPlainText()[1:-1], "testtest")

        # and toggle again
        QTest.mouseClick(fmt_w.multiline_button, Qt.LeftButton)
        self.assertTrue(fmt_w.line_edit.isVisible())
        self.assertFalse(fmt_w.text_edit.isVisible())
        self.assertEqual(fmt_w.line_edit.text()[1:-1], "testtest")

    def test_run_code(self):
        """Test updating the plot"""
        fmt_w = self.fmt_widget
        self.assertTrue(fmt_w.yaml_cb.isChecked())
        fmt_w.group_combo.setCurrentIndex(
            fmt_w.group_combo.findText("Miscallaneous formatoptions")
        )
        fmt_w.set_obj("test")
        QTest.keyClick(fmt_w.line_edit, Qt.Key_Return)
        self.assertEqual(self.project.plotters[0].fmt1.value, "test")

        # test python code
        fmt_w.fmt_combo.setCurrentIndex(1)
        fmt_w.yaml_cb.setChecked(False)
        fmt_w.set_obj("second test")
        QTest.mouseClick(fmt_w.run_button, Qt.LeftButton)
        self.assertEqual(self.project.plotters[0].fmt2.value, "second test")

    def test_fmt_widget(self):
        """Test the :meth:`psyplot.plotter.Formatoption.get_fmt_widget` method"""
        fmt_w = self.fmt_widget
        self.assertIs(fmt_w.fmt_widget, fmt_w.dim_widget)
        fmt_w.group_combo.setCurrentIndex(
            fmt_w.group_combo.findText("Miscallaneous formatoptions")
        )
        self.assertIsInstance(fmt_w.fmt_widget, QPushButton)
        self.assertFalse(yaml.load(fmt_w.line_edit.text(), Loader=yaml.Loader))
        fmt_w.line_edit.setText("")
        QTest.mouseClick(fmt_w.fmt_widget, Qt.LeftButton)
        self.assertEqual(fmt_w.line_edit.text()[1:-1], "Test")
        # test with objects other than string
        fmt_w.fmt_combo.setCurrentIndex(1)
        self.assertIsInstance(fmt_w.fmt_widget, QPushButton)
        fmt_w.clear_text()
        QTest.mouseClick(fmt_w.fmt_widget, Qt.LeftButton)
        self.assertEqual(fmt_w.line_edit.text(), "2")

        # check without yaml
        fmt_w.yaml_cb.setChecked(False)
        QTest.mouseClick(fmt_w.fmt_widget, Qt.LeftButton)
        self.assertEqual(fmt_w.line_edit.text(), "22")

    def test_get_obj(self):
        self.fmt_widget.line_edit.setText('{"okay": True}')
        self.assertEqual(self.fmt_widget.get_obj(), {"okay": True})
