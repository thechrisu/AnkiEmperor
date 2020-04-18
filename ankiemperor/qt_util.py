from aqt import mw
from aqt.qt import QMessageBox
from .util import getPluginName


def debug(debugText):
    QMessageBox.information(mw, getPluginName(), str(debugText))
