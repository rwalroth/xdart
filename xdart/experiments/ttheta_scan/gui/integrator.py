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

params = [
    {'name': 'Single Image', 'type': 'group', 'children': [
            {'name': 'Integrate 1D', 'type': 'group', 'children': [
                {'name': 'numpoints', 'type': 'int', 'value': 1000},
                {'name': 'unit', 'type': 'list', 'values': {
                    "2" + u"\u03B8": units.TTH_DEG, "q (A-1)": units.Q_A
                    }, 'value': units.TTH_DEG},
                {'name': 'radial_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': 0.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True},
                    ]
                },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True},
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
                    "2" + u"\u03B8": units.TTH_DEG, "q (A-1)": units.Q_A
                    }, 'value': units.TTH_DEG},
                {'name': 'radial_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': 0.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True},
                    ]
                },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True},
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
                    "2" + u"\u03B8": units.TTH_DEG, "q (A-1)": units.Q_A
                    }, 'value': units.TTH_DEG},
                {'name': 'radial_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': 0.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True},
                    ]
                },
                {'name': 'azimuth_range', 'type': 'group', 'children': [
                        {'name': 'Low', 'type': 'float', 'value': -180.0},
                        {'name': 'High', 'type': 'float', 'value': 180.0},
                        {'name': 'Auto', 'type': 'bool', 'value': True},
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.layout = Qt.QtWidgets.QHBoxLayout(self.ui.parameterFrame)
        self.parameters = Parameter.create(
            name='params', type='group', children=params
        )
        self.bai_1d_pars = self.parameters.child('Single Image', 'Integrate 1D')
        self.bai_2d_pars = self.parameters.child('Single Image', 'Integrate 2D')
        self.tree = ParameterTree()
        self.tree.setParameters(self.parameters, showTop=False)
        self.layout.addWidget(self.tree)
    
    def update(self, sphere):
        with self.bai_1d_pars.treeChangeBlocker():
            for key, val in sphere.bai_1d_args.items():
                child = self.bai_1d_pars.child(key)
                if 'range' in key:
                    child.child('Low').setValue(val[0])
                    child.child('High').setValue(val[1])
                    child.child('Auto').setValue(False)
                else:
                    child.setValue(val)
        
        with self.bai_2d_pars.treeChangeBlocker():
            for key, val in sphere.bai_2d_args.items():
                child = self.bai_2d_pars.child(key)
                if 'range' in key:
                    child.child('Low').setValue(val[0])
                    child.child('High').setValue(val[1])
                    child.child('Auto').setValue(False)
                else:
                    child.setValue(val)
