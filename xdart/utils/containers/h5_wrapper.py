import h5py
import numpy as np
import pickle


NDARRAY = 0
ARBITRARY = 1
WRAPPER = 2


class H5Wrapper:
    def __init__(self, grp: h5py.Group = None, lazy: bool = False,
                 maxshape: tuple[int] = (None,), nbytes=500e6):
        self._grp = grp
        self._lazy = lazy
        self._maxshape = maxshape
        self._nbytes = nbytes

    def __setattr__(self, key, value):
        if self._lazy:
            if isinstance(value, np.ndarray):
                self._set_array(value, key)
                self._grp[key].attrs["encoded"] = NDARRAY
            elif isinstance(value, list):
                try:
                    self._set_array(np.asarray(value), key)
                    self._grp[key].attrs["encoded"] = NDARRAY
                except TypeError:
                    self._set_arbitrary(key, value)
            elif isinstance(value, H5Wrapper):
                if key in self._grp:
                    if not value._grp == self._grp[key]:
                        del self._grp[key]
                        self._grp[key] = value._grp
                else:
                    self._grp[key] = value._grp
                self._grp[key].attrs["encoded"] = WRAPPER
                object.__setattr__(self, key, value)
            elif type(value) in [int, float, str, bool]:
                if "__scalars" not in self._grp:
                    self._grp.create_group("__scalars")
                self._grp["__scalars"].attrs[key] = value
            else:
                # defaults to using pickle and bytearray but should be expanded
                self._set_arbitrary(key, value)
        else:
            object.__setattr__(self, key, value)

    def _set_arbitrary(self, key, value):
        try:
            p_value = pickle.dumps(value)
        except TypeError:
            raise TypeError(f"Values of type {type(value)} are not supported")
        self._set_array(np.asarray(bytearray(p_value)), key)
        self._grp[key].attrs["encoded"] = ARBITRARY

    def _set_array(self, value: np.ndarray, key):
        if key in self._grp:
            if not isinstance(self._grp[key], h5py.Dataset):
                del self._grp[key]
            try:
                self._grp[key][()] = value[()]
            except TypeError:
                self._grp[key].resize(value.shape)
                self._grp[key][()] = value[()]
        else:
            self._grp.create_dataset(key, data=value, chunks=True, maxshape=self._maxshape)

    def __getattribute__(self, key):
        if self._lazy:
            if key in self._grp:
                encoded = self._grp.attrs.get("encoded", None)
                if encoded == NDARRAY:
                    return self._grp[key]
                if encoded == ARBITRARY:
                    return pickle.loads(self._grp[key][()])
            if "__scalars" in self._grp and key in self._grp["__scalars"].attrs.keys():
                return self._grp["__scalars"].attrs[key]
        return object.__getattribute__(self, key)

    def save_to_hdf5(self, file):
        pass

    def load_from_hdf5(self, file):
        pass

    def set_datafile(self, file, copy_=True):
        if self._lazy:
            if type(file) == str:
                grp = h5py.File(file, 'a', rdcc_nbytes=self._nbytes)
                opened = True
            else:
                grp = file
                opened = False
            try:
                if copy_:
                    self._grp.copy(self._grp, grp, expand_refs=True, expand_soft=True,
                                   expand_external=True)
                self._grp = grp
            finally:
                if opened:
                    grp.close()

    def close(self):
        self._grp = None

