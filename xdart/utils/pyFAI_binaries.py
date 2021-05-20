import os

import pyFAI.resources
import pyFAI.calibrant
import pyFAI.detectors
import pyFAI.io.image
import fabio

from pyFAI.gui.CalibrationWindow import CalibrationWindow
from pyFAI.app.calib2 import parse_options, setup_model
from pyFAI.app.drawmask import MaskImageWidget
from pyFAI.gui.CalibrationContext import CalibrationContext

from pyqtgraph import Qt
import silx
from silx.gui import qt

import logging
logging.basicConfig(level=logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)
try:
    import hdf5plugin  # noqa
except ImportError:
    logger.debug("Unable to load hdf5plugin, backtrace:", exc_info=True)

QFileDialog = Qt.QtWidgets.QFileDialog
logger_uncaught = logging.getLogger("pyFAI-calib2.UNCAUGHT")


def pyFAI_calib2_main():
    # It have to be done before loading Qt
    # --help must also work without Qt
    options = parse_options()

    if options.debug:
        logging.root.setLevel(logging.DEBUG)

    # Then we can load Qt
    if options.opengl:
        silx.config.DEFAULT_PLOT_BACKEND = "opengl"

    pyFAI.resources.silx_integration()
    settings = qt.QSettings(qt.QSettings.IniFormat,
                            qt.QSettings.UserScope,
                            "pyfai",
                            "pyfai-calib2",
                            None)

    context = CalibrationContext(settings)
    context.restoreSettings()

    setup_model(context.getCalibrationModel(), options)
    window = CalibrationWindowXdart(context)
    window.setVisible(True)
    window.setAttribute(qt.Qt.WA_DeleteOnClose, True)

    context.saveSettings()


def pyFAI_drawmask_main(window, processFile):
    usage = "pyFAI-drawmask file1.edf file2.edf ..."
    version = "pyFAI-average version %s from %s" % (pyFAI.version, pyFAI.date)
    description = """
    Draw a mask, i.e. an image containing the list of pixels which are considered invalid
    (no scintillator, module gap, beam stop shadow, ...).
    This will open a window and let you draw on the first image
    (provided) with different tools (brush, rectangle selection...)
    When you are finished, click on the "Save and quit" button.
    """
    epilog = """The mask image is saved into file1-masked.edf.
    Optionally the script will print the number of pixel masked
    and the intensity masked (as well on other files provided in input)"""

    image = fabio.open(processFile).data
    window.setImageData(image)
    outfile = os.path.splitext(processFile)[0] + "-mask.edf"
    window.setOutputFile(outfile)
    window.outFile = outfile

    print("Your mask-file will be saved into %s" % outfile)


class CalibrationWindowXdart(CalibrationWindow):

    def __init__(self, context):
        super(CalibrationWindowXdart, self).__init__(context=context)
        self.context = context

    def closeEvent(self, event):
        poniFile = self.model().experimentSettingsModel().poniFile()

        if not poniFile.isSynchronized():
            button = qt.QMessageBox.question(
                self,
                "calib2",
                "The PONI file was not saved.\nDo you really want to close the application?",
                qt.QMessageBox.Cancel | qt.QMessageBox.No | qt.QMessageBox.Yes,
                qt.QMessageBox.Yes)
            if button != qt.QMessageBox.Yes:
                event.ignore()
                return

        event.accept()
        CalibrationContext._releaseSingleton()


class MaskImageWidgetXdart(MaskImageWidget):
    """
    Window application which allow to create a mask manually.
    It is based on Silx library widgets.
    """

    def __init__(self):
        super(MaskImageWidgetXdart, self).__init__()
        self.outFile = None

    def closeEvent(self, event):
        if os.path.exists(self.outFile):
            mask_file = os.path.basename(self.outFile)
            out_dialog = Qt.QtWidgets.QMessageBox()
            out_dialog.setText(f'{mask_file} saved in Image directory')
            out_dialog.exec_()
        event.accept()
        return
