from typing import Optional

import ORSModel
import pyvista
from ORSServiceClass.ORSWidget.chooseObjectAndNewName.chooseObjectAndNewName import ChooseObjectAndNewName
from OrsLibraries.workingcontext import WorkingContext
from ORSServiceClass.windowclasses.orsabstractwindow import OrsAbstractWindow
from PyQt6.QtCore import pyqtSlot, Qt, QTimer, QCoreApplication
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QDialog

import preprocessing
from .ui_mainformdsb import Ui_MainFormDsb


class MainFormDsb(OrsAbstractWindow):
    def __init__(self, implementation, parent=None):
        super().__init__(implementation, parent)
        self.ui = Ui_MainFormDsb()
        self.ui.setupUi(self)
        WorkingContext.registerOrsWidget('DSB_efd060071a1711f0b40cf83441a96bd5', implementation, 'MainFormDsb', self)
        self.mesh: Optional[pyvista.PolyData] = None

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
            self.ui.lbl_status.setText("No ROI selected")
            return

        self.ui.lbl_status.setText("Converting ROI -> Mesh")
        # self.mesh = preprocessing.roi_to_mesh(roi)
        self.mesh = pyvista.Sphere()

        self.ui.lbl_status.setText("Visualizing ROI")
        self.ui.vis_widget.add_mesh(self.mesh)
        self.ui.vis_widget.reset_camera()

    @pyqtSlot(int)
    def on_sldr_neck_point_valueChanged(self, value):
        percent = value / self.ui.sldr_neck_point.maximum()

        if self.mesh is None:
            return

        self.mesh.translate([0, 0, percent * 10], inplace=True)

    @pyqtSlot()
    def closeEvent(self, event):
        self.ui.vis_widget.Finalize()  # Explicitly finalize to prevent a black screen upon exit of the plugin window
        super().closeEvent(event)
