# -*- coding: utf-8 -*-
"""
@author: thampy, walroth
"""

# Standard library imports
import os
import time
import glob

# Qt imports
from pyqtgraph import Qt
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.parametertree import ParameterTree, Parameter

# This module imports
from xdart.modules.ewald import EwaldArch, EwaldSphere
from .wrangler_widget import wranglerWidget, wranglerThread, wranglerProcess
from .ui.specUI import Ui_Form
from ....gui_utils import NamedActionParameter
from xdart.utils import read_image_file, get_image_meta_data, split_file_name, get_scan_name, get_img_number

from ....widgets import commandLine
from xdart.modules.pySSRL_bServer.bServer_funcs import specCommand

from icecream import ic

ic.configureOutput(prefix='', includeContext=True)

QFileDialog = QtWidgets.QFileDialog

def_poni_file = ''  # '/Users/vthampy/SSRL_Data/RDA/static_det_test_data/test_xfc_data/test_xfc.poni'
def_img_file = ''  # '/Users/vthampy/SSRL_Data/RDA/static_det_test_data/test_xfc_data/images_0004.tif'

params = [
    {'name': 'Calibration', 'type': 'group', 'children': [
        {'name': 'PONI File', 'title': 'PONI   ', 'type': 'str', 'value': def_poni_file},
        NamedActionParameter(name='poni_file_browse', title='Browse...'),
    ], 'expanded': True},
    {'name': 'Signal', 'type': 'group', 'children': [
        {'name': 'inp_type', 'title': '', 'type': 'list',
         'values': ['Image Series', 'Image Directory', 'Single Image'], 'value': 'Image Series'},
        {'name': 'File', 'title': 'Image File   ', 'type': 'str', 'value': def_img_file},
        NamedActionParameter(name='img_file_browse', title='Browse...'),
        {'name': 'img_dir', 'title': 'Directory', 'type': 'str', 'value': '', 'visible': False},
        NamedActionParameter(name='img_dir_browse', title='Browse...', visible=False),
        {'name': 'Filter', 'type': 'str', 'value': '', 'visible': False},
        {'name': 'img_ext', 'title': 'File Type  ', 'type': 'list',
         'values': ['tif', 'raw', 'hdf5', 'h5'], 'value':'tif', 'visible': False},
    ], 'expanded': True},
    {'name': 'BG', 'title': 'Background', 'type': 'group', 'children': [
        {'name': 'bg_type', 'title': '', 'type': 'list',
         'values': ['Single Bkg File', 'Bkg Directory'], 'value': 'Single Bkg'},
        {'name': 'File', 'title': 'Bkg File', 'type': 'str', 'value': ''},
        NamedActionParameter(name='bg_file_browse', title='Browse...'),
        {'name': 'Match', 'title': 'Match Parameter', 'type': 'group', 'children': [
            {'name': 'Parameter', 'type': 'list', 'values': ['File Root'], 'value': 'File Root'},
            {'name': 'bg_dir', 'title': 'Directory', 'type': 'str', 'value': ''},
            NamedActionParameter(name='bg_dir_browse', title='Browse...'),
            {'name': 'Filter', 'type': 'str', 'value': ''},
        ], 'expanded': True, 'visible': False},
        {'name': 'Scale', 'type': 'float', 'value': 1},
        {'name': 'norm_channel', 'title': 'Normalize', 'type': 'list', 'values': ['bstop'], 'value': 'bstop'},
    ], 'expanded': False},
    {'name': 'GI', 'title': 'Grazing Incidence', 'type': 'group', 'children': [
        {'name': 'Grazing', 'type': 'bool', 'value': False},
        {'name': 'th_motor', 'title': 'Theta Motor', 'type': 'list', 'values': ['th'], 'value': 'th'},
    ], 'expanded': False},
    {'name': 'Timeout', 'type': 'float', 'value': 1},
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

    def __init__(self, fname, file_lock, parent=None):
        """fname: str, file path
        file_lock: mp.Condition, process safe lock
        """
        ic()
        super().__init__(fname, file_lock, parent)

        # Scan Parameters
        self.scan_parameters = []
        self.counters = {}
        self.motors = {}

        # Setup gui elements
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.startButton.clicked.connect(self.sigStart.emit)
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
        self.poni_file = self.parameters.child('Calibration').child('PONI File').value()

        # Signal
        self.inp_type = self.parameters.child('Signal').child('inp_type').value()
        self.img_fname = self.parameters.child('Signal').child('File').value()
        self.img_dir = self.parameters.child('Signal').child('img_dir').value()
        self.img_ext = self.parameters.child('Signal').child('img_ext').value()
        self.single_img = True if self.inp_type == 'Single Image' else False
        self.file_filter = self.parameters.child('Signal').child('Filter').value()

        # Background
        self.bg_type = self.parameters.child('BG').child('bg_type').value()
        self.bg_file = self.parameters.child('BG').child('File').value()
        self.bg_dir = self.parameters.child('BG').child('Match').child('bg_dir').value()
        self.bg_matching_par = self.parameters.child('BG').child('Match').child('Parameter').value()
        self.bg_file_filter = self.parameters.child('BG').child('Match').child('Filter').value()
        self.bg_scale = self.parameters.child('BG').child('Scale').value()
        self.bg_norm_channel = self.parameters.child('BG').child('norm_channel').value()

        # Grazing Incidence
        self.gi = self.parameters.child('GI').child('Grazing').value()
        self.th_mtr = self.parameters.child('GI').child('th_motor').value()

        # Timeout
        self.timeout = self.parameters.child('Timeout').value()

        # Wire signals from parameter tree based buttons
        self.parameters.sigTreeStateChanged.connect(self.setup)

        self.parameters.child('Calibration').child('poni_file_browse').sigActivated.connect(
            self.set_poni_file
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

        # Setup thread
        self.thread = specThread(
            self.command_queue,
            self.sphere_args,
            self.file_lock,
            self.fname,
            self.scan_name,
            self.single_img,
            self.poni_file,
            self.inp_type,
            self.img_fname,
            self.img_dir,
            self.img_ext,
            self.file_filter,
            self.bg_type,
            self.bg_file,
            self.bg_dir,
            self.bg_matching_par,
            self.bg_file_filter,
            self.bg_scale,
            self.bg_norm_channel,
            self.gi,
            self.th_mtr,
            self.timeout,
            self
        )

        self.thread.showLabel.connect(self.ui.specLabel.setText)
        self.thread.sigUpdateFile.connect(self.sigUpdateFile.emit)
        self.thread.finished.connect(self.finished.emit)
        self.thread.sigUpdate.connect(self.sigUpdateData.emit)
        self.thread.sigUpdateArch.connect(self.sigUpdateArch.emit)
        self.thread.sigUpdateGI.connect(self.sigUpdateGI.emit)
        self.setup()

    def setup(self):
        """Sets up the child thread, syncs all parameters.
        """
        ic()
        # Calibration
        self.poni_file = self.parameters.child('Calibration').child('PONI File').value()
        self.thread.poni_file = self.poni_file

        # Signal
        self.file_filter = self.parameters.child('Signal').child('Filter').value()
        self.thread.file_filter = self.file_filter
        ic(self.file_filter)

        self.inp_type = self.parameters.child('Signal').child('inp_type').value()
        self.thread.inp_type = self.inp_type
        self.get_img_fname()
        self.thread.img_fname = self.img_fname
        ic(self.img_fname, self.inp_type)

        self.get_scan_parameters()
        self.thread.single_img = self.single_img

        self.img_dir, _, self.img_ext = split_file_name(self.img_fname)
        self.thread.img_dir, self.thread.img_ext = self.img_dir, self.img_ext

        self.scan_name = get_scan_name(self.img_fname)
        self.thread.scan_name = self.scan_name
        ic(self.img_dir, self.scan_name, self.img_ext)

        self.fname = os.path.join(self.img_dir, self.scan_name + '.hdf5')
        self.thread.fname = self.fname

        # Background
        self.bg_type = self.parameters.child('BG').child('bg_type').value()
        self.thread.bg_type = self.bg_type

        self.bg_file = self.parameters.child('BG').child('File').value()
        self.thread.bg_file = self.bg_file

        self.bg_matching_par = self.parameters.child('BG').child('Match').child('Parameter').value()
        self.thread.bg_matching_par = self.bg_matching_par

        self.bg_dir = self.parameters.child('BG').child('Match').child('bg_dir').value()
        self.thread.bg_dir = self.bg_dir

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

        self.thread.file_lock = self.file_lock
        self.thread.sphere_args = self.sphere_args

    def send_command(self):
        """Sends command in command line to spec, and calls
        commandLine send_command method to add command to list of
        commands.
        """
        ic()
        command = self.specCommandLine.text()
        if not (command.isspace() or command == ''):
            try:
                specCommand(command, queue=True)
            except Exception as e:
                print(e)
                print(f"Command '{command}' not sent")

        commandLine.send_command(self.specCommandLine)

    def pause(self):
        ic()
        if self.thread.isRunning():
            self.command_queue.put('pause')

    def cont(self):
        ic()
        if self.thread.isRunning():
            self.command_queue.put('continue')

    def stop(self):
        ic()
        if self.thread.isRunning():
            self.command_queue.put('stop')

    def set_poni_file(self):
        """Opens file dialogue and sets the calibration file
        """
        ic()
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Calibration').child('PONI File').setValue(fname)
        self.poni_file = fname

    def set_inp_type(self):
        """Change Parameter Names depending on Input Type
        """
        self.single_img = False
        self.parameters.child('Signal').child('File').show()
        self.parameters.child('Signal').child('img_file_browse').show()
        self.parameters.child('Signal').child('img_dir').hide()
        self.parameters.child('Signal').child('img_dir_browse').hide()
        self.parameters.child('Signal').child('Filter').hide()
        self.parameters.child('Signal').child('img_ext').hide()

        inp_type = self.parameters.child('Signal').child('inp_type').value()
        if inp_type == 'Image Directory':
            self.parameters.child('Signal').child('File').hide()
            self.parameters.child('Signal').child('img_file_browse').hide()
            self.parameters.child('Signal').child('img_dir').show()
            self.parameters.child('Signal').child('img_dir_browse').show()
            self.parameters.child('Signal').child('Filter').show()
            self.parameters.child('Signal').child('img_ext').show()

        if inp_type == 'Single Image':
            self.single_img = True

        self.inp_type = inp_type
        self.get_img_fname()
        ic(self.single_img, self.inp_type)

    def set_img_file(self):
        """Opens file dialogue and sets the spec data file
        """
        ic()
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('Signal').child('File').setValue(fname)
        self.img_fname = fname

    def set_img_dir(self):
        """Opens file dialogue and sets the signal data folder
        """
        ic()
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
        ic()
        old_fname = self.img_fname
        if self.inp_type != 'Image Directory':
            self.img_fname = self.parameters.child('Signal').child('File').value()
            if not os.path.isfile(self.img_fname):
                self.img_fname = ''
        else:
            img_ext = self.parameters.child('Signal').child('img_ext').value()
            img_dir = self.parameters.child('Signal').child('img_dir').value()
            filters = '*' + '*'.join(f for f in self.file_filter.split()) + '*'
            f_names = sorted(glob.glob(os.path.join(
                img_dir, f'{filters}[0-9][0-9][0-9][0-9].{img_ext}')))
            if len(f_names) > 0:
                self.img_fname = f_names[0]
            else:
                self.img_fname = ''
            ic(img_ext, img_dir, self.img_fname, f_names, filters, self.file_filter)

        ic(old_fname, self.img_fname, self.inp_type)
        if (self.img_fname != old_fname) or (self.img_fname and (len(self.scan_parameters) < 1)):
            self.get_scan_parameters()
            self.set_bg_matching_options()
            self.set_gi_motor_options()
            self.set_bg_norm_options()

    def set_bg_type(self):
        """Change Parameter Names depending on BG Type
        """
        ic()
        self.parameters.child('BG').child('File').show()
        self.parameters.child('BG').child('bg_file_browse').show()
        self.parameters.child('BG').child('Match').hide()

        self.bg_type = self.parameters.child('BG').child('bg_type').value()
        if self.bg_type != 'Single Bkg File':
            self.parameters.child('BG').child('File').hide()
            self.parameters.child('BG').child('bg_file_browse').hide()
            self.parameters.child('BG').child('Match').show()

    def set_bg_file(self):
        """Opens file dialogue and sets the background file
        """
        ic()
        fname, _ = Qt.QtWidgets.QFileDialog().getOpenFileName()
        if fname != '':
            self.parameters.child('BG').child('File').setValue(fname)
        self.bg_file = fname

    def set_bg_dir(self):
        """Opens file dialogue and sets the background folder
        """
        ic()
        path = QFileDialog().getExistingDirectory(
            caption='Choose Bkg Directory',
            directory='',
            options=QFileDialog.ShowDirsOnly
            # options =(QFileDialog.ShowDirsOnly)
        )
        if path != '':
            self.parameters.child('BG').child('Match').child('bg_dir').setValue(path)
        self.bg_dir = path

    def set_bg_matching_options(self):
        """Reads image metadata to populate matching parameters
        """
        ic()
        pars = [p for p in self.scan_parameters if not any(x.lower() in p.lower() for x in ['ROI', 'PD'])]
        pars.insert(0, 'File Root')
        if 'TEMP' in pars:
            pars.insert(1, pars.pop(pars.index('TEMP')))

        value = 'TEMP' if 'TEMP' in pars else 'File Root'
        opts = {'values': pars, 'limits': pars, 'value': value}
        self.parameters.child('BG').child('Match').child('Parameter').setOpts(**opts)

    def set_bg_matching_par(self):
        """Changes bg matching parameter
        """
        ic()
        self.bg_matching_par = self.parameters.child('BG').child('Match').child('Parameter').value()
        ic(self.bg_matching_par)

    def set_bg_norm_options(self):
        """Counter Values used to normalize and subtract background
        """
        ic()
        pars = self.counters
        pars.insert(0, 'None')

        opts = {'values': pars, 'limits': pars, 'value': 'None'}
        self.parameters.child('BG').child('norm_channel').setOpts(**opts)

    def set_bg_norm_channel(self):
        """Changes bg matching parameter
        """
        self.bg_norm_channel = self.parameters.child('BG').child('norm_channel').value()

    def set_gi_motor_options(self):
        """Reads image metadata to populate possible GI theta motor
        """
        ic()
        pars = [p for p in self.scan_parameters if not any(x.lower() in p.lower() for x in ['ROI', 'PD'])]
        if 'th' in pars:
            pars.insert(0, pars.pop(pars.index('th')))
            value = 'th'
        elif 'theta' in pars:
            pars.insert(0, pars.pop(pars.index('theta')))
            value = 'theta'

        opts = {'values': pars, 'limits': pars, 'value': value}
        self.parameters.child('GI').child('th_motor').setOpts(**opts)

    def set_gi_th_motor(self):
        """Update Grazing theta motor"""
        self.th_mtr = self.parameters.child('GI').child('th_motor').value()

    def get_scan_parameters(self):
        """Reads image metadata to populate matching parameters
        """
        ic()
        if not self.img_fname:
            return
        meta_file = os.path.splitext(self.img_fname)[0] + '.txt'
        image_meta_data = get_image_meta_data(meta_file, BL='11-3')
        self.scan_parameters = list(image_meta_data.keys())

        counters = get_image_meta_data(meta_file, BL='11-3', rv='Counters')
        self.counters = list(counters.keys())

        motors = get_image_meta_data(meta_file, BL='11-3', rv='Motors')
        self.motors = list(motors.keys())

    def enabled(self, enable):
        """Sets tree and start button to enable.

        args:
            enable: bool, True for enabled False for disabled.
        """
        ic()
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
        fname: str, path to data file.
        img_fname: str, path to image file
        img_dir: str, path to image directory
        img_ext : str, extension of image file
        poni_file: str, Poni File name
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
            file_lock,
            fname,
            scan_name,
            single_img,
            poni_file,
            inp_type,
            img_fname,
            img_dir,
            img_ext,
            file_filter,
            bg_type,
            bg_file,
            bg_dir,
            bg_matching_par,
            bg_file_filter,
            bg_scale,
            bg_norm_channel,
            gi,
            th_mtr,
            timeout,
            parent=None):

        """command_queue: mp.Queue, queue for commands sent from parent
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        fname: str, path to data file.
        file_lock: mp.Condition, process safe lock for file access
        scan_name: str, name of current scan
        single_img: bool, True if there is only one image
        poni_file: str, poni file name
        img_fname: str, path to input image file
        img_dir: str, path to image directory
        img_ext : str, extension of image file
        timeout: float or int, how long to continue checking for new
            data.
        gi: bool, grazing incidence flag to determine if pyGIX is to be used
        th_mtr: float, incidence angle
        """
        ic()
        super().__init__(command_queue, sphere_args, fname, file_lock, parent)

        self.scan_name = scan_name
        self.single_img = single_img
        self.poni_file = poni_file
        self.inp_type = inp_type
        self.img_fname = img_fname
        self.img_dir = img_dir
        self.img_ext = img_ext
        self.file_filter = file_filter
        self.bg_type = bg_type
        self.bg_file = bg_file
        self.bg_dir = bg_dir
        self.bg_matching_par = bg_matching_par
        self.bg_file_filter = bg_file_filter
        self.bg_scale = bg_scale
        self.bg_norm_channel = bg_norm_channel
        self.gi = gi
        self.th_mtr = th_mtr
        self.timeout = timeout

    def run(self):
        """Initializes specProcess and watches for new commands from
        parent or signals from the process.
        """
        ic()

        process = specProcess(
            self.command_q,
            self.signal_q,
            self.sphere_args,
            self.file_lock,
            self.fname,
            self.scan_name,
            self.single_img,
            self.poni_file,
            self.inp_type,
            self.img_fname,
            self.img_dir,
            self.img_ext,
            self.file_filter,
            self.bg_type,
            self.bg_file,
            self.bg_dir,
            self.bg_matching_par,
            self.bg_file_filter,
            self.bg_scale,
            self.bg_norm_channel,
            self.gi,
            self.th_mtr,
            self.timeout
        )

        process.start()
        last = False
        # Main loop
        while True:
            # Check for new commands
            if not self.input_q.empty():
                command = self.input_q.get()
                ic(command)
                self.command_q.put(command)

            # Check for new updates
            if not self.signal_q.empty():
                signal, data = self.signal_q.get()
                if signal == 'update':
                    self.sigUpdate.emit(data)
                elif signal == 'updateArch':
                    self.sigUpdateArch.emit(data)
                elif signal == 'message':
                    self.showLabel.emit(data)
                elif signal == 'new_scan':
                    ic(data)
                    self.sigUpdateFile.emit(*data)
                    ic(self.scan_name, self.single_img)
                    # self.sigUpdateFile.emit(self.scan_name, self.fname,
                    #                         self.gi, self.th_mtr,
                    #                         self.single_img)
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
        ic()
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
        scan_name: str, name of current scan
        img_ext : str, extension of image file
        signal_q: queue to place signals back to parent thread.
        fname: str, path to data file
        single_img: bool, True if there is only one image
        poni_file: str, poni file name
        img_fname: str, path to input image file
        img_dir: str, path to image directory
        img_ext : str, extension of image file
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

    def __init__(
            self,
            command_q,
            signal_q,
            sphere_args,
            file_lock,
            fname,
            scan_name,
            single_img,
            poni_file,
            inp_type,
            img_fname,
            img_dir,
            img_ext,
            file_filter,
            bg_type,
            bg_file,
            bg_dir,
            bg_matching_par,
            bg_file_filter,
            bg_scale,
            bg_norm_channel,
            gi,
            th_mtr,
            timeout,
            *args, ** kwargs):

        """command_q: mp.Queue, queue for commands from parent thread.
        signal_q: queue to place signals back to parent thread.
        sphere_args: dict, used as **kwargs in sphere initialization.
            see EwaldSphere.
        scan_name: str, name of current scan
        single_img: bool, True if there is only one image
        fname: str, path to data file
        file_lock: mp.Condition, process safe lock for file access
        poni_file: str, poni file name
        img_dir: str, path to image directory
        timeout: float or int, how long to continue checking for new
            data.
        """
        ic()
        super().__init__(command_q, signal_q, sphere_args, fname, file_lock,
                         *args, **kwargs)

        self.scan_name = scan_name
        self.single_img = single_img
        self.poni_file = poni_file
        self.inp_type = inp_type
        self.img_fname = img_fname
        self.img_dir = img_dir
        self.img_ext = img_ext
        self.file_filter = file_filter
        self.bg_type = bg_type
        self.bg_file = bg_file
        self.bg_dir = bg_dir
        self.bg_matching_par = bg_matching_par
        self.bg_file_filter = bg_file_filter
        self.bg_scale = bg_scale
        self.bg_norm_channel = bg_norm_channel
        self.gi = gi
        self.th_mtr = th_mtr
        self.timeout = timeout

        self.meta_ext = 'txt'
        self.user = None
        self.processed = []

    def _main(self):
        """Checks for commands in queue, sends back updates through
        signal queue, and catches errors. Calls wrangle method for
        reading in data, then performs integration.
        """
        ic()

        ic(self.inp_type)
        if self.inp_type != 'Image Directory':
            self.process_scan()
        else:
            pause = False
            start = time.time()
            while True:
                # Check for commands, or wait if paused
                if not self.command_q.empty() or pause:
                    command = self.command_q.get()
                    print(command)
                    if command == 'stop':
                        self.signal_q.put(('TERMINATE', None))
                        break
                    elif command == 'continue':
                        pause = False
                    elif command == 'pause':
                        pause = True
                        continue

                self.scan_name, self.img_fname, self.fname = self._get_new_scan_info()
                if self.scan_name:
                    ic(self.scan_name, self.img_fname, self.fname, self.processed, self.file_filter)
                    self.signal_q.put(('message', f"New Scan: {self.scan_name}"))
                    time.sleep(3)
                    rv = self.process_scan()
                    if rv == 'Stop':
                        self.signal_q.put(('TERMINATE', None))
                        break
                else:
                    elapsed = time.time() - start
                    if elapsed > self.timeout:
                        self.signal_q.put(('message', "Timeout occurred"))
                        self.signal_q.put(('TERMINATE', None))
                        break
                    else:
                        continue
                start = time.time()

            # If loop ends, signal terminate to parent thread.
            self.signal_q.put(('TERMINATE', None))

    def process_scan(self):
        """Go through series of images in a scan and process them individually
        """
        first_img = get_img_number(self.img_fname)
        ic(first_img, self.single_img)
        if (first_img is None) and (self.img_ext not in ['.h5', 'hdf5']):
            self.single_img = True

        # Initialize sphere and save to disk, send update for new scan
        ic(self.fname, self.scan_name, self.single_img, self.gi)
        sphere = EwaldSphere(self.scan_name,
                             data_file=self.fname,
                             static=True,
                             gi=self.gi,
                             th_mtr=self.th_mtr,
                             single_img=self.single_img,
                             **self.sphere_args)
        ic(self.sphere_args)
        with self.file_lock:
            sphere.save_to_h5(replace=True)
            # self.signal_q.put(('new_scan', None))
            self.signal_q.put(('new_scan',
                               (self.scan_name, self.fname,
                                self.gi, self.th_mtr,
                                self.single_img)))
        ic(sphere.name)

        # Enter main loop
        i = 1
        if not self.single_img:
            i = first_img
        pause = False
        start = time.time()
        while True:
            # Check for commands, or wait if paused
            if not self.command_q.empty() or pause:
                command = self.command_q.get()
                print(command)
                if command == 'stop':
                    self.signal_q.put(('TERMINATE', None))
                    return "Stop"
                    # break
                elif command == 'continue':
                    pause = False
                elif command == 'pause':
                    pause = True
                    continue

            # Get result from wrangle
            try:
                print(f'wrangle: {i}')
                flag, data = self.wrangle(i)

            # Errors associated with image not yet taken
            except (KeyError, FileNotFoundError, AttributeError, ValueError):
                elapsed = time.time() - start
                if elapsed > self.timeout:
                    if self.inp_type != 'Image Directory':
                        self.signal_q.put(('message', "Timeout occurred"))
                        self.signal_q.put(('TERMINATE', None))
                    break
                else:
                    continue
            start = time.time()

            # Unpack data and load into sphere
            # TODO: Test how long integrating vs io takes
            if flag == 'image':
                idx, map_raw, scan_info = data
                arch = EwaldArch(
                    idx, map_raw, poni_file=self.poni_file,
                    scan_info=scan_info, static=True, gi=self.gi,
                    th_mtr=self.th_mtr,
                )

                # integrate image to 1d and 2d arrays
                arch.integrate_1d(**sphere.bai_1d_args)
                arch.integrate_2d(**sphere.bai_2d_args)

                ic(sphere.bai_1d_args, sphere.bai_2d_args)

                # Add arch copy to sphere, save to file
                with self.file_lock:
                    arch_copy = arch.copy()
                    sphere.add_arch(
                        arch=arch_copy, calculate=False, update=True,
                        get_sd=True, set_mg=False, static=True, gi=self.gi,
                        th_mtr=self.th_mtr
                    )
                    sphere.save_to_h5(data_only=True, replace=False)

                self.signal_q.put(('message', f'Image {i} integrated'))
                self.signal_q.put(('update', idx))
                if self.single_img:
                    self.signal_q.put(('TERMINATE', None))
                    break

                i += 1

            # Check if terminate signal sent
            elif flag == 'TERMINATE' and data is None:
                self.signal_q.put(('TERMINATE', None))
                break

        # If loop ends, signal terminate to parent thread.
        if self.inp_type != 'Image Directory':
            self.signal_q.put(('TERMINATE', None))

        return None

    def wrangle(self, i):
        """Method for reading in data from raw files and spec file.

        args:
            i: int, index of image to check

        returns:
            flag: str, signal for what kind of data to expect.
            data: tuple (int, numpy array, dict, dict), the
                index of the data, raw image array, metadata
                dict associated with the image.
        """
        ic()
        self.signal_q.put(('message', f'Checking for {i}'))

        # Construct raw_file path from attributes and index
        if (not self.single_img) and (self.img_ext not in ['.h5', '.hdf5']):
            image_file = self._get_image_path(i)
        else:
            image_file = self.img_fname
        ic(image_file)

        # Read raw file into numpy array
        arr = read_image_file(image_file, im=i-1, return_float=True)

        meta_file = f'{os.path.splitext(image_file)[0]}.{self.meta_ext}'
        if os.path.exists(meta_file):
            image_meta = get_image_meta_data(meta_file, BL='11-3')
        else:
            image_meta = {}
        # ic(image_meta)

        # Subtract background if any
        bg = self.get_background(image_meta)
        arr -= bg

        fname = os.path.splitext(os.path.basename(image_file))[0]
        self.signal_q.put(('message', f'{fname} wrangled'))
        # self.signal_q.put(('message', f'Image {i} wrangled'))

        return 'image', (i, arr, image_meta)

    def _get_image_path(self, i):
        """Creates raw path name from attributes, following spec
        convention.

        args:
            i: int, index of image

        returns:
            image_file: str, absolute path to image file.
        """
        ic()
        im_base = '_'.join([
            self.scan_name,
            str(i).zfill(4)
        ])
        return os.path.join(self.img_dir, f'{im_base}.{self.img_ext}')

    def _get_new_scan_info(self):
        """ Gets all unique file roots in a directory that are used
        as scan_names

        Returns:
            scan_names {list, str}: list of scan names in directory
        """
        filters = '*' + '*'.join(f for f in self.file_filter.split()) + '*'
        f_names = sorted(glob.glob(os.path.join(
            self.img_dir, f'{filters}[0-9][0-9][0-9][0-9].{self.img_ext}')))
        ic(filters, self.file_filter)

        if len(f_names) == 0:
            return None, None, None

        scan_names = sorted(list(set([get_scan_name(f) for f in f_names])))
        scan_names = [s for s in scan_names if s not in self.processed]
        # ic(scan_names)

        if len(scan_names) == 0:
            return None, None, None

        ic(filters, scan_names, self.processed)
        self.scan_name = scan_names[0]
        self.processed.append(self.scan_name)

        f_names = sorted(glob.glob(os.path.join(
            self.img_dir, f'{self.scan_name}_[0-9][0-9][0-9][0-9].{self.img_ext}')))

        self.img_fname = f_names[0]
        self.fname = os.path.join(self.img_dir, self.scan_name + '.hdf5')

        return self.scan_name, self.img_fname, self.fname

    def get_background(self, image_meta):
        """Subtract background image if bg_file or bg_dir specified
        """
        ic()
        bg_file, bg_meta = None, None
        ic(self.bg_type, self.bg_file, self.bg_dir, self.bg_matching_par)

        if self.bg_type == 'Single Bkg File':
            if self.bg_file:
                ic(self.bg_file)
                bg_file = self.bg_file
        else:
            if self.bg_dir:
                if self.bg_file_filter == '':
                    self.bg_file_filter = 'bg'
                filters = '*' + '*'.join(f for f in self.bg_file_filter.split()) + '*'
                meta_files = sorted(glob.glob(os.path.join(
                    self.img_dir, f'{filters}[0-9][0-9][0-9][0-9].{self.meta_ext}')))
                ic(filters, meta_files)

                for meta_file in meta_files:
                    bg_meta = get_image_meta_data(meta_file, BL='11-3')
                    if bg_meta[self.bg_matching_par] == image_meta[self.bg_matching_par]:
                        bg_file = f'{os.path.splitext(meta_file)[0]}.{self.img_ext}'
                        ic(meta_file, bg_file)
                        ic(bg_meta[self.bg_matching_par], image_meta[self.bg_matching_par])
                        break

        if not bg_file:
            return 0.

        ic(bg_file)
        bg = read_image_file(self.bg_file, return_float=True)
        bg_meta_file = f'{os.path.splitext(self.bg_file)[0]}.{self.meta_ext}'
        bg_meta = get_image_meta_data(bg_meta_file, BL='11-3')

        bg *= self.bg_scale
        if self.bg_norm_channel != 'None':
            bg *= (image_meta[self.bg_norm_channel]/bg_meta[self.bg_norm_channel])

        return bg
