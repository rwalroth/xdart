# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'displayFrameUI.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1440, 842)
        self.layout = QtWidgets.QHBoxLayout(Form)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setObjectName("layout")
        self.splitter = QtWidgets.QSplitter(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(2)
        self.splitter.setObjectName("splitter")
        self.imageWindow = QtWidgets.QFrame(self.splitter)
        self.imageWindow.setMinimumSize(QtCore.QSize(0, 440))
        self.imageWindow.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.imageWindow.setFrameShadow(QtWidgets.QFrame.Raised)
        self.imageWindow.setLineWidth(3)
        self.imageWindow.setObjectName("imageWindow")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.imageWindow)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.frame_top = QtWidgets.QFrame(self.imageWindow)
        self.frame_top.setMinimumSize(QtCore.QSize(0, 35))
        self.frame_top.setMaximumSize(QtCore.QSize(16777215, 35))
        self.frame_top.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame_top.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_top.setObjectName("frame_top")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.frame_top)
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.frame_4 = QtWidgets.QFrame(self.frame_top)
        self.frame_4.setMinimumSize(QtCore.QSize(260, 0))
        self.frame_4.setMaximumSize(QtCore.QSize(260, 16777215))
        self.frame_4.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_4.setObjectName("frame_4")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.frame_4)
        self.horizontalLayout_8.setContentsMargins(10, 0, 0, 0)
        self.horizontalLayout_8.setSpacing(0)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.normChannel = QtWidgets.QComboBox(self.frame_4)
        self.normChannel.setMinimumSize(QtCore.QSize(135, 0))
        self.normChannel.setMaximumSize(QtCore.QSize(140, 16777215))
        self.normChannel.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.normChannel.setObjectName("normChannel")
        self.normChannel.addItem("")
        self.normChannel.addItem("")
        self.normChannel.addItem("")
        self.normChannel.addItem("")
        self.normChannel.addItem("")
        self.normChannel.addItem("")
        self.horizontalLayout_7.addWidget(self.normChannel)
        spacerItem = QtWidgets.QSpacerItem(15, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem)
        self.setBkg = QtWidgets.QPushButton(self.frame_4)
        self.setBkg.setMinimumSize(QtCore.QSize(90, 0))
        self.setBkg.setMaximumSize(QtCore.QSize(100, 16777215))
        self.setBkg.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setBkg.setObjectName("setBkg")
        self.horizontalLayout_7.addWidget(self.setBkg)
        spacerItem1 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem1)
        self.horizontalLayout_8.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_5.addWidget(self.frame_4)
        self.frame_5 = QtWidgets.QFrame(self.frame_top)
        self.frame_5.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_5.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_5.setObjectName("frame_5")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.frame_5)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.labelCurrent = QtWidgets.QLabel(self.frame_5)
        font = QtGui.QFont()
        font.setPointSize(15)
        self.labelCurrent.setFont(font)
        self.labelCurrent.setAlignment(QtCore.Qt.AlignCenter)
        self.labelCurrent.setObjectName("labelCurrent")
        self.horizontalLayout_6.addWidget(self.labelCurrent)
        self.horizontalLayout_5.addWidget(self.frame_5)
        self.frame_6 = QtWidgets.QFrame(self.frame_top)
        self.frame_6.setMinimumSize(QtCore.QSize(260, 0))
        self.frame_6.setMaximumSize(QtCore.QSize(260, 16777215))
        self.frame_6.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_6.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_6.setObjectName("frame_6")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.frame_6)
        self.horizontalLayout_10.setContentsMargins(0, 0, 10, 0)
        self.horizontalLayout_10.setSpacing(0)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setSpacing(0)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        spacerItem2 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_9.addItem(spacerItem2)
        self.scale = QtWidgets.QComboBox(self.frame_6)
        self.scale.setMinimumSize(QtCore.QSize(80, 0))
        self.scale.setMaximumSize(QtCore.QSize(80, 16777215))
        self.scale.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.scale.setObjectName("scale")
        self.scale.addItem("")
        self.scale.addItem("")
        self.scale.addItem("")
        self.horizontalLayout_9.addWidget(self.scale)
        spacerItem3 = QtWidgets.QSpacerItem(15, 20, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_9.addItem(spacerItem3)
        self.cmap = QtWidgets.QComboBox(self.frame_6)
        self.cmap.setMinimumSize(QtCore.QSize(80, 0))
        self.cmap.setMaximumSize(QtCore.QSize(80, 16777215))
        self.cmap.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.cmap.setObjectName("cmap")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.cmap.addItem("")
        self.horizontalLayout_9.addWidget(self.cmap)
        self.horizontalLayout_10.addLayout(self.horizontalLayout_9)
        self.horizontalLayout_5.addWidget(self.frame_6)
        self.verticalLayout_3.addWidget(self.frame_top)
        self.twoDWindow = QtWidgets.QFrame(self.imageWindow)
        self.twoDWindow.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.twoDWindow.setFrameShadow(QtWidgets.QFrame.Raised)
        self.twoDWindow.setObjectName("twoDWindow")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.twoDWindow)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.splitter_2 = QtWidgets.QSplitter(self.twoDWindow)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setHandleWidth(2)
        self.splitter_2.setObjectName("splitter_2")
        self.imageFrame = QtWidgets.QFrame(self.splitter_2)
        self.imageFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.imageFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.imageFrame.setObjectName("imageFrame")
        self.binnedFrame = QtWidgets.QFrame(self.splitter_2)
        self.binnedFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.binnedFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.binnedFrame.setObjectName("binnedFrame")
        self.horizontalLayout_3.addWidget(self.splitter_2)
        self.verticalLayout_3.addWidget(self.twoDWindow)
        self.imageToolbar = QtWidgets.QFrame(self.imageWindow)
        self.imageToolbar.setMinimumSize(QtCore.QSize(0, 40))
        self.imageToolbar.setMaximumSize(QtCore.QSize(16777215, 40))
        self.imageToolbar.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.imageToolbar.setFrameShadow(QtWidgets.QFrame.Raised)
        self.imageToolbar.setObjectName("imageToolbar")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.imageToolbar)
        self.horizontalLayout_2.setContentsMargins(12, 0, -1, 0)
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.imageUnit = QtWidgets.QComboBox(self.imageToolbar)
        self.imageUnit.setMinimumSize(QtCore.QSize(90, 0))
        self.imageUnit.setMaximumSize(QtCore.QSize(130, 16777215))
        self.imageUnit.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.imageUnit.setObjectName("imageUnit")
        self.imageUnit.addItem("")
        self.imageUnit.addItem("")
        self.imageUnit.addItem("")
        self.horizontalLayout_2.addWidget(self.imageUnit)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem4)
        self.update2D = QtWidgets.QCheckBox(self.imageToolbar)
        self.update2D.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.update2D.setChecked(True)
        self.update2D.setObjectName("update2D")
        self.horizontalLayout_2.addWidget(self.update2D)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem5)
        self.shareAxis = QtWidgets.QCheckBox(self.imageToolbar)
        self.shareAxis.setMaximumSize(QtCore.QSize(90, 16777215))
        self.shareAxis.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.shareAxis.setObjectName("shareAxis")
        self.horizontalLayout_2.addWidget(self.shareAxis)
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem6)
        self.save_2D = QtWidgets.QPushButton(self.imageToolbar)
        self.save_2D.setObjectName("save_2D")
        self.horizontalLayout_2.addWidget(self.save_2D)
        self.verticalLayout_3.addWidget(self.imageToolbar)
        self.plotWindow = QtWidgets.QFrame(self.splitter)
        self.plotWindow.setMinimumSize(QtCore.QSize(0, 400))
        self.plotWindow.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.plotWindow.setFrameShadow(QtWidgets.QFrame.Raised)
        self.plotWindow.setLineWidth(3)
        self.plotWindow.setObjectName("plotWindow")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.plotWindow)
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.oneDWindow = QtWidgets.QFrame(self.plotWindow)
        self.oneDWindow.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.oneDWindow.setFrameShadow(QtWidgets.QFrame.Raised)
        self.oneDWindow.setObjectName("oneDWindow")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.oneDWindow)
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.splitter_3 = QtWidgets.QSplitter(self.oneDWindow)
        self.splitter_3.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_3.setHandleWidth(2)
        self.splitter_3.setObjectName("splitter_3")
        self.plotFrame = QtWidgets.QFrame(self.splitter_3)
        self.plotFrame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.plotFrame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.plotFrame.setObjectName("plotFrame")
        self.horizontalLayout_4.addWidget(self.splitter_3)
        self.verticalLayout_4.addWidget(self.oneDWindow)
        self.plotToolBar = QtWidgets.QFrame(self.plotWindow)
        self.plotToolBar.setMinimumSize(QtCore.QSize(0, 40))
        self.plotToolBar.setMaximumSize(QtCore.QSize(16777215, 40))
        self.plotToolBar.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.plotToolBar.setFrameShadow(QtWidgets.QFrame.Raised)
        self.plotToolBar.setObjectName("plotToolBar")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.plotToolBar)
        self.horizontalLayout.setContentsMargins(12, 0, -1, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.plotUnit = QtWidgets.QComboBox(self.plotToolBar)
        self.plotUnit.setMinimumSize(QtCore.QSize(70, 0))
        self.plotUnit.setMaximumSize(QtCore.QSize(100, 16777215))
        self.plotUnit.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.plotUnit.setObjectName("plotUnit")
        self.plotUnit.addItem("")
        self.plotUnit.addItem("")
        self.plotUnit.addItem("")
        self.horizontalLayout.addWidget(self.plotUnit)
        self.slice = QtWidgets.QCheckBox(self.plotToolBar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.slice.sizePolicy().hasHeightForWidth())
        self.slice.setSizePolicy(sizePolicy)
        self.slice.setMinimumSize(QtCore.QSize(80, 0))
        self.slice.setMaximumSize(QtCore.QSize(80, 16777215))
        self.slice.setObjectName("slice")
        self.horizontalLayout.addWidget(self.slice)
        self.slice_center = QtWidgets.QDoubleSpinBox(self.plotToolBar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.slice_center.sizePolicy().hasHeightForWidth())
        self.slice_center.setSizePolicy(sizePolicy)
        self.slice_center.setMinimumSize(QtCore.QSize(70, 0))
        self.slice_center.setMaximumSize(QtCore.QSize(70, 16777215))
        self.slice_center.setToolTip("")
        self.slice_center.setToolTipDuration(2)
        self.slice_center.setWhatsThis("")
        self.slice_center.setAccessibleDescription("")
        self.slice_center.setMinimum(-180.0)
        self.slice_center.setMaximum(180.0)
        self.slice_center.setSingleStep(0.5)
        self.slice_center.setProperty("value", 0.0)
        self.slice_center.setObjectName("slice_center")
        self.horizontalLayout.addWidget(self.slice_center)
        self.slice_width = QtWidgets.QDoubleSpinBox(self.plotToolBar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.slice_width.sizePolicy().hasHeightForWidth())
        self.slice_width.setSizePolicy(sizePolicy)
        self.slice_width.setMinimumSize(QtCore.QSize(70, 0))
        self.slice_width.setMaximumSize(QtCore.QSize(70, 16777215))
        self.slice_width.setToolTip("")
        self.slice_width.setMinimum(0.0)
        self.slice_width.setMaximum(270.0)
        self.slice_width.setSingleStep(0.5)
        self.slice_width.setProperty("value", 5.0)
        self.slice_width.setObjectName("slice_width")
        self.horizontalLayout.addWidget(self.slice_width)
        spacerItem7 = QtWidgets.QSpacerItem(80, 20, QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem7)
        self.plotMethod = QtWidgets.QComboBox(self.plotToolBar)
        self.plotMethod.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.plotMethod.setObjectName("plotMethod")
        self.plotMethod.addItem("")
        self.plotMethod.addItem("")
        self.plotMethod.addItem("")
        self.plotMethod.addItem("")
        self.plotMethod.addItem("")
        self.horizontalLayout.addWidget(self.plotMethod)
        self.yOffsetLabel = QtWidgets.QLabel(self.plotToolBar)
        self.yOffsetLabel.setMaximumSize(QtCore.QSize(140, 16777215))
        self.yOffsetLabel.setObjectName("yOffsetLabel")
        self.horizontalLayout.addWidget(self.yOffsetLabel)
        self.yOffset = QtWidgets.QDoubleSpinBox(self.plotToolBar)
        self.yOffset.setEnabled(False)
        self.yOffset.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.yOffset.setDecimals(0)
        self.yOffset.setSingleStep(5.0)
        self.yOffset.setProperty("value", 5.0)
        self.yOffset.setObjectName("yOffset")
        self.horizontalLayout.addWidget(self.yOffset)
        self.wf_options = QtWidgets.QPushButton(self.plotToolBar)
        self.wf_options.setEnabled(False)
        self.wf_options.setToolTip("")
        self.wf_options.setWhatsThis("")
        self.wf_options.setObjectName("wf_options")
        self.horizontalLayout.addWidget(self.wf_options)
        spacerItem8 = QtWidgets.QSpacerItem(30, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem8)
        self.showLegend = QtWidgets.QCheckBox(self.plotToolBar)
        self.showLegend.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.showLegend.setChecked(True)
        self.showLegend.setObjectName("showLegend")
        self.horizontalLayout.addWidget(self.showLegend)
        self.clear_1D = QtWidgets.QPushButton(self.plotToolBar)
        self.clear_1D.setObjectName("clear_1D")
        self.horizontalLayout.addWidget(self.clear_1D)
        self.save_1D = QtWidgets.QPushButton(self.plotToolBar)
        self.save_1D.setObjectName("save_1D")
        self.horizontalLayout.addWidget(self.save_1D)
        self.verticalLayout_4.addWidget(self.plotToolBar)
        self.layout.addWidget(self.splitter)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        Form.setTabOrder(self.normChannel, self.setBkg)
        Form.setTabOrder(self.setBkg, self.scale)
        Form.setTabOrder(self.scale, self.cmap)
        Form.setTabOrder(self.cmap, self.imageUnit)
        Form.setTabOrder(self.imageUnit, self.save_2D)
        Form.setTabOrder(self.save_2D, self.plotUnit)
        Form.setTabOrder(self.plotUnit, self.slice_center)
        Form.setTabOrder(self.slice_center, self.slice_width)
        Form.setTabOrder(self.slice_width, self.plotMethod)
        Form.setTabOrder(self.plotMethod, self.yOffset)
        Form.setTabOrder(self.yOffset, self.save_1D)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.normChannel.setItemText(0, _translate("Form", "Norm Channel"))
        self.normChannel.setItemText(1, _translate("Form", "Monitor"))
        self.normChannel.setItemText(2, _translate("Form", "sec"))
        self.normChannel.setItemText(3, _translate("Form", "bstop"))
        self.normChannel.setItemText(4, _translate("Form", "I0"))
        self.normChannel.setItemText(5, _translate("Form", "I1"))
        self.setBkg.setText(_translate("Form", "Set Bkg"))
        self.labelCurrent.setText(_translate("Form", "Current"))
        self.scale.setItemText(0, _translate("Form", "Linear"))
        self.scale.setItemText(1, _translate("Form", "Log"))
        self.scale.setItemText(2, _translate("Form", "Sqrt"))
        self.cmap.setItemText(0, _translate("Form", "Default"))
        self.cmap.setItemText(1, _translate("Form", "viridis"))
        self.cmap.setItemText(2, _translate("Form", "grey"))
        self.cmap.setItemText(3, _translate("Form", "plasma"))
        self.cmap.setItemText(4, _translate("Form", "inferno"))
        self.cmap.setItemText(5, _translate("Form", "magma"))
        self.cmap.setItemText(6, _translate("Form", "thermal"))
        self.cmap.setItemText(7, _translate("Form", "flame"))
        self.cmap.setItemText(8, _translate("Form", "yellowy"))
        self.cmap.setItemText(9, _translate("Form", "bipolar"))
        self.cmap.setItemText(10, _translate("Form", "greyclip"))
        self.imageUnit.setItemText(0, _translate("Form", "Q-Chi"))
        self.imageUnit.setItemText(1, _translate("Form", "2Th-Chi"))
        self.imageUnit.setItemText(2, _translate("Form", "Qz-Qxy"))
        self.update2D.setText(_translate("Form", "Update 2D"))
        self.shareAxis.setText(_translate("Form", "Share Axis"))
        self.save_2D.setText(_translate("Form", "Save"))
        self.plotUnit.setItemText(0, _translate("Form", "Q (A-1)"))
        self.plotUnit.setItemText(1, _translate("Form", "2 u\\u03B8"))
        self.plotUnit.setItemText(2, _translate("Form", "Chi"))
        self.slice.setText(_translate("Form", "X Range"))
        self.plotMethod.setItemText(0, _translate("Form", "Single"))
        self.plotMethod.setItemText(1, _translate("Form", "Overlay"))
        self.plotMethod.setItemText(2, _translate("Form", "Average"))
        self.plotMethod.setItemText(3, _translate("Form", "Sum"))
        self.plotMethod.setItemText(4, _translate("Form", "Waterfall"))
        self.yOffsetLabel.setToolTip(_translate("Form", "y Offset for Overlay Mode"))
        self.yOffsetLabel.setText(_translate("Form", "Offset"))
        self.wf_options.setText(_translate("Form", "Options"))
        self.showLegend.setText(_translate("Form", "Legend"))
        self.clear_1D.setText(_translate("Form", "Clear"))
        self.save_1D.setText(_translate("Form", "Save"))
