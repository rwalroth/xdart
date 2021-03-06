# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports

# Qt imports
import pyqtgraph as pg
from pyqtgraph import Qt
from pyqtgraph.parametertree import Parameter

# This module imports
from .integratorUI import Ui_Form
from xdart.gui.gui_utils import rangeWidget

params = [
    {'name': 'Default', 'type': 'group', 'children': [
            {'name': 'Integrate 1D', 'type': 'group', 'children': [
                {'name': 'numpoints', 'type': 'int', 'value': 1000},
                {'name': 'unit', 'type': 'list', 'values': {
                    "2" + u"\u03B8": '2th_deg', "q (A-1)": 'q_A^-1'
                    }, 'value': '2th_deg'},
                {'name': 'radial_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': 0.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': False,
                         'visible': False},
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
                    ], 'value':'csr'},
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
                        {'name': 'Auto', 'type': 'bool', 'value': False, 
                        'visible': False},
                    ]
                },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': False, 
                        'visible': False},
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
                    ], 'value':'csr'},
                {'name': 'safe', 'type': 'bool', 'value': True}
                ]
            }
        ]

    },
    {'name': 'Multi. Geometry', 'type': 'group', 'children': [
            {'name': 'Multi Geometry Setup', 'type': 'group', 'children': [
                {'name': 'unit', 'type': 'list', 'values': {
                    "2" + u"\u03B8": '2th_deg', "q (A-1)": 'q_A^-1'
                    }, 'value': '2th_deg'},
                {'name': 'radial_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': 0.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': False, 
                         'visible': False, 'enabled': False},
                    ]
                },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': False, 
                         'visible': False, 'enabled': False},
                    ]
                },
                {'name': 'empty', 'type': 'float', 'value': -1.0},
                {'name': 'chi_disc', 'type': 'float', 'value': 180},
            ]
            },
            {'name': 'Integrate 1D', 'type': 'group', 'children': [
                {'name': 'npt', 'type': 'int', 'value': 1000},
                {'name': 'monitor', 'type': 'str', 'value': 'None'},
                {'name': 'correctSolidAngle', 'type': 'bool', 'value': True},
                {'name': 'Apply polarization factor', 'type': 'bool', 'value': False},
                {'name': 'polarization_factor', 'type': 'float', 'value': 0, 
                    'limits': (-1, 1)}
                ]
            },
            {'name': 'Integrate 2D', 'type': 'group', 'children': [
                {'name': 'npt_rad', 'type': 'int', 'value': 1000},
                {'name': 'npt_azim', 'type': 'int', 'value': 1000},
                {'name': 'monitor', 'type': 'str', 'value': 'None'},
                {'name': 'correctSolidAngle', 'type': 'bool', 'value': True},
                {'name': 'Apply polarization factor', 'type': 'bool', 'value': False},
                {'name': 'polarization_factor', 'type': 'float', 'value': 0, 
                    'limits': (-1, 1)}
                ]
            }
        ]

    }
]

