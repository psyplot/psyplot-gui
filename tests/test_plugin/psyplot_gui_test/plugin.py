# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

from psyplot.config.rcsetup import RcParams, validate_bool, validate_dict

from psyplot_gui.common import DockMixin
from psyplot_gui.compat.qtcompat import Qt, QWidget


class W1(QWidget, DockMixin):
    title = "w1"
    dock_position = Qt.LeftDockWidgetArea


class W2(QWidget, DockMixin):
    title = "w2"
    dock_position = Qt.BottomDockWidgetArea
    hidden = True


rcParams = RcParams(
    defaultParams={
        "test_plugin": [True, validate_bool],
        "project.plotters": [
            {
                "gui_test_plotter": {
                    "module": "psyplot_gui_test.plotter",
                    "plotter_name": "TestPlotter",
                    "import_plotter": True,
                }
            },
            validate_dict,
        ],
    }
)
rcParams.update_from_defaultParams()
