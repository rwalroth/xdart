from collections import OrderedDict
from pyFAI.detectors import Detector
import numpy as np

from ...containers import PONI
from ..Operation import Operation

inputs = OrderedDict(
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

outputs = {
    'Distance': 0,
    'Poni1': 0,
    'Poni2': 0,
    'Rot1': 0,
    'Rot2': 0,
    'Rot3': 0,
    'Wavelength': 0,
    'Detector': 'Detector',
    'Detector_config': {
        'pixel1': 100e-6,
        'pixel2': 100e-6,
        'max_shape': None
    }
}

class MakePONI(Operation):
    def __init__(self):
        super(MakePONI, self).__init__(inputs, outputs)
        self.base = None
    
    def run(self):
        if self.base is None:
            self._set_base()
        poni = PONI.from_ponifile(self.inputs['poni_file'])
        
        for key, val in self.inputs['rotations'].items():
            if val is not None:
                r = np.radians(-self.inputs['spec_dict'][val]) + getattr(self.base, key)
                setattr(poni, key, r)
        
        self.outputs.update(poni.to_dict())

        return self.outputs
    
    def _set_base(self):
        base = PONI.from_ponifile(self.inputs['poni_file'])
        for key, val in self.inputs['calib_rotations'].items():
            r = getattr(base, key) - val
            setattr(base, key, r)
        self.base = base

