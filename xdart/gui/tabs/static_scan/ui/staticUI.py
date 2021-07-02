# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'staticUI.ui'
#
# Created by: PyQt5 UI code generator 5.15.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1920, 600)
        self.horizontalLayout = QtWidgets.QHBoxLayout(Form)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.mainSplitter = QtWidgets.QSplitter(Form)
        self.mainSplitter.setOrientation(QtCore.Qt.Horizontal)
        self.mainSplitter.setObjectName("mainSplitter")
        self.leftFrame = QtWidgets.QFrame(self.mainSplitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.leftFrame.sizePolicy().hasHeightForWidth())
        self.leftFrame.setSizePolicy(sizePolicy)
        self.leftFrame.setMinimumSize(QtCore.QSize(115, 0))
        self.leftFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.leftFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.leftFrame.setLineWidth(5)
        self.leftFrame.setObjectName("leftFrame")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.leftFrame)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.leftSplitter = QtWidgets.QSplitter(self.leftFrame)
        self.leftSplitter.setOrientation(QtCore.Qt.Vertical)
        self.leftSplitter.setObjectName("leftSplitter")
        self.hdf5Frame = QtWidgets.QFrame(self.leftSplitter)
        self.hdf5Frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.hdf5Frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.hdf5Frame.setLineWidth(3)
        self.hdf5Frame.setObjectName("hdf5Frame")
        self.metaFrame = QtWidgets.QFrame(self.leftSplitter)
        self.metaFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.metaFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.metaFrame.setLineWidth(3)
        self.metaFrame.setObjectName("metaFrame")
        self.horizontalLayout_4.addWidget(self.leftSplitter)
        self.middleFrame = QtWidgets.QFrame(self.mainSplitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.middleFrame.sizePolicy().hasHeightForWidth())
        self.middleFrame.setSizePolicy(sizePolicy)
        self.middleFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.middleFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.middleFrame.setLineWidth(5)
        self.middleFrame.setObjectName("middleFrame")
        self.rightFrame = QtWidgets.QFrame(self.mainSplitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rightFrame.sizePolicy().hasHeightForWidth())
        self.rightFrame.setSizePolicy(sizePolicy)
        self.rightFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.rightFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.rightFrame.setLineWidth(5)
        self.rightFrame.setObjectName("rightFrame")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.rightFrame)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.rightSplitter = QtWidgets.QSplitter(self.rightFrame)
        self.rightSplitter.setOrientation(QtCore.Qt.Vertical)
        self.rightSplitter.setObjectName("rightSplitter")
        self.integratorFrame = QtWidgets.QFrame(self.rightSplitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.integratorFrame.sizePolicy().hasHeightForWidth())
        self.integratorFrame.setSizePolicy(sizePolicy)
        self.integratorFrame.setMaximumSize(QtCore.QSize(16777215, 400))
        self.integratorFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.integratorFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.integratorFrame.setLineWidth(3)
        self.integratorFrame.setObjectName("integratorFrame")
        self.wranglerFrame = QtWidgets.QFrame(self.rightSplitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.wranglerFrame.sizePolicy().hasHeightForWidth())
        self.wranglerFrame.setSizePolicy(sizePolicy)
        self.wranglerFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.wranglerFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.wranglerFrame.setLineWidth(3)
        self.wranglerFrame.setObjectName("wranglerFrame")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.wranglerFrame)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.wranglerBox = QtWidgets.QComboBox(self.wranglerFrame)
        self.wranglerBox.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.wranglerBox.setObjectName("wranglerBox")
        self.verticalLayout.addWidget(self.wranglerBox)
        self.wranglerStack = QtWidgets.QStackedWidget(self.wranglerFrame)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.wranglerStack.sizePolicy().hasHeightForWidth())
        self.wranglerStack.setSizePolicy(sizePolicy)
        self.wranglerStack.setObjectName("wranglerStack")
        self.verticalLayout.addWidget(self.wranglerStack)
        self.horizontalLayout_3.addWidget(self.rightSplitter)
        self.horizontalLayout.addWidget(self.mainSplitter)

        self.retranslateUi(Form)
        self.wranglerBox.currentIndexChanged['int'].connect(self.wranglerStack.setCurrentIndex)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())
