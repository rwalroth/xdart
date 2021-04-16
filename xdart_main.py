# -*- coding: utf-8 -*-
"""
@author: walroth
"""
__version__ = '0.4.2'
# Top level script for running gui based program

# Standard library imports
import sys
import gc
import os

# Other imports

# Qt imports
import qdarkstyle
from pyqtgraph.Qt import QtGui, QtWidgets

# This module imports
from xdart.gui.mainWindow import Ui_MainWindow
from xdart.gui import tabs

import multiprocessing


def setup_data_folders(exp_list):
    """
    Creates xdart/data folder and xdart/data/tabs folder for storing
    local data. These are ignored by gitignore.

    Parameters
    ----------
    exp_list : list, set of tabs to be

    Returns
    -------
    tab_paths : dict, paths for tabs to store data
    """
    current_directory = os.path.dirname(__file__)
    data_directory = os.path.join(current_directory, "data")
    if not os.path.isdir(data_directory):
        os.mkdir(data_directory)
    tab_paths = {}
    for e in exp_list:
        tab_directory = os.path.join(data_directory, e)
        tab_paths[e] = tab_directory
        if not os.path.isdir(tab_directory):
            os.mkdir(tab_directory)
    return tab_paths


QMainWindow = QtWidgets.QMainWindow


class Main(QMainWindow):
    def __init__(self, tab_paths):
        """

        Parameters
        ----------
        tab_paths : dict
        """
        super().__init__()
        self.tab_paths = tab_paths
        self.tabs = {}
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.actionOpen.triggered.connect(self.openFile)
        self.ui.actionExit.triggered.connect(self.exit)
        self.fname = None
        self.tabwidget = QtWidgets.QTabWidget()
        self.tabwidget.setTabsClosable(True)
        self.tabwidget.tabCloseRequested.connect(self.closeExperiment)
        self.setCentralWidget(self.tabwidget)
        self.set_tabs()
        #
        self.show()

    def exit(self):
        try:
            for i in range(self.tabwidget.count()):
                self.closeExperiment(i)
        finally:
            sys.exit()

    def openFile(self):
        try:
            self.tabwidget.currentWidget().open_file()
        except Exception as e:
            print(e)

    def set_tabs(self):
        for e in tabs.exp_list:
            self.ui.menuExperiments.addAction(e)
        self.ui.menuExperiments.triggered.connect(self.openExperiment)

    def openExperiment(self, q):
        if q.text() == 'ttheta_scan':
            if 'ttheta_scan' not in self.tabs:
                self.tabs['ttheta_scan'] = tabs.ttheta_scan.tthetaWidget(local_path=self.tab_paths['ttheta_scan'])
                self.tabwidget.addTab(self.tabs['ttheta_scan'], 'ttheta_scan')
        elif q.text() == 'static_scan':
            if 'static_scan' not in self.tabs:
                self.tabs['static_scan'] = tabs.static_scan.staticWidget(local_path=self.tab_paths['static_scan'])
                self.tabwidget.addTab(self.tabs['static_scan'], 'static_scan')

    def closeExperiment(self, q):
        _to_close = self.tabwidget.widget(q)
        name = self.tabwidget.tabText(q)
        _to_close.close()
        self.tabwidget.removeTab(q)
        del self.tabs[name]
        gc.collect()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    tab_paths = setup_data_folders(tabs.exp_list)
    app = QtGui.QApplication(sys.argv)
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    mw = Main(tab_paths)
    mw.show()
    app.exec_()
