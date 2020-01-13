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
        Form.resize(383, 401)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.buttonFrame1D = QtWidgets.QFrame(Form)
        self.buttonFrame1D.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.buttonFrame1D.setFrameShadow(QtWidgets.QFrame.Raised)
        self.buttonFrame1D.setObjectName("buttonFrame1D")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.buttonFrame1D)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(self.buttonFrame1D)
        self.label_2.setMaximumSize(QtCore.QSize(30, 16777215))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.integrate1D = QtWidgets.QPushButton(self.buttonFrame1D)
        self.integrate1D.setObjectName("integrate1D")
        self.horizontalLayout_2.addWidget(self.integrate1D)
        self.advanced1D = QtWidgets.QPushButton(self.buttonFrame1D)
        self.advanced1D.setObjectName("advanced1D")
        self.horizontalLayout_2.addWidget(self.advanced1D)
        self.all1D = QtWidgets.QCheckBox(self.buttonFrame1D)
        self.all1D.setObjectName("all1D")
        self.horizontalLayout_2.addWidget(self.all1D)
        self.verticalLayout.addWidget(self.buttonFrame1D)
        self.buttonFrame2D = QtWidgets.QFrame(Form)
        self.buttonFrame2D.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.buttonFrame2D.setFrameShadow(QtWidgets.QFrame.Raised)
        self.buttonFrame2D.setObjectName("buttonFrame2D")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.buttonFrame2D)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(self.buttonFrame2D)
        self.label.setMaximumSize(QtCore.QSize(30, 16777215))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.integrate2D = QtWidgets.QPushButton(self.buttonFrame2D)
        self.integrate2D.setObjectName("integrate2D")
        self.horizontalLayout.addWidget(self.integrate2D)
        self.advanced2D = QtWidgets.QPushButton(self.buttonFrame2D)
        self.advanced2D.setObjectName("advanced2D")
        self.horizontalLayout.addWidget(self.advanced2D)
        self.all2D = QtWidgets.QCheckBox(self.buttonFrame2D)
        self.all2D.setObjectName("all2D")
        self.horizontalLayout.addWidget(self.all2D)
        self.verticalLayout.addWidget(self.buttonFrame2D)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label_2.setText(_translate("Form", "1D"))
        self.integrate1D.setText(_translate("Form", "Integrate"))
        self.advanced1D.setText(_translate("Form", "Advanced..."))
        self.all1D.setText(_translate("Form", "All"))
        self.label.setText(_translate("Form", "2D"))
        self.integrate2D.setText(_translate("Form", "Integrate"))
        self.advanced2D.setText(_translate("Form", "Advanced..."))
        self.all2D.setText(_translate("Form", "All"))

