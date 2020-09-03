# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'specUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1440, 817)
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
        self.specLabel.setText("")
        self.specLabel.setObjectName("specLabel")
        self.verticalLayout.addWidget(self.specLabel)
        self.frame = QtWidgets.QFrame(Form)
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.startButton = QtWidgets.QPushButton(self.frame)
        self.startButton.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.startButton.setObjectName("startButton")
        self.horizontalLayout.addWidget(self.startButton)
        self.pauseButton = QtWidgets.QPushButton(self.frame)
        self.pauseButton.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.pauseButton.setObjectName("pauseButton")
        self.horizontalLayout.addWidget(self.pauseButton)
        self.continueButton = QtWidgets.QPushButton(self.frame)
        self.continueButton.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.continueButton.setObjectName("continueButton")
        self.horizontalLayout.addWidget(self.continueButton)
        self.stopButton = QtWidgets.QPushButton(self.frame)
        self.stopButton.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.stopButton.setObjectName("stopButton")
        self.horizontalLayout.addWidget(self.stopButton)
        self.verticalLayout.addWidget(self.frame)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.startButton.setText(_translate("Form", "Start"))
        self.pauseButton.setText(_translate("Form", "Pause"))
        self.continueButton.setText(_translate("Form", "Continue"))
        self.stopButton.setText(_translate("Form", "Stop"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

