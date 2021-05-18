from collections import namedtuple
import struct
from sys import getsizeof


def _get_type_size(fchar, sample):
    """
    Returns the length of a list of bytes to represent the character
    using struct.pack

    Parameters
    ----------
    fchar : str
        One letter code for the struct format
    sample : variable
        A valid representation of the type to be packed

    Returns
    -------
    int
        Number of bytes needed to pack the type
    """
    return len(list(struct.pack(fchar, sample)))


DataType = namedtuple("DataType", ["size", "equivalent", "unpack", "pack"])


char_t = DataType(_get_type_size('b', 0), int,
                  lambda x: struct.unpack('b', x)[0],
                  lambda x: struct.pack('b', x))
uchar_t = DataType(_get_type_size('B', 0), int,
                   lambda x: struct.unpack('B', x)[0],
                   lambda x: struct.pack('B', x))
bool_t = DataType(_get_type_size('?', True), bool,
                  lambda x: struct.unpack('?', x)[0],
                  lambda x: struct.pack('?', x))
short_t = DataType(_get_type_size('h', 0), int,
                   lambda x: struct.unpack('h', x)[0],
                   lambda x: struct.pack('h', x))
ushort_t = DataType(_get_type_size('H', 0), int,
                    lambda x: struct.unpack('H', x)[0],
                    lambda x: struct.pack('H', x))
int_t = DataType(_get_type_size('i', 0), int,
                 lambda x: struct.unpack('i', x)[0],
                 lambda x: struct.pack('i', x))
uint_t = DataType(_get_type_size('I', 0), int,
                  lambda x: struct.unpack('I', x)[0],
                  lambda x: struct.pack('I', x))
long_t = DataType(_get_type_size('l', 0), int,
                  lambda x: struct.unpack('l', x)[0],
                  lambda x: struct.pack('l', x))
ulong_t = DataType(_get_type_size('L', 0), int,
                   lambda x: struct.unpack('L', x)[0],
                   lambda x: struct.pack('L', x))
llong_t = DataType(_get_type_size('q', 0), int,
                   lambda x: struct.unpack('q', x)[0],
                   lambda x: struct.pack('q', x))
ullong_t = DataType(_get_type_size('Q', 0), int,
                    lambda x: struct.unpack('Q', x)[0],
                    lambda x: struct.pack('Q', x))
float_t = DataType(_get_type_size('f', 0), float,
                   lambda x: struct.unpack('f', x)[0],
                   lambda x: struct.pack('f', x))
double_t = DataType(_get_type_size('d', 0), float,
                    lambda x: struct.unpack('d', x)[0],
                    lambda x: struct.pack('d', x))


key_to_dtype = {
    "char_t": char_t,
    "uchar_t": uchar_t,
    "bool_t": bool_t,
    "short_t": short_t,
    "ushort_t": ushort_t,
    "int_t": int_t,
    "uint_t": uint_t,
    "long_t": long_t,
    "ulong_t": ulong_t,
    "llong_t": llong_t,
    "ullong_t": ullong_t,
    "float_t": float_t,
    "double_t": double_t,
}

dtype_to_key = {val: key for key, val in key_to_dtype.items()}
