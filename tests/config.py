# -*- coding: utf-8 -*-

import os

xdart_dir = 'C:/Users/walroth/Documents/repos/xdart/'

if __name__ == '__main__':
    xdart_dir_current = os.getcwd().split('xdart')[0] + 'xdart'
    print(f"Ensure xdart_dir '{xdart_dir}' matches '{xdart_dir_current}'")