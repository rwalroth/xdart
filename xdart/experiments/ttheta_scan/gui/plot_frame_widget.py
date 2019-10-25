import os

import numpy as np

import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Point import Point

from .plotFrameUI import * 
from .gui_utils import *
# Note: change u03B8 to " + u"\u03B8" after compiling for proper display

class plotFrameWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None, sphere=None):
        _translate = QtCore.QCoreApplication.translate
        super().__init__(parent)
        self.sphere = None
        self.arch = None
        self.auto_last = False

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.image_layout = Qt.QtWidgets.QVBoxLayout(self.ui.imageFrame)
        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        self.imageViewBox = CustomViewBox()
        self.image_plot = self.image_win.addPlot(viewBox=self.imageViewBox)
        self.image = pg.ImageItem()
        self.image_plot.addItem(self.image)

        self.ui.imageUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))
        self.ui.imageIntRaw.activated.connect(self.update)
        self.ui.imageMethod.activated.connect(self.update)
        self.ui.imageUnit.activated.connect(self.update)
        self.ui.imageNRP.activated.connect(self.update)
        self.ui.imageMask.stateChanged.connect(self.update)
        self.ui.shareAxis.stateChanged.connect(self.update)

        self.plot_layout = Qt.QtWidgets.QVBoxLayout(self.ui.plotFrame)
        self.plot_win = pg.GraphicsLayoutWidget()
        self.plot_layout.addWidget(self.plot_win)
        vb = CustomViewBox()
        self.plot = self.plot_win.addPlot(viewBox=vb)
        self.curve1 = self.plot.plot(pen=(50,100,255))
        self.curve2 = self.plot.plot(
            pen=(200,50,50,200), 
            symbolBrush=(200,50,50,200), 
            symbolPen=(0,0,0,0), 
            symbolSize=4
        )

        self.ui.plotUnit.setItemText(0, _translate("Form", "2" + u"\u03B8"))
        self.ui.plotMethod.activated.connect(self.update)
        self.ui.plotUnit.activated.connect(self.update)
        self.ui.plotNRP.activated.connect(self.update)
        self.ui.plotOverlay.stateChanged.connect(self.update)

        self.ui.pushRight.clicked.connect(self.next_arch)
        self.ui.pushLeft.clicked.connect(self.prev_arch)
        self.ui.pushRightLast.clicked.connect(self.last_arch)
        self.ui.pushLeftLast.clicked.connect(self.first_arch)

        self.update()
    
    def update(self):
        if self.sphere is not None:
            if self.arch is None:
                self.ui.labelCurrent.setText(self.sphere.name)
            else:
                self.ui.labelCurrent.setText("Image " + str(self.arch))

        if self.ui.shareAxis.isChecked():
            self.ui.plotUnit.setCurrentIndex(self.ui.imageUnit.currentIndex())
            self.plot.setXLink(self.image_plot)
        else:
            self.plot.setXLink(None)
        if self.auto_last and self.sphere is not None:
            self.arch = self.sphere.arches.iloc[-1].idx
        self.update_image(self.sphere, self.arch)
        self.update_plot(self.sphere, self.arch)

    def read_NRP(self, box, int_data):
        if box.currentIndex() == 0:
            data = int_data.norm[()].T
        elif box.currentIndex() == 1:
            data = int_data.raw[()].T
        elif box.currentIndex() == 2:
            data = int_data.pcount[()].T
        return data

    def get_xdata(self, box, int_data):
        if box.currentIndex() == 0:
            xdata = int_data.ttheta
        elif box.currentIndex() == 1:
            xdata = int_data.q
        return xdata
    
    def update_image(self, sphere, arch):
        if sphere is None:
            data = np.arange(100).reshape(10,10)
            rect = Qt.QtCore.QRect(1,1,1,1)
        
        elif arch is not None:
            data, rect = self.get_arch_data_2d(sphere, arch)
        
        else:
            data, rect = self.get_sphere_data_2d(sphere)
        
        self.image.setImage(data)
        self.image.setRect(rect)

    def get_sphere_data_2d(self, sphere):
        if self.ui.imageMethod.currentIndex() == 0:
            int_data = sphere.mgi_2d
            if type(int_data.ttheta) == int:
                self.ui.imageMethod.setCurrentIndex(1)
                int_data = sphere.bai_2d
        elif self.ui.imageMethod.currentIndex() == 1:
            int_data = sphere.bai_2d
        
        rect = get_rect(
            self.get_xdata(self.ui.imageUnit, int_data), 
            int_data.chi
        )
        
        data = self.read_NRP(self.ui.imageNRP, int_data)
        
        return data, rect

    def get_arch_data_2d(self, sphere, arch):
        arc = sphere.arches[arch]
        int_data = arc.int_2d
        
        rect = get_rect(
            self.get_xdata(self.ui.imageUnit, int_data), 
            int_data.chi
        )
        
        if self.ui.imageIntRaw.currentIndex() == 0:
            data = self.read_NRP(self.ui.imageNRP, int_data)
        
        elif self.ui.imageIntRaw.currentIndex() == 1:
            if self.ui.imageNRP.currentIndex() == 0:
                data = arc.map_norm.copy()
            else:
                data = arc.map_raw.copy()
            if self.ui.imageMask.isChecked():
                data *= np.where(arc.mask==1, 0, np.ones_like(arc.mask))
        
        return data, rect
    
    def update_plot(self, sphere, arch):
        if sphere is None:
            data = (np.arange(100), np.arange(100))
            self.curve1.setData(data[0], data[1])
            self.curve2.setData(data[0], data[1])
            return data
        
        else:
            if self.ui.plotMethod.currentIndex() == 0:
                sphere_int_data = sphere.mgi_1d
                if type(sphere_int_data.ttheta) == int:
                    self.ui.plotMethod.setCurrentIndex(1)
                    sphere_int_data = sphere.bai_1d
            elif self.ui.plotMethod.currentIndex() == 1:
                sphere_int_data = sphere.bai_1d
            
            s_ydata = self.read_NRP(self.ui.plotNRP, sphere_int_data)
            xdata = self.get_xdata(self.ui.plotUnit, sphere_int_data)

            if arch is not None:
                arc_int_data = sphere.arches[arch].int_1d

                if self.ui.plotOverlay.isChecked():
                    self.curve1.setData(*return_no_zero(xdata, s_ydata))
                else:
                    self.curve1.clear()
                
                a_ydata = self.read_NRP(self.ui.plotNRP, arc_int_data)
                self.curve2.setData(*return_no_zero(xdata, a_ydata))

                return return_no_zero(xdata, a_ydata)
            
            else:
                self.curve1.setData(*return_no_zero(xdata, s_ydata))
                self.curve2.clear()

                return return_no_zero(xdata, s_ydata)
    
    def next_arch(self):
        if self.arch == self.sphere.arches.iloc[-1].idx or self.arch is None:
            pass
        else:
            self.arch += 1
            self.auto_last = False
            self.ui.pushRightLast.setEnabled(True)
            self.update()
    
    def prev_arch(self):
        if self.arch == self.sphere.arches.iloc[0].idx or self.arch is None:
            pass
        else:
            self.arch -= 1
            self.auto_last = False
            self.ui.pushRightLast.setEnabled(True)
            self.update()
    
    def last_arch(self):
        if self.arch is None:
            pass

        else: 
            if self.arch == self.sphere.arches.iloc[-1].idx:
                pass

            else:
                self.arch = self.sphere.arches.iloc[-1].idx
                self.update()
        
            self.auto_last = True
            self.ui.pushRightLast.setEnabled(False)

    def first_arch(self):
        if self.arch == self.sphere.arches.iloc[0].idx or self.arch is None:
            pass
        else:
            self.arch = self.sphere.arches.iloc[0].idx
            self.auto_last = False
            self.ui.pushRightLast.setEnabled(True)
            self.update()
          
        

class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)
        
    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            self.autoRange()
            
    def mouseDragEvent(self, ev, axis=None):
        ev.accept()  ## we accept all buttons
        
        pos = ev.pos()
        lastPos = ev.lastPos()
        dif = pos - lastPos
        dif = dif * -1

        ## Ignore axes if mouse is disabled
        mouseEnabled = np.array(self.state['mouseEnabled'], dtype=np.float)
        mask = mouseEnabled.copy()
        if axis is not None:
            mask[1-axis] = 0.0

        if ev.button() == QtCore.Qt.RightButton:
            ev.ignore()
        
        elif ev.button() == QtCore.Qt.LeftButton:
            pg.ViewBox.mouseDragEvent(self, ev)
        
        else:
            tr = dif*mask
            tr = self.mapToView(tr) - self.mapToView(Point(0,0))
            x = tr.x() if mask[0] == 1 else None
            y = tr.y() if mask[1] == 1 else None
            
            self._resetTarget()
            if x is not None or y is not None:
                self.translateBy(x=x, y=y)
            self.sigRangeChangedManually.emit(self.state['mouseEnabled'])


