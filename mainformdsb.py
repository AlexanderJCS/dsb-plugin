import os
from typing import Optional

from PyQt6.QtGui import QIntValidator, QShortcut, QKeySequence

import ORSModel
import numpy as np
from scipy.spatial import KDTree
import trimesh
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

        self.ui.line_spine_num.setValidator(QIntValidator(0, 9999))
        self.ui.btn_go_to_spine_num.setEnabled(False)
        self.ui.sldr_neck_point.setMaximum(1000)
        WorkingContext.registerOrsWidget('DSB_efd060071a1711f0b40cf83441a96bd5', implementation, 'MainFormDsb', self)
        self.mesh: Optional[trimesh.Trimesh] = None
        self.visualizer = None
        self.spine_skeletons = None
        self.neck_point_slider_values = []
        self.annotations_kdtree: Optional[KDTree] = None
        self.annotations = []
        self.neck_pt_3d: Optional[np.ndarray] = None
        self.neck_pt_tangent: Optional[np.ndarray] = None
        self.worker: Optional[PreprocessingWorker] = None

        self.shortcut_neck_point_left = QShortcut(QKeySequence("Q"), self)
        self.shortcut_neck_point_left.activated.connect(self.move_slider_left)

        self.shortcut_neck_point_right = QShortcut(QKeySequence("E"), self)
        self.shortcut_neck_point_right.activated.connect(self.move_slider_right)

        self.ui.btn_next_spine.setShortcut("D")
        self.ui.btn_prev_spine.setShortcut("A")
        self.ui.btn_save_head.setShortcut("R")
        self.ui.btn_go_to_spine_num.setShortcut("Enter")

    def move_slider_left(self):
        self.ui.sldr_neck_point.setValue(self.ui.sldr_neck_point.value() - 10)

    def move_slider_right(self):
        self.ui.sldr_neck_point.setValue(self.ui.sldr_neck_point.value() + 10)

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

        self.worker = PreprocessingWorker(
            filepath,
            ORSModel.orsObj(self.ui.ccb_channel_chooser.getSelectedGuid()),
            selected_roi
        )

        self.worker.update_label.connect(self.update_status_label)
        self.worker.finished.connect(lambda: self.ui.btn_preprocessing_run.setEnabled(True))

        self.worker.start()
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

    @pyqtSlot()
    def closeEvent(self, event):
        self.ui.vis_widget.Finalize()  # Explicitly finalize to prevent a black screen upon exit of the plugin window
        super().closeEvent(event)
