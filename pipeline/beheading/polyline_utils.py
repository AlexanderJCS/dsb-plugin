import numpy as np


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
