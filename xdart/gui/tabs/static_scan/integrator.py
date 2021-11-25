# -*- coding: utf-8 -*-
"""
@author: thampy
"""

# Standard library imports
import os
import sys
import subprocess

from xdart.utils.pyFAI_binaries import pyFAI_calib2_main
from xdart.utils.pyFAI_binaries import pyFAI_drawmask_main
from xdart.utils.pyFAI_binaries import MaskImageWidgetXdart
from pyFAI.app.drawmask import postProcessId21
# from xdart.utils._utils import launch

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import Parameter

# This module imports
if sys.platform == 'win32':
    from .ui.integratorUI_windows import Ui_Form
else:
    from .ui.integratorUI_mac import Ui_Form

from .sphere_threads import integratorThread

_translate = Qt.QtCore.QCoreApplication.translate
QFileDialog = Qt.QtWidgets.QFileDialog

AA_inv = u'\u212B\u207B\u00B9'
Th = u'\u03B8'
Deg = u'\u00B0'
Units = [f"Q ({AA_inv})", f"2{Th} ({Deg})"]
Units_dict = {Units[0]: 'q_A^-1', Units[1]: '2th_deg'}
# Units_dict_inv = {'q_A^-1': Units[0], '2th_deg': Units[1]}
Units_dict_inv = {'q_A^-1': 0, '2th_deg': 1}

params = [
    {'name': 'Default', 'type': 'group', 'children': [
            {'name': 'Integrate 1D', 'type': 'group', 'children': [
                # {'name': 'numpoints', 'type': 'int', 'value': 1000, 'visible': False},
                # {'name': 'unit', 'type': 'list', 'values': {
                #     # "2" + u"\u03B8": '2th_deg', "q (A-1)": 'q_A^-1'
                #     Units[0]: 'q_A^-1', Units[1]: '2th_deg',
                #     }, 'value': 'q_A^-1', 'visible':False
                #  },  # 2th_deg
                # {'name': 'radial_range', 'type': 'group', 'children': [
                #     {'name': 'Low', 'type': 'float', 'value': 0.0, 'visible': False},
                #     {'name': 'High', 'type': 'float', 'value': 60.0, 'visible': False},
                #     {'name': 'Auto', 'type': 'bool', 'value': True, 'visible': False},
                #     ], 'visible': False,
                #  },
                # {'name': 'azimuth_range', 'type': 'group', 'children': [
                #         {'name': 'Low', 'type': 'float', 'value': -180.0, 'visible': False},
                #         {'name': 'High', 'type': 'float', 'value': 180.0, 'visible': False},
                #         {'name': 'Auto', 'type': 'bool', 'value': True, 'visible': False},
                #     ], 'visible': False,
                #  },
                {'name': 'monitor', 'type': 'str', 'value': 'I0'},
                {'name': 'correctSolidAngle', 'type': 'bool', 'value': True},
                {'name': 'dummy', 'type': 'float', 'value': -1.0},
                {'name': 'delta_dummy', 'type': 'float', 'value': 0.0},
                {'name': 'Apply polarization factor', 'type': 'bool', 'value': False},
                {'name': 'polarization_factor', 'type': 'float', 'value': 0,
                    'limits': (-1, 1)},
                {'name': 'method', 'type': 'list', 'values': [
                        "numpy", "cython", "BBox", "splitpixel", "lut", "csr",
                        "nosplit_csr", "full_csr", "lut_ocl", "csr_ocl"
                    ], 'value':'csr'},
                {'name': 'safe', 'type': 'bool', 'value': True},
                # {'name': 'block_size', 'type': 'int', 'value': 32},
                # {'name': 'profile', 'type': 'bool', 'value': False},
                ]
             },
            {'name': 'Integrate 2D', 'type': 'group', 'children': [
                # {'name': 'npt_rad', 'type': 'int', 'value': 1000, 'visible': False},
                # {'name': 'npt_azim', 'type': 'int', 'value': 1000, 'visible': False},
                # {'name': 'unit', 'type': 'list', 'values': {
                #     Units[0]: 'q_A^-1', Units[1]: '2th_deg',
                #     # "2" + u"\u03B8": '2th_deg', "q (A-1)": 'q_A^-1'
                #     }, 'value': 'q_A^-1', 'visible': False},
                # {'name': 'radial_range', 'type': 'group', 'children': [
                #         {'name': 'Low', 'type': 'float', 'value': 0.0},
                #         {'name': 'High', 'type': 'float', 'value': 180.0},
                #         {'name': 'Auto', 'type': 'bool', 'value': True},
                #     ], 'visible': False,
                #  },
                # {'name': 'azimuth_range', 'type': 'group', 'children': [
                #         {'name': 'Low', 'type': 'float', 'value': -180.0},
                #         {'name': 'High', 'type': 'float', 'value': 180.0},
                #         {'name': 'Auto', 'type': 'bool', 'value': True,
                #          'visible': True},
                #     ], 'visible': False,
                #  },
                {'name': 'monitor', 'type': 'str', 'value': 'None'},
                {'name': 'correctSolidAngle', 'type': 'bool', 'value': True},
                {'name': 'dummy', 'type': 'float', 'value': -1.0},
                {'name': 'delta_dummy', 'type': 'float', 'value': 0.0},
                {'name': 'Apply polarization factor', 'type': 'bool', 'value': False},
                {'name': 'polarization_factor', 'type': 'float', 'value': 0,
                    'limits': (-1, 1)},
                {'name': 'method', 'type': 'list', 'values': [
                        "numpy", "cython", "BBox", "splitpixel", "lut",
                        "csr", "lut_ocl", "csr_ocl"
                    ], 'value':'csr'},
                {'name': 'safe', 'type': 'bool', 'value': True}
                ]
             }
        ]

     },
]


