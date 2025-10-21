import os
from typing import Optional

import ORSModel
from OrsLibraries.workingcontext import WorkingContext
from ORSServiceClass.windowclasses.orsabstractwindow import OrsAbstractWindow
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog

from .pipeline.headcenters.preprocessingworker import PreprocessingWorker
from .ui_mainformdsb import Ui_MainFormDsb


class MainFormDsb(OrsAbstractWindow):
    def __init__(self, implementation, parent=None):
        super().__init__(implementation, parent)
        self.ui = Ui_MainFormDsb()
        self.ui.setupUi(self)
        self.ui.ccb_dendrite_roi_chooser.setManagedClass([ORSModel.ROI])
        self.ui.ccb_channel_chooser.setManagedClass([ORSModel.Channel])

        WorkingContext.registerOrsWidget('DSB_efd060071a1711f0b40cf83441a96bd5', implementation, 'MainFormDsb', self)
        self.preprocessing_worker: Optional[PreprocessingWorker] = None
        # self.radius_worker: Optional[RadiusWorker] = None

    def update_status_label(self, text: str):
        self.ui.lbl_status.setText(text)

    @pyqtSlot()
    def on_btn_preprocessing_run_clicked(self):
        selected_roi = ORSModel.orsObj(self.ui.ccb_dendrite_roi_chooser.getSelectedGuid())
        if selected_roi is None:
            self.ui.lbl_status.setText("No ROI selected")
            return

        filepath = self.ui.line_preprocessing_output_path.text()
        if not filepath:
            self.ui.lbl_status.setText("No output path selected")
            return

        if not os.path.isdir(os.path.dirname(filepath)):
            self.ui.lbl_status.setText("Output path is invalid")
            return

        self.preprocessing_worker = PreprocessingWorker(
            filepath,
            ORSModel.orsObj(self.ui.ccb_channel_chooser.getSelectedGuid()),
            selected_roi
        )

        self.preprocessing_worker.update_label.connect(self.update_status_label)
        self.preprocessing_worker.finished.connect(lambda: self.ui.btn_preprocessing_run.setEnabled(True))

        self.preprocessing_worker.start()
        self.ui.btn_preprocessing_run.setEnabled(False)  # Disable it until the worker is done

    @pyqtSlot()
    def on_btn_select_csv_output_clicked(self):
        filepath, _ = QFileDialog.getSaveFileName(
            None,
            "Select Output CSV Location",
            "",
            "CSV File (*.csv)"
        )

        if filepath:
            self.ui.line_csv_output.setText(filepath)
        else:
            self.ui.lbl_status.setText("No file selected")
            return

    @pyqtSlot()
    def on_btn_preprocessing_output_clicked(self):
        filepath, _ = QFileDialog.getSaveFileName(
            None,
            "Select Output File Location",
            "",
            "DSB Files (*.dsb)"
        )

        if filepath:
            self.ui.line_preprocessing_output_path.setText(filepath)
        else:
            self.ui.lbl_status.setText("No file selected")
            return
