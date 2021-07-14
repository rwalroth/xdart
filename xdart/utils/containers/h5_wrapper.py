import h5py
import numpy as np


class H5Wrapper:
    def __init__(self, grp: h5py.Group, lazy: bool):
        self._grp = grp
        self._lazy = lazy

    def __setattr__(self, key, value):
        if self._lazy:
            if isinstance(value, np.ndarray):
                if key in self._grp:
                    if not isinstance(self._grp[key], h5py.Dataset):
                        raise TypeError(f"{key} is already set as array like, cannot be set to {type(value)}")
                    try:
                        self._grp[key][()] = value[()]
                    except TypeError:
                        self._grp[key].resize(value.shape)
                        self._grp[key][()] = value[()]
            elif isinstance(value, H5Wrapper):
                object.__setattr__(self, key, value)
        else:
            object.__setattr__(self, key, value)

    def __getattribute__(self, name):
        if self._lazy:
            pass
        else:
            object.__getattribute__(self, name)
