from typing import Optional

import ORSModel
import pyvista
from ORSServiceClass.ORSWidget.chooseObjectAndNewName.chooseObjectAndNewName import ChooseObjectAndNewName
from OrsLibraries.workingcontext import WorkingContext
from ORSServiceClass.windowclasses.orsabstractwindow import OrsAbstractWindow
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtWidgets import QDialog

import preprocessing
from .ui_mainformdsb import Ui_MainFormDsb


class MainFormDsb(OrsAbstractWindow):
    def __init__(self, implementation, parent=None):
        super().__init__(implementation, parent)
        self.ui = Ui_MainFormDsb()
        self.ui.setupUi(self)
        WorkingContext.registerOrsWidget('DSB_efd060071a1711f0b40cf83441a96bd5', implementation, 'MainFormDsb', self)

    @staticmethod
    def roi_dialog() -> Optional[ORSModel.ROI]:
        chooser = ChooseObjectAndNewName(
            managedClass=[ORSModel.ROI],
            parent=WorkingContext.getCurrentContextWindow(),
        )

        chooser.setWindowTitle("Select an annotation or X to stop")
        chooser.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint
        )

        if chooser.exec() == QDialog.DialogCode.Rejected:
            return None

        guid = chooser.getObjectGUID()
        roi = ORSModel.orsObj(guid)

        return roi

    @pyqtSlot()
    def on_btn_select_roi_clicked(self):
        roi = self.roi_dialog()
        if roi is None:
            return

        mesh = preprocessing.roi_to_mesh(roi)

        pv_mesh = pyvista.wrap(mesh)
        self.ui.vtk_widget.clear()
        self.ui.vtk_widget.add_mesh(pv_mesh, color="lightgrey", opacity=0.3, show_edges=True)
        self.ui.vtk_widget.reset_camera()
        self.ui.vtk_widget.render()
        self.ui.vtk_widget.show()