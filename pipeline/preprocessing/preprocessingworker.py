import ORSModel
from PyQt6.QtCore import QThread, pyqtSignal

from typing import Optional

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

        except Exception as e:
            self.update_label.emit(f"An unexpected error occurred while preprocessing")
            raise e
        finally:
            self.finished.emit()
