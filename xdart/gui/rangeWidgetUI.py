# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'c:\Users\walroth\Documents\repos\xdart\xdart\gui\rangeWidgetUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(415, 300)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.rangeLabel = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.rangeLabel.setFont(font)
        self.rangeLabel.setObjectName("rangeLabel")
        self.gridLayout.addWidget(self.rangeLabel, 0, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(Form)
        self.label_4.setAlignment(QtCore.Qt.AlignCenter)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 2, 1, 1)
        self.points = QtWidgets.QSpinBox(Form)
        self.points.setMinimum(1)
        self.points.setMaximum(10000000)
        self.points.setObjectName("points")
        self.gridLayout.addWidget(self.points, 1, 1, 1, 1)
        self.low = QtWidgets.QDoubleSpinBox(Form)
        self.low.setObjectName("low")
        self.gridLayout.addWidget(self.low, 0, 1, 1, 1)
        self.pointsLabel = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.pointsLabel.setFont(font)
        self.pointsLabel.setObjectName("pointsLabel")
        self.gridLayout.addWidget(self.pointsLabel, 1, 0, 1, 1)
        self.high = QtWidgets.QDoubleSpinBox(Form)
        self.high.setObjectName("high")
        self.gridLayout.addWidget(self.high, 0, 3, 1, 1)
        self.units = QtWidgets.QComboBox(Form)
        self.units.setObjectName("units")
        self.gridLayout.addWidget(self.units, 0, 4, 1, 1)
        self.stepLabel = QtWidgets.QLabel(Form)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.stepLabel.setFont(font)
        self.stepLabel.setObjectName("stepLabel")
        self.gridLayout.addWidget(self.stepLabel, 1, 2, 1, 1)
        self.step = QtWidgets.QDoubleSpinBox(Form)
        self.step.setDecimals(3)
        self.step.setMaximum(1000000.0)
        self.step.setSingleStep(0.1)
        self.step.setObjectName("step")
        self.gridLayout.addWidget(self.step, 1, 3, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.rangeLabel.setText(_translate("Form", "Title Range"))
        self.label_4.setText(_translate("Form", "to"))
        self.pointsLabel.setText(_translate("Form", "Title Points"))
        self.stepLabel.setText(_translate("Form", "Step Size"))

