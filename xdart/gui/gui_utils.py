import numpy as np
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Point import Point
from PyQt5 import QtCore, QtGui, QtWidgets

def return_no_zero(x, y):
    return x[y > 0], y[y > 0]

def get_rect(x, y):
    left = x[0]
    top = y[0]
    width = max(x) - min(x)
    height = max(y) - min(y)
    return Qt.QtCore.QRectF(left, top, width, height)

def to_rgba(arr, cmap, alpha=1):
    img = cmap(
        (arr - arr.min()) / (arr.max() - arr.min())
    )
    img[:, :, 3] = alpha

    return img


class RectViewBox(pg.ViewBox):
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