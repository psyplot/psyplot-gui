# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

# -*- coding: utf-8 -*-
"""Script to test the :mod:`psyplot_gui.dependencies` module"""
import unittest

import _base_testing as bt
import numpy as np
import psyplot
import yaml

import psyplot_gui
from psyplot_gui.compat.qtcompat import QLabel


class TestDependencies(bt.PsyPlotGuiTestCase):
    """Test the :class:`psyplot_gui.preferences.Preferences` widget"""

    def setUp(self):
        super(TestDependencies, self).setUp()
        self.window.show_dependencies()
        self.deps = self.window.dependencies

    def tearDown(self):
        # make sure the preferences widget is closed completely
        self.deps.close()
        del self.deps
        super(TestDependencies, self).tearDown()

    def test_widget(self):
        """Test whether the tree is filled correctly"""
        deps = self.deps
        label = QLabel("", parent=self.window)
        deps.tree.selectAll()
        deps.copy_selected(label)
        d = yaml.load(str(label.text()), Loader=yaml.Loader)
        self.assertEqual(d["psyplot"], psyplot.__version__)
        self.assertEqual(d["psyplot_gui"], psyplot_gui.__version__)
        self.assertIn("numpy", d)
        self.assertEqual(d["numpy"], np.__version__)
        label.close()


if __name__ == "__main__":
    unittest.main()
