# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'c:\Users\walroth\Documents\repos\xdart\xdart\experiments\ttheta_scan\gui\tthetaUI.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(794, 550)
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
        self.hdf5Frame.setObjectName("hdf5Frame")
        self.metaFrame = QtWidgets.QFrame(self.leftSplitter)
        self.metaFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.metaFrame.setFrameShadow(QtWidgets.QFrame.Raised)
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
        self.middleFrame.setObjectName("middleFrame")
        self.rightFrame = QtWidgets.QFrame(self.mainSplitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.rightFrame.sizePolicy().hasHeightForWidth())
        self.rightFrame.setSizePolicy(sizePolicy)
        self.rightFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.rightFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.rightFrame.setObjectName("rightFrame")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.rightFrame)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.rightSplitter = QtWidgets.QSplitter(self.rightFrame)
        self.rightSplitter.setOrientation(QtCore.Qt.Vertical)
        self.rightSplitter.setObjectName("rightSplitter")
        self.integratorFrame = QtWidgets.QFrame(self.rightSplitter)
        self.integratorFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.integratorFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.integratorFrame.setObjectName("integratorFrame")
        self.wranglerFrame = QtWidgets.QFrame(self.rightSplitter)
        self.wranglerFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.wranglerFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.wranglerFrame.setObjectName("wranglerFrame")
        self.horizontalLayout_3.addWidget(self.rightSplitter)
        self.horizontalLayout.addWidget(self.mainSplitter)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))

