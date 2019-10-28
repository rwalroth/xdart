# -*- coding: utf-8 -*-
"""
@author: walroth
"""
__version__ = '0.1.0'
# Top level script for running gui based program

# Standard library imports
import sys
import os
import gc
import time

os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'

# Other imports
import numpy as np
import h5py

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow
from PyQt5 import QtWidgets
import qdarkstyle
import pyqtgraph as pg

# This module imports
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
            for i in range(self.tabwidget.count()):
                self.closeExperiment(i)
        finally:
            sys.exit()

    def openFile(self):
        try:
            self.tabwidget.currentWidget().open_file()
        except Exception as e:
            print(e)
        

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