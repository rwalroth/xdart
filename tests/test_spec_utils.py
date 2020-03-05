# -*- coding: utf-8 -*-

# Standard Library imports
import time
import os
import unittest
import traceback

# Other imports
import numpy as np 
import pandas as pd

# add xdart to path
import sys
if __name__ == "__main__":
    from config import xdart_dir
else:
    from .config import xdart_dir

if xdart_dir not in sys.path:
    sys.path.append(xdart_dir)

from xdart.classes.spec import get_spec_header, get_spec_scan

print(os.getcwd())
SPEC_PATH = os.path.join(xdart_dir, 'tests/test_data/spec_pd100k/Lab6_2')

header = get_spec_header(SPEC_PATH)
df, meta = get_spec_scan(SPEC_PATH, 1, header)

if __name__ == '__main__':
    print(header)
    print('-'*72)
    print(df)
    print('-'*72)
    print(meta)