class integratorTree(Qt.QtWidgets.QWidget):
    sigUpdateArgs = Qt.QtCore.Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.parameters = Parameter.create(
            name='integrator', type='group', children=params
        )
        self.bai_1d_pars = self.parameters.child('Default', 'Integrate 1D')
        self.bai_2d_pars = self.parameters.child('Default', 'Integrate 2D')
        self.mg_pars = self.parameters.child('Multi. Geometry', 
                                             'Multi Geometry Setup')
        self.mg_1d_pars = self.parameters.child('Multi. Geometry', 
                                                'Integrate 1D')
        self.mg_2d_pars = self.parameters.child('Multi. Geometry', 
                                                'Integrate 2D')
        self.radialRange1D = rangeWidget("Radial", 
                                       unit=["2" + u"\u03B8" + " (deg.)", 
                                             "q (A-1)"], 
                                       range_high=180, 
                                       points_high=1e9, 
                                       parent=self,
                                       range_low=0, 
                                       defaults=[0,180,1000])
        self.azimuthalRange2D = rangeWidget("Azimuthal", 
                                          unit="(deg.)", 
                                          range_high=180, 
                                          points_high=1e9, 
                                          parent=self,
                                          range_low=-180, 
                                          defaults=[-180,180,1000])
        self.radialRange2D = rangeWidget("Radial", 
                                       unit=["2" + u"\u03B8" + " (deg.)", 
                                             "q (A-1)"], 
                                       range_high=180, 
                                       points_high=1e9, 
                                       parent=self,
                                       range_low=0, 
                                       defaults=[0,180,1000])
        self.ui.layout1D.insertWidget(1, self.radialRange1D)
        self.ui.layout2D.insertWidget(1, self.azimuthalRange2D)
        self.ui.layout2D.insertWidget(1, self.radialRange2D)
        
        self.radialRange1D.sigRangeChanged.connect(self._set_radial_range1D)
        self.radialRange1D.sigUnitChanged.connect(self._set_radial_unit1D)
        self.radialRange1D.sigPointsChanged.connect(self._set_radial_points1D)
        
        self.radialRange2D.sigRangeChanged.connect(self._set_radial_range2D)
        self.radialRange2D.sigUnitChanged.connect(self._set_radial_unit2D)
        self.radialRange2D.sigPointsChanged.connect(self._set_radial_points2D)
        
        self.azimuthalRange2D.sigRangeChanged.connect(self._set_azimuthal_range2D)
        self.azimuthalRange2D.sigPointsChanged.connect(self._set_azimuthal_points2D)
        
        self.advancedWidget1D = advancedParameters(self.bai_1d_pars, 'bai_1d')
        self.advancedWidget1D.sigUpdateArgs.connect(self.sigUpdateArgs.emit)
        self.advancedWidget2D = advancedParameters(self.bai_2d_pars, 'bai_2d')
        self.advancedWidget2D.sigUpdateArgs.connect(self.sigUpdateArgs.emit)
        
        self.ui.advanced1D.clicked.connect(self.advancedWidget1D.show)
        self.ui.advanced2D.clicked.connect(self.advancedWidget2D.show)
    
    def update(self, sphere):
        self._sync_ranges(sphere)
        self._update_params(sphere)
    
    def setEnabled(self, enable):
        self.advancedWidget1D.setEnabled(enable)
        self.advancedWidget2D.setEnabled(enable)
        self.radialRange1D.setEnabled(enable)
        self.radialRange2D.setEnabled(enable)
        self.azimuthalRange2D.setEnabled(enable)
        self.ui.integrate1D.setEnabled(enable)
        self.ui.integrate2D.setEnabled(enable)
        self.ui.advanced1D.setEnabled(enable)
        self.ui.advanced2D.setEnabled(enable)
        
    
    def _sync_ranges(self, sphere):
        with sphere.sphere_lock:
            self._sync_range(
                sphere.bai_1d_args, 'radial_range', 'numpoints', self.radialRange1D
            )
            self._sync_range(
                sphere.bai_2d_args, 'radial_range', 'npt_rad', self.radialRange2D
            )
            self._sync_range(
                sphere.bai_2d_args, 'azimuth_range', 'npt_azim', self.azimuthalRange2D
            )
    
    def _sync_range(self, args, rkey, pkey, rwidget):
        rwidget.blockSignals(True)
        try:
            self._sync_range_hilow(args, rkey, rwidget)
            self._sync_range_points(args, pkey, rwidget)
        finally:
            rwidget.blockSignals(False)
        
    def _sync_range_points(self, args, pkey, rwidget):
        if pkey in args:
            rwidget.ui.points.setValue(args[pkey])
        else:
            args[pkey] = rwidget.ui.points.value()

    def _sync_range_hilow(self, args, rkey, rwidget):
        if rkey in args:
            if args[rkey] is None:
                args[rkey] = [rwidget.ui.low.value(),
                             rwidget.ui.high.value()]
            else:
                rwidget.ui.low.setValue(args[rkey][0])
                rwidget.ui.high.setValue(args[rkey][1])
        else:
            args[rkey] = [rwidget.ui.low.value(), rwidget.ui.high.value()]
            
    
    def _update_params(self, sphere):
        with sphere.sphere_lock:
            self._args_to_params(sphere.bai_1d_args, self.bai_1d_pars)
            self._args_to_params(sphere.bai_2d_args, self.bai_2d_pars)
            self._args_to_params(sphere.mg_args, self.mg_pars)
        
    def get_args(self, sphere, key):
        with sphere.sphere_lock:
            if key == 'bai_1d':
                self._params_to_args(sphere.bai_1d_args, self.bai_1d_pars)
                self._sync_range(sphere.bai_1d_args, 'radial_range', 'numpoints',
                                self.radialRange1D)
            elif key == 'bai_2d':
                self._params_to_args(sphere.bai_2d_args, self.bai_2d_pars)
                self._sync_range(sphere.bai_2d_args, 'radial_range',
                                'npt_rad', self.radialRange2D)
                self._sync_range(sphere.bai_2d_args, 'azimuth_range',
                                'npt_azim', self.azimuthalRange2D)
            

    def _args_to_params(self, args, tree):
        with tree.treeChangeBlocker():
            for key, val in args.items():
                if 'range' in key:
                    _range = tree.child(key)
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
        for child in tree.children():
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
    
    def _set_radial_range1D(self, low, high):
        self.bai_1d_pars.child("radial_range", "Low").setValue(low)
        self.bai_1d_pars.child("radial_range", "High").setValue(high)
        self.sigUpdateArgs.emit('bai_1d')
        
    def _set_radial_unit1D(self, val):
        self.bai_1d_pars.child("unit").setIndex(val)
        self.sigUpdateArgs.emit('bai_1d')

    def _set_radial_points1D(self, val):
        self.bai_1d_pars.child("numpoints").setValue(val)
        self.sigUpdateArgs.emit("bai_1d")
    
    def _set_radial_range2D(self, low, high):
        self.bai_2d_pars.child("radial_range", "Low").setValue(low)
        self.bai_2d_pars.child("radial_range", "High").setValue(high)
        self.sigUpdateArgs.emit('bai_2d')
        
    def _set_radial_unit2D(self, val):
        self.bai_2d_pars.child("unit").setIndex(val)
        self.sigUpdateArgs.emit('bai_2d')

    def _set_radial_points2D(self, val):
        self.bai_2d_pars.child("npt_rad").setValue(val)
        self.sigUpdateArgs.emit("bai_2d")

    def _set_azimuthal_range2D(self, low, high):
        self.bai_2d_pars.child("azimuth_range", "Low").setValue(low)
        self.bai_2d_pars.child("azimuth_range", "High").setValue(high)
        self.sigUpdateArgs.emit('bai_2d')
    
    def _set_azimuthal_points2D(self, val):
        self.bai_2d_pars.child("npt_azim").setValue(val)
        self.sigUpdateArgs.emit("bai_2d")


class advancedParameters(Qt.QtWidgets.QWidget):
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
