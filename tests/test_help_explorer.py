# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

"""Module for testing the components of the
:class:`psyplot_gui.help_explorer.HelpExplorer` class"""
import inspect
import os.path as osp
import unittest

import _base_testing as bt
import dummy_module as d

from psyplot_gui import rcParams
from psyplot_gui.compat.qtcompat import Qt, QTest, asstring
from psyplot_gui.help_explorer import (
    HelpExplorer,
    UrlHelp,
    _viewers,
    html2file,
)


class UrlHelpTestMixin(bt.PsyPlotGuiTestCase):
    """Convenience class for UrlHelp tests"""

    @classmethod
    def setUpClass(cls):
        super(UrlHelpTestMixin, cls).setUpClass()
        cls._original_intersphinx = rcParams["help_explorer.use_intersphinx"]
        rcParams["help_explorer.use_intersphinx"] = False
        # we render the docs in the same process to avoid problems with
        # signals not being send and time problems
        cls._original_pdocs = rcParams["help_explorer.render_docs_parallel"]
        rcParams["help_explorer.render_docs_parallel"] = False

    @classmethod
    def tearDownClass(cls):
        super(UrlHelpTestMixin, cls).tearDownClass()
        rcParams["help_explorer.use_intersphinx"] = cls._original_intersphinx
        rcParams["help_explorer.render_docs_parallel"] = cls._original_pdocs

    def setUp(self):
        super(UrlHelpTestMixin, self).setUp()
        self.help_explorer.set_viewer("HTML help")

    @property
    def help_explorer(self):
        return self.window.help_explorer

    @property
    def viewer(self):
        ret = self.help_explorer.viewer
        self.assertIs(ret, self.help_explorer.viewers["HTML help"])
        return ret

    def _test_if_sphinx_worked(self, oname):
        html = osp.join(
            osp.join(self.viewer.sphinx_dir, "_build", "html", oname + ".html")
        )
        self.assertEqual(html2file(self.viewer.html.url().toString()), html)
        # we emit the urlChanged signal manually because it is not emitted
        # without main loop
        self.viewer.html.urlChanged.emit(self.viewer.html.url())
        self.assertEqual(self.viewer.tb_url.currentText(), oname)

    def _test_browsing(self):
        rcParams["help_explorer.online"] = True
        self.viewer.browse("www.google.de")
        url = asstring(self.viewer.html.url().toString())
        self.assertTrue(
            url.startswith("https://www.google.de"), msg="Wrong url " + url
        )

    def _test_object_docu(self, obj, oname):
        """Test whether an html help of a python object can be shown"""
        self.help_explorer.show_help(obj, oname)
        fname = osp.join(self.viewer.sphinx_dir, oname + ".rst")
        self.assertTrue(osp.exists(fname), msg=fname + " is not existent!")
        self._test_if_sphinx_worked(oname)


class UrlHelpTest(UrlHelpTestMixin):
    """Test the :class:`psyplot_gui.help_explorer.UrlHelp`"""

    def test_browsing(self):
        """Test browsing"""
        self._test_browsing()

    def test_show_rst(self):
        """Test whether the showing of an rst string is working"""
        s = """
        That's a test
        =============

        Just a dummy string"""
        self.help_explorer.show_rst(s, "test")
        fname = osp.join(self.viewer.sphinx_dir, "test.rst")
        self.assertTrue(osp.exists(fname), msg=fname + " is not existent!")
        self._test_if_sphinx_worked("test")

    def test_module_doc(self):
        """Test whether the sphinx rendering works for a module"""
        self._test_object_docu(d, "dummy_module")

    def test_class_doc(self):
        """Test whether the sphinx rendering works for a class"""
        self._test_object_docu(d.DummyClass, "d.DummyClass")

    def test_func_doc(self):
        """Test whether the sphinx rendering works for a class"""
        self._test_object_docu(d.dummy_func, "d.dummy_func")

    def test_method_doc(self):
        """Test whether the sphinx rendering works for a method"""
        self._test_object_docu(
            d.DummyClass.dummy_method, "d.DummyClass.dummy_method"
        )
        ini = d.DummyClass()
        self._test_object_docu(ini.dummy_method, "ini.dummy_method")

    def test_instance_doc(self):
        """Test whether the sphinx rendering works for a instance of a class"""
        ini = d.DummyClass()
        self._test_object_docu(ini, "ini")


# XXX Not yet working XXX
#    def test_classattr_doc(self):
#        """Test whether the sphinx rendering works for a method"""
#        ini = d.DummyClass(2)
#        self._test_object_docu(ini.a, 'ini.a')
#
#    def test_moduleattr_doc(self):
#        """Test whether the sphinx rendering works for a method"""
#        self._test_object_docu(d.a, 'd.a')


