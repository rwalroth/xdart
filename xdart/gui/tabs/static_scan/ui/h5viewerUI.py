# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'h5viewerUI.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1440, 842)
        Form.setMinimumSize(QtCore.QSize(0, 0))
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setContentsMargins(8, 8, 8, 12)
        self.gridLayout.setObjectName("gridLayout")
        self.label_3 = QtWidgets.QLabel(Form)
        self.label_3.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(Form)
        self.label_4.setMaximumSize(QtCore.QSize(70, 16777215))
        self.label_4.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 1, 1, 1, 1)
        self.show_all = QtWidgets.QPushButton(Form)
        self.show_all.setMaximumSize(QtCore.QSize(16777215, 25))
        self.show_all.setObjectName("show_all")
        self.gridLayout.addWidget(self.show_all, 3, 0, 1, 1)
        self.auto_last = QtWidgets.QPushButton(Form)
        self.auto_last.setMaximumSize(QtCore.QSize(16777215, 25))
        self.auto_last.setObjectName("auto_last")
        self.gridLayout.addWidget(self.auto_last, 3, 1, 1, 1)
        self.splitter = QtWidgets.QSplitter(Form)
        self.splitter.setMinimumSize(QtCore.QSize(0, 0))
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.listScans = QtWidgets.QListWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listScans.sizePolicy().hasHeightForWidth())
        self.listScans.setSizePolicy(sizePolicy)
        self.listScans.setMinimumSize(QtCore.QSize(30, 0))
        self.listScans.setResizeMode(QtWidgets.QListView.Adjust)
        self.listScans.setObjectName("listScans")
        self.listData = QtWidgets.QListWidget(self.splitter)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.listData.sizePolicy().hasHeightForWidth())
        self.listData.setSizePolicy(sizePolicy)
        self.listData.setMinimumSize(QtCore.QSize(45, 0))
        self.listData.setMaximumSize(QtCore.QSize(60, 16777215))
        self.listData.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.listData.setTabKeyNavigation(False)
        self.listData.setAlternatingRowColors(True)
        self.listData.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.listData.setObjectName("listData")
        self.gridLayout.addWidget(self.splitter, 2, 0, 1, 2)
        self.frame = QtWidgets.QFrame(Form)
        self.frame.setMaximumSize(QtCore.QSize(16777215, 20))
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.gridLayout.addWidget(self.frame, 0, 0, 1, 2)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label_3.setText(_translate("Form", "  Scans"))
        self.label_4.setText(_translate("Form", "Data"))
        self.show_all.setText(_translate("Form", "Show All"))
        self.auto_last.setText(_translate("Form", "Auto Last"))
