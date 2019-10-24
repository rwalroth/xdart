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

        self.update()
    
    def update(self):
        self.update_image(self.sphere, self.arch)
        self.update_plot(self.sphere, self.arch)
    
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
        
        ydata = int_data.chi
        if self.ui.imageUnit.currentIndex() == 0:
            xdata = int_data.ttheta
        elif self.ui.imageUnit.currentIndex() == 1:
            xdata = int_data.q
        rect = get_rect(xdata, ydata, force_1=False)
        
        if self.ui.imageNRP.currentIndex() == 0:
            data = int_data.norm[()].T
        elif self.ui.imageNRP.currentIndex() == 1:
            data = int_data.raw[()].T
        elif self.ui.imageNRP.currentIndex() == 2:
            data = int_data.pcount[()].T
        
        return data, rect

    def get_arch_data_2d(self, sphere, arch):
        arc = self.sphere.arches[arch]
        int_data = arc.int_2d
        
        ydata = int_data.chi
        if self.ui.imageUnit.currentIndex() == 0:
            xdata = int_data.ttheta
        elif self.ui.imageUnit.currentIndex() == 1:
            xdata = int_data.q
        
        rect = get_rect(xdata, ydata, force_1=False)
        
        if self.ui.imageIntRaw.currentIndex() == 0:
            if self.ui.imageNRP.currentIndex() == 0:
                data = int_data.norm.copy().T
            elif self.ui.imageNRP.currentIndex() == 1:
                data = int_data.raw.copy().T
            elif self.ui.imageNRP.currentIndex() == 2:
                data = int_data.pcount.copy().T
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
        
        elif arch is not None:
            self.plot_win
            data_arch = sphere.arches[arch].int_1d.norm[()]
            data_sphere = sphere.bai_1d.norm[()]
            tth = sphere.bai_1d.ttheta[()]
            self.curve1.setData(*return_no_zero(tth, data_sphere))
            self.curve2.setData(*return_no_zero(tth, data_arch))
        
        else:
            data = sphere.bai_1d.norm[()]
            tth = sphere.bai_1d.ttheta[()]
            self.curve1.setData(*return_no_zero(tth, data))
            self.curve2.clear()
          
        

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


