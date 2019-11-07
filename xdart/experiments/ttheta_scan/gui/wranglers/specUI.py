# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'c:\Users\walroth\Documents\repos\xdart\xdart\experiments\ttheta_scan\gui\wranglers\specUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.paramFrame = QtWidgets.QFrame(Form)
        self.paramFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.paramFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.paramFrame.setObjectName("paramFrame")
        self.verticalLayout.addWidget(self.paramFrame)
        self.specLabel = QtWidgets.QLabel(Form)
        self.specLabel.setText("")
        self.specLabel.setObjectName("specLabel")
        self.verticalLayout.addWidget(self.specLabel)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))

