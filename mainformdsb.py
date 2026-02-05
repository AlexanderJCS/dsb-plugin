import os
from typing import Optional

import ORSModel
from OrsLibraries.workingcontext import WorkingContext
from ORSServiceClass.windowclasses.orsabstractwindow import OrsAbstractWindow
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog

from .pipeline.headradius_worker import HeadRadiusWorker
from .pipeline.preprocessingworker import PreprocessingWorker
from .ui_mainformdsb import Ui_MainFormDsb


class MainFormDsb(OrsAbstractWindow):
    def __init__(self, implementation, parent=None):
        super().__init__(implementation, parent)
        self.ui = Ui_MainFormDsb()
        self.ui.setupUi(self)
        self.ui.ccb_dendrite_mesh_preprocessing.setManagedClass([ORSModel.FaceVertexMesh])
        self.ui.ccb_head_points.setManagedClass([ORSModel.Annotation])
        self.ui.ccb_dendrite_mesh_postprocessing.setManagedClass([ORSModel.FaceVertexMesh])
        self.ui.ccb_psd_annotation.setManagedClass([ORSModel.Annotation])
        self.ui.ccb_psd_multiroi.setManagedClass([ORSModel.MultiROI])

        self.ui.ccb_psd_annotation.setEnabled(False)
        self.ui.ccb_psd_multiroi.setEnabled(False)

        # I have to set these manually for some reason
        self.ui.chk_psd_annotation.stateChanged.connect(self.on_chk_psd_annotation_stateChanged)
        self.ui.chk_psd_multiroi.stateChanged.connect(self.on_chk_psd_multiroi_stateChanged)

        WorkingContext.registerOrsWidget('DSB_efd060071a1711f0b40cf83441a96bd5', implementation, 'MainFormDsb', self)
        self.preprocessing_worker: Optional[PreprocessingWorker] = None
        self.radius_worker: Optional[HeadRadiusWorker] = None

    @pyqtSlot()
    def on_chk_psd_annotation_stateChanged(self):
        self.ui.ccb_psd_annotation.setEnabled(self.ui.chk_psd_annotation.isChecked())

    @pyqtSlot()
    def on_chk_psd_multiroi_stateChanged(self):
        self.ui.ccb_psd_multiroi.setEnabled(self.ui.chk_psd_multiroi.isChecked())

    def update_status_label(self, text: str):
        self.ui.lbl_status.setText(text)

    def dialog_save_filename(self, extension: str) -> str:
        """
        Prompts the user to select a filename to save to and ensures the correct extension is used.
        :param extension: The desired file extension (without dot). E.g.: "csv", "txt"
        :return: The selected filename with the correct extension, or an empty string if canceled.
        """

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output File",
            "",
            f"{extension.upper()} files (*.{extension});;All Files (*)"
        )

        if not filename:
            return filename

        if not filename.lower().endswith(f".{extension.lower()}"):
            filename += f".{extension}"

        return filename

    @pyqtSlot()
    def on_btn_select_csv_output_clicked(self):
        self.ui.line_csv_output.setText(self.dialog_save_filename("csv"))

    @pyqtSlot()
    def on_btn_select_dsb_output_clicked(self):
        self.ui.line_dsb_output.setText(self.dialog_save_filename("dsb"))

    def get_psd_multiroi(self) -> Optional[ORSModel.ors.MultiROI]:
        if self.ui.chk_psd_multiroi.isChecked():
            return ORSModel.orsObj(self.ui.ccb_psd_multiroi.getSelectedGuid())
        return None

    def get_psd_annotation(self) -> Optional[ORSModel.ors.Annotation]:
        if self.ui.chk_psd_annotation.isChecked():
            return ORSModel.orsObj(self.ui.ccb_psd_annotation.getSelectedGuid())
        return None

    @pyqtSlot()
    def on_btn_preprocessing_run_clicked(self):
        selected_roi = ORSModel.orsObj(self.ui.ccb_dendrite_mesh_preprocessing.getSelectedGuid())
        if selected_roi is None:
            self.ui.lbl_status.setText("No ROI selected")
            return

        if self.ui.line_dsb_output.text() == "":
            self.ui.lbl_status.setText("No output path specified")
            return

        self.preprocessing_worker = PreprocessingWorker(
            ORSModel.orsObj(self.ui.ccb_dendrite_mesh_preprocessing.getSelectedGuid()),
            self.get_psd_annotation(),
            self.get_psd_multiroi(),
            self.ui.line_dsb_output.text()
        )

        self.preprocessing_worker.update_label.connect(self.update_status_label)
        self.preprocessing_worker.finished.connect(lambda: self.ui.btn_preprocessing_run.setEnabled(True))

        self.preprocessing_worker.start()
        self.ui.btn_preprocessing_run.setEnabled(False)  # Disable it until the worker is done

    @pyqtSlot()
    def on_btn_process_head_radii_clicked(self):
        dragonfly_mesh = ORSModel.orsObj(self.ui.ccb_dendrite_mesh_postprocessing.getSelectedGuid())
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

        self.radius_worker.progress_updated.connect(self.update_status_label)
        self.radius_worker.finished.connect(lambda: self.ui.btn_process_head_radii.setEnabled(True))

        self.radius_worker.start()
        self.ui.btn_process_head_radii.setEnabled(False)  # Disable it until the worker is done
