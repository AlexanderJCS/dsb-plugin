import math

import ORSModel
from OrsHelpers.primitivehelper import PrimitiveHelper
from PyQt6.QtCore import QThread, pyqtSignal

from . import skeleton_helper

from . import meshhelper


class HeadRadiusWorker(QThread):
    def __init__(self, out_path: str, mesh: ORSModel.ors.FaceVertexMesh, annotation: ORSModel.ors.Annotation):
        super().__init__()

        self.out_path = out_path
        self.mesh = mesh
        self.annotation = annotation

    def run(self):
        try:
            tm_mesh = meshhelper.ors_to_trimesh(self.mesh)
            points = meshhelper.get_points_from_annotation(self.annotation)

            csv_data = "Point Index,Annotation Label,Radius (nm)\n"

            for i, point in enumerate(points):
                print(f"Processing point {i+1}/{len(points)}")
                radius = skeleton_helper.get_radius_point(
                    point, tm_mesh, n_rays=500, aggregate="mean", projection="sphere")[0]
                annotation_label = self.annotation.getControlPointCaptionAtIndex(i, 0)
                csv_data += f"{i+1},{annotation_label},{radius}\n"

            with open(self.out_path, "w") as f:
                f.write(csv_data)

        except Exception as e:
            print(f"Error in HeadRadiusWorker: {e}")