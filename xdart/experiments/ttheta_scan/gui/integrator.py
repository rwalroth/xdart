# -*- coding: utf-8 -*-
"""
@author: walroth
"""

# Standard library imports

# Other imports
from pyFAI import units

# Qt imports
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph import Qt
from pyqtgraph.parametertree import (
    Parameter, ParameterTree, ParameterItem, registerParameterType
)

# This module imports
from .integratorUI import *
from ....gui.gui_utils import rangeWidget

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
                        {'name': 'Auto', 'type': 'bool', 'value': False},
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
                        {'name': 'Auto', 'type': 'bool', 'value': False},
                    ]
                },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': False},
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
        self.azimuthalRange = rangeWidget("Azimuthal", 
                                          unit="(deg.)", 
                                          range_high=180, 
                                          points_high=1e9, 
                                          parent=self,
                                          range_low=-180, 
                                          defaults=[-180,180,1000])
        self.radialRange = rangeWidget("Radial", 
                                       unit=["2" + u"\u03B8" + " (deg.)", 
                                             "q (A-1)"], 
                                       range_high=180, 
                                       points_high=1e9, 
                                       parent=self,
                                       range_low=0, 
                                       defaults=[0,180,1000])
        self.ui.verticalLayout.insertWidget(0, self.azimuthalRange)
        self.ui.verticalLayout.insertWidget(0, self.radialRange)
        
        self.radialRange.sigRangeChanged.connect(self._set_radial_range)
        self.radialRange.sigUnitChanged.connect(self._set_radial_unit)
        self.radialRange.sigPointsChanged.connect(self._set_radial_points)
        
        self.azimuthalRange.sigRangeChanged.connect(self._set_azimuthal_range)
        self.azimuthalRange.sigPointsChanged.connect(self._set_azimuthal_points)
    
    def update(self, sphere):
        self._update_ranges(sphere)
        self._update_params(sphere)
    
    def _update_ranges(self, sphere):
        # block all signals here
        # update radial range, points
        # update azimuthal range, points
        # unblock all signals here
        pass
    
    def _update_params(self, sphere):
        self._args_to_params(sphere.bai_1d_args, self.bai_1d_pars)
        self._args_to_params(sphere.bai_2d_args, self.bai_2d_pars)
        self._args_to_params(sphere.mg_args, self.mg_pars)
        
    def get_args(self, sphere, key):
        if key == 'bai_1d':
            self._params_to_args(sphere.bai_1d_args, self.bai_1d_pars)
        elif key == 'bai_2d':
            self._params_to_args(sphere.bai_2d_args, self.bai_2d_pars)
            

    def _args_to_params(self, args, tree):
        for key, val in args.items():
            if 'range' in key:
                _range = tree.child(key)
                if val is None:
                    _range.child("Auto").setValue(True)
                else:
                    _range.child("Low").setValue(val[0])
                    _range.child("High").setValue(val[1])
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
                    child.setValue(val)
    
    def _params_to_args(self, args, tree):
        if change[2] == 'None':
            upval = None
        else:
            upval = change[2]
        if 'range' in change[0].parent().name():
            _range = change[0].parent()
            if _range.child('Auto').value():
                args[_range.name()] = None
            else:
                args[_range.name()] = [
                    _range.child('Low').value(),
                    _range.child('High').value(),
                ]
        elif change[0].name() == 'polarization_factor':
            if change[0].parent().child('Apply polarization factor').value():
                args['polarization_factor'] = upval

        elif change[0].name() == 'Apply polarization factor':
            if upval:
                args['polarization_factor'] = \
                    self.integratorTree.bai_1d_pars.child('polarization_factor').value()
            else:
                args['polarization_factor'] = None
        else:
            args.update(
                [(change[0].name(), upval)]
            )
        with tree.treeChangeBlocker():
            for key in args.keys():
                try:
                    child = tree.child(key)
                except:
                    # pg does not throw specific exception for child not being found
                    child = None
                if child is not None:
                    if 'range' in key:
                        if child.child('Auto').value():
                            args[key] = None
                        else:
                            args[key] = [child.child('Low').value(),
                                         child.child('High').value()]
                    else:
                        args[key] = child.value()
    
    def _set_radial_range(self, low, high):
        self.bai_1d_pars.child("radial_range", "Low").setValue(low)
        self.bai_1d_pars.child("radial_range", "High").setValue(high)
        self.bai_2d_pars.child("radial_range", "Low").setValue(low)
        self.bai_2d_pars.child("radial_range", "High").setValue(high)
        self.sigUpdateArgs.emit('bai_1d')
        self.sigUpdateArgs.emit('bai_2d')
        
    def _set_radial_unit(self, val):
        self.bai_1d_pars.child("unit").setIndex(val)
        self.bai_2d_pars.child("unit").setIndex(val)
        self.sigUpdateArgs.emit('bai_1d')
        self.sigUpdateArgs.emit('bai_2d')

    def _set_radial_points(self, val):
        self.bai_1d_pars.child("numpoints").setValue(val)
        self.bai_2d_pars.child("npt_rad").setValue(val)
        self.sigUpdateArgs.emit("bai_1d")
        self.sigUpdateArgs.emit("bai_2d")

    def _set_azimuthal_range(self, low, high):
        self.bai_2d_pars.child("azimuthal_range", "Low").setValue(low)
        self.bai_2d_pars.child("azimuthal_range", "High").setValue(high)
        self.sigUpdateArgs.emit('bai_2d')
    
    def _set_azimuthal_points(self, val):
        self.bai_2d_pars.child("npt_azim").setValue(val)
        self.sigUpdateArgs.emit("bai_2d")
    

