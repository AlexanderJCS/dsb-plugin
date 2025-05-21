import trimesh

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor


class Visualizer:
    def __init__(self, interactor: QtInteractor, mesh: trimesh.Trimesh, spine_polylines: np.ndarray):
        self.plotter: QtInteractor = interactor
        self.mesh_actor = self.plotter.add_mesh(pv.wrap(mesh), opacity=0.3, color=(0.7, 0.7, 0.7))

        self.spine_polyline_actors = []
        for polyline in spine_polylines:
            # Convert polyline to a set of line segments
            segments = np.empty((2 * (len(polyline) - 1), 3), dtype=polyline.dtype)

            # Even rows = start points, odd rows = end points
            segments[0::2] = polyline[:-1]
            segments[1::2] = polyline[1:]

            actor = self.plotter.add_lines(segments, color=(1, 0, 0))
            self.spine_polyline_actors.append(actor)

        self.spine_point_actors = []
        for polyline in spine_polylines:
            self.spine_point_actors.append(
                self.plotter.add_points(polyline[0], color=(1, 0, 0), point_size=10)
            )

    def set_mesh(self, mesh: trimesh.Trimesh):
        if self.mesh_actor is not None:
            self.plotter.remove_actor(self.mesh_actor)

        self.mesh_actor = self.plotter.add_mesh(pv.wrap(mesh), color=(0.7, 0.7, 0.7), opacity=0.3)
        self.plotter.update()

