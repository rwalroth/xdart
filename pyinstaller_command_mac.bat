pyi-makespec xdart_main.py --onefile -w -n xdart -i icons/Everaldo-Crystal-Clear-App-x.ico --collect-submodules "pyFAI" --collect-data "pyFAI" --collect-submodules "fabio" --collect-all "hdf5plugin" --collect-all "silx"
pyinstaller xdart.spec --clean
