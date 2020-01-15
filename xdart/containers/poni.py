from pyFAI.detectors import Detector
from pyFAI import detector_factory
import yaml

class PONI(object):
    _poni_keys = {
        'Distance': 'dist',
        'Poni1': 'poni1',
        'Poni2': 'poni2',
        'Rot1': 'rot1',
        'Rot2': 'rot2',
        'Rot3': 'rot3',
        'Wavelength': 'wavelength'
    }
    def __init__(self, dist=0, poni1=0, poni2=0, rot1=0, rot2=0, rot3=0, 
                 wavelength=1e-10, detector=Detector(100e-6, 100e-6)):
        self.dist = dist
        self.poni1 = poni1 
        self.poni2 = poni2 
        self.rot1 = rot1 
        self.rot2 = rot2 
        self.rot3 = rot3 
        self.wavelength = wavelength
        self.detector = detector

    
    def to_dict(self):
        return {
            'Distance': self.dist,
            'Poni1': self.poni1,
            'Poni2': self.poni2,
            'Rot1': self.rot1,
            'Rot2': self.rot2,
            'Rot3': self.rot3,
            'Wavelength': self.wavelength,
            'Detector': self.detector.name,
            'Detector_config': {
                'pixel1': self.detector.pixel1,
                'pixel2': self.detector.pixel2,
                'max_shape': self.detector.max_shape
            }
        }

    @classmethod
    def from_dict(cls, input):
        out = cls()
        for key in input:
            setattr(out, key, input[key])
        return out
    
    @classmethod
    def from_yamdict(cls, input):
        out = cls()
        for key in input:
            if key == 'Detector':
                if 'Detector_config' in input:
                    if 'max_shape' in input['Detector_config']:
                        if not (input['Detector_config']['max_shape'] is None or 
                                type(input['Detector_config']['max_shape']) == str):
                            input['Detector_config']['max_shape'] = list(input['Detector_config']['max_shape'])
                    out.detector = detector_factory(
                        input['Detector'], config=input['Detector_config']
                    )
                elif 'PixelSize1' in input and 'PixelSize2' in input:
                    out.detector = detector_factory(
                        input['Detector'], 
                        config={
                            'pixel1': input['PixelSize1'],
                            'pixel2': input['PixelSize2'],
                        }
                    )
                else:
                    out.detector = detector_factory(input['Detector'])
            elif key == 'Wavelength':
                if type(input[key]) == str:
                    out.wavelength = eval(input[key])
                else:
                    out.wavelength = input[key]
            else:
                try:
                    setattr(out, cls._poni_keys[key], input[key])
                except KeyError:
                    pass
        return out
    
    @classmethod
    def from_yaml(cls, stream):
        input = yaml.safe_load(stream)
        return cls.from_yamdict(input)
    
    @classmethod
    def from_ponifile(cls, file):
        if type(file) == str:
            with open(file, 'r') as f:
                out = cls.from_yaml(f)
        else:
            out = cls.from_yaml(file)
        return out

        
            

