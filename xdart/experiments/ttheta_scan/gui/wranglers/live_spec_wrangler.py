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
from .....pySSRL_bServer.watcher import Watcher
from .....pySSRL_bServer.helper_funcs import get_from_pdi
from .....pySSRL_bServer.bServer_funcs import specCommand

params = [
    {'name': 'Image Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='image_dir_browse', title= 'Browse...'),
    {'name': 'PDI Directory', 'type': 'str', 'default': ''},
    NamedActionParameter(name='pdi_dir_browse', title= 'Browse...'),
    {'name': 'File Types', 'type': 'str', 'default': "raw, pdi"},
    {'name': 'Polling Period', 'type': 'float', 'default': 0.1},
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
        self.ui.buttonSend.clicked.connect(self.send_command)
        self.keep_trying = True

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
        self.parameters.child('pdi_dir_browse').sigActivated.connect(
            self.set_pdi_dir
        )
        self.parameters.child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )
        self.poniGen = MakePONI()
        self.parameters.sigTreeStateChanged.connect(self.update)
        self.update()
        self.showLabel.connect(self.ui.specLabel.setText)
        self.watch_command = Queue()
        self.cache = None
    
    def send_command(self):
        command = self.ui.specCommandLine.text()
        specCommand(command, queue=False)
    
    def set_image_dir(self):
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('Image Directory').setValue(dname)
    
    def set_pdi_dir(self):
        dname = Qt.QtWidgets.QFileDialog.getExistingDirectory(self)
        if dname != '':
            self.parameters.child('PDI Directory').setValue(dname)
    
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
        self.watch_command.put('stop')
        self.keep_trying = False
        self.sigStop.emit()
           
    def start_watching(self):
        self.keep_trying = True
        pollingPeriod=self.parameters.child('Polling Period').value()
        if pollingPeriod <= 0:
            pollingPeriod = 0.1
        self.queues = {fp: Queue() for fp in 
            self.parameters.child('File Types').value().split()
        }
        self.watcher = Watcher(
            watchPaths=[
                self.parameters.child('Image Directory').value(),
                self.parameters.child('PDI Directory').value(),
            ],
            filetypes=self.parameters.child('File Types').value().split(),
            pollingPeriod=pollingPeriod,
            queues=self.queues,
            command_q = self.watch_command,
            daemon=True
        )
        self.watcher.start()
        self.sigStart.emit()
    
    def parse_file(self, path):
        _, name = os.path.split(path)
        name = name.split('.')[0]
        args = name.split('_')
        scan_name = args[-2]
        scan_number = int(scan_name[4:])
        idx = int(args[-1])
        return scan_number, idx
    
    def read_pdi(self, pdi_file):
        counters, motors = get_from_pdi(pdi_file)
        image_meta = {}
        image_meta.update(counters)
        image_meta.update(motors)
        return image_meta

    def wrangle(self, i):
        # image file names formed as predictable pattern
        cache = False
        if self.cache is not None:
            cache = copy.deepcopy(self.cache)
            self.cache = None
            return cache[0], cache[1]
        for key, q in self.queues.items():
            added = q.get()
            self.showLabel.emit(added)
            print(type(added))
            print(added)
            if added == 'BREAK':
                print('breaking')
                return 'TERMINATE', None
            elif key == 'pdi':
                pdi_file = added
            elif key == 'raw':
                raw_file = added
        
        scan_number, i = self.parse_file(raw_file)
        if scan_number != self.scan_number:
            cache = True
            self.scan_number = scan_number
        while self.keep_trying:
            # Looks for relevant data, loops until it is found or a
            # timeout occurs
            try:
                arr = self.read_raw(raw_file)

                image_meta = self.read_pdi(pdi_file)

                self.poniGen.inputs['spec_dict'] = copy.deepcopy(image_meta)

                poni = copy.deepcopy(self.poniGen.run())

                if cache:
                    self.cache = 'image', (i, arr, image_meta, poni)
                    self.sigEndScan.emit()
                    self.sigNewScan.emit(scan_number)
                    time.sleep(0.1)
                    return 'TERMINATE', None
                else:
                    return 'image', (i, arr, image_meta, poni)

            except (KeyError, FileNotFoundError, AttributeError, ValueError) as e:
                print(type(e))
                traceback.print_tb(e.__traceback__)
        return 'TERMINATE', None
    

