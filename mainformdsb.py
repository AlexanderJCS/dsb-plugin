import os
from typing import Optional

import ORSModel
from OrsLibraries.workingcontext import WorkingContext
from ORSServiceClass.windowclasses.orsabstractwindow import OrsAbstractWindow
from PyQt6.QtCore import pyqtSlot

from .pipeline.headcenters.headradius_worker import HeadRadiusWorker
from .pipeline.headcenters.preprocessingworker import PreprocessingWorker
from .ui_mainformdsb import Ui_MainFormDsb


class MainFormDsb(OrsAbstractWindow):
    def __init__(self, implementation, parent=None):
        super().__init__(implementation, parent)
        self.ui = Ui_MainFormDsb()
        self.ui.setupUi(self)
        self.ui.ccb_dendrite_roi_chooser.setManagedClass([ORSModel.ROI])
        self.ui.ccb_channel_chooser.setManagedClass([ORSModel.Channel])
        self.ui.ccb_head_points.setManagedClass([ORSModel.Annotation])
        self.ui.ccb_dragonfly_mesh.setManagedClass([ORSModel.FaceVertexMesh])

        WorkingContext.registerOrsWidget('DSB_efd060071a1711f0b40cf83441a96bd5', implementation, 'MainFormDsb', self)
        self.preprocessing_worker: Optional[PreprocessingWorker] = None
        self.radius_worker: Optional[HeadRadiusWorker] = None

    def update_status_label(self, text: str):
        self.ui.lbl_status.setText(text)

    @pyqtSlot()
    def on_btn_preprocessing_run_clicked(self):
        selected_roi = ORSModel.orsObj(self.ui.ccb_dendrite_roi_chooser.getSelectedGuid())
        if selected_roi is None:
            self.ui.lbl_status.setText("No ROI selected")
            return

        self.preprocessing_worker = PreprocessingWorker(
            ORSModel.orsObj(self.ui.ccb_channel_chooser.getSelectedGuid()),
            selected_roi
        )

        self.preprocessing_worker.update_label.connect(self.update_status_label)
        self.preprocessing_worker.finished.connect(lambda: self.ui.btn_preprocessing_run.setEnabled(True))

        self.preprocessing_worker.start()
        self.ui.btn_preprocessing_run.setEnabled(False)  # Disable it until the worker is done

    @pyqtSlot()
    def on_btn_process_head_radii_clicked(self):
        dragonfly_mesh = ORSModel.orsObj(self.ui.ccb_dragonfly_mesh.getSelectedGuid())
        if dragonfly_mesh is None:
            self.ui.lbl_status.setText("No Dragonfly mesh selected")
            return

        annotation = ORSModel.orsObj(self.ui.ccb_head_points.getSelectedGuid())
        if annotation is None:
            self.ui.lbl_status.setText("No head points annotation selected")
            return

        csv_output_path = self.ui.line_csv_output.text()
        if not csv_output_path or not os.path.isdir(os.path.dirname(csv_output_path)):
            self.ui.lbl_status.setText("Invalid CSV output path")
            return

        self.radius_worker = HeadRadiusWorker(
            csv_output_path,
            dragonfly_mesh,
            annotation
        )

        self.radius_worker.start()
        self.ui.btn_process_head_radii.setEnabled(False)  # Disable it until the worker is done
