import numpy as np
import trimesh
from tqdm import tqdm
from trimesh.proximity import ProximityQuery


def get_branch_polylines_by_length(skeleton, min_length=1000, max_length=5000, min_nodes=5, max_nodes=30, radius_threshold=2000):
    """
    Extract branches from the skeleton based on length, node count, and each node's radius, and return a list of polylines
    along with their corresponding radii for each node.

    Parameters
    ----------
    skeleton : meshparty.skeleton.Skeleton
        The skeleton object with vertices and edges.
    min_length : float
        The minimum branch length in nanometers.
    max_length : float
        The maximum branch length in nanometers.
    min_nodes : int
        The minimum number of nodes in the branch.
    max_nodes : int
        The maximum number of nodes in the branch.
    radius_threshold : float
        The maximum radius of the last node in nanometers.

    Returns
    -------
    polylines : list of np.ndarray
        A list of polylines where each polyline is an array of vertices.
    radii : list of np.ndarray
        A list of radii for each polyline, where each radii array corresponds to the radii of all nodes in the polyline.
    """
    polylines = []
    radii = []

    # Identify the largest segment to skip later since it is likely the main branch
    largest_segment = None
    for seg in skeleton.get_segments():
        if largest_segment is None or len(seg) > len(largest_segment):
            largest_segment = seg

    for seg in skeleton.get_segments():
        if seg == largest_segment:
            continue

        # Check if the number of nodes in the branch are outside the specified range
        if len(seg) < min_nodes or len(seg) > max_nodes:
            continue

        # Calculate the total length of the branch
        branch_vertices = skeleton.vertices[seg]
        branch_edges = np.diff(branch_vertices, axis=0)
        branch_lengths = np.linalg.norm(branch_edges, axis=1)
        total_length = np.sum(branch_lengths)

        # Check if the branch length and last node's radius are outside the specified ranges
        length_outside_range = total_length < min_length or total_length > max_length
        last_node_radius_outside_range = skeleton.swc.loc[seg[-1], "radius"] >= radius_threshold

        if length_outside_range or last_node_radius_outside_range:
            continue

        # Get the radii for all nodes in the branch
        node_radii = skeleton.swc.loc[seg, "radius"].values

        # Append the branch vertices as a polyline and its corresponding node radii
        polylines.append(branch_vertices)
        radii.append(node_radii)

    return polylines, radii


def mark_at_radius(polylines, radii, mark_position="last_node"):
    """
    Marks a point based on the chosen marking position option: at the radius from the last node, 
    at the radius from the second-to-last node, or at the midpoint between the two.

    Parameters
    ----------
    polylines : list of np.ndarray
        A list of polylines, where each polyline is an array of 3D points.
    radii : list of np.ndarray
        A list of radii for each node in the corresponding polyline.
    mark_position : str, optional
        The position where the point will be marked. Options are:
        - "last_node": at the radius distance from the last node.
        - "second_last_node": at the radius distance from the second-to-last node.
        - "midpoint": at the midpoint between the two radius points.

    Returns
    -------
    list of np.ndarray
        A list of 3D coordinates of the marked points based on the selected marking option.
    """
    marked_points = []

    for polyline, radii_polyline in zip(polylines, radii):
        if len(polyline) < 2:
            # Skip polylines with fewer than 2 nodes
            continue

        # Get the last and second-to-last nodes
        last_node = polyline[-1]
        second_last_node = polyline[-2]

        # Get the radii for the last and second-to-last nodes
        radius_last_node = radii_polyline[-1]
        radius_second_last_node = radii_polyline[-2]

        # Calculate the direction vector from the last node to the second-last node
        direction_vector = second_last_node - last_node
        direction_unit_vector = direction_vector / np.linalg.norm(direction_vector)

        # Calculate the point at the radius distance from the last node
        point_from_last_node = last_node + radius_last_node * direction_unit_vector

        # Calculate the point at the radius distance from the second-last node
        point_from_second_last_node = second_last_node - radius_second_last_node * direction_unit_vector

        if mark_position == "last_node":
            # Mark at the point from the last node
            marked_point = point_from_last_node
        elif mark_position == "second_last_node":
            # Mark at the point from the second-to-last node
            marked_point = point_from_second_last_node
        elif mark_position == "midpoint":
            # Mark at the midpoint between the two points
            marked_point = (point_from_last_node + point_from_second_last_node) / 2
        else:
            raise ValueError(f"Invalid mark_position option '{mark_position}'. Choose 'last_node', 'second_last_node', or 'midpoint'.")

        # Append the marked point to the list
        marked_points.append(marked_point)

    return marked_points

def mark_at_fraction(polylines, fraction=0.25):
    """
    Mark a point at a user-defined fraction between the last and second-last nodes for each polyline.

    Parameters
    ----------
    polylines : list of np.ndarray
        List of polylines (each polyline is an array of points).
    fraction : float, optional
        Fraction along the line between the second-to-last and last node where the point should be marked.
        A fraction of 0.0 will place the marker at the second-to-last node, and a fraction of 1.0 will place
        the marker at the last node. The default is 0.5 (midpoint).

    Returns
    -------
    markers : list of np.ndarray
        List of marked points (one point at the specified fraction between the last and second-to-last nodes for each polyline).
    """
    markers = []
    
    for polyline in polylines:
        last_node = polyline[-1]
        second_last_node = polyline[-2]
        
        # Calculate the point based on the user-defined fraction
        marked_point = second_last_node + fraction * (last_node - second_last_node)
        
        markers.append(marked_point)
    
    return markers


def snap_marked_points_to_mesh(mesh, marked_points, snap_to="vertex"):
    """
    Snap each marked point to the nearest vertex or face on the mesh, with progress tracking.

    Parameters
    ----------
    mesh : trimesh.Trimesh
        The mesh to snap the points onto.
    marked_points : list of np.ndarray
        A list of 3D coordinates representing the marked points.
    snap_to : str, optional
        The snapping method: "vertex" to snap to the nearest vertex, "face" to snap to the nearest face.
        Default is "vertex".

    Returns
    -------
    snapped_points : list of np.ndarray
        A list of 3D coordinates of the snapped points.
    """
    # Initialize proximity query for the mesh
    proximity_query = ProximityQuery(mesh)
    
    snapped_points = []

    # Iterate through each marked point and snap it to the nearest vertex or face with progress tracking
    for point in tqdm(marked_points, desc="Snapping points to mesh", unit="point"):
        if snap_to == "vertex":
            # Snap to the nearest vertex
            _, nearest_vertex_idx = proximity_query.vertex([point])
            snapped_point = mesh.vertices[nearest_vertex_idx[0]]
        elif snap_to == "face":
            # Snap to the nearest face
            nearest_point_on_surface, _, _ = proximity_query.on_surface([point])
            snapped_point = nearest_point_on_surface[0]
        else:
            raise ValueError("Invalid snap_to option. Use 'vertex' or 'face'.")
        
        # Append the snapped point
        snapped_points.append(snapped_point)

    return snapped_points
