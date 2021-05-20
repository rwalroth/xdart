# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'c:\Users\walroth\Documents\repos\xdart\xdart\experiments\static_scan\gui\wranglers\liveSpecUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.paramFrame = QtWidgets.QFrame(Form)
        self.paramFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.paramFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.paramFrame.setObjectName("paramFrame")
        self.verticalLayout.addWidget(self.paramFrame)
        self.specLabel = QtWidgets.QLabel(Form)
        self.specLabel.setMaximumSize(QtCore.QSize(16777215, 40))
        self.specLabel.setText("")
        self.specLabel.setObjectName("specLabel")
        self.verticalLayout.addWidget(self.specLabel)
        self.commandFrame = QtWidgets.QFrame(Form)
        self.commandFrame.setMaximumSize(QtCore.QSize(16777215, 40))
        self.commandFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.commandFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.commandFrame.setObjectName("commandFrame")
        self.commandLayout = QtWidgets.QHBoxLayout(self.commandFrame)
        self.commandLayout.setObjectName("commandLayout")
        self.verticalLayout.addWidget(self.commandFrame)
        self.frame = QtWidgets.QFrame(Form)
        self.frame.setMaximumSize(QtCore.QSize(16777215, 40))
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.startButton = QtWidgets.QPushButton(self.frame)
        self.startButton.setObjectName("startButton")
        self.horizontalLayout.addWidget(self.startButton)
        self.stopButton = QtWidgets.QPushButton(self.frame)
        self.stopButton.setObjectName("stopButton")
        self.horizontalLayout.addWidget(self.stopButton)
        self.verticalLayout.addWidget(self.frame)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.startButton.setText(_translate("Form", "Start"))
        self.stopButton.setText(_translate("Form", "Stop"))

