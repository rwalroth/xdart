# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'c:\Users\walroth\Documents\repos\xdart\xdart\experiments\ttheta_scan\gui\h5viewerUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(666, 445)
        self.layout = QtWidgets.QGridLayout(Form)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setVerticalSpacing(0)
        self.layout.setObjectName("layout")
        self.frame = QtWidgets.QFrame(Form)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.layout.addWidget(self.frame, 0, 0, 1, 1)
        self.label = QtWidgets.QLabel(Form)
        self.label.setObjectName("label")
        self.layout.addWidget(self.label, 1, 0, 1, 1)
        self.listScans = QtWidgets.QListWidget(Form)
        self.listScans.setObjectName("listScans")
        self.layout.addWidget(self.listScans, 2, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.layout.addWidget(self.label_2, 1, 1, 1, 1)
        self.listData = QtWidgets.QListWidget(Form)
        self.listData.setObjectName("listData")
        self.layout.addWidget(self.listData, 2, 1, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label.setText(_translate("Form", "Scans"))
        self.label_2.setText(_translate("Form", "Data"))

