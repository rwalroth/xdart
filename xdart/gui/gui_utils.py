# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
import json

# Other imports
import numpy as np
import pandas as pd
from pyFAI.units import Unit

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.Point import Point
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from pyqtgraph.parametertree.ParameterItem import ParameterItem
from pyqtgraph.parametertree.Parameter import Parameter

# This module imports


def return_no_zero(x, y):
    """Returns only values greater than 0 for plotting.
    
    args:
        x, y: arrays, x and y data
    
    returns:
        x[y > 0], y[y > 0]
    """
    return x[y > 0], y[y > 0]


def get_rect(x, y):
    """Gets a QRectF object from given x and y data.
    
    args:
        x, y: arrays, x and y data
    
    returns:
        QRectF object
    """
    left = x[0]
    top = y[0]
    width = max(x) - min(x)
    height = max(y) - min(y)
    return Qt.QtCore.QRectF(left, top, width, height)


def to_rgba(arr, cmap, alpha=1):
    """Converts array to rgba image.
    
    args:
        arr: numpy array, 2D array to convert
        cmap: colormap to use
        alpha: scalar or array of same shape as arr, alpha values
    
    returns:
        img: numpy array, 3D rgba array
    """
    img = cmap(
        (arr - arr.min()) / (arr.max() - arr.min())
    )
    img[:, :, 3] = alpha

    return img


class RectViewBox(pg.ViewBox):
    """Special viewbox based on pyqtgraph ViewBox. Uses a box for zoom
    functions, scroll wheel to zoom.
    """
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


class DFTableModel(QtCore.QAbstractTableModel):
    """TableModel for handling pandas DataFrame. Used with a QTableView.
    See QAbstractTableModel for details on implemented methods.
    
    attributes:
        dataFrame: pandas DataFrame, where data is stored.
    """
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        if data is None:
            data = pd.DataFrame()
        self.dataFrame = data
    
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self.dataFrame.iloc[index.row(), index.column()])
        return None

    def rowCount(self, parent):
        return self.dataFrame.shape[0]
    
    def columnCount(self, parent):
        return self.dataFrame.shape[1]
    
    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                try:
                    return str(self.dataFrame.columns.values[section])
                except IndexError:
                    return ' '
            elif orientation == QtCore.Qt.Vertical:
                return str(self.dataFrame.index[section])
        return QtCore.QAbstractTableModel.headerData(self, section, orientation, role)
    
    
class NamedActionParameterItem(ParameterItem):
    """pyqtgraph ActionParameterItem which can display a title.
    """
    def __init__(self, param, depth):
        ParameterItem.__init__(self, param, depth)
        self.layoutWidget = QtGui.QWidget()
        self.layout = QtGui.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layoutWidget.setLayout(self.layout)
        title = param.opts.get('title', None)
        if title is None:
            title = param.name()
        self.button = QtGui.QPushButton(title)
        #self.layout.addSpacing(100)
        self.layout.addWidget(self.button)
        self.layout.addStretch()
        self.button.clicked.connect(self.buttonClicked)
        param.sigNameChanged.connect(self.paramRenamed)
        self.setText(0, '')
        
    def treeWidgetChanged(self):
        ParameterItem.treeWidgetChanged(self)
        tree = self.treeWidget()
        if tree is None:
            return
        
        tree.setFirstItemColumnSpanned(self, True)
        tree.setItemWidget(self, 0, self.layoutWidget)
        
    def paramRenamed(self, param, name):
        self.button.setText(name)
        
    def buttonClicked(self):
        self.param.activate()

        
class NamedActionParameter(Parameter):
    """Used for displaying a button within the tree."""
    itemClass = NamedActionParameterItem
    sigActivated = QtCore.Signal(object)
    
    def activate(self):
        self.sigActivated.emit(self)
        self.emitStateChanged('activated', None)


class XdartEncoder(json.JSONEncoder):
    def default(self, o):
        if type(o) == Unit:
            return {
                '_type': 'pfunit',
                'value': str(o)
            }
        return super().default(o)


class XdartDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)
    
    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        if obj['_type'] == 'pfunit':
            return Unit(obj['value'])
        return obj
