import os

import numpy as np

import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Point import Point

from .plotFrameUI import * 
# Note: change u03B8 to " + u"\u03B8" after compiling for proper display

class plotFrameWidget(Qt.QtWidgets.QWidget):
    def __init__(self, parent=None, sphere=None):
        _translate = QtCore.QCoreApplication.translate
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.imageUnit2Theta.setText(_translate("Form", "2" + u"\u03B8"))
        self.ui.plotUnit2Theta.setText(_translate("Form", "2" + u"\u03B8"))

        self.image_layout = Qt.QtWidgets.QVBoxLayout(self.ui.imageFrame)
        self.image_win = pg.GraphicsLayoutWidget()
        self.image_layout.addWidget(self.image_win)
        vb = CustomViewBox()
        self.image_plot = self.image_win.addPlot(viewBox=vb)
        self.image = pg.ImageItem()
        self.image_plot.addItem(self.image)

        self.plot_layout = Qt.QtWidgets.QVBoxLayout(self.ui.plotFrame)
        self.plot_win = pg.GraphicsLayoutWidget()
        self.plot_layout.addWidget(self.plot_win)
        vb = CustomViewBox()
        self.plot_plot = self.plot_win.addPlot(viewBox=vb)
        self.plot_curve1 = self.plot_plot.plot(pen=(50,100,255))
        self.plot_curve2 = self.plot_plot.plot(
            pen=(200,50,50,200), 
            symbolBrush=(200,50,50,200), 
            symbolPen=(0,0,0,0), 
            symbolSize=4
        )

        self.update(sphere)
    
    def update(self, sphere, arch=None):
        self.update_image(sphere, arch)
        self.update_plot(sphere)
    
    def update_image(self, sphere, arch):
        if sphere is None:
            data = np.arange(100).reshape(10,10)
            rect = Qt.QtCore.QRect(1,1,1,1)
        
        elif arch is not None:
            data = sphere.arches[arch].int_2d.norm[()].T
            rect = Qt.QtCore.QRect(
                sphere.arches[arch].int_2d.ttheta[0],
                sphere.arches[arch].int_2d.chi[0],
                max(sphere.arches[arch].int_2d.ttheta) - min(sphere.arches[arch].int_2d.ttheta),
                max(sphere.arches[arch].int_2d.chi) - min(sphere.arches[arch].int_2d.chi)
            )
        
        else:
            data = sphere.bai_2d.norm[()].T
            rect = Qt.QtCore.QRect(
                sphere.bai_2d.ttheta[0],
                sphere.bai_2d.chi[0],
                max(sphere.bai_2d.ttheta) - min(sphere.bai_2d.ttheta),
                max(sphere.bai_2d.chi) - min(sphere.bai_2d.chi)
            )
        
        self.image.setImage(data)
        self.image.setRect(rect)
    
    def update_plot(self, sphere):
        data = (np.arange(100), np.arange(100))
        
        self.plot_curve1.setData(data[0], data[1])
        self.plot_curve2.setData(data[0], data[1])
          
        

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