class integratorTree(Qt.QtWidgets.QWidget):
    """Widget for controlling integration of loaded data. Presents basic
    parameters to the user in easy to control widgets, and also
    launches menus for more advanced options.

    attributes:
        advancedWidget1D, advancedWidget2D: advancedParameters, pop up
            windows with advanced parameters
        azimuthalRange2D, radialRange1D, radialRange2D: rangeWidget,
            widgets which control the integration ranges for 1D and 2D
            integration
        bai_1d_pars, bai_2d_pars: pyqtgraph parameters, children of
            main parameters attribute that hold parameters related to
            1D and 2D integration
        mg_1d_pars, mg_2d_pars: unused, hold paramters for multigeometry
            integration
        mg_pars: unused, holds parameters for setting up multigeometry
        ui: Ui_Form from qtdesigner

    methods:
        get_args: Gets requested parameters and converts them to args
            in EwaldSphere object.
        setEnabled: Enables integration and parameter modification.
        update: Grabs args from EwaldSphere object and sets all params
            to match.
    """
    def __init__(self, sphere, arch, file_lock,
                 arches, arch_ids, data_1d, data_2d, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.sphere = sphere
        self.arch = arch
        self.file_lock = file_lock
        self.arches = arches
        self.arch_ids = arch_ids
        self.data_1d = data_1d
        self.data_2d = data_2d
        self.parameters = Parameter.create(
            name='integrator', type='group', children=params
        )
        self.bai_1d_pars = self.parameters.child('Default', 'Integrate 1D')
        self.bai_2d_pars = self.parameters.child('Default', 'Integrate 2D')
        self.mask_window = None

        # UI adjustments
        _translate = Qt.QtCore.QCoreApplication.translate
        self.ui.unit_1D.setItemText(0, _translate("Form", Units[0]))
        self.ui.unit_1D.setItemText(1, _translate("Form", Units[1]))
        self.ui.label_azim_1D.setText(f"Chi ({Deg})")

        self.ui.unit_2D.setItemText(0, _translate("Form", Units[0]))
        self.ui.unit_2D.setItemText(1, _translate("Form", Units[1]))
        self.ui.label_azim_2D.setText(f"Chi ({Deg})")

        # Set constraints on range inputs
        self._validate_ranges()

        # Set AutoRange Flags
        self.radial_autoRange_1D = self.ui.radial_autoRange_1D.isChecked()
        self.azim_autoRange_1D = self.ui.azim_autoRange_1D.isChecked()
        self.radial_autoRange_2D = self.ui.radial_autoRange_2D.isChecked()
        self.azim_autoRange_2D = self.ui.azim_autoRange_2D.isChecked()

        # Setup advanced parameters tree widget
        self.advancedWidget1D = advancedParameters(self.bai_1d_pars, 'bai_1d')
        self.advancedWidget2D = advancedParameters(self.bai_2d_pars, 'bai_2d')

        # Connect input parameter value signals
        self._connect_inp_signals()

        # Connect integrate and advanced button signals
        self.ui.advanced1D.clicked.connect(self.advancedWidget1D.show)
        self.ui.advanced2D.clicked.connect(self.advancedWidget2D.show)

        self.ui.integrate1D.clicked.connect(self.bai_1d)
        self.ui.integrate2D.clicked.connect(self.bai_2d)

        self.integrator_thread = integratorThread(
            self.sphere, self.arch, self.file_lock,
            self.arches, self.arch_ids, self.data_1d, self.data_2d
        )

        # Connect Calibrate and Mask Buttons
        self.ui.pyfai_calib.clicked.connect(self.run_pyfai_calib)
        self.ui.get_mask.clicked.connect(self.run_pyfai_drawmask)

        self.setEnabled()
        # self.set_image_units()

        # Connect Axis 2D signal
        self.ui.axis2D.currentIndexChanged.connect(self._update_axes)

    def update(self):
        """Grabs args from sphere and uses _sync_ranges and
        _update_params private methods to update.

        args:
            sphere: EwaldSphere, object to get args from.
        """
        self._update_params()

    def setEnabled(self, enable=True):
        """Overrides parent class method. Ensures appropriate child
        widgets are enabled.

        args:
            enable: bool, If True widgets are enabled. If False
                they are disabled.
        """
        self.ui.frame1D.setEnabled(enable)
        self.ui.frame2D.setEnabled(enable)
        self.advancedWidget1D.setEnabled(enable)
        self.advancedWidget2D.setEnabled(enable)

        if self.radial_autoRange_1D:
            self.ui.radial_low_1D.setEnabled(False)
            self.ui.radial_high_1D.setEnabled(False)

        if self.azim_autoRange_1D:
            self.ui.azim_low_1D.setEnabled(False)
            self.ui.azim_high_1D.setEnabled(False)

        if self.radial_autoRange_2D:
            self.ui.radial_low_2D.setEnabled(False)
            self.ui.radial_high_2D.setEnabled(False)

        if self.azim_autoRange_2D:
            self.ui.azim_low_2D.setEnabled(False)
            self.ui.azim_high_2D.setEnabled(False)

        # self.ui.integrate1D.setEnabled(False)
        # self.ui.integrate2D.setEnabled(False)

    def update_radial_autoRange_1D(self):
        """Disable/Enable radial 1D widget if auto range is un/selected
        """
        self.radial_autoRange_1D = self.ui.radial_autoRange_1D.isChecked()
        # self.setEnabled()

        self.bai_1d_pars.child('radial_range', 'Auto').setValue(
            self.radial_autoRange_1D)
        if self.radial_autoRange_1D:
            self.sphere.bai_1d_args['radial_range'] = None
            self.ui.radial_low_1D.setEnabled(False)
            self.ui.radial_high_1D.setEnabled(False)
        else:
            self.ui.radial_low_1D.setEnabled(True)
            self.ui.radial_high_1D.setEnabled(True)

        # print(f'integrator > update_radial_autoRange_1D: sphere_bai_1d = {self.sphere.bai_1d_args}')

    def update_azim_autoRange_1D(self):
        """Disable/Enable azim 1D widget if auto range is un/selected
        """
        self.azim_autoRange_1D = self.ui.azim_autoRange_1D.isChecked()

        self.bai_1d_pars.child('azimuth_range', 'Auto').setValue(
            self.azim_autoRange_1D)

        if self.azim_autoRange_1D:
            self.sphere.bai_1d_args['azimuth_range'] = None
            self.ui.azim_low_1D.setEnabled(False)
            self.ui.azim_high_1D.setEnabled(False)
        else:
            self.ui.azim_low_1D.setEnabled(True)
            self.ui.azim_high_1D.setEnabled(True)

        # print(f"integrator > update_azim_autoRange_1D: radial_range {self.sphere.bai_1d_args['radial_range']}")

    def update_radial_autoRange_2D(self):
        """Disable/Enable radial 2D widget if auto range is un/selected
        """
        #ic()
        self.radial_autoRange_2D = self.ui.radial_autoRange_2D.isChecked()

        self.bai_2d_pars.child('radial_range', 'Auto').setValue(
            self.radial_autoRange_2D)

        if self.radial_autoRange_2D:
            self.sphere.bai_2d_args['radial_range'] = None
            self.ui.radial_low_2D.setEnabled(False)
            self.ui.radial_high_2D.setEnabled(False)
        else:
            self.ui.radial_low_2D.setEnabled(True)
            self.ui.radial_high_2D.setEnabled(True)

        # print(f"integrator > update_radial_autoRange_2D: radial_range {self.sphere.bai_2d_args['radial_range']}")

    def update_azim_autoRange_2D(self):
        """Disable/Enable radial 2D widget if auto range is un/selected
        """
        #ic()
        self.azim_autoRange_2D = self.ui.azim_autoRange_2D.isChecked()

        self.bai_2d_pars.child('azimuth_range', 'Auto').setValue(
            self.azim_autoRange_2D)

        if self.azim_autoRange_2D:
            self.sphere.bai_2d_args['azimuth_range'] = None
            self.ui.azim_low_2D.setEnabled(False)
            self.ui.azim_high_2D.setEnabled(False)
        else:
            self.ui.azim_low_2D.setEnabled(True)
            self.ui.azim_high_2D.setEnabled(True)

        # print(f"integrator > update_azim_autoRange_2D: azimuth_range = {self.sphere.bai_2d_args['azimuth_range']}")

    def _validate_ranges(self):
        #ic()
        self.ui.npts_1D.setValidator(Qt.QtGui.QIntValidator(0, 50000))
        self.ui.npts_radial_2D.setValidator(Qt.QtGui.QIntValidator(0, 50000))
        self.ui.npts_azim_2D.setValidator(Qt.QtGui.QIntValidator(0, 50000))

        minmax = (0, 50)
        if self.ui.unit_1D.currentIndex() == 1:
            minmax = (-180, 180)
        self.ui.radial_low_1D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))
        self.ui.radial_high_1D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))

        minmax = (0, 50)
        if self.ui.unit_2D.currentIndex() == 1:
            minmax = (-180, 180)
        self.ui.radial_low_2D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))
        self.ui.radial_high_2D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))

        self.ui.azim_low_1D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))
        self.ui.azim_high_1D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))
        self.ui.azim_low_2D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))
        self.ui.azim_high_2D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))

    def _update_params(self):
        """Grabs args from sphere and syncs parameters with them.

        args:
            sphere: EwaldSphere, object to get args from.
        """
        #ic()

        self._disconnect_inp_signals()
        with self.sphere.sphere_lock:
            self._args_to_params(self.sphere.bai_1d_args, self.bai_1d_pars, dim='1D')
            self._args_to_params(self.sphere.bai_2d_args, self.bai_2d_pars, dim='2D')
        self._connect_inp_signals()

    def get_args(self, key):
        """Updates sphere with all parameters held in integrator.

        args:
            sphere: EwaldSphere, object to update
            key: str, which args to update.
        """
        #ic()
        with self.sphere.sphere_lock:
            if key == 'bai_1d':
                #ic('bai_1D_args before', self.sphere.bai_1d_args)
                self._get_npts_1D()
                self._get_unit_1D()
                self._get_radial_range_1D()
                self._get_azim_range_1D()
                self._params_to_args(self.sphere.bai_1d_args, self.bai_1d_pars)
                #ic('bai_1D_args after', self.sphere.bai_1d_args)

            elif key == 'bai_2d':
                #ic('bai_2D_args before', self.sphere.bai_2d_args)
                self._get_npts_radial_2D()
                self._get_npts_azim_2D()
                self._get_unit_2D()
                self._get_radial_range_2D()
                self._get_azim_range_2D()
                self._params_to_args(self.sphere.bai_2d_args, self.bai_2d_pars)
                #ic('bai_2D_args after', self.sphere.bai_2d_args)

    def _args_to_params(self, args, tree, dim='1D'):
        """Takes in args dictionary and sets all parameters in tree
        to match the args.

        args:
            args: dict, values to use for updating tree
            tree: pyqtgraph Parameter, parameters to update
        """
        #ic()

        #ic(args)
        if len(args) == 0:
            return

        with tree.treeChangeBlocker():
            for key, val in args.items():
                if key == 'radial_range':
                    if dim == '1D':
                        self._set_radial_range_1D()
                    else:
                        self._set_radial_range_2D()
                elif key == 'azimuth_range':
                    if dim == '1D':
                        self._set_azim_range_1D()
                    else:
                        self._set_azim_range_2D()
                elif key == 'unit':
                    if dim == '1D':
                        self._set_unit_1D()
                    else:
                        self._set_unit_2D()
                elif key == 'numpoints':
                    self._set_npts_1D()
                elif key == 'npt_rad':
                    self._set_npts_radial_2D()
                elif key == 'npt_azim':
                    self._set_npts_azim_2D()
                elif key == 'polarization_factor':
                    if val is None:
                        tree.child('Apply polarization factor').setValue(True)
                    else:
                        tree.child('Apply polarization factor').setValue(True)
                        tree.child(key).setValue(val)
                else:
                    try:
                        child = tree.child(key)
                    except:
                        # No specific error thrown for missing child
                        child = None
                    if child is not None:
                        if val is None:
                            child.setValue('None')
                        else:
                            child.setValue(val)

    def _params_to_args(self, args, tree):
        """Sets all values in args to match tree.

        args:
            args: dict, values to be updates
            tree: pyqtgraph Parameter, parameters used to update args
        """
        #ic()

        #ic(tree, args)
        for child in tree.children():
            # print(f'integrator > _params_to_args: child.name, value = {child.name()}, {child.value()}')
            if 'range' in child.name():
                if child.child("Auto").value():
                    args[child.name()] = None
                else:
                    args[child.name()] = [child.child("Low").value(),
                                          child.child("High").value()]
            elif child.name() == 'polarization_factor':
                pass
            elif child.name() == 'Apply polarization factor':
                if child.value():
                    args['polarization_factor'] = \
                        tree.child('polarization_factor').value()
                else:
                    args['polarization_factor'] = None
            else:
                val = child.value()
                if val == 'None':
                    args[child.name()] = None
                else:
                    args[child.name()] = val

    def _get_radial_range_1D(self):
        """Sets Sphere 1D radial range in bai_1d_args from UI values"""
        #ic()

        auto = self.ui.radial_autoRange_1D.isChecked()
        self.radial_autoRange_1D = auto

        _range = None
        if not auto:
            _range = self._get_valid_range(self.ui.radial_low_1D,
                                           self.ui.radial_high_1D)
        self.sphere.bai_1d_args['radial_range'] = _range

        self.ui.radial_low_1D.setEnabled(not auto)
        self.ui.radial_high_1D.setEnabled(not auto)
        #ic(_range)

    def _set_radial_range_1D(self):
        """Sets UI values from Sphere 1D radial range in bai_1d_args"""
        #ic()

        self._disconnect_radial_range_1D_signals()

        _range = self.sphere.bai_1d_args['radial_range']
        #ic(self.sphere.bai_1d_args, _range)
        if _range is None:
            self.ui.radial_autoRange_1D.setChecked(True)
            auto = True
        else:
            self.ui.radial_low_1D.setText(str(_range[0]))
            self.ui.radial_high_1D.setText(str(_range[0]))
            auto = False

        self.radial_autoRange_1D = auto
        self.ui.radial_low_1D.setEnabled(not auto)
        self.ui.radial_high_1D.setEnabled(not auto)

        self._connect_radial_range_1D_signals()

    def _get_azim_range_1D(self):
        """Sets Sphere 1D azimuth range in bai_1d_args from UI values"""
        #ic()

        auto = self.ui.azim_autoRange_1D.isChecked()
        self.azim_autoRange_1D = auto

        _range = None
        if not auto:
            _range = self._get_valid_range(self.ui.azim_low_1D,
                                           self.ui.azim_high_1D)
        self.sphere.bai_1d_args['azimuth_range'] = _range

        self.ui.azim_low_1D.setEnabled(not auto)
        self.ui.azim_high_1D.setEnabled(not auto)
        #ic(_range)

    def _set_azim_range_1D(self):
        """Sets UI values from Sphere 1D aazimuth range in bai_1d_args"""
        #ic()

        self._disconnect_azim_range_1D_signals()

        _range = self.sphere.bai_1d_args['azimuth_range']
        #ic(self.sphere.bai_1d_args, _range)
        if _range is None:
            self.ui.azim_autoRange_1D.setChecked(True)
            auto = True
        else:
            self.ui.azim_low_1D.setText(str(_range[0]))
            self.ui.azim_high_1D.setText(str(_range[0]))
            auto = False

        self.azim_autoRange_1D = auto
        self.ui.azim_low_1D.setEnabled(not auto)
        self.ui.azim_high_1D.setEnabled(not auto)

        self._connect_azim_range_1D_signals()

    def _get_radial_range_2D(self):
        """Sets Sphere 2D radial range in bai_1d_args from UI values"""
        #ic()

        auto = self.ui.radial_autoRange_2D.isChecked()
        self.radial_autoRange_2D = auto

        _range = None
        if not auto:
            _range = self._get_valid_range(self.ui.radial_low_2D,
                                           self.ui.radial_high_2D)

        if self.ui.axis2D.currentIndex() == 1:
            self.sphere.bai_2d_args['x_range'] = _range
        else:
            self.sphere.bai_2d_args['radial_range'] = _range

        self.ui.radial_low_2D.setEnabled(not auto)
        self.ui.radial_high_2D.setEnabled(not auto)
        #ic(_range)

    def _set_radial_range_2D(self):
        """Sets UI values from Sphere 2D radial range in bai_2d_args"""
        #ic()

        self._disconnect_radial_range_2D_signals()

        _range = self.sphere.bai_2d_args['radial_range']
        #ic(self.sphere.bai_2d_args, _range)
        if _range is None:
            self.ui.radial_autoRange_2D.setChecked(True)
            auto = True
        else:
            self.ui.radial_low_2D.setText(str(_range[0]))
            self.ui.radial_high_2D.setText(str(_range[0]))
            auto = False

        self.radial_autoRange_2D = auto
        self.ui.radial_low_2D.setEnabled(not auto)
        self.ui.radial_high_2D.setEnabled(not auto)

        self._connect_radial_range_2D_signals()

    def _get_azim_range_2D(self):
        """Sets Sphere 2D azimuth range in bai_1d_args from UI values"""
        #ic()

        auto = self.ui.azim_autoRange_2D.isChecked()
        self.azim_autoRange_2D = auto

        _range = None
        if not auto:
            _range = self._get_valid_range(self.ui.azim_low_2D,
                                           self.ui.azim_high_2D)

        if self.ui.axis2D.currentIndex() == 1:
            self.sphere.bai_2d_args['y_range'] = _range
        else:
            self.sphere.bai_2d_args['azimuth_range'] = _range

        self.ui.azim_low_2D.setEnabled(not auto)
        self.ui.azim_high_2D.setEnabled(not auto)
        #ic(_range)

    def _set_azim_range_2D(self):
        """Sets UI values from Sphere 1D aazimuth range in bai_1d_args"""
        #ic()

        self._disconnect_azim_range_2D_signals()

        _range = self.sphere.bai_2d_args['azimuth_range']
        #ic(self.sphere.bai_2d_args, _range)
        if _range is None:
            self.ui.azim_autoRange_2D.setChecked(True)
            auto = True
        else:
            self.ui.azim_low_2D.setText(str(_range[0]))
            self.ui.azim_high_2D.setText(str(_range[0]))
            auto = False

        self.azim_autoRange_1D = auto
        self.ui.azim_low_2D.setEnabled(not auto)
        self.ui.azim_high_2D.setEnabled(not auto)

        self._connect_azim_range_2D_signals()

    @staticmethod
    def _get_valid_range(low, high):
        """Validate range to return float values"""

        low, high = low.text(), high.text()
        try:
            low = float(low)
        except ValueError:
            low = 0.
        try:
            high = float(high)
        except ValueError:
            high = 0.
        return [low, high]

    def _get_unit_1D(self):
        #ic()

        val = self.ui.unit_1D.currentText()
        #ic(val, Units_dict[val])
        self.sphere.bai_1d_args['unit'] = Units_dict[val]
        self._validate_ranges()

    def _set_unit_1D(self):
        #ic()

        self.ui.unit_1D.currentTextChanged.disconnect(self._get_unit_1D)
        val = self.sphere.bai_1d_args['unit']
        #ic(val, type(val), Units_dict_inv[val])
        self.ui.unit_1D.setCurrentIndex(Units_dict_inv[val])
        self.ui.unit_1D.currentTextChanged.connect(self._get_unit_1D)

    def _get_unit_2D(self):
        #ic()

        val = self.ui.unit_2D.currentText()
        #ic(val, Units_dict[val])
        self.sphere.bai_2d_args['unit'] = Units_dict[val]
        self._validate_ranges()

    def _set_unit_2D(self):
        #ic()

        self.ui.unit_2D.currentTextChanged.disconnect(self._get_unit_2D)
        val = self.sphere.bai_2d_args['unit']
        #ic(val, type(val), Units_dict_inv[val])
        self.ui.unit_2D.setCurrentIndex(Units_dict_inv[val])
        # self.ui.unit_2D.setCurrentText(Units_dict_inv[val])
        self.ui.unit_2D.currentTextChanged.connect(self._get_unit_2D)

    def _get_npts_1D(self):
        #ic()

        val = self.ui.npts_1D.text()
        val = 500 if (not val) else int(val)
        #ic(val)
        self.sphere.bai_1d_args['numpoints'] = val

    def _set_npts_1D(self):
        #ic()

        self.ui.npts_1D.textChanged.disconnect(self._get_npts_1D)
        val = str(self.sphere.bai_1d_args['numpoints'])
        #ic(val, type(val))
        self.ui.npts_1D.setText(val)
        self.ui.npts_1D.textChanged.connect(self._get_npts_1D)

    def _get_npts_radial_2D(self):
        #ic()

        val = self.ui.npts_radial_2D.text()
        val = 500 if (not val) else int(val)
        #ic(val)
        self.sphere.bai_2d_args['npt_rad'] = val

    def _set_npts_radial_2D(self):
        #ic()

        self.ui.npts_radial_2D.textChanged.disconnect(self._get_npts_radial_2D)
        val = str(self.sphere.bai_2d_args['npt_rad'])
        #ic(val, type(val))
        self.ui.npts_radial_2D.setText(val)
        self.ui.npts_radial_2D.textChanged.connect(self._get_npts_radial_2D)

    def _get_npts_azim_2D(self):
        #ic()

        val = self.ui.npts_azim_2D.text()
        val = 500 if (not val) else int(val)
        #ic(val)
        self.sphere.bai_2d_args['npt_azim'] = val

    def _set_npts_azim_2D(self):
        #ic()

        self.ui.npts_azim_2D.textChanged.disconnect(self._get_npts_azim_2D)
        val = str(self.sphere.bai_2d_args['npt_azim'])
        #ic(val, type(val))
        self.ui.npts_azim_2D.setText(val)
        self.ui.npts_azim_2D.textChanged.connect(self._get_npts_azim_2D)

    def _connect_inp_signals(self):
        """Connect signals for all input sphere bai parameters"""
        #ic()

        # Connect points and units signals
        self.ui.npts_1D.textChanged.connect(self._get_npts_1D)
        self.ui.unit_1D.currentTextChanged.connect(self._get_unit_1D)

        self.ui.npts_radial_2D.textChanged.connect(self._get_npts_radial_2D)
        self.ui.npts_azim_2D.textChanged.connect(self._get_npts_azim_2D)
        self.ui.unit_2D.currentTextChanged.connect(self._get_unit_2D)

        # Connect range signals
        self._connect_radial_range_1D_signals()
        self._connect_azim_range_1D_signals()
        self._connect_radial_range_2D_signals()
        self._connect_azim_range_2D_signals()

        # Connect advanced parameters signals
        self.advancedWidget1D.sigUpdateArgs.connect(self.get_args)
        self.advancedWidget2D.sigUpdateArgs.connect(self.get_args)

    def _disconnect_inp_signals(self):
        """Disconnect signals for all input sphere bai parameters"""
        #ic()

        # Disconnect points and units signals
        self.ui.npts_1D.textChanged.disconnect(self._get_npts_1D)
        self.ui.unit_1D.currentTextChanged.disconnect(self._get_unit_1D)
        self.ui.npts_radial_2D.textChanged.disconnect(self._get_npts_radial_2D)
        self.ui.npts_azim_2D.textChanged.disconnect(self._get_npts_azim_2D)
        self.ui.unit_2D.currentTextChanged.disconnect(self._get_unit_2D)

        # Disconnect range signals
        self._disconnect_radial_range_1D_signals()
        self._disconnect_azim_range_1D_signals()
        self._disconnect_radial_range_2D_signals()
        self._disconnect_azim_range_2D_signals()

        # Disconnect advanced parameters signals
        self.advancedWidget1D.sigUpdateArgs.disconnect(self.get_args)
        self.advancedWidget2D.sigUpdateArgs.disconnect(self.get_args)

    def _connect_radial_range_1D_signals(self):
        """Connect signals for radial 1D range"""
        self.ui.radial_low_1D.textChanged.connect(self._get_radial_range_1D)
        self.ui.radial_high_1D.textChanged.connect(self._get_radial_range_1D)
        self.ui.radial_autoRange_1D.stateChanged.connect(self._get_radial_range_1D)

    def _disconnect_radial_range_1D_signals(self):
        """Disconnect signals for radial 1D range"""
        self.ui.radial_low_1D.textChanged.disconnect(self._get_radial_range_1D)
        self.ui.radial_high_1D.textChanged.disconnect(self._get_radial_range_1D)
        self.ui.radial_autoRange_1D.stateChanged.disconnect(self._get_radial_range_1D)

    def _connect_azim_range_1D_signals(self):
        """Connect signals for azimuth 1D range"""
        self.ui.azim_low_1D.textChanged.connect(self._get_azim_range_1D)
        self.ui.azim_high_1D.textChanged.connect(self._get_azim_range_1D)
        self.ui.azim_autoRange_1D.stateChanged.connect(self._get_azim_range_1D)

    def _disconnect_azim_range_1D_signals(self):
        """Disconnect signals for azimuth 1D range"""
        self.ui.azim_low_1D.textChanged.disconnect(self._get_azim_range_1D)
        self.ui.azim_high_1D.textChanged.disconnect(self._get_azim_range_1D)
        self.ui.azim_autoRange_1D.stateChanged.disconnect(self._get_azim_range_1D)

    def _connect_radial_range_2D_signals(self):
        """Connect signals for radial 2D range"""
        self.ui.radial_low_2D.textChanged.connect(self._get_radial_range_2D)
        self.ui.radial_high_2D.textChanged.connect(self._get_radial_range_2D)
        self.ui.radial_autoRange_2D.stateChanged.connect(self._get_radial_range_2D)

    def _disconnect_radial_range_2D_signals(self):
        """Disconnect signals for radial 2D range"""
        self.ui.radial_low_2D.textChanged.disconnect(self._get_radial_range_2D)
        self.ui.radial_high_2D.textChanged.disconnect(self._get_radial_range_2D)
        self.ui.radial_autoRange_2D.stateChanged.disconnect(self._get_radial_range_2D)

    def _connect_azim_range_2D_signals(self):
        """Connect signals for azimuth 2D range"""
        self.ui.azim_low_2D.textChanged.connect(self._get_azim_range_2D)
        self.ui.azim_high_2D.textChanged.connect(self._get_azim_range_2D)
        self.ui.azim_autoRange_2D.stateChanged.connect(self._get_azim_range_2D)

    def _disconnect_azim_range_2D_signals(self):
        """Disconnect signals for azimuth 2D range"""
        self.ui.azim_low_2D.textChanged.disconnect(self._get_azim_range_2D)
        self.ui.azim_high_2D.textChanged.disconnect(self._get_azim_range_2D)
        self.ui.azim_autoRange_2D.stateChanged.disconnect(self._get_azim_range_2D)

    def bai_1d(self, q):
        """Uses the integrator_thread attribute to call bai_1d
        """
        with self.integrator_thread.lock:
            if len(self.sphere.arches.index) > 0:
                self.integrator_thread.method = 'bai_1d_all'
            # # if self.ui.all1D.isChecked() or type(self.arch.idx) != int:
            # if self.ui.all1D.isChecked() or ('Overall' in self.arch_ids):
            #     self.integrator_thread.method = 'bai_1d_all'
            # else:
            #     self.integrator_thread.method = 'bai_1d_SI'
        self.data_1d.clear()
        self.setEnabled(False)
        self.integrator_thread.start()

    def bai_2d(self, q):
        """Uses the integrator_thread attribute to call bai_2d
        """
        with self.integrator_thread.lock:
            if len(self.sphere.arches.index) > 0:
                self.integrator_thread.method = 'bai_2d_all'
            # if self.ui.all2D.isChecked() or type(self.arch.idx) != int:
            # if self.ui.all2D.isChecked() or ('Overall' in self.arch_ids):
            #     self.integrator_thread.method = 'bai_2d_all'
            # else:
            #     self.integrator_thread.method = 'bai_2d_SI'
        self.data_2d.clear()
        self.setEnabled(False)
        self.integrator_thread.start()

    @staticmethod
    def run_pyfai_calib():
        # pyFAI_calib2_main()
        # launch(f'{current_directory}/pyFAI-calib2-xdart')
        # if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        #     current_directory = sys._MEIPASS
        #     launch(f'{current_directory}/pyFAI-calib2')
        # else:
        #     pyFAI_calib2_main()
        process = subprocess.run(['pyFAI-calib2'], check=True, shell=True,
                                 stdout=subprocess.PIPE, universal_newlines=True)
        _ = process.stdout

    # @staticmethod
    def run_pyfai_drawmask(self):
        filters = f'Images (*.tif *tiff)'
        processFile, _ = QFileDialog().getOpenFileName(
            filter=filters,
            caption='Choose Image File',
            options=QFileDialog.DontUseNativeDialog
        )
        if not os.path.exists(processFile):
            print('No Image Chosen')
            return

        self.mask_window = MaskImageWidgetXdart()
        self.mask_window.setWindowModality(Qt.QtCore.Qt.WindowModal)
        self.mask_window.show()
        pyFAI_drawmask_main(self.mask_window, processFile)

        mask = self.mask_window.getSelectionMask()
        postProcessId21([processFile], mask)

    def set_image_units(self):
        """Disable/Enable Qz-Qxy option if we are/are not in GI mode"""
        if not self.sphere.gi:
            self.ui.axis2D.removeItem(1)
        else:
            if self.ui.axis2D.count() == 1:
                self.ui.axis2D.addItem(_translate("Form", 'Qz-Qxy'))

    def _update_axes(self, n):
        """Updates axes to allow user to set Qz-Qxy integration ranges in GI mode"""
        pass
        # if n == 1:
        #     if self.ui.unit_2D


class advancedParameters(Qt.QtWidgets.QWidget):
    """Pop up window for setting more advanced integration parameters.

    attributes:
        name: str, name of the window
        parameter: pyqtgraph Parameter, parameters displayed
        tree: pyqtgraph ParameterTree, tree to hold parameter
        layout: QVBoxLayout, holds tree

    methods:
        process_change: Handles sigTreeStateChanged signal from tree

    signals:
        sigUpdateArgs: str, sends own name for updating args.
    """
    sigUpdateArgs = Qt.QtCore.Signal(str)

    def __init__(self, parameter, name, parent=None):
        #ic()
        super().__init__(parent)
        self.name = name
        self.parameter = parameter
        self.tree = pg.parametertree.ParameterTree()
        self.tree.addParameters(parameter)
        self.parameter.sigTreeStateChanged.connect(self.process_change)
        self.layout = Qt.QtWidgets.QVBoxLayout(self)
        self.setLayout(self.layout)
        self.layout.addWidget(self.tree)

    def process_change(self, tree, changes):
        #ic()
        self.sigUpdateArgs.emit(self.name)
