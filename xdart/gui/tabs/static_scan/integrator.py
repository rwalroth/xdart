# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt, QtCore
from pyqtgraph.parametertree import Parameter

# This module imports
from .ui.integratorUI import Ui_Form
from .sphere_threads import integratorThread
from ...widgets import rangeWidget

AA_inv = u'\u212B\u207B\u00B9'
Th = u'\u03B8'
Deg = u'\u00B0'
Units = [f"2{Th} ({Deg})", f"Q ({AA_inv})"]

params = [
    {'name': 'Default', 'type': 'group', 'children': [
            {'name': 'Integrate 1D', 'type': 'group', 'children': [
                {'name': 'numpoints', 'type': 'int', 'value': 1000},
                {'name': 'unit', 'type': 'list', 'values': {
                    # "2" + u"\u03B8": '2th_deg', "q (A-1)": 'q_A^-1'
                    Units[0]: '2th_deg', Units[1]: 'q_A^-1'
                    }, 'value': '2th_deg'},
                {'name': 'radial_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': 0.0},
                        {'name': 'High', 'type': 'float', 'value': 60.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True,
                         'visible': True},
                    ]
                 },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True},
                    ]
                },
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
                    ], 'value':'cython'},
                {'name': 'safe', 'type': 'bool', 'value': True},
                {'name': 'block_size', 'type': 'int', 'value': 32},
                {'name': 'profile', 'type': 'bool', 'value': False},
                ]
             },
            {'name': 'Integrate 2D', 'type': 'group', 'children': [
                {'name': 'npt_rad', 'type': 'int', 'value': 1000},
                {'name': 'npt_azim', 'type': 'int', 'value': 1000},
                {'name': 'unit', 'type': 'list', 'values': {
                    "2" + u"\u03B8": '2th_deg', "q (A-1)": 'q_A^-1'
                    }, 'value': '2th_deg'},
                {'name': 'radial_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': 0.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True,
                        'visible': True},
                    ]
                 },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True,
                        'visible': True},
                    ]
                 },
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
                    ], 'value':'cython'},
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
    def __init__(self, sphere, arch, file_lock, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.sphere = sphere
        self.arch = arch
        self.file_lock = file_lock
        self.parameters = Parameter.create(
            name='integrator', type='group', children=params
        )
        self.bai_1d_pars = self.parameters.child('Default', 'Integrate 1D')
        self.bai_2d_pars = self.parameters.child('Default', 'Integrate 2D')

        self.radialRange1D = rangeWidget(
            "Radial",
            unit=["2" + u"\u03B8" + " (deg.)", "q (A-1)"],
            range_high=180,
            points_high=1e9,
            parent=self,
            range_low=0,
            defaults=[0, 180, 1000])
        self.radialRange1D.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.azimuthalRange2D = rangeWidget(
            "Azimuthal",
            unit="(deg.)",
            range_high=180,
            points_high=1e9,
            parent=self,
            range_low=-180,
            defaults=[-180, 180, 1000])
        self.azimuthalRange2D.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.radialRange2D = rangeWidget(
            "Radial",
            unit=["2" + u"\u03B8" + " (deg.)", "q (A-1)"],
            range_high=180,
            points_high=1e9,
            parent=self,
            range_low=0,
            defaults=[0, 180, 1000])
        self.radialRange2D.setFocusPolicy(QtCore.Qt.ClickFocus)

        # self.ui.layout1D.insertWidget(1, self.radialRange1D)
        # self.ui.layout2D.insertWidget(1, self.azimuthalRange2D)
        # self.ui.layout2D.insertWidget(1, self.radialRange2D)

        # UI adjustments
        _translate = Qt.QtCore.QCoreApplication.translate
        self.ui.unit_1D.setItemText(0, _translate("Form", Units[0]))
        self.ui.unit_1D.setItemText(1, _translate("Form", Units[1]))
        self.ui.label_azim_1D.setText(f"Chi ({Deg})")

        self.ui.unit_2D.setItemText(0, _translate("Form", Units[0]))
        self.ui.unit_2D.setItemText(1, _translate("Form", Units[1]))
        self.ui.label_azim_2D.setText(f"Chi ({Deg})")

        self._validate_ranges()

        # Set AutoRange Flags
        # self.int1d_radial_autoRange = self.ui.int1D_autoRange.isChecked()
        self.radial_autoRange_1D = self.ui.radial_autoRange_1D.isChecked()
        self.azim_autoRange_1D = self.ui.azim_autoRange_1D.isChecked()
        self.radial_autoRange_2D = self.ui.radial_autoRange_2D.isChecked()
        self.azim_autoRange_2D = self.ui.azim_autoRange_2D.isChecked()
        # self.int2d_radial_autoRange = self.ui.int2D_rad_autoRange.isChecked()
        # self.int2d_azim_autoRange = self.ui.int2D_azim_autoRange.isChecked()

        # self.update_radial_autoRange_1D()
        # self.update_azim_autoRange_1D()
        # self.update_radial_autoRange_2D()
        # self.update_azim_autoRange_2D()

        # self.radialRange1D.sigUnitChanged.connect(self._set_radial_unit1D)
        # self.radialRange1D.sigPointsChanged.connect(self._set_radial_points1D)
        self.ui.npts.textChanged.connect(self._set_npts_1D)
        self.ui.unit_1D.currentIndexChanged.connect(self._set_radial_unit1D)

        # self.radialRange1D.sigRangeChanged.connect(self._set_radial_range1D)
        self.ui.radial_low_1D.textChanged.connect(self._set_radial_range1D_low)
        self.ui.radial_high_1D.textChanged.connect(self._set_radial_range1D_high)
        self.ui.radial_autoRange_1D.stateChanged.connect(self._set_radial_range1D_auto)

        self.ui.azim_low_1D.textChanged.connect(self._set_azim_range1D_low)
        self.ui.azim_high_1D.textChanged.connect(self._set_azim_range1D_high)
        self.ui.azim_autoRange_1D.stateChanged.connect(self._set_azim_range1D_auto)

        self.ui.npts_radial_2D.textChanged.connect(self._set_npts_radial_2D)
        self.ui.npts_azim_2D.textChanged.connect(self._set_npts_azim_2D)
        self.ui.unit_2D.currentIndexChanged.connect(self._set_radial_unit2D)

        self.ui.radial_low_2D.textChanged.connect(self._set_radial_range2D_low)
        self.ui.radial_high_2D.textChanged.connect(self._set_radial_range2D_high)
        self.ui.radial_autoRange_2D.stateChanged.connect(self._set_radial_range2D_auto)

        self.ui.azim_low_2D.textChanged.connect(self._set_azim_range2D_low)
        self.ui.azim_high_2D.textChanged.connect(self._set_azim_range2D_high)
        self.ui.azim_autoRange_2D.stateChanged.connect(self._set_azim_range2D_auto)

        # self.radialRange2D.sigRangeChanged.connect(self._set_radial_range2D)
        # self.radialRange2D.sigUnitChanged.connect(self._set_radial_unit2D)
        # self.radialRange2D.sigPointsChanged.connect(self._set_radial_points2D)

        # self.azimuthalRange2D.sigRangeChanged.connect(self._set_azimuthal_range2D)
        # self.azimuthalRange2D.sigPointsChanged.connect(self._set_azimuthal_points2D)

        self.advancedWidget1D = advancedParameters(self.bai_1d_pars, 'bai_1d')
        self.advancedWidget1D.sigUpdateArgs.connect(self.get_args)
        self.advancedWidget2D = advancedParameters(self.bai_2d_pars, 'bai_2d')
        self.advancedWidget2D.sigUpdateArgs.connect(self.get_args)

        # self.ui.int1D_autoRange.stateChanged.connect(self.update_radial_autoRange_1D)
        # self.ui.radial_autoRange_2D.stateChanged.connect(self.update_radial_autoRange_2D)
        # self.ui.azim_autoRange_2D.stateChanged.connect(self.update_azim_autoRange_2D)

        self.ui.advanced1D.clicked.connect(self.advancedWidget1D.show)
        self.ui.advanced2D.clicked.connect(self.advancedWidget2D.show)

        self.ui.integrate1D.clicked.connect(self.bai_1d)
        self.ui.integrate2D.clicked.connect(self.bai_2d)

        self.integrator_thread = integratorThread(self.sphere, self.arch,
                                                  self.file_lock)

        self.setEnabled()

    def update(self):
        """Grabs args from sphere and uses _sync_ranges and
        _update_params private methods to update.

        args:
            sphere: EwaldSphere, object to get args from.
        """
        print(f'integrator > update')
        # self._sync_ranges()
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

    def setEnabled_(self, enable=True):
        """Overrides parent class method. Ensures appropriate child
        widgets are enabled.

        args:
            enable: bool, If True widgets are enabled. If False
                they are disabled.
        """
        self.advancedWidget1D.setEnabled(enable)
        self.advancedWidget2D.setEnabled(enable)

        self.ui.frame1D_Range.setEnabled(enable)
        self.ui.npts.setEnabled(enable)

        if self.radial_autoRange_1D:
            self.ui.radial_low_1D.setEnabled(False)
            self.ui.radial_high_1D.setEnabled(False)

        if self.azim_autoRange_1D:
            self.ui.azim_low_1D.setEnabled(False)
            self.ui.azim_high_1D.setEnabled(False)

        self.ui.frame2D_Range.setEnabled(enable)
        self.ui.npts_radial_2D.setEnabled(enable)
        self.ui.npts_azim_2D.setEnabled(enable)

        # self.radialRange2D.setEnabled(enable)
        # if self.int2d_radial_autoRange:
        if self.radial_autoRange_2D:
            self.radialRange2D.setEnabled(False)
        self.radialRange2D.ui.points.setEnabled(enable)

        self.azimuthalRange2D.setEnabled(enable)
        if self.int2d_azim_autoRange:
            self.azimuthalRange2D.setEnabled(False)
        self.azimuthalRange2D.ui.points.setEnabled(enable)

        self.ui.integrate1D.setEnabled(enable)
        self.ui.integrate2D.setEnabled(enable)
        self.ui.advanced1D.setEnabled(enable)
        self.ui.advanced2D.setEnabled(enable)

    def update_radial_autoRange_1D(self):
        """Disable/Enable radial 1D widget if auto range is un/selected
        """
        # self.int1d_radial_autoRange = self.ui.int1D_autoRange.isChecked()
        self.radial_autoRange_1D = self.ui.radial_autoRange_1D.isChecked()
        self.setEnabled()
        # self.radialRange1D.ui.points.setEnabled(True)
        # self.radialRange1D.setEnabled(not self.int1d_radial_autoRange)

        int1d_radial_range = self.bai_1d_pars.child('radial_range')
        print(f'integrator > update_radial_autoRange_1D: sphere_bai_1d = {self.sphere.bai_1d_args}')
        if self.radial_autoRange_1D:
            int1d_radial_range.child("Auto").setValue(True)
            self.sphere.bai_1d_args['radial_range'] = None
            print(f"integrator > update_radial_autoRange_1D: radial_range {self.sphere.bai_1d_args['radial_range']}")
        else:
            int1d_radial_range.child("Auto").setValue(False)
            print(f"integrator > update_radial_autoRange_1D: radial_range {self.sphere.bai_1d_args['radial_range']}")
        print(f'integrator > update_radial_autoRange_1D: sphere_bai_1d = {self.sphere.bai_1d_args}')

    def update_azim_autoRange_1D(self):
        """Disable/Enable azim 1D widget if auto range is un/selected
        """
        self.azim_autoRange_1D = self.ui.azim_autoRange_1D.isChecked()
        self.setEnabled()

        self.bai_1d_pars.child('azimuth_range', 'Auto').setValue(
            self.azim_autoRange_1D)

        if self.radial_autoRange_1D:
            # azim_range_1D.child("Auto").setValue(True)
            self.sphere.bai_1d_args['radial_range'] = None

        print(f"integrator > update_azim_autoRange_1D: radial_range {self.sphere.bai_1d_args['radial_range']}")

    def update_radial_autoRange_2D(self):
        """Disable/Enable radial 2D widget if auto range is un/selected
        """
        self.radial_autoRange_2D = self.ui.radial_autoRange_2D.isChecked()
        self.setEnabled()

        # radial_range_2D = self.bai_2d_pars.child('radial_range')
        self.bai_2d_pars.child('radial_range', 'Auto').setValue(
            self.radial_autoRange_2D)

        if self.radial_autoRange_2D:
            # radial_range_2D.child("Auto").setValue(True)
            self.sphere.bai_2d_args['radial_range'] = None

        print(f"integrator > update_radial_autoRange_2D: radial_range {self.sphere.bai_2d_args['radial_range']}")

    def update_azim_autoRange_2D(self):
        """Disable/Enable radial 2D widget if auto range is un/selected
        """
        self.azim_autoRange_2D = self.ui.azim_autoRange_2D.isChecked()
        self.setEnabled()

        # azim_autoRange_2D = self.bai_2d_pars.child('azim_range')
        self.bai_2d_pars.child('azimuth_range', 'Auto').setValue(
            self.azim_autoRange_2D)

        if self.azim_autoRange_2D:
            # radial_range_2D.child("Auto").setValue(True)
            self.sphere.bai_2d_args['azimuth_range'] = None

        print(f"integrator > update_azim_autoRange_2D: azimuth_range = {self.sphere.bai_2d_args['azimuth_range']}")

    def _validate_ranges(self):
        self.ui.npts.setValidator(Qt.QtGui.QIntValidator(0, 50000))
        self.ui.npts_radial_2D.setValidator(Qt.QtGui.QIntValidator(0, 50000))
        self.ui.npts_azim_2D.setValidator(Qt.QtGui.QIntValidator(0, 50000))

        minmax = (0, 50)
        if self.ui.unit_1D.currentIndex() == 0:
            minmax = (-180, 180)
        self.ui.radial_low_1D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))
        self.ui.radial_high_1D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))
        self.ui.radial_low_2D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))
        self.ui.radial_high_2D.setValidator(Qt.QtGui.QDoubleValidator(minmax[0], minmax[1], 2))

        self.ui.azim_low_1D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))
        self.ui.azim_high_1D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))
        self.ui.azim_low_2D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))
        self.ui.azim_high_2D.setValidator(Qt.QtGui.QDoubleValidator(-180, 180, 2))

    def _sync_ranges(self):
        """Syncs the range widgets. If sphere has set range arguments,
        applies those to rangeWidgets. Otherwise, adds current values to
        sphere.

        args:
            sphere: EwaldSphere, object to get args from.
        """
        print(f'integrator > _sync_ranges')
        with self.sphere.sphere_lock:
            if not self.radial_autoRange_1D:
                self._sync_range(
                    self.sphere.bai_1d_args, 'radial_range', 'numpoints',
                    self.radialRange1D
                )

            # if not self.int2d_radial_autoRange:
            if not self.radial_autoRange_2D:
                self._sync_range(
                    self.sphere.bai_2d_args, 'radial_range', 'npt_rad',
                    self.radialRange2D
                )
            # if not self.int2d_azim_autoRange:
            if not self.azim_autoRange_2D:
                self._sync_range(
                    self.sphere.bai_2d_args, 'azimuth_range', 'npt_azim',
                    self.azimuthalRange2D
                )

    def _sync_range(self, args, rkey, pkey, rwidget):
        """Generic function for syncing a rangeWidget. Blocks signals
        so that internal functions don't activate while ranges are being
        updated.

        args:
            args: dict, arguments to check for values
            rkey: str, key for range hi and low values
            pkey: str, key for points
            rwidget: rangeWidget, widget to sync based on args
        """
        print(f'integrator > _sync_range')
        rwidget.blockSignals(True)
        try:
            self._sync_range_hilow(args, rkey, rwidget)
            self._sync_range_points(args, pkey, rwidget)
        finally:
            rwidget.blockSignals(False)

    def _sync_range_points(self, args, pkey, rwidget):
        """Syncs number of points between rwidget and args.

        args:
            args: dict, arguments to sync
            pkey: str, key for points value in args
            rwidget: rangeWidget, widget to sync
        """
        if pkey in args:
            rwidget.ui.points.setValue(args[pkey])
        else:
            args[pkey] = rwidget.ui.points.value()

    def _sync_range_hilow(self, args, rkey, rwidget):
        """Syncs range hi and low between rwidget and args.

        args:
            args: dict, arguments to sync
            rkey: str, key for hi and low list value in args
            rwidget: rangeWidget, widget to sync
        """
        if rkey in args:
            if args[rkey] is None:
                args[rkey] = [rwidget.ui.low.value(),
                             rwidget.ui.high.value()]
            else:
                rwidget.ui.low.setValue(args[rkey][0])
                rwidget.ui.high.setValue(args[rkey][1])
        else:
            args[rkey] = [rwidget.ui.low.value(), rwidget.ui.high.value()]

    def _update_params(self):
        """Grabs args from sphere and syncs parameters with them.

        args:
            sphere: EwaldSphere, object to get args from.
        """
        print(f'integrator > _update_params')
        with self.sphere.sphere_lock:
            self._args_to_params(self.sphere.bai_1d_args, self.bai_1d_pars)
            self._args_to_params(self.sphere.bai_2d_args, self.bai_2d_pars)

    def get_args(self, key):
        """Updates sphere with all parameters held in integrator.

        args:
            sphere: EwaldSphere, object to update
            key: str, which args to update.
        """
        print(f'integrator > get_args')
        with self.sphere.sphere_lock:
            if key == 'bai_1d':
                self._params_to_args(self.sphere.bai_1d_args, self.bai_1d_pars)
                self.update_radial_autoRange_1D()
                # if not self.radial_autoRange_1D:
                #     self._sync_range(self.sphere.bai_1d_args, 'radial_range',
                #                      'numpoints', self.radialRange1D)
                # else:
                #     self.update_radial_autoRange_1D()

            elif key == 'bai_2d':
                self._params_to_args(self.sphere.bai_2d_args, self.bai_2d_pars)
                self.update_radial_autoRange_2D()
                self.update_azim_autoRange_2D()

                # if not self.int2d_radial_autoRange:
                # if not self.radial_autoRange_2D:
                #     self._sync_range(self.sphere.bai_2d_args, 'radial_range',
                #                      'npt_rad', self.radialRange2D)
                # else:
                #     self.update_radial_autoRange_2D()

                # if not self.azim_autoRange_2D:
                #     self._sync_range(self.sphere.bai_2d_args, 'azimuth_range',
                #                      'npt_azim', self.azimuthalRange2D)
                # else:
                #     self.update_azim_autoRange_2D()

    def _args_to_params(self, args, tree):
        """Takes in args dictionary and sets all parameters in tree
        to match the args.

        args:
            args: dict, values to use for updating tree
            tree: pyqtgraph Parameter, parameters to update
        """
        print(f'integrator > _args_to_param')
        with tree.treeChangeBlocker():
            for key, val in args.items():
                if 'range' in key:
                    _range = tree.child(key)
                    print(f'integrator> _args_to_params: args = {args}')
                    print(f'integrator> _args_to_params: key, val, _range = {key}, {val}, {_range}')
                    if val is None:
                        _range.child("Auto").setValue(True)
                    else:
                        _range.child("Low").setValue(val[0])
                        _range.child("High").setValue(val[1])
                        _range.child("Auto").setValue(False)
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
        print(f'integrator > _params_to_args')
        for child in tree.children():
            if 'range' in child.name():
                print(f'****integrator > _params_to_args: args = {args}')
                print(f'integrator > _params_to_args: child, child.name = {child}, {child.name()}')
                print(f'integrator > _params_to_args: child.child.Auto = {child.child("Auto").value()}')
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

    # def _set_radial_range1D(self, low, high):
    #     self.bai_1d_pars.child("radial_range", "Low").setValue(low)
    #     self.bai_1d_pars.child("radial_range", "High").setValue(high)
    #     self.bai_1d_pars.child("radial_range", "Auto").setValue()
    #     self.get_args('bai_1d')

    def _set_radial_range1D_low(self, low):
        self.bai_1d_pars.child("radial_range", "Low").setValue(low)
        self.get_args('bai_1d')

    def _set_radial_range1D_high(self, high):
        self.bai_1d_pars.child("radial_range", "High").setValue(high)
        self.get_args('bai_1d')

    def _set_radial_range1D_auto(self, auto):
        auto = bool(auto)
        self.radial_autoRange_1D = auto
        self.bai_1d_pars.child("radial_range", "Auto").setValue(auto)

        if not auto:
            low = self.ui.radial_low_1D.text()
            high = self.ui.radial_high_1D.text()
            self.bai_1d_pars.child("radial_range", "Low").setValue(low)
            self.bai_1d_pars.child("radial_range", "High").setValue(high)

        self.ui.radial_low_1D.setEnabled(not auto)
        self.ui.radial_high_1D.setEnabled(not auto)
        self.get_args('bai_1d')

    def _set_azim_range1D_low(self, low):
        self.bai_1d_pars.child("azimuth_range", "Low").setValue(low)
        self.get_args('bai_1d')

    def _set_azim_range1D_high(self, high):
        self.bai_1d_pars.child("azimuth_range", "High").setValue(high)
        self.get_args('bai_1d')

    def _set_azim_range1D_auto(self, auto):
        auto = bool(auto)
        self.bai_1d_pars.child("radial_range", "Auto").setValue(auto)

        if not auto:
            low = self.ui.azim_low_1D.text()
            high = self.ui.azim_high_1D.text()
            self.bai_1d_pars.child("azimuth_range", "Low").setValue(low)
            self.bai_1d_pars.child("azimuth_range", "High").setValue(high)

        self.ui.azim_low_1D.setEnabled(not auto)
        self.ui.azim_high_1D.setEnabled(not auto)
        self.get_args('bai_1d')

    def _set_radial_unit1D(self, val):
        self.bai_1d_pars.child("unit").setIndex(val)
        self.get_args('bai_1d')

    # def _set_radial_points1D(self, val):
    #     self.bai_1d_pars.child("numpoints").setValue(val)
    #     self.get_args("bai_1d")

    def _set_npts_1D(self, val):
        self.bai_1d_pars.child("numpoints").setValue(val)
        self.get_args("bai_1d")

    # def _set_npts_2D(self, val):
    #     self.bai_2d_pars.child("npt_rad").setValue(val)
    #     self.get_args("bai_2d")

    def _set_npts_radial_2D(self, val):
        self.bai_2d_pars.child("npt_rad").setValue(val)
        self.get_args("bai_2d")

    def _set_npts_azim_2D(self, val):
        self.bai_2d_pars.child("npt_azim").setValue(val)
        self.get_args("bai_2d")

    def _set_radial_unit2D(self, val):
        self.bai_2d_pars.child("unit").setIndex(val)
        self.get_args('bai_2d')

    # def _set_radial_range2D(self, low, high):
    #     self.bai_2d_pars.child("radial_range", "Low").setValue(low)
    #     self.bai_2d_pars.child("radial_range", "High").setValue(high)
    #     self.get_args('bai_2d')

    def _set_radial_range2D_low(self, low):
        self.bai_2d_pars.child("radial_range", "Low").setValue(low)
        self.get_args('bai_2d')

    def _set_radial_range2D_high(self, high):
        self.bai_2d_pars.child("radial_range", "High").setValue(high)
        self.get_args('bai_2d')

    def _set_radial_range2D_auto(self, auto):
        auto = bool(auto)
        self.radial_autoRange_2D = auto
        self.bai_2d_pars.child("radial_range", "Auto").setValue(auto)

        if not auto:
            low = self.ui.radial_low_2D.text()
            high = self.ui.radial_high_2D.text()
            self.bai_2d_pars.child("radial_range", "Low").setValue(low)
            self.bai_2d_pars.child("radial_range", "High").setValue(high)

        self.ui.radial_low_2D.setEnabled(not auto)
        self.ui.radial_high_2D.setEnabled(not auto)
        self.get_args('bai_2d')

    # def _set_azimuthal_range2D(self, low, high):
    #     self.bai_2d_pars.child("azimuth_range", "Low").setValue(low)
    #     self.bai_2d_pars.child("azimuth_range", "High").setValue(high)
    #     self.get_args('bai_2d')

    def _set_azim_range2D_low(self, low):
        self.bai_2d_pars.child("azimuth_range", "Low").setValue(low)
        self.get_args('bai_2d')

    def _set_azim_range2D_high(self, high):
        self.bai_2d_pars.child("azimuth_range", "High").setValue(high)
        self.get_args('bai_2d')

    def _set_azim_range2D_auto(self, auto):
        auto = bool(auto)
        self.bai_2d_pars.child("radial_range", "Auto").setValue(auto)

        if not auto:
            low = self.ui.azim_low_2D.text()
            high = self.ui.azim_high_2D.text()
            self.bai_2d_pars.child("azimuth_range", "Low").setValue(low)
            self.bai_2d_pars.child("azimuth_range", "High").setValue(high)

        self.ui.azim_low_2D.setEnabled(not auto)
        self.ui.azim_high_2D.setEnabled(not auto)
        self.get_args('bai_2d')

    # def _set_azimuthal_points2D(self, val):
    #     self.bai_2d_pars.child("npt_azim").setValue(val)
    #     self.get_args("bai_2d")

    def bai_1d(self, q):
        """Uses the integrator_thread attribute to call bai_1d
        """
        with self.integrator_thread.lock:
            if self.ui.all1D.isChecked() or type(self.arch.idx) != int:
                self.integrator_thread.method = 'bai_1d_all'
            else:
                self.integrator_thread.method = 'bai_1d_SI'
        self.setEnabled(False)
        self.integrator_thread.start()

    def bai_2d(self, q):
        """Uses the integrator_thread attribute to call bai_2d
        """
        with self.integrator_thread.lock:
            if self.ui.all2D.isChecked() or type(self.arch.idx) != int:
                self.integrator_thread.method = 'bai_2d_all'
            else:
                self.integrator_thread.method = 'bai_2d_SI'
        self.setEnabled(False)
        self.integrator_thread.start()


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
        self.sigUpdateArgs.emit(self.name)
