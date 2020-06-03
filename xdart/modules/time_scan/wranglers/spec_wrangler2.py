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

# Other imports
import numpy as np
from xdart.classes.spec import MakePONI, get_spec_header, get_spec_scan
from xdart.containers import PONI
from xdart.classes.ewald import EwaldArch, EwaldSphere
from xdart.utils import catch_h5py_file as catch
from xdart.utils import read_image_file, get_image_meta_data

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .specUI import Ui_Form
from xdart.gui.gui_utils import NamedActionParameter

params = [
    {'name': 'Scan Number', 'type': 'int', 'value': 0},
    {'name': 'Spec File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='spec_file_browse', title= 'Browse...'),
    {'name': 'Image File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='image_file_browse', title= 'Browse...'),
    {'name': 'Calibration PONI File', 'type': 'str', 'default': ''},
    NamedActionParameter(name='poni_file_browse', title= 'Browse...'),
    {'name': 'Timeout', 'type': 'float', 'value': 1},
    # {'name': 'Rotation Motors', 'type': 'group', 'children': [
    #     {'name': 'Rot1', 'type': 'str', 'default': ''},
    #     {'name': 'Rot2', 'type': 'str', 'default': 'TwoTheta'},
    #     {'name': 'Rot3', 'type': 'str', 'default': ''}
    # ]},
    # {'name': 'Calibration Angles', 'type': 'group', 'children': [
    #     {'name': 'Rot1', 'type': 'float', 'value': 0},
    #     {'name': 'Rot2', 'type': 'float', 'value': 0},
    #     {'name': 'Rot3', 'type': 'float', 'value': 0}
    # ]},

]

class specWrangler(wranglerWidget):
    """Widget for integrating data associated with spec file. Can be
    used "live", will continue to poll data folders until image data
    and corresponding spec data are available.
    
    attributes:
        command_queue: Queue, used to send commands to thread
        file_lock, mp.Condition, process safe lock for file access
        fname: str, path to data file
        parameters: pyqtgraph Parameter, stores parameters from user
        scan_name: str, current scan name, used to handle syncing data
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        thread: wranglerThread or subclass, QThread for controlling
            processes
        timeout: int, how long before thread stops looking for new
            data.
        tree: pyqtgraph ParameterTree, stores and organizes parameters
        ui: Ui_Form from qtdesigner
    
    methods:
        cont, pause, stop: functions to pass continue, pause, and stop
            commands to thread via command_queue 
        enabled: Enables or disables interactivity
        set_poni_file: sets the calibration poni file
        set_spec_file: sets the spec data file
        set_fname: Method to safely change file name
        setup: Syncs thread parameters prior to starting
    
    signals:
        finished: Connected to thread.finished signal
        sigStart: Tells timescanWidget to start the thread and prepare
            for new data.
        sigUpdateData: int, signals a new arch has been added.
        sigUpdateFile: (str, str), sends new scan_name and file name
            to timescanWidget.
        showLabel: str, connected to thread showLabel signal, sets text
            in specLabel
    """
    showLabel = Qt.QtCore.Signal(str)
    def __init__(self, fname, file_lock, parent=None):
        """fname: str, file path
        file_lock: mp.Condition, process safe lock
        """
        super().__init__(fname, file_lock, parent)

        # Setup gui elements
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.sigStart.emit)
        self.ui.pauseButton.clicked.connect(self.pause)
        self.ui.stopButton.clicked.connect(self.stop)
        self.ui.continueButton.clicked.connect(self.cont)

        # Setup parameter tree
        self.tree = ParameterTree()
        self.parameters = Parameter.create(
            name='spec_wrangler', type='group', children=params
        )
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout = Qt.QtWidgets.QVBoxLayout(self.ui.paramFrame)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.addWidget(self.tree)
        
        # Wire signals from parameter tree based buttons
        self.parameters.child('spec_file_browse').sigActivated.connect(
            self.set_spec_file
        )
        self.parameters.child('image_file_browse').sigActivated.connect(
            self.set_image_file
        )
        self.parameters.child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )
        
        # Set attributes
        self.scan_number = self.parameters.child('Scan Number').value()
        self.timeout = self.parameters.child('Timeout').value()
        self.parameters.sigTreeStateChanged.connect(self.setup)
        
        # Setup thread
        self.thread = specThread(
            self.command_queue, 
            self.sphere_args, 
            self.fname, 
            self.file_lock, 
            self.scan_name, 
            0, 
            {},
            {}, None, None, None, 5, self
        )
        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.sigUpdateFile.emit)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        self.setup()

    def setup(self):
        """Sets up the child thread, syncs all parameters.
        """
        self.thread.mp_inputs.update(self._get_mp_inputs())
        lsf_inputs = self._get_lsf_inputs()
        self.thread.lsf_inputs.update(lsf_inputs)
        self.scan_number = self.parameters.child('Scan Number').value()
        self.scan_name = lsf_inputs['spec_file_name'] + '_scan' + \
                         str(self.scan_number)
        
        self.thread.scan_name = self.scan_name
        self.thread.scan_number = self.scan_number
        
        self.image_path = self.parameters.child('Image File').value()
        self.thread.image_path = self.image_path
        print(f'image_path: {self.image_path}')

        img_dir, img_root, img_ext = self.split_image_name(self.image_path)
        self.img_dir, self.img_root, self.img_ext = img_dir, img_root, img_ext
        self.thread.img_dir, self.thread.img_root, self.thread.img_ext = img_dir, img_root, img_ext
        
        self.fname = os.path.join(self.img_dir, self.img_root + '.hdf5')
        self.thread.fname = self.fname
        
        self.timeout = self.parameters.child('Timeout').value()
        self.thread.timeout = self.parameters.child('Timeout').value()
        
        self.thread.file_lock = self.file_lock
        self.thread.sphere_args = self.sphere_args

    def pause(self):
        if self.thread.isRunning():
            self.command_queue.put('pause')

    def cont(self):
        if self.thread.isRunning():
            self.command_queue.put('continue')

    def stop(self):
        if self.thread.isRunning():
            self.command_queue.put('stop')
    
    def set_spec_file(self):
        """Opens file dialogue and sets the spec data file
        """
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Spec File').setValue(fname)
    
    def set_image_file(self):
        """Opens file dialogue and sets the spec data file
        """
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Image File').setValue(fname)
    
    def split_image_name(self, fname):
        """Splits image filename to get directory, file root and extension

        Arguments:
            fname {str} -- full image file name with path
        """
        dir = os.path.dirname(fname)
        root, ext = os.path.splitext(os.path.basename(fname))
        
        return dir, root[:-5], ext
    
    def set_poni_file(self):
        """Opens file dialogue and sets the calibration file
        """
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Calibration PONI File').setValue(fname)
    
    def _get_mp_inputs(self):
        """Organizes inputs for MakePONI from parameters.
        """
        mp_inputs = OrderedDict(
            # rotations = {
            #     "rot1": None,
            #     "rot2": None,
            #     "rot3": None
            # },
            # calib_rotations = {
            #     "rot1": 0,
            #     "rot2": 0,
            #     "rot3": 0
            # },
            poni_file = None,
            spec_dict = {}
        )
        # rot_mot = self.parameters.child('Rotation Motors')
        # for child in rot_mot:
        #     if child.value() == "":
        #         mp_inputs['rotations'][child.name().lower()] = None
        #     else:
        #         mp_inputs['rotations'][child.name().lower()] = child.value()

        
        # cal_rot = self.parameters.child('Calibration Angles')
        # for child in cal_rot:
        #     if child.value() == 0:
        #         pass
        #     else:
        #         mp_inputs['calib_rotations'][child.name().lower()] = child.value()
        
        mp_inputs['poni_file'] = self.parameters.child(
                                     'Calibration PONI File').value()

        return mp_inputs

    def _get_lsf_inputs(self):
        """Organizes inputs for LoadSpecFile from parameters. No longer
        used.
        """
        dirname, fname = os.path.split(self.parameters.child('Spec File').value())
        lsf_inputs = OrderedDict(
            spec_file_path=dirname,
            spec_file_name=fname
        )

        return lsf_inputs

    def enabled(self, enable):
        """Sets tree and start button to enable.
        
        args:
            enable: bool, True for enabled False for disabled.
        """
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)
                

