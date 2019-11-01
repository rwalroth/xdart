# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'c:\Users\walroth\Documents\repos\xdart\xdart\experiments\ttheta_scan\gui\integratorUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.layout = QtWidgets.QVBoxLayout(Form)
        self.layout.setObjectName("layout")
        self.parameterFrame = QtWidgets.QFrame(Form)
        self.parameterFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.parameterFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.parameterFrame.setObjectName("parameterFrame")
        self.layout.addWidget(self.parameterFrame)
        self.integratorButtons = QtWidgets.QFrame(Form)
        self.integratorButtons.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.integratorButtons.setFrameShadow(QtWidgets.QFrame.Raised)
        self.integratorButtons.setObjectName("integratorButtons")
        self.gridLayout = QtWidgets.QGridLayout(self.integratorButtons)
        self.gridLayout.setObjectName("gridLayout")
        self.integrateBAI1D = QtWidgets.QPushButton(self.integratorButtons)
        self.integrateBAI1D.setObjectName("integrateBAI1D")
        self.gridLayout.addWidget(self.integrateBAI1D, 1, 0, 1, 1)
        self.integrateMG2D = QtWidgets.QPushButton(self.integratorButtons)
        self.integrateMG2D.setObjectName("integrateMG2D")
        self.gridLayout.addWidget(self.integrateMG2D, 4, 1, 1, 1)
        self.integrateBAI2D = QtWidgets.QPushButton(self.integratorButtons)
        self.integrateBAI2D.setObjectName("integrateBAI2D")
        self.gridLayout.addWidget(self.integrateBAI2D, 1, 1, 1, 1)
        self.integrateBAIAll = QtWidgets.QCheckBox(self.integratorButtons)
        self.integrateBAIAll.setObjectName("integrateBAIAll")
        self.gridLayout.addWidget(self.integrateBAIAll, 1, 2, 1, 1)
        self.integrateMG1D = QtWidgets.QPushButton(self.integratorButtons)
        self.integrateMG1D.setObjectName("integrateMG1D")
        self.gridLayout.addWidget(self.integrateMG1D, 4, 0, 1, 1)
        self.setupMG = QtWidgets.QPushButton(self.integratorButtons)
        self.setupMG.setObjectName("setupMG")
        self.gridLayout.addWidget(self.setupMG, 4, 2, 1, 1)
        self.line = QtWidgets.QFrame(self.integratorButtons)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.gridLayout.addWidget(self.line, 2, 0, 1, 3)
        self.label = QtWidgets.QLabel(self.integratorButtons)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 3)
        self.label_2 = QtWidgets.QLabel(self.integratorButtons)
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 3)
        self.layout.addWidget(self.integratorButtons)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.integrateBAI1D.setText(_translate("Form", "Int. 1D"))
        self.integrateMG2D.setText(_translate("Form", "Int. 2D"))
        self.integrateBAI2D.setText(_translate("Form", "Int. 2D"))
        self.integrateBAIAll.setText(_translate("Form", "All"))
        self.integrateMG1D.setText(_translate("Form", "Int. 1D"))
        self.setupMG.setText(_translate("Form", "Setup MG"))
        self.label.setText(_translate("Form", "Singe Image"))
        self.label_2.setText(_translate("Form", "Multi. Geometry"))

