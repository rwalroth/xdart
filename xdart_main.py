# -*- coding: utf-8 -*-
"""
@author: walroth
"""
__version__ = '0.4.2'
# Top level script for running gui based program

# Standard library imports
import sys
import gc

# Other imports

# Qt imports
import qdarkstyle
from pyqtgraph.Qt import QtGui, QtWidgets
QMainWindow = QtWidgets.QMainWindow

# This module imports
from xdart.gui.mainWindow import Ui_MainWindow
from xdart.gui import tabs

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
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
                self.tabs['ttheta_scan'] = tabs.ttheta_scan.tthetaWidget()
                self.tabwidget.addTab(self.tabs['ttheta_scan'], 'ttheta_scan')

    def closeExperiment(self, q):
        _to_close = self.tabwidget.widget(q)
        name = self.tabwidget.tabText(q)
        _to_close.close()
        self.tabwidget.removeTab(q)
        del self.tabs[name]
        gc.collect()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    mw = Main()
    mw.show()
    app.exec_()