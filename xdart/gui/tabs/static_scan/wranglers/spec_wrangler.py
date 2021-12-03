# -*- coding: utf-8 -*-
"""
@author: thampy, walroth
"""

# Standard library imports
import os
import time
import glob
import fnmatch
from copy import deepcopy
import numpy as np
from pathlib import Path
from collections import deque

# pyFAI imports
import fabio

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from xdart.modules.ewald import EwaldArch, EwaldSphere
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .ui.specUI import Ui_Form
from ....gui_utils import NamedActionParameter
from xdart.utils import get_img_data, get_img_meta
from xdart.utils import split_file_name, get_scan_name, get_img_number, get_fname_dir
from xdart.utils import match_img_detector, get_spec_file
from xdart.utils import write_xye, write_csv
from xdart.utils.containers.poni import get_poni_dict

from ....widgets import commandLine
from xdart.modules.pySSRL_bServer.bServer_funcs import specCommand

# from icecream import ic; ic.configureOutput(prefix='', includeContext=True)

QFileDialog = QtWidgets.QFileDialog
QDialog = QtWidgets.QDialog
QMessageBox = QtWidgets.QMessageBox
QPushButton = QtWidgets.QPushButton

def_poni_file = '/Users/vthampy/SSRL_Data/RDA/static_det_test_data/test_xfc_data/test_xfc.poni'
def_img_file = '/Users/vthampy/SSRL_Data/RDA/static_det_test_data/test_xfc_data/images/images_0005.tif'

if not os.path.exists(def_poni_file):
    def_poni_file = ''
    def_img_file = ''

