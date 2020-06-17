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
from ..gui_utils import XdartDecoder, XdartEncoder

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
    sigSetUserDefaults = Qt.QtCore.Signal()

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
    
    def save_defaults(self, checked=False, fname=None):
        """Opens a QFileDialog and saves the current values as json
        file.

        Parameters
        ----------
        fname : str, path to file to save defaults
        """
        emit = False
        if fname is None:
            fname, _ = Qt.QtWidgets.QFileDialog().getSaveFileName(filter="*.json")
            emit = True
        self.set_all_defaults()
        jdict = {}
        for key, param in self.parameters.items():
            jdict[key] = self.param_to_valdict(param)

        if fname != "":
            with open(fname, 'w') as f:
                json.dump(jdict, f, cls=XdartEncoder)
        if emit:
            self.sigSetUserDefaults.emit()
    
    def load_defaults(self, checked=False, fname=None):
        """Opens a QFileDialog and loads values from json file.

        Parameters
        ----------
        checked : bool, used by QAction triggered signal
        fname : str, path to file to load
        """
        emit = False
        if fname is None:
            fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName(filter="*.json")
            emit = True
        if fname != "":
            with open(fname, 'r') as f:
                valdict = json.load(f, cls=XdartDecoder)
            for key, param in self.parameters.items():
                try:
                    self.set_defaults(param, valdict[key])
                except KeyError:
                    print(f"Key Error in load_default, key: {key}")
        if emit:
            self.sigSetUserDefaults.emit()
    
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