import math
import os
from typing import Optional

import ORSModel
import pyvista
import trimesh
from OrsLibraries.workingcontext import WorkingContext
from ORSServiceClass.windowclasses.orsabstractwindow import OrsAbstractWindow
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFileDialog

from pipeline.beheading import skel_helper, spine_analysis, polyline_utils
from pipeline.preprocessing import meshhelper
from pipeline.beheading import geometry as geom
from pipeline import payload
from .ui_mainformdsb import Ui_MainFormDsb
from visualize import visualize as vis


class MainFormDsb(OrsAbstractWindow):
    def __init__(self, implementation, parent=None):
        super().__init__(implementation, parent)
        self.ui = Ui_MainFormDsb()
        self.ui.setupUi(self)
        self.ui.ccb_dendrite_roi_chooser.setManagedClass([ORSModel.ROI])
        WorkingContext.registerOrsWidget('DSB_efd060071a1711f0b40cf83441a96bd5', implementation, 'MainFormDsb', self)
        self.mesh: Optional[trimesh.Trimesh] = None
        self.visualizer = None
        self.spine_skeletons = None

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

        self.ui.lbl_status.setText("Converting ROI to Mesh")
        self.mesh = meshhelper.roi_to_mesh(selected_roi)

        self.ui.lbl_status.setText("Skeletonizing Mesh")
        skeleton = meshhelper.skeletonize_mesh(self.mesh)

        self.ui.lbl_status.setText("Saving...")
        payload.save(
            payload.Payload(
                dendrite_mesh=self.mesh,
                skeleton=skeleton
            ),
            filepath=filepath
        )
        self.ui.lbl_status.setText("Saved!")

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

    def compute_neck_point_and_tangent(self, idx: int):
        """
        Computes the neck point of the spine

        :return: The neck point as a 3D coordinate and the neck tangent as a 3D vector
        """

        if self.mesh is None or self.spine_skeletons is None:
            return None, None

        spine_skeleton = self.spine_skeletons[idx]
        spacing = 6

        points_tangents, radii_tangents = skel_helper.get_radius_polyline(
            spine_skeleton[::-1], self.mesh, n_rays=150, aggregate='percentile99',
            projection='tangents', path_interpolation_spacing=spacing
        )

        cumulative_points = geom.accumulate(points_tangents)

        neck_point_1d = spine_analysis.find_neck_point_from_head_radius(spine_skeleton[::-1], self.mesh, cumulative_points,
                                                            radii_tangents)

        neck_point_3d, neck_tangent = geom.point_and_tangent_along_polyline(spine_skeleton, neck_point_1d)
        return neck_point_3d, neck_tangent

    @pyqtSlot()
    def on_btn_prev_spine_clicked(self):
        if self.visualizer is None:
            self.ui.lbl_status.setText("Load a preprocessing file first")
            return None, None

        vis_current = self.visualizer.currently_visualizing
        vis_next = (vis_current - 1) if vis_current is not None else 0
        vis_next %= len(self.visualizer.spine_polyline_actors)

        if not self.visualizer.has_spine_point(vis_next):
            neck_pt, tangent = self.compute_neck_point_and_tangent(vis_next)
            if neck_pt is None or tangent is None:
                self.ui.lbl_status.setText("Failed to compute neck point and tangent")
                return

            self.visualizer.set_spine_point(vis_next, neck_pt)

        self.visualizer.vis_spine_idx(vis_next)

    @pyqtSlot()
    def on_btn_next_spine_clicked(self):
        if self.visualizer is None:
            self.ui.lbl_status.setText("Load a preprocessing file first")
            return

        vis_current = self.visualizer.currently_visualizing
        vis_next = (vis_current + 1) if vis_current is not None else 0
        vis_next %= len(self.visualizer.spine_polyline_actors)

        if not self.visualizer.has_spine_point(vis_next):
            neck_pt, tangent = self.compute_neck_point_and_tangent(vis_next)
            if neck_pt is None or tangent is None:
                self.ui.lbl_status.setText("Failed to compute neck point and tangent")
                return

            self.visualizer.set_spine_point(vis_next, neck_pt)

        self.visualizer.vis_spine_idx(vis_next)

    @pyqtSlot()
    def on_btn_select_preprocessing_file_clicked(self):
        filepath, _ = QFileDialog.getOpenFileName(
            None,
            "Select Preprocessing File",
            "",
            "DSB Files (*.dsb)"
        )

        if not filepath:
            self.ui.lbl_status.setText("No file selected")
            return

        pld = payload.load(filepath)
        self.mesh = pld.dendrite_mesh
        self.spine_skeletons, radii = polyline_utils.get_branch_polylines_by_length(
            pld.skeleton, min_length=0, max_length=50000, min_nodes=15, max_nodes=5000, radius_threshold=math.inf
        )

        self.ui.vis_widget.show()
        self.visualizer = vis.Visualizer(self.ui.vis_widget, pld.dendrite_mesh, self.spine_skeletons)
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
