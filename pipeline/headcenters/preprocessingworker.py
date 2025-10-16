import math

import ORSModel
from OrsHelpers.primitivehelper import PrimitiveHelper
from PyQt6.QtCore import QThread, pyqtSignal

from . import spine_detection
from . import skeleton_helper
from . import geometry as geom
from . import spine_analysis as sa


from . import meshhelper
class PreprocessingWorker(QThread):
    update_label: pyqtSignal = pyqtSignal(str)
    finished: pyqtSignal = pyqtSignal()

    def __init__(self, filepath: str, channel: ORSModel.ors.Channel, selected_roi: ORSModel.ors.ROI):
        super().__init__()

        self.selected_roi = selected_roi
        self.channel = channel
        self.filepath = filepath

    def run(self):
        try:
            self.update_label.emit("Converting ROI to Mesh")
            ors_mesh = meshhelper.roi_to_ors_mesh(self.channel, self.selected_roi, smooth=True)
            ors_mesh.setTitle("DSB Dendrite Mesh")
            ors_mesh.publish()

            tm_mesh = meshhelper.ors_to_trimesh(ors_mesh)

            self.update_label.emit("Skeletonizing Mesh")
            skeleton = meshhelper.skeletonize_mesh(tm_mesh)

            self.update_label.emit("Pruning branches")
            spine_skeletons, radii = spine_detection.get_branch_polylines_by_length(
                skeleton, min_length=0, max_length=10000 / 1e6, min_nodes=5, max_nodes=math.inf,
                radius_threshold=math.inf
            )

            total_length = min(len(spine_skeletons), len(radii))
            head_radii = []
            head_center_points = []
            for idx, (spine_skeleton, spine_radii) in enumerate(zip(spine_skeletons, radii)):
                self.update_label.emit(f"Computing head radius for {idx}/{total_length} spines")
                spacing = 3  # nm

                points_tangents, radii_tangents = skeleton_helper.get_radius_polyline(
                    spine_skeleton[::-1], tm_mesh, n_rays=200,
                    aggregate='mean', projection='tangents', path_interpolation_spacing=spacing,
                    fallback=None
                )

                cumulative_points = geom.accumulate(points_tangents)

                radius, head_point_3d = sa.find_head_radius(
                    spine_skeleton[::-1],
                    tm_mesh,
                    cumulative_points,
                    radii_tangents,
                    0.004,
                    # f"out/headradius/spine_graph/spine_head_{idx}.npz"
                    None
                )
                head_radii.append(radius)
                head_center_points.append(head_point_3d)

            heads_annotation: ORSModel.ors.Annotation = PrimitiveHelper.createPrimitive(
                primitiveClass=ORSModel.ors.VisualPoints,
                aLayoutName="Test",
                associatedState="OrsStatePointsEdit"
            )

            for head_point in head_center_points:
                head_point /= 1e9  # nm -> m

                heads_annotation.addControlPoint(ORSModel.ors.Vector3(*head_point), 0, None)

            heads_annotation.publish()


        except Exception as e:
            self.update_label.emit(f"An unexpected error occurred while preprocessing")
            raise e
        finally:
            self.finished.emit()
