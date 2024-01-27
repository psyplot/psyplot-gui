# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

# -*- coding: utf-8 -*-
"""Test module for the :mod:`psyplot_gui.dataframeeditor` module"""
import sys
import unittest

import _base_testing as bt
import numpy as np
import pandas as pd
import six
from pandas.testing import assert_frame_equal

from psyplot_gui.compat.qtcompat import QApplication, Qt

if six.PY2:
    try:
        import CStringIO as io
    except ImportError:
        import StringIO as io
else:
    import io


def df_equals(df, df_ref, *args, **kwargs):
    """Simple wrapper around assert_frame_equal to use unittests assertion

    Parameters
    ----------
    df: pd.DataFrame
        The simulation data frame
    df_ref: pd.DataFrame
        The reference data frame

    Returns
    -------
    None or Exception
        Either None if everything went fine, otherwise the raised Exception"""
    try:
        assert_frame_equal(df, df_ref, *args, **kwargs)
    except Exception as e:
        return e


class DataFrameEditorTest(bt.PsyPlotGuiTestCase):
    #: The :class:`psyplot_gui.dataframeeditor.DataFrameEditor`
    editor = None

    @property
    def table(self):
        return self.editor.table

    @property
    def model(self):
        return self.table.model()

    def setUp(self):
        super(DataFrameEditorTest, self).setUp()
        self.editor = self.window.new_data_frame_editor()

    def tearDown(self):
        self.editor = None

    def test_dtypes(self):
        df = pd.DataFrame(
            [
                [True, "bool"],
                [1 + 1j, "complex"],
                ["test", "string"],
                [1.11, "float"],
                [1, "int"],
                [np.random.rand(3, 3), "Unkown type"],
                ["áéí", "unicode"],
            ],
            index=["a", "b", np.nan, np.nan, np.nan, "c", "d"],
            columns=[np.nan, "Type"],
        )
        self.editor.set_df(df)
        self.assertIs(self.table.model().df, df)

    def test_multiindex(self):
        """Test the handling of DataFrames with MultiIndex"""
        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=list("abc"))
        self.editor.set_df(df)
        self.assertTrue(self.model.index_editable)
        self.assertTrue(self.editor.cb_index_editable.isChecked())

        table = self.table
        table.selectColumn(1)
        table.set_index_action.trigger()
        self.assertEqual(list(df.index.names), ["a"])
        self.assertTrue(self.model.index_editable)
        self.assertTrue(self.editor.cb_index_editable.isChecked())

        table.selectColumn(2)
        table.append_index_action.trigger()
        self.assertEqual(list(df.index.names), ["a", "b"])
        self.assertFalse(self.model.index_editable)
        self.assertFalse(self.editor.cb_index_editable.isChecked())
        table.selectColumn(1)
        table.set_index_action.trigger()
        self.assertEqual(list(df.index.names), ["index"])
        self.assertEqual(list(df.columns), list("abc"))
        self.assertTrue(self.model.index_editable)
        self.assertTrue(self.editor.cb_index_editable.isChecked())

    def test_sort(self):
        """Test the sorting"""
        df = pd.DataFrame(
            [[4, 5, 6 + 1j], [1, object, 3]], columns=list("abc")
        )
        self.editor.set_df(df)
        self.assertTrue(self.model.sort(1, return_check=True))
        self.assertEqual(list(df.index.values), [1, 0])
        self.assertTrue(self.model.sort(0, return_check=True))
        self.assertEqual(list(df.index.values), [0, 1])

        # test complex numbers
        self.assertTrue(
            self.model.sort(3, Qt.AscendingOrder, return_check=True)
        )
        self.assertEqual(list(df["c"].values), [3 + 0j, 6 + 1j])
        self.assertTrue(
            self.model.sort(3, Qt.DescendingOrder, return_check=True)
        )
        self.assertEqual(list(df["c"].values), [6 + 1j, 3 + 0j])

        # sorting is not enabled
        self.table.sortByColumn(1)
        self.assertEqual(list(df["a"]), [4, 1])

        # enable sorting
        self.table.setSortingEnabled(True)
        self.table.header_class.setSortIndicator(1, Qt.AscendingOrder)
        self.table.sortByColumn(1)
        self.assertEqual(list(df["a"]), [1, 4])
        self.table.header_class.setSortIndicator(1, Qt.DescendingOrder)
        self.table.sortByColumn(1)
        self.assertEqual(list(df["a"]), [4, 1])

    @unittest.expectedFailure
    def test_sort_failure(self):
        df = pd.DataFrame(
            [[4, 5, 6 + 1j], [1, object, 3]], columns=list("abc")
        )
        self.editor.set_df(df)

        # test false sorting
        if not six.PY2:
            self.assertFalse(self.model.sort(2, return_check=True))

    @unittest.expectedFailure
    def test_sort_failure_2(self):
        df = pd.DataFrame(
            [[4, 5, 6 + 1j], [1, object, 3]], columns=list("abc")
        )
        self.editor.set_df(df)

        # test a column that cannot be sorted
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(2)

    def test_edit(self):
        """Test the editing of the editor"""

        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=list("abc"))
        self.editor.set_df(df)

        table = self.table

        # edit a regular cell
        table.selectRow(0)
        idx = table.selectedIndexes()[2]  # first row, second column
        self.model.setData(idx, 4)
        self.assertEqual(df.iloc[0, 1], 4)

        # now edit the index
        table.selectRow(1)
        idx = table.selectedIndexes()[0]  # first row, second column
        self.model.setData(idx, 6)
        self.assertEqual(df.index[1], 6)

        # now we change a data type
        table.selectColumn(2)
        table.dtype_actions["To float"].trigger()
        self.assertIs(df.dtypes["b"], np.array(5.4).dtype)

    def test_large_df(self):
        df = pd.DataFrame(np.zeros((int(1e6), 100)))
        self.editor.set_df(df)
        model = self.model
        self.assertLess(model.rows_loaded, df.shape[0])
        self.assertLess(model.cols_loaded, df.shape[1])
        self.assertEqual((model.total_rows, model.total_cols), df.shape)
        self.assertTrue(model.can_fetch_more(rows=True, columns=True))
        old_rows, old_cols = model.rows_loaded, model.cols_loaded
        self.table.load_more_data(
            self.table.verticalScrollBar().maximum(), rows=True
        )
        self.table.load_more_data(
            self.table.horizontalScrollBar().maximum(), columns=True
        )
        self.assertGreater(model.rows_loaded, old_rows)
        self.assertGreater(model.cols_loaded, old_cols)
        self.assertLess(model.rows_loaded, df.shape[0])
        self.assertLess(model.cols_loaded, df.shape[1])

    def test_insert_rows_above(self):
        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=list("abc"))
        self.editor.set_df(df)

        # insert one row
        self.table.selectRow(1)
        self.table.insert_row_above_action.trigger()
        self.assertEqual(df.shape, (3, 3))
        self.assertEqual(list(df.index), [0, 0, 1])
        self.assertTrue(
            np.isnan(df.iloc[1, :].values).all(), msg=str(df.iloc[1, :])
        )

        # insert two rows
        self.model.insertRows(2, 2)
        self.assertEqual(df.shape, (5, 3))
        self.assertEqual(list(df.index), [0, 0, 0, 0, 1])
        self.assertTrue(
            np.isnan(df.iloc[2:-1, :].values).all(), msg=str(df.iloc[2:-1, :])
        )

    def test_insert_rows_below(self):
        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=list("abc"))
        self.editor.set_df(df)

        # insert one row
        self.table.selectRow(1)
        self.table.insert_row_below_action.trigger()
        self.assertEqual(df.shape, (3, 3))
        self.assertEqual(list(df.index), [0, 1, 1])
        self.assertTrue(
            np.isnan(df.iloc[2, :].values).all(), msg=str(df.iloc[2, :])
        )

        # insert two rows
        self.model.insertRows(3, 2)
        self.assertEqual(df.shape, (5, 3))
        self.assertEqual(list(df.index), [0, 1, 1, 1, 1])
        self.assertTrue(
            np.isnan(df.iloc[-2:, :].values).all(), msg=str(df.iloc[-2:, :])
        )

    def test_copy(self):
        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=list("abc"))
        self.editor.set_df(df)
        self.table.selectAll()
        self.table.copy()
        clipboard = QApplication.clipboard()
        stream = io.StringIO(clipboard.text())

        df2 = pd.read_csv(stream, delim_whitespace=True)
        self.assertIsNone(df_equals(df2, df))

        self.table.selectColumn(1)
        self.table.copy()
        stream = io.StringIO(clipboard.text())
        arr = np.loadtxt(stream)
        self.assertEqual(arr.tolist(), [1, 4])

    @unittest.skipIf(
        sys.platform == "win32",
        "Avoid potential troubles with temporary csv files.",
    )
    def test_open_dataframe(self):
        """Test the opening of a dataframe"""
        from tempfile import NamedTemporaryFile

        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]], columns=list("abc"))
        self.editor.open_dataframe(df)
        self.editor.open_dataframe("")
        f = NamedTemporaryFile(suffix=".csv")
        df.to_csv(f.name, index=False)
        self.editor.open_dataframe(f.name)
        self.assertIsNone(df_equals(self.model.df, df))

    @unittest.expectedFailure
    def test_open_nonexistent(self):
        self.editor.open_dataframe("NONEXISTENT.csv")
        self.assertIsNone(self.model.df)

    def test_close(self):
        self.editor.close()
        self.assertFalse(self.window.dataframeeditors)