class specThread(wranglerThread):
    """Thread for controlling the specProcessor process. Receives
    manages a command and signal queue to pass commands from the main
    thread and communicate back relevant signals.
    
    attributes:
        command_q: mp.Queue, queue to send commands to process
        file_lock: mp.Condition, process safe lock for file access
        fname: str, path to data file.
        img_dir: str, path to image directory
        img_root: str, image filename without path and extension and image number
        img_ext: str, extension of image file
        mp_inputs: dict, input parameters for MakePONI
        input_q: mp.Queue, queue for commands sent from parent
        signal_q: mp.Queue, queue for commands sent from process
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        timeout: float or int, how long to continue checking for new
            data.
    
    signals:
        showLabel: str, sends out text to be used in specLabel
    
    methods:
        run: Main method, called by start
    """
    showLabel = Qt.QtCore.Signal(str)
    def __init__(
            self, 
            command_queue, 
            sphere_args, 
            fname, 
            file_lock,
            scan_name, 
            scan_number,
            mp_inputs, 
            lsf_inputs,
            img_dir, 
            img_root, 
            img_ext, 
            timeout,
            parent=None):
        """command_queue: mp.Queue, queue for commands sent from parent
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file.
        file_lock: mp.Condition, process safe lock for file access
        mp_inputs: dict, input parameters for MakePONI
        img_dir: str, path to image directory
        img_root: str, image filename without path and extension and image number
        img_ext: str, extension of image file
        timeout: float or int, how long to continue checking for new
            data.
        """
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)
        self.mp_inputs = mp_inputs
        self.lsf_inputs = lsf_inputs
        self.img_dir = img_dir
        self.img_root = img_root
        self.img_ext = img_ext
        self.timeout = timeout

    def run(self):
        """Initializes specProcess and watches for new commands from
        parent or signals from the process.
        """
        process = specProcess(
            self.command_q, 
            self.signal_q, 
            self.sphere_args, 
            self.scan_name,
            self.scan_number,
            self.fname, 
            self.file_lock,
            self.lsf_inputs, 
            self.mp_inputs,
            self.img_dir,
            self.img_root,
            self.img_ext,
            self.timeout
        )
        process.start()
        last = False
        # Main loop
        while True:
            # Check for new commands
            if not self.input_q.empty():
                command = self.input_q.get()
                print(command)
                self.command_q.put(command)
            
            #Check for new updates
            if not self.signal_q.empty():
                signal, data = self.signal_q.get()
                if signal == 'update':
                    self.sigUpdate.emit(data)
                elif signal == 'message':
                    self.showLabel.emit(data)
                elif signal == 'new_scan':
                    self.sigUpdateFile.emit(self.scan_name, self.fname)
                    # print(self.image_path, self.fname)
                    # self.sigUpdateFile.emit(self.image_path, self.fname)
                elif signal == 'TERMINATE':
                    last = True
            
            # Breaks on signal from process
            if last:
                break
        
        # Empty queues of any other items after main loop ends.
        self._empty_q(self.signal_q)
        self._empty_q(self.command_q)
        process.join()
    
    def _empty_q(self, q):
        """Empties out a given queue.
        args:
            q: Queue
        """
        while not q.empty():
            _ = q.get()
    

