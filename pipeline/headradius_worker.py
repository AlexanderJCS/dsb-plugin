import ORSModel
from PyQt6.QtCore import QThread, pyqtSignal

from . import meshhelper, skeleton_helper


class HeadRadiusWorker(QThread):
    progress_updated = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, out_path: str, mesh: ORSModel.ors.FaceVertexMesh, annotation: ORSModel.ors.Annotation):
        super().__init__()

        self.out_path = out_path
        self.mesh = mesh
        self.annotation = annotation

    def run(self):
        try:
            self.progress_updated.emit("Initializing mesh...")
            tm_mesh = meshhelper.ors_to_trimesh(self.mesh)
            points = meshhelper.get_points_from_annotation(self.annotation)

            csv_data = "Point Index,Annotation Label,Radius (nm),Point X, Point Y, Point Z\n"

            total_points = len(points)
            self.progress_updated.emit(f"Processing {total_points} points...")

            for i, point in enumerate(points):
                progress_percent = (i + 1) / total_points * 100
                self.progress_updated.emit(f"Processing point {i+1}/{total_points} ({progress_percent:.1f}%)")

                radius = skeleton_helper.get_radius_point(
                    point, tm_mesh, n_rays=500, aggregate="mean", projection="sphere")[0]
                annotation_label = self.annotation.getControlPointCaptionAtIndex(i, 0)
                csv_data += f"{i+1},{annotation_label},{radius},{point[0]},{point[1]},{point[2]}\n"

            self.progress_updated.emit("Writing results to file...")
            with open(self.out_path, "w") as f:
                f.write(csv_data)

            self.progress_updated.emit("Processing complete!")

        except Exception as e:
            error_msg = f"Error in HeadRadiusWorker: {e}"
            self.progress_updated.emit(error_msg)

        finally:
            self.finished.emit()