params = [
    {'name': 'Calibration', 'type': 'group', 'children': [
        {'name': 'poni_file', 'title': 'PONI File    ', 'type': 'str', 'value': def_poni_file},
        NamedActionParameter(name='poni_file_browse', title='Browse...'),
    ], 'expanded': True},
    {'name': 'Signal', 'type': 'group', 'children': [
        {'name': 'inp_type', 'title': '', 'type': 'list',
         'values': ['Image Series', 'Image Directory', 'Single Image'], 'value': 'Image Series'},
        {'name': 'File', 'title': 'Image File   ', 'type': 'str', 'value': def_img_file},
        NamedActionParameter(name='img_file_browse', title='Browse...'),
        {'name': 'img_dir', 'title': 'Directory', 'type': 'str', 'value': '', 'visible': False},
        NamedActionParameter(name='img_dir_browse', title='Browse...', visible=False),
        {'name': 'include_subdir', 'title': 'Subdirectories', 'type': 'bool', 'value': False, 'visible': False},
        {'name': 'img_ext', 'title': 'File Type  ', 'type': 'list',
         'values': ['tif', 'raw', 'h5', 'mar3450'], 'value':'tif', 'visible': False},
        {'name': 'meta_ext', 'title': 'Meta File', 'type': 'list',
         'values': ['None', 'txt', 'pdi', 'SPEC'], 'value':'txt'},
        {'name': 'Filter', 'type': 'str', 'value': '', 'visible': False},
        {'name': 'write_mode', 'title': 'Write Mode  ', 'type': 'list',
         'values': ['Append', 'Overwrite'], 'value':'Append'},
        {'name': 'mask_file', 'title': 'Mask File', 'type': 'str', 'value': ''},
        NamedActionParameter(name='mask_file_browse', title='Browse...'),
    ], 'expanded': True, 'visible': False},
    {'name': 'BG', 'title': 'Background', 'type': 'group', 'children': [
        {'name': 'bg_type', 'title': '', 'type': 'list',
         'values': ['None', 'Single BG File', 'BG Directory'], 'value': 'None'},
        {'name': 'File', 'title': 'BG File', 'type': 'str', 'value': '', 'visible': False},
        NamedActionParameter(name='bg_file_browse', title='Browse...', visible=False),
        {'name': 'Match', 'title': 'Match Parameter', 'type': 'group', 'children': [
            {'name': 'Parameter', 'type': 'list', 'values': ['None'], 'value': 'None'},
            {'name': 'match_fname', 'title': 'Match File Root', 'type': 'bool', 'value': False},
            {'name': 'bg_dir', 'title': 'Directory', 'type': 'str', 'value': ''},
            NamedActionParameter(name='bg_dir_browse', title='Browse...'),
            {'name': 'Filter', 'type': 'str', 'value': ''},
        ], 'expanded': True, 'visible': False},
        {'name': 'Scale', 'type': 'float', 'value': 1, 'visible': False},
        {'name': 'norm_channel', 'title': 'Normalize', 'type': 'list', 'values': ['bstop'], 'value': 'bstop',
         'visible': False},
    ], 'expanded': False, 'visible': False},
    {'name': 'GI', 'title': 'Grazing Incidence', 'type': 'group', 'children': [
        {'name': 'Grazing', 'type': 'bool', 'value': False},
        {'name': 'th_motor', 'title': 'Theta Motor', 'type': 'list', 'values': ['th'], 'value': 'th'},
    ], 'expanded': False, 'visible': False},
    {'name': 'h5_dir', 'title': 'Save Path', 'type': 'str', 'value': get_fname_dir(), 'enabled': False},
    NamedActionParameter(name='h5_dir_browse', title='Browse...', visible=False),
    {'name': 'Timeout', 'type': 'float', 'value': 1, 'visible': False},
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
        set_image_dir: sets the image directory
        set_poni_file: sets the calibration poni file
        set_spec_file: sets the spec data file
        set_fname: Method to safely change file name
        setup: Syncs thread parameters prior to starting

    signals:
        finished: Connected to thread.finished signal
        sigStart: Tells tthetaWidget to start the thread and prepare
            for new data.
        sigUpdateData: int, signals a new arch has been added.
        sigUpdateFile: (str, str, bool, str, bool), sends new scan_name, file name
            GI flag (grazing incidence), theta motor for GI, and
             single_image flag to static_scan_Widget.
        sigUpdateGI: bool, signals the grazing incidence condition has changed.
        showLabel: str, connected to thread showLabel signal, sets text
            in specLabel
    """
    showLabel = Qt.QtCore.Signal(str)

    def __init__(self, fname, file_lock, sphere, data_1d, data_2d, parent=None):
        """fname: str, file path
        file_lock: mp.Condition, process safe lock
        """
        super().__init__(fname, file_lock, parent)

        # Scan Parameters
        self.poni_dict = None
        self.scan_parameters = []
        self.counters = []
        self.motors = []
        self.command = None
        self.sphere = sphere
        self.data_1d = data_1d
        self.data_2d = data_2d

        # Setup gui elements
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.start)
        # self.ui.startButton.clicked.connect(self.sigStart.emit)
        self.ui.pauseButton.clicked.connect(self.pause)
        self.ui.stopButton.clicked.connect(self.stop)
        self.ui.continueButton.clicked.connect(self.cont)

        # SpecCommand Line
        self.specCommandLine = commandLine(self)
        self.specCommandLine.send_command = self.send_command
        self.ui.commandLayout.addWidget(self.specCommandLine)
        self.buttonSend = QtWidgets.QPushButton(self)
        self.buttonSend.setText('Send')
        self.buttonSend.clicked.connect(self.send_command)
        self.ui.commandLayout.addWidget(self.buttonSend)
        self.commands = ['']
        self.current = -1
        self.keep_trying = True
        self.showLabel.connect(self.ui.specLabel.setText)

        # Setup parameter tree
        self.tree = ParameterTree()
        self.stylize_ParameterTree()
        self.parameters = Parameter.create(
            name='spec_wrangler', type='group', children=params
        )
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout = Qt.QtWidgets.QVBoxLayout(self.ui.paramFrame)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.tree)

        # Set attributes from Parameter Tree and a couple more
        # Calibration
        self.poni_file = self.parameters.child('Calibration').child('poni_file').value()
        self.get_poni_dict()

        # Signal
        self.inp_type = self.parameters.child('Signal').child('inp_type').value()
        self.img_file = self.parameters.child('Signal').child('File').value()
        self.img_dir = self.parameters.child('Signal').child('img_dir').value()
        self.include_subdir = self.parameters.child('Signal').child('include_subdir').value()
        self.img_ext = self.parameters.child('Signal').child('img_ext').value()
        self.single_img = True if self.inp_type == 'Single Image' else False
        self.file_filter = self.parameters.child('Signal').child('Filter').value()
        self.meta_ext = self.parameters.child('Signal').child('meta_ext').value()
        if self.meta_ext == 'None':
            self.meta_ext = None

        # Mask
        self.mask_file = self.parameters.child('Signal').child('mask_file').value()

        # Write Mode
        self.write_mode = self.parameters.child('Signal').child('write_mode').value()

        # Background
        self.bg_type = self.parameters.child('BG').child('bg_type').value()
        self.bg_file = self.parameters.child('BG').child('File').value()
        self.bg_dir = self.parameters.child('BG').child('Match').child('bg_dir').value()
        self.bg_matching_par = self.parameters.child('BG').child('Match').child('Parameter').value()
        self.bg_match_fname = self.parameters.child('BG').child('Match').child('match_fname').value()
        self.bg_file_filter = self.parameters.child('BG').child('Match').child('Filter').value()
        self.bg_scale = self.parameters.child('BG').child('Scale').value()
        self.bg_norm_channel = self.parameters.child('BG').child('norm_channel').value()

        # Grazing Incidence
        self.gi = self.parameters.child('GI').child('Grazing').value()
        self.th_mtr = self.parameters.child('GI').child('th_motor').value()

        # Timeout
        self.timeout = self.parameters.child('Timeout').value()

        # HDF5 Save Path
        self.h5_dir = self.parameters.child('h5_dir').value()

        # Wire signals from parameter tree based buttons
        self.parameters.sigTreeStateChanged.connect(self.setup)

        self.parameters.child('Calibration').child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
        )
        self.parameters.child('Calibration').child('poni_file').sigValueChanged.connect(
            self.get_poni_dict
        )
        self.parameters.child('Signal').child('inp_type').sigValueChanged.connect(
            self.set_inp_type
        )
        self.parameters.child('Signal').child('img_file_browse').sigActivated.connect(
            self.set_img_file
        )
        self.parameters.child('Signal').child('img_dir_browse').sigActivated.connect(
            self.set_img_dir
        )
        self.parameters.child('Signal').child('mask_file_browse').sigActivated.connect(
            self.set_mask_file
        )
        self.parameters.child('Signal').child('meta_ext').sigValueChanged.connect(
            self.set_meta_ext
        )
        self.parameters.child('BG').child('bg_type').sigValueChanged.connect(
            self.set_bg_type
        )
        self.parameters.child('BG').child('bg_file_browse').sigActivated.connect(
            self.set_bg_file
        )
        self.parameters.child('BG').child('Match').child('bg_dir_browse').sigActivated.connect(
            self.set_bg_dir
        )
        self.parameters.child('BG').child('Match').child('Parameter').sigValueChanged.connect(
            self.set_bg_matching_par
        )
        self.parameters.child('BG').child('norm_channel').sigValueChanged.connect(
            self.set_bg_norm_channel
        )
        self.parameters.child('GI').child('th_motor').sigValueChanged.connect(
            self.set_gi_th_motor
        )
        self.parameters.child('h5_dir_browse').sigActivated.connect(
            self.set_h5_dir
        )

        # Setup thread
        self.thread = specThread(
            self.command_queue,
            self.sphere_args,
            self.file_lock,
            self.fname,
            self.h5_dir,
            self.scan_name,
            self.single_img,
            self.poni_dict,
            self.inp_type,
            self.img_file,
            self.img_dir,
            self.include_subdir,
            self.img_ext,
            self.file_filter,
            self.mask_file,
            self.write_mode,
            self.bg_type,
            self.bg_file,
            self.bg_dir,
            self.bg_matching_par,
            self.bg_match_fname,
            self.bg_file_filter,
            self.bg_scale,
            self.bg_norm_channel,
            self.gi,
            self.th_mtr,
            self.timeout,
            self.command,
            self.sphere,
            self.data_1d,
            self.data_2d,
            self
        )

        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.sigUpdateFile.emit)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        # self.thread.sigUpdateArch.connect(self.sigUpdateArch.emit)
        self.thread.sigUpdateGI.connect(self.sigUpdateGI.emit)

        # Enable/disable buttons initially
        self.ui.pauseButton.setEnabled(False)
        self.ui.continueButton.setEnabled(False)
        self.ui.stopButton.setEnabled(False)

        self.setup()

    def setup(self):
        """Sets up the child thread, syncs all parameters.
        """
        # ic()
        # Calibration
        self.poni_file = self.parameters.child('Calibration').child('poni_file').value()
        self.thread.poni_dict = self.poni_dict

        # Signal
        self.file_filter = self.parameters.child('Signal').child('Filter').value()
        self.thread.file_filter = self.file_filter

        self.inp_type = self.parameters.child('Signal').child('inp_type').value()
        self.thread.inp_type = self.inp_type

        self.get_img_fname()
        self.thread.img_file = self.img_file

        self.scan_name = get_scan_name(self.img_file)
        self.thread.scan_name = self.scan_name

        self.thread.single_img = self.single_img
        self.thread.img_dir, self.thread.img_ext = self.img_dir, self.img_ext

        self.include_subdir = self.parameters.child('Signal').child('include_subdir').value()
        self.thread.include_subdir = self.include_subdir

        self.thread.meta_ext = self.meta_ext

        self.thread.h5_dir = self.h5_dir
        self.fname = os.path.join(self.h5_dir, self.scan_name + '.hdf5')
        self.thread.fname = self.fname

        self.mask_file = self.parameters.child('Signal').child('mask_file').value()
        self.thread.mask_file = self.mask_file

        # Write Mode
        self.write_mode = self.parameters.child('Signal').child('write_mode').value()
        self.thread.write_mode = self.write_mode

        # Background
        self.bg_type = self.parameters.child('BG').child('bg_type').value()
        self.thread.bg_type = self.bg_type

        self.bg_file = self.parameters.child('BG').child('File').value()
        self.thread.bg_file = self.bg_file

        self.bg_matching_par = self.parameters.child('BG').child('Match').child('Parameter').value()
        self.thread.bg_matching_par = self.bg_matching_par

        self.bg_dir = self.parameters.child('BG').child('Match').child('bg_dir').value()
        self.thread.bg_dir = self.bg_dir

        self.bg_match_fname = self.parameters.child('BG').child('Match').child('match_fname').value()
        self.thread.bg_match_fname = self.bg_match_fname

        self.bg_file_filter = self.parameters.child('BG').child('Match').child('Filter').value()
        self.thread.bg_file_filter = self.bg_file_filter

        self.bg_scale = self.parameters.child('BG').child('Scale').value()
        self.thread.bg_scale = self.bg_scale

        self.bg_norm_channel = self.parameters.child('BG').child('norm_channel').value()
        self.thread.bg_norm_channel = self.bg_norm_channel

        # Grazing Incidence
        self.gi = self.parameters.child('GI').child('Grazing').value()
        self.thread.gi = self.gi

        self.th_mtr = self.parameters.child('GI').child('th_motor').value()
        self.thread.th_mtr = self.th_mtr

        # Timeout
        self.timeout = self.parameters.child('Timeout').value()
        self.thread.timeout = self.timeout

        self.thread.command = self.command

        self.thread.file_lock = self.file_lock
        self.thread.sphere_args = self.sphere_args

        self.thread.sphere = self.sphere
        self.thread.data_1d = self.data_1d
        self.thread.data_2d = self.data_2d

    def send_command(self):
        """Sends command in command line to spec, and calls
        commandLine send_command method to add command to list of
        commands.
        """
        command = self.specCommandLine.text()
        if not (command.isspace() or command == ''):
            try:
                specCommand(command, queue=True)
            except Exception as e:
                print(e)
                print(f"Command '{command}' not sent")

        commandLine.send_command(self.specCommandLine)

    def start(self):
        self.command = 'start'
        self.thread.command = 'start'
        self.ui.pauseButton.setEnabled(True)
        self.ui.continueButton.setEnabled(False)
        self.ui.stopButton.setEnabled(True)
        self.sigStart.emit()

    def pause(self):
        self.command = 'pause'
        self.thread.command = 'pause'
        # if self.thread.isRunning():
        self.ui.pauseButton.setEnabled(False)
        self.ui.continueButton.setEnabled(True)

    def cont(self):
        self.command = 'continue'
        self.thread.command = 'continue'
        # if self.thread.isRunning():
        self.ui.pauseButton.setEnabled(True)
        self.ui.continueButton.setEnabled(False)

    def stop(self):
        self.command = 'stop'
        self.thread.command = 'stop'
        # if self.thread.isRunning():
        self.ui.pauseButton.setEnabled(False)
        self.ui.continueButton.setEnabled(False)
        self.ui.stopButton.setEnabled(False)

    def set_poni_file(self):
        """Opens file dialogue and sets the calibration file
        """
        fname, _ = QFileDialog().getOpenFileName(
            filter="PONI (*.poni *.PONI)"
        )
        if fname != '':
            self.parameters.child('Calibration').child('poni_file').setValue(fname)
            self.poni_file = fname

    def get_poni_dict(self):
        """Opens file dialogue and sets the calibration file
        """
        if not os.path.exists(self.poni_file):
            for child in self.parameters.children():
                child.hide()
            self.parameters.child('Calibration').show()
            return

        self.poni_dict = get_poni_dict(self.poni_file)
        if self.poni_dict is None:
            print('Invalid Poni File')
            self.thread.signal_q.put(('message', 'Invalid Poni File'))
            return

        for child in self.parameters.children():
            child.show()

    def set_inp_type(self):
        """Change Parameter Names depending on Input Type
        """
        # ic()
        self.single_img = False
        self.parameters.child('Signal').child('File').show()
        self.parameters.child('Signal').child('img_file_browse').show()
        self.parameters.child('Signal').child('img_dir').hide()
        self.parameters.child('Signal').child('img_dir_browse').hide()
        self.parameters.child('Signal').child('include_subdir').hide()
        self.parameters.child('Signal').child('Filter').hide()
        self.parameters.child('Signal').child('img_ext').hide()

        inp_type = self.parameters.child('Signal').child('inp_type').value()
        if inp_type == 'Image Directory':
            self.parameters.child('Signal').child('File').hide()
            self.parameters.child('Signal').child('img_file_browse').hide()
            self.parameters.child('Signal').child('img_dir').show()
            self.parameters.child('Signal').child('img_dir_browse').show()
            self.parameters.child('Signal').child('include_subdir').show()
            self.parameters.child('Signal').child('Filter').show()
            self.parameters.child('Signal').child('img_ext').show()

        if inp_type == 'Single Image':
            self.single_img = True

        self.inp_type = inp_type
        self.get_img_fname()

    def set_img_file(self):
        """Opens file dialogue and sets the spec data file
        """
        # ic()
        fname, _ = QFileDialog().getOpenFileName(
            filter="Images (*.tiff *.tif *.h5 *.raw *.mar3450)"
        )
        if fname != '':
            self.parameters.child('Signal').child('File').setValue(fname)

    def set_img_dir(self):
        """Opens file dialogue and sets the signal data folder
        """
        # ic()
        path = QFileDialog().getExistingDirectory(
            caption='Choose Image Directory',
            directory='',
            options=QFileDialog.ShowDirsOnly
        )
        if path != '':
            self.parameters.child('Signal').child('img_dir').setValue(path)
        self.img_dir = path

    def get_img_fname(self):
        """Sets file name based on chosen options
        """
        # ic()
        old_fname = self.img_file
        if self.inp_type != 'Image Directory':
            img_file = self.parameters.child('Signal').child('File').value()
            if os.path.exists(img_file):
                self.img_file = img_file
                self.img_dir, _, self.img_ext = split_file_name(self.img_file)
                # self.meta_ext = self.get_meta_ext(self.img_file)

        else:
            self.img_ext = self.parameters.child('Signal').child('img_ext').value()
            self.img_dir = self.parameters.child('Signal').child('img_dir').value()
            self.include_subdir = self.parameters.child('Signal').child('include_subdir').value()

            filters = '*' + '*'.join(f for f in self.file_filter.split()) + '*'
            filters = filters if filters != '**' else '*'

            for subdir, dirs, files in os.walk(self.img_dir):
                for file in files:
                    fname = os.path.join(subdir, file)
                    if fnmatch.fnmatch(fname, f'{filters}.{self.img_ext}'):
                        if match_img_detector(fname, self.poni_dict):
                            if self.meta_ext:
                                if self.exists_meta_file(fname):
                                    self.img_file = fname
                                    break
                                else:
                                    continue
                            else:
                                self.img_file = fname
                                break
                            # self.meta_ext = self.get_meta_ext(fname)
                if not self.include_subdir:
                    break

        if (((self.img_file != old_fname) or (self.img_file and (len(self.scan_parameters) < 1)))
                and self.meta_ext):
            self.set_pars_from_meta()

    def set_meta_ext(self):
        self.meta_ext = self.parameters.child('Signal').child('meta_ext').value()
        if self.meta_ext == 'None':
            self.meta_ext = None
        self.get_img_fname()

    def exists_meta_file(self, img_file):
        """Checks for existence of meta file for image file"""
        if self.meta_ext != 'SPEC':
            meta_files = [
                f'{os.path.splitext(img_file)[0]}.{self.meta_ext}',
                f'{os.path.splitext(img_file)}.{self.meta_ext}'
            ]
            if os.path.exists(meta_files[0]) or os.path.exists(meta_files[1]):
                return True
        else:
            meta_file = get_spec_file(img_file)
            if meta_file and os.path.exists(meta_file):
                return True

        return False

    def set_pars_from_meta(self):
        self.get_scan_parameters()
        self.set_bg_matching_options()
        self.set_gi_motor_options()
        self.set_bg_norm_options()

    def set_mask_file(self):
        """Opens file dialogue and sets the mask file
        """
        fname, _ = QFileDialog().getOpenFileName(
            filter="EDF (*.edf)"
        )
        if fname != '':
            self.parameters.child('Signal').child('mask_file').setValue(fname)
        self.mask_file = fname

    def set_bg_type(self):
        """Change Parameter Names depending on BG Type
        """
        # ic()
        for child in self.parameters.child('BG').children():
            child.hide()
        self.parameters.child('BG').child('bg_type').show()

        self.bg_type = self.parameters.child('BG').child('bg_type').value()
        if self.bg_type == 'None':
            return
        elif self.bg_type == 'Single BG File':
            self.parameters.child('BG').child('File').show()
            self.parameters.child('BG').child('bg_file_browse').show()
        else:
            self.parameters.child('BG').child('Match').show()

        self.parameters.child('BG').child('Scale').show()
        self.parameters.child('BG').child('norm_channel').show()

    def set_bg_file(self):
        """Opens file dialogue and sets the background file
        """
        # ic()
        fname, _ = QFileDialog().getOpenFileName(
            filter=f"Images (*.{self.img_ext})"
            )
        if fname != '':
            self.parameters.child('BG').child('File').setValue(fname)
        self.bg_file = fname

    def set_bg_dir(self):
        """Opens file dialogue and sets the background folder
        """
        # ic()
        path = QFileDialog().getExistingDirectory(
            caption='Choose BG Directory',
            directory='',
            options=QFileDialog.ShowDirsOnly
            # options =(QFileDialog.ShowDirsOnly)
        )
        if path != '':
            self.parameters.child('BG').child('Match').child('bg_dir').setValue(path)
        self.bg_dir = path

    def set_h5_dir(self):
        """Opens file dialogue and sets the path where processed data is stored
        """
        # ic()
        path = QFileDialog().getExistingDirectory(
            caption='Choose Save Directory',
            directory='',
            options=QFileDialog.ShowDirsOnly
        )
        if path != '':
            Path(path).mkdir(parents=True, exist_ok=True)
            self.parameters.child('h5_dir').setValue(path)
            self.h5_dir = path

    def set_bg_matching_options(self):
        """Reads image metadata to populate matching parameters
        """
        # ic()
        pars = [p for p in self.scan_parameters if not any(x.lower() in p.lower() for x in ['ROI', 'PD'])]
        pars.insert(0, 'None')
        if 'TEMP' in pars:
            pars.insert(1, pars.pop(pars.index('TEMP')))

        value = 'None'
        opts = {'values': pars, 'limits': pars, 'value': value}
        self.parameters.child('BG').child('Match').child('Parameter').setOpts(**opts)

    def set_bg_matching_par(self):
        """Changes bg matching parameter
        """
        # ic()
        self.bg_matching_par = self.parameters.child('BG').child('Match').child('Parameter').value()
        if self.bg_matching_par == 'None':
            self.bg_matching_par = None

    def set_bg_norm_options(self):
        """Counter Values used to normalize and subtract background
        """
        # ic()
        pars = self.counters
        pars.insert(0, 'None')

        opts = {'values': pars, 'limits': pars, 'value': 'None'}
        self.parameters.child('BG').child('norm_channel').setOpts(**opts)

    def set_bg_norm_channel(self):
        """Changes bg matching parameter
        """
        # ic()
        self.bg_norm_channel = self.parameters.child('BG').child('norm_channel').value()

    def set_gi_motor_options(self):
        """Reads image metadata to populate possible GI theta motor
        """
        # ic()
        # pars = [p for p in self.scan_parameters if not any(x.lower() in p.lower() for x in ['ROI', 'PD'])]
        pars = [p for p in self.motors if not any(x.lower() in p.lower() for x in ['ROI', 'PD'])]
        if 'th' in pars:
            pars.insert(0, pars.pop(pars.index('th')))
            value = 'th'
        elif 'theta' in pars:
            pars.insert(0, pars.pop(pars.index('theta')))
            value = 'theta'
        else:
            value = 'Theta'

        opts = {'values': pars, 'limits': pars, 'value': value}
        self.parameters.child('GI').child('th_motor').setOpts(**opts)

    def set_gi_th_motor(self):
        """Update Grazing theta motor"""
        self.th_mtr = self.parameters.child('GI').child('th_motor').value()

    def get_scan_parameters(self):
        """Reads image metadata to populate matching parameters
        """
        # ic()
        if not self.img_file:
            return

        img_meta = get_img_meta(self.img_file, self.meta_ext)
        self.scan_parameters = list(img_meta.keys())

        counters = get_img_meta(self.img_file, self.meta_ext, rv='Counters')
        self.counters = list(counters.keys())

        motors = get_img_meta(self.img_file, self.meta_ext, rv='Motors')
        self.motors = list(motors.keys())

    def enabled(self, enable):
        """Sets tree and start button to enable.

        args:
            enable: bool, True for enabled False for disabled.
        """
        # ic()
        self.tree.setEnabled(enable)
        self.ui.startButton.setEnabled(enable)

    def stylize_ParameterTree(self):
        self.tree.setStyleSheet("""
        QTreeView::item:has-children {
            background-color: rgb(230, 230, 230); 
            color: rgb(30, 30, 30);
        }
            """)


class specThread(wranglerThread):

    """Thread for controlling the specProcessor process. Receives
    manages a command and signal queue to pass commands from the main
    thread and communicate back relevant signals

    attributes:
        command_q: mp.Queue, queue to send commands to process
        file_lock: mp.Condition, process safe lock for file access
        scan_name: str, name of current scan
        fname: str, full path to data file.
        h5_dir: str, data file directory.
        img_file: str, path to image file
        img_dir: str, path to image directory
        img_ext : str, extension of image file
        meta_ext : str, extension of metadata file
        poni_dict: str, Poni File name
        detector: str, Detector name
        input_q: mp.Queue, queue for commands sent from parent
        signal_q: mp.Queue, queue for commands sent from process
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        timeout: float or int, how long to continue checking for new
            data.
        command: command passed to stop, pause, continue etc.
        data_1d/2d: Dictionaries to store processed data for plotting

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
            file_lock,
            fname,
            h5_dir,
            scan_name,
            single_img,
            poni_dict,
            inp_type,
            img_file,
            img_dir,
            include_subdir,
            img_ext,
            meta_ext,
            file_filter,
            mask_file,
            write_mode,
            bg_type,
            bg_file,
            bg_dir,
            bg_matching_par,
            bg_match_fname,
            bg_file_filter,
            bg_scale,
            bg_norm_channel,
            gi,
            th_mtr,
            timeout,
            command,
            sphere,
            data_1d,
            data_2d,
            parent=None):

        """command_queue: mp.Queue, queue for commands sent from parent
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file.
        h5_dir: str, data file directory.
        file_lock: mp.Condition, process safe lock for file access
        scan_name: str, name of current scan
        single_img: bool, True if there is only one image
        poni_dict: str, poni file name
        detector: str, Detector name
        img_file: str, path to input image file
        img_dir: str, path to image directory
        include_subdir: bool, flag to include subdirectories
        img_ext : str, extension of image file
        meta_ext : str, extension of metadata file
        timeout: float or int, how long to continue checking for new
            data.
        command: command passed to stop, pause, continue etc.
        gi: bool, grazing incidence flag to determine if pyGIX is to be used
        th_mtr: float, incidence angle
        """
        # ic()
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)

        self.h5_dir = h5_dir
        self.scan_name = scan_name
        self.single_img = single_img
        self.poni_dict = poni_dict
        self.inp_type = inp_type
        self.img_file = img_file
        self.img_dir = img_dir
        self.include_subdir = include_subdir
        self.img_ext = img_ext
        self.meta_ext = meta_ext
        self.file_filter = file_filter
        self.mask_file = mask_file
        self.write_mode = write_mode
        self.bg_type = bg_type
        self.bg_file = bg_file
        self.bg_dir = bg_dir
        self.bg_matching_par = bg_matching_par
        self.bg_match_fname = bg_match_fname
        self.bg_file_filter = bg_file_filter
        self.bg_scale = bg_scale
        self.bg_norm_channel = bg_norm_channel
        self.gi = gi
        self.th_mtr = th_mtr
        self.timeout = timeout
        self.command = command
        self.sphere = sphere
        self.data_1d = data_1d
        self.data_2d = data_2d

        self.user = None
        self.mask = None
        self.detector = None
        self.img_fnames = []
        self.processed = []
        self.sub_label = ''

    def run(self):
        """Initializes specProcess and watches for new commands from
        parent or signals from the process.
        """
        # ic()
        t0 = time.time()
        if (self.poni_dict == '') or (self.img_file == ''):
            return

        self.img_fnames.clear()
        self.processed.clear()
        self.detector = self.poni_dict['detector']
        self.sub_label = ''
        self.get_mask()

        self.process_scan()
        print(f'Total Time: {time.time() - t0:0.2f}')

    def process_scan(self):
        """Go through series of images in a scan and process them individually
        """
        sphere = None
        files_processed = 0

        start = time.time()
        # start1 = time.time()
        # print(f'Start time: {time.time() - start1:0.2f}')
        while True:
            # Check for commands, or wait if paused
            command = self.command
            # ic(command)
            if command == 'stop':
                break
            elif command == 'pause':
                self.showLabel.emit(f'Paused')
                time.sleep(0.5)
                continue
            else:
                pass

            img_file, img_number, img_data = self.get_next_image()
            if img_data is None:
                if img_file is None:
                    self.showLabel.emit(f'Checking for next image')
                    time.sleep(0.5)
                else:
                    print(f'Invalid Image File {os.path.basename(img_file)}. Skipping...')

                elapsed = time.time() - start
                if elapsed > self.timeout:
                    self.showLabel.emit(f'Timeout occurred')
                    break
                else:
                    continue

            self.scan_name = get_scan_name(img_file)

            # Initialize sphere and save to disk, send update for new scan
            if (sphere is None) or (self.scan_name != sphere.name):
                sphere = self.initialize_sphere()

            if img_number in list(sphere.arches.index):
                if self.single_img:
                    self.sigUpdate.emit(img_number)
                    break
                continue

            # Get Meta Data
            img_meta = get_img_meta(img_file, self.meta_ext) if self.meta_ext else {}
            # print(f'Image meta: {time.time() - start1:0.2f}')

            # Get Background
            # if self.bg_type != 'None':
            bg_raw = self.get_background(img_file, img_number, img_meta)
                # bg_raw = self.get_background()
                # self.subtract_bg(img_data, img_file, img_number, img_meta)
            # print(f'Subtracted BG: {time.time() - start1:0.2f}')

            arch = EwaldArch(
                img_number, img_data, poni_dict=self.poni_dict,
                scan_info=img_meta, static=True, gi=self.gi,
                # mask=self.mask, th_mtr=self.th_mtr,
                th_mtr=self.th_mtr, bg_raw=bg_raw,
            )

            # integrate image to 1d and 2d arrays
            arch.integrate_1d(global_mask=self.mask, **sphere.bai_1d_args)
            # print(f'Integrated 1D: {time.time() - start1:0.2f}')
            arch.integrate_2d(global_mask=self.mask, **sphere.bai_2d_args)
            # print(f'Integrated 2D: {time.time() - start1:0.2f}')

            # self.data_1d[int(img_number)] = arch.copy(include_2d=False)
            # self.data_2d[int(img_number)] = {
            #     'map_raw': deepcopy(arch.map_raw),
            #     'mask': deepcopy(arch.mask),
            #     'int_2d': deepcopy(arch.int_2d)
            # }
            # print(f'Copied data to Data dicts: {time.time() - start1:0.2f}')

            # Add arch copy to sphere, save to file
            with self.file_lock:
                sphere.add_arch(
                    arch=arch, calculate=False, update=True,
                    get_sd=True, set_mg=False, static=True, gi=self.gi,
                    th_mtr=self.th_mtr
                )
                # print(f'Added arch data to sphere: {time.time() - start1:0.2f}')
                sphere.save_to_h5(data_only=True, replace=False)
            # print(f'Saved data to h5: {time.time() - start1:0.2f}')

            # Save 1D integrated data in CSV and xye files
            self.save_1d(sphere, arch, img_number)
            # print(f'Saved 1D data: {time.time() - start1:0.2f}')

            fname = os.path.splitext(os.path.basename(img_file))[0]
            print(f'Processed {fname} {self.sub_label}')
            if len(fname) > 40:
                fname = f'{fname[:8]}....{fname[-30:]}'
            self.showLabel.emit(f'{fname}')
            self.sigUpdate.emit(img_number)
            files_processed += 1

            if self.single_img:
                self.sigUpdate.emit(img_number)
                break

            time.sleep(0.02)
            start = time.time()

        # If loop ends, signal terminate to parent thread.
        print(f'\nTotal Files Processed: {files_processed}')

    def get_next_image(self):
        """ Gets next image in image series or in directory to process

        Returns:
            image_name {str}: image file path
            image_number {int}: image file number (if part of series)
            image_data {np.ndarray}: image file data array
        """
        if self.single_img:
            img_data = get_img_data(self.img_file, self.detector,return_float=True)
            return self.img_file, get_img_number(self.img_file), img_data

        if len(self.img_fnames) == 0:
            if self.inp_type != 'Image Directory':
                first_img = self.img_file
                self.img_fnames = Path(self.img_dir).glob(f'{self.scan_name}_*.{self.img_ext}')
            else:
                first_img = ''
                filters = '*' + '*'.join(f for f in self.file_filter.split()) + '*'
                filters = filters if filters != '**' else '*'
                if self.include_subdir:
                    self.img_fnames = Path(self.img_dir).rglob(f'{filters}.{self.img_ext}')
                else:
                    self.img_fnames = Path(self.img_dir).glob(f'{filters}.{self.img_ext}')

            self.img_fnames = [str(f) for f in self.img_fnames if
                               (str(f) >= first_img) and (str(f) not in self.processed)]

        # ic(self.img_fnames, self.processed)
        self.img_fnames = deque(sorted(self.img_fnames))
        for nn in range(len(self.img_fnames)):
            img_file = self.img_fnames[0]
            self.processed.append(img_file)
            self.img_fnames.popleft()

            img_number = get_img_number(img_file)
            img_data = get_img_data(img_file, self.detector, im=img_number-1, return_float=True)
            if img_data is not None:
                return img_file, img_number, img_data

        return None, None, None

    def get_meta_data(self, img_file):
        meta_file = f'{os.path.splitext(img_file)[0]}.{self.meta_ext}'
        return get_img_meta(meta_file)

    def subtract_bg(self, img_data, img_file, img_number, img_meta):
        bg = self.get_background(img_file, img_number, img_meta)
        try:
            img_data -= bg
            # min_int = img_data.min()
            # if min_int < 0:
            #     img_data -= min_int
        except ValueError:
            pass

    def initialize_sphere(self):
        """ If scan changes, initialize new EwaldSphere object
        If mode is overwrite, replace existing HDF5 file, else append to it
        """
        fname = os.path.join(self.h5_dir, self.scan_name + '.hdf5')
        sphere = EwaldSphere(self.scan_name,
                             data_file=fname,
                             static=True,
                             gi=self.gi,
                             th_mtr=self.th_mtr,
                             single_img=self.single_img,
                             global_mask=self.mask,
                             **self.sphere_args)

        write_mode = self.write_mode
        if not os.path.exists(fname):
            write_mode = 'Overwrite'

        with self.file_lock:
            if write_mode == 'Append':
                sphere.load_from_h5(replace=False, mode='a')
                existing_arches = sphere.arches.index
                if len(existing_arches) == 0:
                    sphere.save_to_h5(replace=True)
            else:
                sphere.save_to_h5(replace=True)

        self.sigUpdateFile.emit(
            self.scan_name, fname,
            self.gi, self.th_mtr, self.single_img
        )
        print(f'\n***** New Scan *****')

        return sphere

    def get_mask(self):
        """Get mask array from mask file
        """
        self.mask = self.detector.calc_mask()
        if self.mask_file and os.path.exists(self.mask_file):
            if self.mask is not None:
                try:
                    self.mask += fabio.open(self.mask_file).data
                except ValueError:
                    print('Mask file not valid for Detector')
                    pass
            else:
                self.mask = fabio.open(self.mask_file).data

        if self.mask is None:
            return None

        if self.mask.shape != self.detector.shape:
            print('Mask file not valid for Detector')
            return None

        self.mask = np.flatnonzero(self.mask)

    def get_background(self, img_file, img_number, img_meta):
        """Subtract background image if bg_file or bg_dir specified
        """
        if self.bg_type == 'None':
            return 0

        bg_file, bg_meta, norm_factor = None, None, 1
        self.sub_label, norm_label, bg_scale_label = '', '', ''

        if self.bg_type == 'Single BG File':
            if self.bg_file:
                bg_file = self.bg_file
                bg_meta = get_img_meta(bg_file, self.meta_ext)
        else:
            if self.bg_dir and (self.bg_match_fname or self.bg_matching_par):
                bg_file_filter = 'bg' if not self.bg_file_filter else self.bg_file_filter
                if self.bg_match_fname:
                    bg_file_filter = f'{self.scan_name} {bg_file_filter}'
                filters = '*' + '*'.join(f for f in bg_file_filter.split()) + '*'
                filters = filters if filters != '**' else '*'

                meta_files = sorted(glob.glob(os.path.join(
                    # self.img_dir, f'{filters}[0-9][0-9][0-9][0-9].{self.meta_ext}')))
                    self.img_dir, f'{filters}.{self.meta_ext}')))

                for meta_file in meta_files:
                    bg_file = f'{os.path.splitext(meta_file)[0]}.{self.img_ext}'
                    if bg_file == img_file:
                        bg_file = None
                        continue

                    # bg_meta = get_img_meta(meta_file)
                    bg_meta = get_img_meta(bg_file, self.meta_ext)
                    if self.bg_match_fname:
                        if img_number == get_img_number(meta_file):
                            break
                    else:
                        try:
                            if bg_meta[self.bg_matching_par] == img_meta[self.bg_matching_par]:
                                break
                        except KeyError:
                            bg_file = None
                            continue

        if bg_file is None:
            return 0.

        bg = get_img_data(bg_file, self.detector, return_float=True)
        if bg is None:
            return 0.

        if self.bg_scale != 1:
            bg *= self.bg_scale
            bg_scale_label = f'{self.bg_scale:0.2f} [Scale] x '
        if (self.bg_norm_channel != 'None') and (img_meta is not None) and (bg_meta is not None):
            try:
                if ((self.bg_norm_channel in img_meta.keys()) and
                        (self.bg_norm_channel in bg_meta.keys()) and
                        (bg_meta[self.bg_norm_channel] != 0)):
                    norm_factor = (img_meta[self.bg_norm_channel]/bg_meta[self.bg_norm_channel])
                    bg *= norm_factor
                    norm_label = f'{norm_factor:0.2f} [Normalized to Channel - {self.bg_norm_channel}] x '
            except (KeyError, TypeError):
                pass

        self.sub_label = f'[Subtracted {bg_scale_label}{norm_label}{os.path.basename(bg_file)}]'
        return bg

    @staticmethod
    def save_1d(sphere, arch, idx):
        """
        Automatically save 1D integrated data
        """
        path = os.path.dirname(sphere.data_file)
        path = os.path.join(path, sphere.name)
        Path(path).mkdir(parents=True, exist_ok=True)

        q, tth, intensity = arch.int_1d.q, arch.int_1d.ttheta, arch.int_1d.norm

        # Write I(q) to xye
        fname = os.path.join(path, f'iq_{sphere.name}_{str(idx).zfill(4)}.xye')
        write_xye(fname, q, intensity, np.sqrt(abs(intensity)))

        # Write I(tth) to xye
        fname = os.path.join(path, f'itth_{sphere.name}_{str(idx).zfill(4)}.xye')
        write_xye(fname, tth, intensity, np.sqrt(abs(intensity)))

        # Write I(q) to csv
        fname = os.path.join(path, f'iq_{sphere.name}_{str(idx).zfill(4)}.csv')
        write_csv(fname, q, intensity)

        # Write I(tth) to csv
        fname = os.path.join(path, f'itth_{sphere.name}_{str(idx).zfill(4)}.csv')
        write_csv(fname, tth, intensity)
