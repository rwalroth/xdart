# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'imageWidgetUI.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(688, 480)
        self.horizontalLayout = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.imageFrame = QtWidgets.QFrame(Form)
        self.imageFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.imageFrame.setFrameShadow(QtWidgets.QFrame.Plain)
        self.imageFrame.setLineWidth(0)
        self.imageFrame.setObjectName("imageFrame")
        self.horizontalLayout.addWidget(self.imageFrame)
        self.toolFrame = QtWidgets.QFrame(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toolFrame.sizePolicy().hasHeightForWidth())
        self.toolFrame.setSizePolicy(sizePolicy)
        self.toolFrame.setMinimumSize(QtCore.QSize(120, 0))
        self.toolFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.toolFrame.setFrameShadow(QtWidgets.QFrame.Plain)
        self.toolFrame.setLineWidth(0)
        self.toolFrame.setObjectName("toolFrame")
        self.toolLayout = QtWidgets.QGridLayout(self.toolFrame)
        self.toolLayout.setContentsMargins(1, 1, 1, 1)
        self.toolLayout.setObjectName("toolLayout")
        self.cmapBox = QtWidgets.QComboBox(self.toolFrame)
        self.cmapBox.setObjectName("cmapBox")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.cmapBox.addItem("")
        self.toolLayout.addWidget(self.cmapBox, 0, 1, 1, 1)
        self.logButton = QtWidgets.QToolButton(self.toolFrame)
        self.logButton.setMinimumSize(QtCore.QSize(30, 0))
        self.logButton.setMaximumSize(QtCore.QSize(30, 16777215))
        self.logButton.setCheckable(True)
        self.logButton.setObjectName("logButton")
        self.toolLayout.addWidget(self.logButton, 0, 0, 1, 1)
        self.horizontalLayout.addWidget(self.toolFrame)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.cmapBox.setItemText(0, _translate("Form", "grey"))
        self.cmapBox.setItemText(1, _translate("Form", "viridis"))
        self.cmapBox.setItemText(2, _translate("Form", "plasma"))
        self.cmapBox.setItemText(3, _translate("Form", "inferno"))
        self.cmapBox.setItemText(4, _translate("Form", "magma"))
        self.cmapBox.setItemText(5, _translate("Form", "spectrum"))
        self.cmapBox.setItemText(6, _translate("Form", "thermal"))
        self.cmapBox.setItemText(7, _translate("Form", "flame"))
        self.cmapBox.setItemText(8, _translate("Form", "yellowy"))
        self.cmapBox.setItemText(9, _translate("Form", "bipolar"))
        self.cmapBox.setItemText(10, _translate("Form", "cyclic"))
        self.cmapBox.setItemText(11, _translate("Form", "greyclip"))
        self.logButton.setText(_translate("Form", "Log"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())