class BrowserTest(UrlHelpTestMixin):
    """Testcase for the :class:`psyplot_gui.help_explorer.UrlBrowser` class"""

    def setUp(self):
        super(BrowserTest, self).setUp()
        self._help = viewer = UrlHelp(parent=self.window.help_explorer)
        self.window.help_explorer.viewers["HTML help"] = viewer
        self.window.help_explorer.set_viewer(viewer)

    def tearDown(self):
        self._help.close(force=True)
        super(BrowserTest, self).tearDown()

    def test_added_url(self):
        """Test to add an url on the top"""

        def check_google():
            combo.add_text_on_top("https://www.google.com/", block=True)
            self.assertEqual(combo.itemText(0), "https://www.google.com/")

        combo = self.viewer.tb_url
        current = combo.itemText(0)
        check_google()
        combo.insertItem(0, "test")
        check_google()
        self.assertEqual(combo.itemText(1), "test")
        self.assertEqual(combo.itemText(2), current)

    def test_lock(self):
        """Test the url lock"""
        url = self.viewer.html.url().toString()
        QTest.mouseClick(self.viewer.bt_lock, Qt.LeftButton)
        self.help_explorer.show_help(int, "int")
        fname = osp.join(self.viewer.sphinx_dir, "int.rst")
        self.assertFalse(osp.exists(fname), msg=fname + " exists wrongly!")
        self.help_explorer.show_rst(int.__doc__, "int")
        self.assertFalse(osp.exists(fname), msg=fname + " exists wrongly!")
        self.viewer.browse("www.google.de")
        self.assertEqual(self.viewer.html.url().toString(), url)

    def test_url_lock(self):
        """Test whether to object documentation works"""
        self._test_browsing()
        QTest.mouseClick(self.viewer.bt_url_lock, Qt.LeftButton)
        self.help_explorer.show_help(int, "int")
        self._test_object_docu(int, "int")
        self.viewer.browse("www.unil.ch")
        self._test_object_docu(int, "int")


class TextHelpTest(bt.PsyPlotGuiTestCase):
    """Testcase for the :class:`psyplot_gui.help_explorer.TextHelp` class"""

    def setUp(self):
        super(TextHelpTest, self).setUp()
        self.help_explorer.set_viewer("Plain text")

    @property
    def help_explorer(self):
        return self.window.help_explorer

    @property
    def viewer(self):
        return self.help_explorer.viewer

    def _test_doc(self, doc, oname, obj=None):
        """Test whether an the documentation is shown correctly

        Notes
        -----
        May be improved in the future for a more exact test"""
        self.assertTrue(
            doc in self.viewer.editor.toPlainText(),
            msg="%s was not documented!\nObject docu: %s\nHelp test: %s"
            % (oname, doc, self.viewer.editor.toPlainText()),
        )

    def _test_object_docu(self, obj, oname, doc=None):
        """Test whether an help of a python object can be shown"""
        self.help_explorer.show_help(obj, oname)
        if doc is None:
            doc = inspect.getdoc(obj)
        self._test_doc(doc, oname, obj)

    def test_show_rst(self):
        """Test whether the showing of an rst string is working"""
        s = """
        That's a test
        =============

        Just a dummy string"""
        self.help_explorer.show_rst(s, "test")
        self._test_doc(s, "test")

    def test_module_doc(self):
        """Test whether the sphinx rendering works for a module"""
        self._test_object_docu(d, "dummy_module")

    def test_class_doc(self):
        """Test whether the sphinx rendering works for a class"""
        self._test_object_docu(d.DummyClass, "d.DummyClass")

    def test_func_doc(self):
        """Test whether the sphinx rendering works for a class"""
        self._test_object_docu(d.dummy_func, "d.dummy_func")

    def test_method_doc(self):
        """Test whether the sphinx rendering works for a method"""
        self._test_object_docu(
            d.DummyClass.dummy_method, "d.DummyClass.dummy_method"
        )
        ini = d.DummyClass()
        self._test_object_docu(ini.dummy_method, "ini.dummy_method")

    def test_instance_doc(self):
        """Test whether the sphinx rendering works for a instance of a class"""
        ini = d.DummyClass()
        self._test_object_docu(ini, "ini")


class NoHTMLTest(TextHelpTest):
    """Test running without the HTML viewer"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        rcParams["help_explorer.use_webengineview"] = False
        del HelpExplorer.viewers["HTML help"]
        cls._orig_viewers = _viewers.copy()
        _viewers.clear()

    def setUp(self):
        super(TextHelpTest, self).setUp()

    @classmethod
    def tearDownClass(cls):
        rcParams["help_explorer.use_webengineview"] = True
        HelpExplorer.viewers["HTML help"] = UrlHelp
        for key, val in cls._orig_viewers.items():
            _viewers[key] = val
        super().tearDownClass()

    def test_no_html(self):
        """Test if the HTML help has been removed"""
        self.assertNotIn("HTML help", self.help_explorer.viewers)


if __name__ == "__main__":
    unittest.main()
