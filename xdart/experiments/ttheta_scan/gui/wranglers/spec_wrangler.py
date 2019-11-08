# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports
import os
from collections import OrderedDict
import time
import copy

# Other imports
import numpy as np
from paws.operations.SPEC import LoadSpecFile, MakePONI

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from .specUI import *
from .....gui.gui_utils import NamedActionParameter

params = [
    {'name': 'Scan Number', 'type': 'int', 'value': 0},
    {'name': 'Spec File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='spec_file_browse', title= 'Browse...'),
    {'name': 'Image Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='image_dir_browse', title= 'Browse...'),
    {'name': 'Calibration PONI File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='poni_file_browse', title= 'Browse...'),
    {'name': 'Timeout', 'type': 'float', 'value': 5},
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

class specWrangler(Qt.QtWidgets.QWidget):
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.tree = ParameterTree()
        self.parameters = Parameter.create(
            name='params', type='group', children=params
        )
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout = Qt.QtWidgets.QVBoxLayout(self.ui.paramFrame)
        self.layout.addWidget(self.tree)
        self.parameters.child('spec_file_browse').sigActivated.connect(
            self.set_spec_file
        )
        self.parameters.child('image_dir_browse').sigActivated.connect(
            self.set_image_dir
        )
        self.parameters.child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )
        self.specFileReader = LoadSpecFile()
        self.poniGen = MakePONI()
        self.specFile = {}
        self.spec_name = None
        self.user = None
        self.scan_number = 0
        self.timeout = 5
        self.parameters.sigTreeStateChanged.connect(self.update)
        self.update()
        self.showLabel.connect(self.ui.specLabel.setText)
    
    def set_spec_file(self):
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Spec File').setValue(fname)
    
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
            if child.valueIsDefault():
                pass
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

    def _get_lsf_inputs(self):
        dirname, fname = os.path.split(self.parameters.child('Spec File').value())
        lsf_inputs = OrderedDict(
            spec_file_path=dirname,
            spec_file_name=fname
        )

        return lsf_inputs

    def _get_raw_path(self, i):
        im_base = '_'.join([
            self.user,
            self.spec_name,
            'scan' + str(self.parameters.child('Scan Number').value()),
            str(i).zfill(4)
        ])
        return os.path.join(
            self.parameters.child('Image Directory').value(), im_base + '.raw')
    
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
        self.specFileReader.inputs.update(self._get_lsf_inputs())
        self.scan_number = self.parameters.child('Scan Number').value()
        self.timeout = self.parameters.child('Timeout').value()
    
    def enabled(self, enable):
        self.tree.setEnabled(enable)

    def wrangle(self, i):
        self.showLabel.emit(f'Checking for {i}')

        # image file names formed as predictable pattern

        start = time.time()
        limit = np.inf
        while True:
            if i > limit:
                return 'TERMINATE', None
            # Looks for relevant data, loops until it is found or a
            # timeout occurs
            try:
                # reads in spec data file
                self.specFile = self.specFileReader.run()

                if self.user is None:
                    self.user = self.specFile['header']['meta']['User']
                if self.spec_name is None:
                    self.spec_name = self.specFile['header']['meta']['File'][0]

                raw_file = self._get_raw_path(i)

                if self.scan_number in self.specFile['scans'].keys():
                    print(self.scan_number)
                    image_meta = self.specFile['scans']\
                                        [self.scan_number].loc[i].to_dict()
                
                else:
                    print('not found')
                    image_meta = self.specFile['current_scan'].loc[i].to_dict()
                self.poniGen.inputs['spec_dict'] = \
                    copy.deepcopy(image_meta)
                poni = copy.deepcopy(self.poniGen.run())
                arr = self.read_raw(raw_file)
                self.showLabel.emit(f'Image {i} wrangled')
        
                return 'image', (i, arr, image_meta, poni)
            except (KeyError, FileNotFoundError, AttributeError, ValueError) as e:
                print(e)
                elapsed = time.time() - start
            if elapsed > self.timeout:
                self.showLabel.emit("Timeout occurred")
                return 'TERMINATE', None
    

