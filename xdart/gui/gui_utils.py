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
from .range_widget import rangeWidget

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
                return str(self.dataFrame.columns.values[section])
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


class defaultWidget(Qt.QtWidgets.QWidget):
    """Pop up window for displaying default values for a parameterTree.
    
    attributes:
        layout: QGridLayout, widget layout
        openButton: QPushButton, opens default file
        parameters: pyqtgraph Parameters
        saveButton: QPushButton, saves to json file
        tree: pyqtgraph ParameterTree
    
    methods:
        load_defaults: Loads in a json file with defaults
        param_to_valdict: Prepares parameters for saving by converting
            them to dictionary
        save_defaults: Saves the default values to json file
        set_all_defaults: Makes the current values the default values
        set_defaults: Sets the default values using a provided dict
        set_parameters: Sets the list of parameters
    """
    def __init__(self, parameters=None, parent=None):
        """parameters: dict, parameters to use
        """
        super().__init__(parent)
        self.parameters = {}
        self.tree = pg.parametertree.ParameterTree()
        if parameters is not None:
            self.set_parameters(parameters)
        self.layout = Qt.QtWidgets.QGridLayout(self)
        self.setLayout(self.layout)
        self.layout.addWidget(self.tree, 0, 0, 1, 2)
        self.saveButton = Qt.QtWidgets.QPushButton()
        self.saveButton.clicked.connect(self.save_defaults)
        self.saveButton.setText("Save")
        self.layout.addWidget(self.saveButton, 1, 0)
        self.openButton = Qt.QtWidgets.QPushButton()
        self.openButton.clicked.connect(self.load_defaults)
        self.openButton.setText("Open")
        self.layout.addWidget(self.openButton, 1, 1)
    
    def set_parameters(self, parameters):
        """Sets the current parameters to the provided parameters.
        
        parameters: pyqtgraph Parameter, parameters to set
        """
        self.parameters = {}
        self.tree.clear()
        for param in parameters:
            self.parameters[param.name()] = param
            self.tree.addParameters(param)
    
    def param_to_valdict(self, param):
        """Converts parameters to dictionary
        
        args:
            param: pyqtgraph Parameter, value to be converted
        
        returns:
            valdict: dictionary of parameter values
        """
        valdict = {}
        if param.isType('group'):
            valdict[param.name()] = {}
            if param.hasChildren():
                for child in param.children():
                    valdict[param.name()].update(self.param_to_valdict(child))
        else:
            valdict[param.name()] = param.value()
        return valdict

    def set_defaults(self, param, valdict):
        """Sets the defaults of the parameters to the provided valdict
        values.
        
        args:
            param: pyqtgraph Parameter, value whose default will be set
            valdict: dict, values to be set as defaults.
        """
        if param.isType('group'):
            if param.hasChildren():
                for child in param.children():
                    self.set_defaults(child, valdict[param.name()])
        elif param.name() in valdict:
            param.setDefault(valdict[param.name()])
            param.setValue(valdict[param.name()])
    
    def save_defaults(self):
        """Opens a QFileDialog and saves the current values as json
        file.
        """
        self.set_all_defaults()
        jdict = {}
        for key, param in self.parameters.items():
            jdict[key] = self.param_to_valdict(param)
        
        fname, _ = Qt.QtWidgets.QFileDialog().getSaveFileName(filter="*.json")
        if fname != "":
            with open(fname, 'w') as f:
                json.dump(jdict, f, cls=XdartEncoder)
    
    def load_defaults(self):
        """Opens a QFileDialog and loads values from json file.
        """
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName(filter="*.json")
        if fname != "":
            with open(fname, 'r') as f:
                valdict = json.load(f, cls=XdartDecoder)
            for key, param in self.parameters.items():
                try:
                    self.set_defaults(param, valdict[key])
                except KeyError:
                    print(f"Key Error in load_default, key: {key}")
    
    def set_all_defaults(self):
        """Sets the current values to be the default values for all
        parameters
        """
        for key, param in self.parameters.items():
            valdict = self.param_to_valdict(param)
            self.set_defaults(param, valdict)


class commandLine(QtWidgets.QLineEdit):
    """Widget to simulate a command line interface. Stores past
    commands, support enter to send and up and down arrow navigation.
    
    attributes:
        current: int, index of current command
        commands: list, list of previous commands
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = -1
        self.commands = ['']
        
    def keyPressEvent(self, QKeyEvent):
        """Handles return, up, and down arrow key presses.
        """
        key = QKeyEvent.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self.send_command()
        elif key == QtCore.Qt.Key_Up:
            self.current -= 1
            if self.current < -len(self.commands):
                self.current = -len(self.commands)
            self.setText(self.commands[self.current])
        elif key == QtCore.Qt.Key_Down:
            self.current += 1
            if self.current > -1:
                self.current = -1
            self.setText(self.commands[self.current])
        else:
            super().keyPressEvent(QKeyEvent)
    
    def send_command(self):
        """Adds the current text to list of commands, clears the
        command line, and moves current index to -1. Subclasses should
        overwrite this to actually send the command, and call this
        method after to handle command storage.
        """
        command = self.text()
        if not (command.isspace() or command == ''):
            self.commands.insert(-1, command)
        self.setText('')
        self.current = -1
