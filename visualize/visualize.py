import typing

import trimesh

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor


def line_actor(lines, color='w', width=5, connected=False):
    """
    Create a line plot actor from a set of points. Borrowed from pyvistaqt's source code, but modified to remove the
    line:
    self.add_actor(actor, reset_camera=False, name=name, pickable=False)

    which adds the actor to the plotter.

    Parameters
    ----------
    lines : np.ndarray
        Points representing line segments.  For example, two line
        segments would be represented as ``np.array([[0, 1, 0],
        [1, 0, 0], [1, 1, 0], [2, 0, 0]])``.

    color : ColorLike, default: 'w'
        Either a string, rgb list, or hex color string.  For example:

        * ``color='white'``
        * ``color='w'``
        * ``color=[1.0, 1.0, 1.0]``
        * ``color='#FFFFFF'``

    width : float, default: 5
        Thickness of lines.

    label : str, default: None
        String label to use when adding a legend to the scene with
        :func:`pyvista.Plotter.add_legend`.

    connected : bool, default: False
        Treat ``lines`` as points representing a series of *connected* lines.
        For example, two connected line segments would be represented as
        ``np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0]])``. If ``False``, an *even*
        number of points must be passed to ``lines``, and the lines need not be
        connected.

    Returns
    -------
    vtk.vtkActor
        Lines actor.
    """
    if not isinstance(lines, np.ndarray):
        raise TypeError('Input should be an array of point segments')

    lines = (
        pv.lines_from_points(lines)
        if connected
        else pv.line_segments_from_points(lines)
    )

    actor = pv.Actor(mapper=pv.DataSetMapper(lines))
    actor.prop.line_width = width
    actor.prop.show_edges = True
    actor.prop.edge_color = color
    actor.prop.color = color
    actor.prop.lighting = False

    return actor


class Visualizer:
    def __init__(self, interactor: QtInteractor, mesh: trimesh.Trimesh, spine_polylines: np.ndarray):
        self.plotter: QtInteractor = interactor
        self.mesh_actor = self.plotter.add_mesh(pv.wrap(mesh), opacity=0.3, color=(0.7, 0.7, 0.7))

        self.active_actors = []  # Actors that are currently visible in the plotter and aren't the dendrite mesh actor

        self.spine_polyline_actors = []
        for polyline in spine_polylines:
            self.spine_polyline_actors.append(
                line_actor(polyline, color=(1, 0, 0), connected=True)
            )

        self.spine_point_actors: list[typing.Optional[pv.Actor]] = [None for _ in range(len(spine_polylines))]

        self.currently_visualizing: typing.Optional[int] = None

    def set_mesh(self, mesh: trimesh.Trimesh):
        if self.mesh_actor is not None:
            self.plotter.remove_actor(self.mesh_actor)

        self.mesh_actor = self.plotter.add_mesh(pv.wrap(mesh), color=(0.7, 0.7, 0.7), opacity=0.3)
        self.plotter.update()

    def focus_camera_on_point(self, point, distance=None):
        """
        Center the camera view on a specific point.

        Parameters:
        -----------
        plotter : pyvista.Plotter or QtInteractor
            The plotter instance
        point : array-like
            The [x, y, z] coordinates to focus on
        distance : float, optional
            Distance from the point. If None, uses current distance.
        """

        # Get current camera position
        current_position = self.plotter.camera_position

        # If no distance specified, use current distance
        if distance is None:
            # Calculate current distance
            current_distance = np.linalg.norm(
                np.array(current_position[0]) - np.array(current_position[1])
            )
        else:
            current_distance = distance

        # Calculate the vector from the focal point to the current position
        current_direction = np.array(current_position[0]) - np.array(current_position[1])
        if np.linalg.norm(current_direction) > 0:
            current_direction = current_direction / np.linalg.norm(current_direction)
        else:
            current_direction = np.array([0, 0, 1])  # Default direction

        # Calculate new camera position
        new_position = np.array(point) - current_distance * current_direction

        # Set camera position
        self.plotter.camera_position = [
            new_position,  # Camera position
            point,  # Focal point
            current_position[2]  # Camera up direction (keep the same)
        ]

    def has_spine_point(self, idx: int) -> bool:
        """
        Check if the point actor for the given index exists.
        :param idx: The index of the point actor to check.
        :return: True if the point actor exists, False otherwise.
        """
        return self.spine_point_actors[idx] is not None

    def set_spine_point(self, idx: int, point_loc: np.ndarray) -> None:
        """
        Set the point actor for the given index to the specified location.
        If the point actor does not exist, create it.
        :param idx: The index of the point actor to set.
        :param point_loc: The location of the point actor.
        """

        if not self.has_spine_point(idx):
            self.spine_point_actors[idx] = self.plotter.add_points(point_loc, color=(1, 0, 0), render_points_as_spheres=True, point_size=10)
        else:
            self.spine_point_actors[idx].position = point_loc
            self.plotter.update()

    def vis_spine_idx(self, idx: int) -> None:
        for actor in self.active_actors:
            self.plotter.remove_actor(actor)

        self.active_actors.clear()

        if not self.has_spine_point(idx):
            raise ValueError(f"No point actor exists for index {idx}. Please set the point first using set_point_idx.")

        self.currently_visualizing = idx
        self.plotter.add_actor(self.spine_polyline_actors[idx])
        self.active_actors.append(self.spine_polyline_actors[idx])

        self.plotter.add_actor(self.spine_point_actors[idx])
        self.active_actors.append(self.spine_point_actors[idx])

        self.focus_camera_on_point(self.spine_point_actors[idx].center, distance=8000)
