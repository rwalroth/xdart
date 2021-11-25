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
import signal

# Qt imports
from pyqtgraph.Qt import QtGui, QtWidgets

# This module imports
from xdart.gui.mainWindow import Ui_MainWindow
from xdart.gui import tabs

# Other imports
# import multiprocessing
# multiprocessing.freeze_support()
# try:
#     multiprocessing.set_start_method('spawn')
# except RuntimeError:
#     pass


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
    data_directory = os.path.join(current_directory, "../data")
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
        self.resize(1600, 920)

    def exit(self):
        try:
            for i in range(self.tabwidget.count()):
                self.closeExperiment(i)
        finally:
            self.close()
            gc.collect()
            try:
                os.killpg(os.getpid(), signal.SIGTERM)
            except ProcessLookupError:
                pass
            sys.exit(1)

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
                if self.width() < 1300:
                    self.resize(1300, self.height())
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


def main():
    # multiprocessing.freeze_support()
    os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
    tab_paths = setup_data_folders(tabs.exp_list)
    app = QtGui.QApplication(sys.argv)
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    mw = Main(tab_paths)
    mw.show()
    app.exec_()

    # try:
    #     os.killpg(os.getpid(), signal.SIGTERM)
    # except AttributeError or ProcessLookupError:
    #     pass


if __name__ == '__main__':
    sys.exit(main())