class specProcess(wranglerProcess):
    """Process for integrating scanning area detector data. Checks for
    a specified scan in a spec file, and then searches for associated
    raw files. Data is stored with an EwaldSphere object, saving all
    data to an hdf5 file.
    
    attributes:
        command_q: mp.Queue, queue for commands from parent thread.
        file_lock: mp.Condition, process safe lock for file access
        fname: str, path to data file
        img_dir: str, path to image directory
        img_root: str, image filename without path and extension and image number
        img_ext: str, extension of image file
        mp_inputs: dict, input parameters for MakePONI
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        timeout: float or int, how long to continue checking for new
            data.
        user: str, user name from spec file
    
    methods:
        _main: Controls flow of integration, checking for commands,
            providing updates, and catching errors.
        read_raw: method for reading in binary .raw files and returning
            data as a numpy array.
        wrangle: Method which handles data loading from files.
    """
    def __init__(self, command_q, signal_q, sphere_args, scan_name, 
                 scan_number, fname, file_lock, lsf_inputs, mp_inputs,
                 # fname, file_lock, mp_inputs,
                 img_dir, img_root, img_ext, timeout, *args, **kwargs):
        """command_q: mp.Queue, queue for commands from parent thread.
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file
        file_lock: mp.Condition, process safe lock for file access
        mp_inputs: dict, input parameters for MakePONI
        img_dir: str, path to image directory
        img_root: str, image filename without path and extension and image number
        img_ext: str, extension of image file
        timeout: float or int, how long to continue checking for new
            data.
        """
        super().__init__(command_q, signal_q, sphere_args, fname, file_lock,
                         *args, **kwargs)
        self.lsf_inputs = lsf_inputs
        self.mp_inputs = mp_inputs
        self.scan_name = scan_name
        self.scan_number = scan_number
        self.img_dir = img_dir
        self.img_root = img_root
        self.img_ext = img_ext
        self.specFile = OrderedDict(
            header=dict(
                    meta={},
                    motors={},
                    motors_r={},
                    detectors={},
                    detectors_r={}
                    ),
            scans={},
            scans_meta={}
        )
        self.user = None
        self.spec_name = None
        self.timeout = timeout
    
    def _main(self):
        """Checks for commands in queue, sends back updates through
        signal queue, and catches errors. Calls wrangle method for
        reading in data, then performs integration.
        """
        # Initialize sphere and save to disk, send update for new scan
        print(f'self.fname: {self.fname}')
        print(f'self.fname[:-5]: {self.fname[:-5]}')
        sphere = EwaldSphere(self.scan_name, data_file=self.fname,
                             **self.sphere_args)
        # sphere = EwaldSphere(1, data_file=self.fname,
        #                      **self.sphere_args)
        with self.file_lock:
            sphere.save_to_h5(replace=True)
            self.signal_q.put(('new_scan', None))
        
        # Operation instantiated within process to avoid conflicts with locks
        make_poni = MakePONI()
        make_poni.inputs.update(self.mp_inputs)
        
        # full spec path grabbed from lsf_inputs
        # TODO: just give full spec path as argument
        spec_path = os.path.join(self.lsf_inputs['spec_file_path'],
                                 self.lsf_inputs['spec_file_name'])

        # Enter main loop
        i = 0   # To change this
        pause = False
        start = time.time()
        while True:
            # Check for commands, or wait if paused
            if not self.command_q.empty() or pause:
                command = self.command_q.get()
                print(command)
                if command == 'stop':
                    break
                elif command == 'continue':
                    pause = False
                elif command == 'pause':
                    pause = True
                    continue
            
            # Get result from wrangle
            try:
                flag, data = self.wrangle(i, spec_path, make_poni)
                # flag, data = self.wrangle(i)#, spec_path, make_poni)
            # Errors associated with image not yet taken
            except (KeyError, FileNotFoundError, AttributeError, ValueError):
                elapsed = time.time() - start
                if elapsed > self.timeout:
                    self.signal_q.put(('message', "Timeout occurred"))
                    self.signal_q.put(('TERMINATE', None))
                    break
                else:
                    continue
            start = time.time()
            
            # Unpack data and load into sphere
            # TODO: Test how long integrating vs io takes
            if flag == 'image':
                idx, map_raw, scan_info, poni = data
                # idx, map_raw, scan_info = data
                arch = EwaldArch(
                    idx, map_raw, poni_file=self.mp_inputs['poni_file'], scan_info=scan_info
                )
                
                # integrate image to 1d and 2d arrays
                arch.integrate_1d(**sphere.bai_1d_args)
                arch.integrate_2d(**sphere.bai_2d_args)

                # Add arch copy to sphere, save to file
                with self.file_lock:
                    sphere.add_arch(
                        arch=arch.copy(), calculate=False, update=True,
                        get_sd=True, set_mg=False
                    )
                    sphere.save_to_h5(data_only=True, replace=False)
                
                self.signal_q.put(('message', f'Image {i} integrated'))
                self.signal_q.put(('update', idx))
                i += 1
            
            # Check if terminate signal sent
            elif flag == 'TERMINATE' and data is None:
                self.signal_q.put(('TERMINATE', None))
                break
        
        # If loop ends, signal terminate to parent thread.
        self.signal_q.put(('TERMINATE', None))


    # def wrangle(self, i):#, spec_path, make_poni):
    def wrangle(self, i, spec_path, make_poni):
        """Method for reading in data from raw files and spec file.
        
        args:
            i: int, index of image to check
            spec_path: str, absolute path to spec file
            make_poni: MakePONI, operation for creating poni objects
        
        returns:
            flag: str, signal for what kind of data to expect.
            data: tuple (int, numpy array, dict, dict), the
                index of the data, raw image array, metadata, and PONI
                dict associated with the image.
        """
        self.signal_q.put(('message', f'Checking for {i}'))
        
        # reads in spec data file header
        self.specFile['header'] = get_spec_header(spec_path)
        
        # reads in scan data
        self.specFile['scans'][self.scan_number], \
        self.specFile['scans_meta'][self.scan_number] = get_spec_scan(
            spec_path, self.scan_number, self.specFile['header']
        )

        # checks for user and spec_name information
        if self.user is None:
            self.user = self.specFile['header']['meta']['User']
        if self.spec_name is None:
            self.spec_name = self.specFile['header']['meta']['File'][0]

        # Construct raw_file path from attributes and index
        # raw_file = self._get_raw_path(i)
        image_file = self._get_image_path(i+1)

        # Get scan meta data
        if self.scan_number in self.specFile['scans'].keys():
            image_meta = self.specFile['scans']\
                                [self.scan_number].loc[i].to_dict()
        
        else:
            image_meta = self.specFile['current_scan'].loc[i].to_dict()
        
        # Get poni dict based on meta data
        make_poni.inputs['spec_dict'] = copy.deepcopy(image_meta)
        poni = copy.deepcopy(make_poni.run())
        
        # Read raw file into numpy array
        # arr = self.read_raw(raw_file)
        arr = read_image_file(image_file)#, flip=True)
        
        self.signal_q.put(('message', f'Image {i} wrangled'))

        return 'image', (i, arr, image_meta, poni)

        self.signal_q.put(('message', f'Checking for {i}'))
        
        # Construct image_file path from attributes and index
        image_file = self._get_image_path(i+1)

        # Read raw file into numpy array
        print(f'Image File Name: {image_file}')
        arr = read_image_file(image_file)#, flip=True)

        # Get scan meta data
        meta_file = image_file[:-3] + 'txt'
        image_meta = get_image_meta_data(meta_file, BL='11-3')
        # print(f'Image Meta Data: {image_meta}')
        
        self.signal_q.put(('message', f'Image {i} wrangled'))

        return 'image', (i, arr, image_meta, poni)
        # return 'image', (i, arr, image_meta)

    def _get_image_path(self, i):
        """Creates raw path name from attributes, following spec
        convention.
        
        args:
            i: int, index of image
        
        returns:
            image_file: str, absolute path to image file.
        """
        im_base = '_'.join([
            self.img_root,
            str(i).zfill(4)
        ])
        return os.path.join(self.img_dir, im_base + self.img_ext)