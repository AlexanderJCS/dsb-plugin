import numpy as np
import math


def get_branch_polylines_by_length(skeleton, min_length=1000, max_length=5000, min_nodes=5, max_nodes=30, radius_threshold=2000, angle_threshold=math.inf):
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
    max_nodes : int | float
        The maximum number of nodes in the branch, or math.inf
    radius_threshold : float
        The maximum radius of the last node in nanometers.
    angle_threshold : float
        The maximum average angle between segments in degrees

    Returns
    -------
    polylines : list of np.ndarray
        A list of polylines where each polyline is an array of vertices.
    radii : list of np.ndarray
        A list of radii for each polyline, where each radii array corresponds to the radii of all nodes in the polyline.
    """
    polylines = []
    radii = []

    angle_threshold = np.radians(angle_threshold)

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

        # Calculate average angle between adjacent edges using dot products
        if len(branch_edges) > 1:
            # Filter out zero-length edges to avoid division by zero
            non_zero_mask = branch_lengths > 0
            if np.sum(non_zero_mask) <= 1:
                # Not enough non-zero edges to calculate angles
                avg_angle = 0.0
            else:
                # Normalize the edge vectors (only non-zero edges)
                normalized_edges = branch_edges[non_zero_mask] / branch_lengths[non_zero_mask, np.newaxis]

                # Calculate dot products between consecutive edges
                dot_products = np.sum(normalized_edges[:-1] * normalized_edges[1:], axis=1)

                # Clamp dot products to [-1, 1] to avoid numerical errors with arccos
                dot_products = np.clip(dot_products, -1.0, 1.0)

                # Calculate angles from dot products
                angles = np.arccos(dot_products)

                # Calculate the average angle
                avg_angle = np.mean(angles)
        else:
            # If there's only one edge, set average angle to 0 (straight line)
            avg_angle = 0.0

        # Check if the branch length and last node's radius are outside the specified ranges
        length_outside_range = total_length < min_length or total_length > max_length
        last_node_radius_outside_range = skeleton.swc.loc[seg[-1], "radius"] >= radius_threshold
        angle_outside_range = avg_angle > angle_threshold

        if length_outside_range or last_node_radius_outside_range or angle_outside_range:
            continue

        # Get the radii for all nodes in the branch
        node_radii = skeleton.swc.loc[seg, "radius"].values

        # Append the branch vertices as a polyline and its corresponding node radii
        polylines.append(branch_vertices)
        radii.append(node_radii)

    return polylines, radii
