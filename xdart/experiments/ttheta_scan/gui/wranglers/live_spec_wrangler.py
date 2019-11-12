# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
from collections import OrderedDict
import time
import copy
import traceback
from multiprocessing import Queue

# Other imports
import numpy as np
from paws.operations.SPEC import LoadSpecFile, MakePONI

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from .wrangler_widget import wranglerWidget
from .liveSpecUI import *
from .....gui.gui_utils import NamedActionParameter

params = [
    {'name': 'Image Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='image_dir_browse', title= 'Browse...'),
    {'name': 'Calibration PONI File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='poni_file_browse', title= 'Browse...'),
    {'name': 'Rotation Motors', 'type': 'group', 'children': [
        {'name': 'Rot1', 'type': 'str', 'default': ''},
        {'name': 'Rot2', 'type': 'str', 'default': ''},
        {'name': 'Rot3', 'type': 'str', 'default': ''}
    ]},
    {'name': 'Calibration Angles', 'type': 'group', 'children': [
        {'name': 'Rot1', 'type': 'float', 'value': 0},
        {'name': 'Rot2', 'type': 'float', 'value': 0},
        {'name': 'Rot3', 'type': 'float', 'value': 0}
    ]},

]

class liveSpecWrangler(wranglerWidget):
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.start_watching)
        self.ui.stopButton.clicked.connect(self.stop_watching)

        self.tree = ParameterTree()
        self.parameters = Parameter.create(
            name='live_spec_wrangler', type='group', children=params
        )
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout = Qt.QtWidgets.QVBoxLayout(self.ui.paramFrame)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.tree)
        self.parameters.child('image_dir_browse').sigActivated.connect(
            self.set_image_dir
        )
        self.parameters.child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )
        self.poniGen = MakePONI()
        self.parameters.sigTreeStateChanged.connect(self.update)
        self.update()
        self.showLabel.connect(self.ui.specLabel.setText)
        self.watch_queue = Queue()
    
    def set_image_dir(self):
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('Image Directory').setValue(dname)
    
    def set_poni_file(self):
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Calibration PONI File').setValue(fname)
    
    def _get_mp_inputs(self):
        mp_inputs = OrderedDict(
            rotations = {
                "rot1": None,
                "rot2": None,
                "rot3": None
            },
            calib_rotations = {
                "rot1": 0,
                "rot2": 0,
                "rot3": 0
            },
            poni_file = None,
            spec_dict = {}
        )
        rot_mot = self.parameters.child('Rotation Motors')
        for child in rot_mot:
            if child.value() == "":
                mp_inputs['rotations'][child.name().lower()] = None
            else:
                mp_inputs['rotations'][child.name().lower()] = child.value()
        
        cal_rot = self.parameters.child('Calibration Angles')
        for child in cal_rot:
            if child.value() == 0:
                pass
            else:
                mp_inputs['calib_rotations'][child.name().lower()] = child.value()
        
        mp_inputs['poni_file'] = self.parameters.child(
                                     'Calibration PONI File').value()

        return mp_inputs
    
    def read_raw(self, file, mask=True):
        with open(file, 'rb') as im:
            arr = np.fromstring(im.read(), dtype='int32')
            arr = arr.reshape((195, 487))
            if mask:
                for i in range(0, 10):
                    arr[:,i] = -2.0
                for i in range(477, 487):
                    arr[:,i] = -2.0
            return arr.T

    def update(self):
        self.poniGen.inputs.update(self._get_mp_inputs())
    
    def enabled(self, enable):
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)
    
    def stop_watching(self):
        self.watch = False
        self.sigStop.emit()
           
    def start_watching(self):
        while not self.watch_queue.empty():
            self.watch_queue.get()
        self.watch = True
        self.sigStart.emit()

    def wrangle(self, i):
        # image file names formed as predictable pattern
        while True:
            if not self.watch:
                return 'TERMINATE', None
            # Looks for relevant data, loops until it is found or a
            # timeout occurs
            added = self.watch_queue.get()
            try:
                # reads in spec data file
                self.specFile = self.specFileReader.run()

                if self.user is None:
                    self.user = self.specFile['header']['meta']['User']
                if self.spec_name is None:
                    self.spec_name = self.specFile['header']['meta']['File'][0]

                raw_file = self._get_raw_path(i)

                if self.scan_number in self.specFile['scans'].keys():
                    image_meta = self.specFile['scans']\
                                        [self.scan_number].loc[i].to_dict()
                
                else:
                    image_meta = self.specFile['current_scan'].loc[i].to_dict()
                self.poniGen.inputs['spec_dict'] = \
                    copy.deepcopy(image_meta)
                poni = copy.deepcopy(self.poniGen.run())
                arr = self.read_raw(raw_file)
                self.showLabel.emit(f'Image {i} wrangled')
        
                return 'image', (i, arr, image_meta, poni)
            except (KeyError, FileNotFoundError, AttributeError, ValueError) as e:
                print(type(e))
                print(e.args)
                traceback.print_tb(e.__traceback__)
                elapsed = time.time() - start
            if elapsed > self.timeout:
                self.showLabel.emit("Timeout occurred")
                return 'TERMINATE', None
    

