import math
import traceback

import ORSModel
from OrsHelpers.primitivehelper import PrimitiveHelper
from PyQt6.QtCore import QThread, pyqtSignal

from OrsLibraries.logger import Logger

from . import spine_detection
from . import skeleton_helper
from . import geometry as geom
from . import spine_analysis as sa

from . import meshhelper

log = Logger(__file__)


class PreprocessingWorker(QThread):
    update_label: pyqtSignal = pyqtSignal(str)
    finished: pyqtSignal = pyqtSignal()

    def __init__(self, mesh: ORSModel.ors.FaceVertexMesh):
        super().__init__()

        self.mesh = mesh

    def run(self):
        try:
            tm_mesh = meshhelper.ors_to_trimesh(self.mesh)

            self.update_label.emit("Skeletonizing Mesh")
            skeleton = meshhelper.skeletonize_mesh(tm_mesh)

            self.update_label.emit("Pruning branches")
            log.info("Pruning skeleton branches")
            spine_skeletons, radii = spine_detection.get_branch_polylines_by_length(
                skeleton, min_length=50, max_length=10000, min_nodes=5, max_nodes=math.inf,
                radius_threshold=math.inf, angle_threshold=80
            )

            total_length = min(len(spine_skeletons), len(radii))
            head_center_points = []

            skipped_spines_count = 0

            log.info("Iterating over spines to compute radii as a function of path length")
            for idx, (spine_skeleton, spine_radii) in enumerate(zip(spine_skeletons, radii)):
                try:
                    self.update_label.emit(f"Computing head radius for {idx + 1}/{total_length} spines")
                    spacing = 5  # nm

                    log.info(f"Spine {idx}: computing radii")
                    points_tangents, radii_tangents = skeleton_helper.get_radius_polyline(
                        spine_skeleton[::-1], tm_mesh, n_rays=140,
                        aggregate='mean', projection='tangents', path_interpolation_spacing=spacing,
                        fallback=None
                    )

                    log.info(f"Spine {idx}: {len(points_tangents)} points for head radius computation")

                    cumulative_points = geom.accumulate(points_tangents)
                    log.info(f"Spine {idx}: Length is {cumulative_points[-1]} nm")

                    log.info(f"Spine {idx}: Computing head point")
                    head_point_3d = sa.find_head_point(
                        spine_skeleton[::-1],
                        cumulative_points,
                        radii_tangents,
                        0.004,
                        # f"out/headradius/spine_graph/spine_head_{idx}.npz"
                        None
                    )
                    head_center_points.append(head_point_3d)

                    log.info(f"Spine {idx}: Head point at {head_point_3d}")
                except Exception:
                    log.error(f"An error occurred while processing spine {idx}. Skipping to next spine.")
                    log.error(traceback.format_exc())
                    skipped_spines_count += 1

            self.update_label.emit("Creating head centers annotation")
            log.info("Creating head centers annotation")
            heads_annotation: ORSModel.ors.Annotation = PrimitiveHelper.createPrimitive(
                primitiveClass=ORSModel.ors.VisualPoints,
                aLayoutName="head_centers_annotation",
                associatedState="OrsStatePointsEdit"
            )

            heads_annotation.setTitle("Head Centers Annotation")

            for head_point in head_center_points:
                head_point /= 1e9  # nm -> m
                heads_annotation.addControlPoint(ORSModel.ors.Vector3(*head_point), 0, None)

            heads_annotation.publish()


            self.update_label.emit(f"Finished. Skipped {skipped_spines_count} spine{'s' if skipped_spines_count != 1 else ''}.")

        except Exception:
            self.update_label.emit(f"An error occurred while processing. Check Dragonfly logs.")
            log.fatal("An error occurred in PreprocessingWorker:")
            log.fatal(traceback.format_exc())
        finally:
            self.finished.emit()

   