# Top level script for running gui based program
__version__ = '0.0.1'

import sys
import os
import gc

os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'

from pyqtgraph import Qt

import numpy as np
import h5py
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow
from PyQt5 import QtWidgets
import qdarkstyle
import pyqtgraph as pg

import xdart
from xdart.gui.mainWindow import Ui_MainWindow
from xdart import experiments

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.actionOpen.triggered.connect(self.openFile)
        self.ui.actionExit.triggered.connect(self.exit)
        self.fname = None
        self.tabwidget = QtWidgets.QTabWidget()
        self.tabwidget.setTabsClosable(True)
        self.tabwidget.tabCloseRequested.connect(self.closeExperiment)
        self.setCentralWidget(self.tabwidget)
        self.set_experiments()
        #
        self.show()

    def exit(self):
        try:
            self.file.close()
        finally:
            sys.exit()

    def openFile(self):
        self.fname, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File')
        self.tabwidget.currentWidget().update_file(self.fname)
        

    def set_experiments(self):
        for e in experiments.exp_list:
            self.ui.menuExperiments.addAction(e)
        self.ui.menuExperiments.triggered.connect(self.openExperiment)
    
    def openExperiment(self, q):
        if q.text() == 'ttheta_scan':
            self.ttheta_tab = experiments.ttheta_scan.tthetaWidget()
            self.tabwidget.addTab(self.ttheta_tab, 'ttheta_scan')
    
    def closeExperiment(self, q):
        self.tabwidget.setCurrentIndex(q)
        self.tabwidget.currentWidget().close()
        self.tabwidget.removeTab(q)
        gc.collect()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    mw = Main()
    mw.show()
    app.exec_()