import numpy as np
import numbers

import ncollpyde
import scipy

from skeletor.post.radiusextraction import fibonacci_sphere


def interpolate_along_path(points, spacing):
    """
    Interpolates points along a 3D polyline at a given spacing.
    Parameters:
        points (np.ndarray): An (N, 3) array of 3D points defining the path.
        spacing (float): The desired distance between interpolated points.
    Returns:
        np.ndarray: An (M, 3) array of interpolated 3D points.
    """
    # Calculate distances between consecutive points
    diffs = np.diff(points, axis=0)
    seg_lengths = np.linalg.norm(diffs, axis=1)

    # Compute cumulative arc-lengths
    s = np.concatenate(([0], np.cumsum(seg_lengths)))

    # Create new parameter values at the desired spacing
    new_s = np.arange(0, s[-1], spacing)

    # Interpolate x, y, and z coordinates
    x_interp = np.interp(new_s, s, points[:, 0])
    y_interp = np.interp(new_s, s, points[:, 1])
    z_interp = np.interp(new_s, s, points[:, 2])

    return np.column_stack((x_interp, y_interp, z_interp))


def rotate_points_to_normal(points, target_normal):
    """
    Rotates a set of 3D points such that the plane's normal (originally [0, 0, 1])
    is aligned with target_normal.

    Parameters:
        points (np.ndarray): Array of shape (N, 3) representing the points.
        target_normal (np.ndarray): A normalized 3D vector representing the desired normal.

    Returns:
        np.ndarray: The rotated points.
    """

    n0 = np.array([0, 0, 1])  # Original normal vector

    target_normal /= np.linalg.norm(target_normal)

    # Compute the rotation axis via the cross product between n0 and target_normal
    axis = np.cross(n0, target_normal)
    axis_norm = np.linalg.norm(axis)

    # If the norm of the axis is nearly zero, the normals are parallel or antiparallel. This is a special case that
    #  needs to be accounted for to prevent divide by zero errors in axis /= axis_norm
    if np.isclose(axis_norm, 0):
        if np.allclose(target_normal, -n0):  # Rotate 180 degrees if the normals are antiparallel
            # For a 180-degree rotation, we can rotate around any axis perpendicular to n0. The x-axis is chosen.
            R = np.array([[1, 0, 0],
                          [0, -1, 0],
                          [0, 0, -1]])

            return points.dot(R.T)

        return points

    axis /= axis_norm  # Normalize rotation axis
    theta = np.arccos(np.clip(np.dot(n0, target_normal), -1.0, 1.0))  # Rotation angle

    # Create the skew-symmetric matrix of the rotation axis.
    K = np.array([[0, -axis[2], axis[1]],
                  [axis[2], 0, -axis[0]],
                  [-axis[1], axis[0], 0]])

    # Rodrigues' rotation formula: R = I + sin(theta)*K + (1-cos(theta))*K^2
    R = np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * np.dot(K, K)

    return points.dot(R.T)  # Apply rotation and return



def polyline_tangents(points):
    """
    Compute the tangents of a polyline given its points using vectorized operations.

    For middle points, the tangent is computed as:
        tangent[i] = points[i+1] - points[i-1]
    For the endpoints:
        tangent[0] = points[1] - points[0]
        tangent[-1] = points[-1] - points[-2]

    :param points: An (N, 3) array of 3D points defining the polyline.
    :return: An (N, 3) array of normalized tangent vectors.
    """

    tangents = np.empty_like(points)

    # Compute the tangent for the first and last point
    tangents[0] = points[1] - points[0]
    tangents[-1] = points[-1] - points[-2]

    # For middle points, compute the difference between the next and previous points
    tangents[1:-1] = points[2:] - points[:-2]

    dists = np.linalg.norm(tangents, axis=1, keepdims=True)

    assert np.all(dists != 0), "Some tangent vectors have zero length. Are there duplicate points?"

    return tangents / dists  # Normalize tangents and return


def get_radius_knn(coords, mesh, n=5, aggregate='mean'):
    """Extract radii using k-nearest-neighbors.

    Parameters
    ----------
    coords :    numpy.ndarray
    mesh :      trimesh.Trimesh
    n :         int
                Radius will be the mean over n nearest-neighbors.
    aggregate : "mean" | "median" | "max" | "min" | "percentile75"
                Function used to aggregate radii for `n` nearest neighbors.

    Returns
    -------
    radii :     np.ndarray
                Corresponds to input coords.

    """
    agg_map = {'mean': np.mean, 'max': np.max, 'min': np.min,
               'median': np.median, 'percentile75': lambda x, **kwargs: np.percentile(x, 75, **kwargs),
               'percentile99': lambda x, **kwargs: np.percentile(x, 99, **kwargs)}
    assert aggregate in agg_map
    agg_func = agg_map[aggregate]

    # Generate kdTree
    tree = scipy.spatial.cKDTree(mesh.vertices)

    # Query for coordinates
    dist, ix = tree.query(coords, k=5)

    # Aggregate
    return agg_func(dist, axis=1)


def get_radius_polyline(polyline, mesh, n_rays=20, aggregate='mean', projection='sphere',
                        fallback='knn', path_interpolation_spacing=5):
    """
    Extract radii using ray casting.

    Parameters
    ----------
    polyline :      np.ndarray
                    A (N, 3) array of 3D points defining the polyline.
    mesh :          trimesh.Trimesh
    n_rays :        int
                    Number of rays to cast for each node.
    aggregate :     "mean" | "median" | "max" | "min" | "percentile75"
                    Function used to aggregate radii for over all intersections
                    for a given node.
    projection :    "sphere" | "tangents"
                    Whether to cast rays in a sphere around each node or in a
                    circle orthogonally to the node's tangent vector.
    fallback :      "knn" | None | number
                    If a point is outside or right on the surface of the mesh
                    the raycasting will return nonsense results. We can either
                    ignore those cases (``None``), assign an arbitrary number or
                    we can fall back to radii from k-nearest-neighbors (``knn``).

    path_interpolation_spacing: The distance between points on the path (polyline) to sample.

    :returns (points sampled, their corresponding radii)

    """
    agg_map = {'mean': np.mean, 'max': np.max, 'min': np.min,
               'median': np.median, 'percentile75': lambda x: np.percentile(x, 75), 'percentile99': lambda x: np.percentile(x, 99)}
    assert aggregate in agg_map
    agg_func = agg_map[aggregate]

    assert projection in ['sphere', 'tangents']
    assert (fallback == 'knn') or isinstance(fallback, numbers.Number) or isinstance(fallback, type(None))

    # Get max dimension of mesh
    dim = polyline.max(axis=0) - polyline.min(axis=0)
    radius = max(dim)

    # Vertices for each point on the circle
    points = interpolate_along_path(polyline, path_interpolation_spacing)
    sources = np.repeat(points, n_rays, axis=0)

    if projection == 'sphere':
        # Repeat points n_rays times
        sources = np.repeat(points, n_rays, axis=0)

        targets = fibonacci_sphere(n_rays, randomize=True) * radius  # Uniform sphere points sphere scaled by radius
        targets = np.tile(targets, (points.shape[0], 1))  # Reshape to match sources
        targets += sources # Offset onto sources
    else:
        tangents = polyline_tangents(points)

        # Follow these steps:
        #  1. Create a unit disk of n_rays points along axes x and y
        #  2. Scale the unit disk by radius
        #  3. Duplicate the disk by the number of points to equal the length of sources: shape [len(points), n_rays, 3]
        #  4. Rotate the unit disk to align with the tangent vector
        #  5. Define a targets array by adding the rotated disk to the sources

        # Step 1
        zero_to_2pi = np.linspace(0, 2 * np.pi, n_rays, endpoint=False)
        disk = np.column_stack((np.cos(zero_to_2pi), np.sin(zero_to_2pi), np.zeros(n_rays)))

        # Step 2
        disk *= radius

        # Step 3
        disk = np.repeat(disk[np.newaxis, :, :], points.shape[0], axis=0)

        # Step 4
        for i, tangent in enumerate(tangents):
            disk[i] = rotate_points_to_normal(disk[i], tangent)

        # Step 5
        disk = disk.reshape(-1, 3)
        targets = sources + disk

    # Initialize ncollpyde Volume
    coll = ncollpyde.Volume(mesh.vertices, mesh.faces, validate=False)

    # Get intersections: `ix` points to index of line segment; `loc` is the
    #  x/y/z coordinate of the intersection and `is_backface` is True if
    # intersection happened at the inside of a mesh
    ix, loc, is_backface = coll.intersections(sources, targets)

    # Calculate intersection distances
    dist = np.sqrt(np.sum((sources[ix] - loc) ** 2, axis=1))

    # Map from `ix` back to index of original point
    org_ix = (ix / n_rays).astype(int)

    # Split by original index
    split_ix = np.where(org_ix[:-1] - org_ix[1:])[0]
    split = np.split(dist, split_ix)

    # Aggregate over each original ix
    final_dist = np.zeros(points.shape[0])
    for l, i in zip(split, np.unique(org_ix)):
        final_dist[i] = agg_func(l)

    if not isinstance(fallback, type(None)):
        # See if any needs fixing
        inside = coll.contains(points)
        is_zero = final_dist == 0
        needs_fix = ~inside | is_zero

        if any(needs_fix):
            if isinstance(fallback, numbers.Number):
                final_dist[needs_fix] = fallback
            elif fallback == 'knn':
                final_dist[needs_fix] = get_radius_knn(points[needs_fix], mesh, aggregate=aggregate)

    return points, final_dist


def get_radius_point(point: np.ndarray, mesh, n_rays=20, aggregate='mean', projection='sphere', fallback='knn'):
    """
    Extract radii using ray casting.

    Parameters
    ----------
    point :      np.ndarray
                    A 3-element array describing a 3D point defining the polyline.
    mesh :          trimesh.Trimesh
    n_rays :        int
                    Number of rays to cast for each node.
    aggregate :     "mean" | "median" | "max" | "min" | "percentile75"
                    Function used to aggregate radii for over all intersections
                    for a given node.
    projection :    "sphere" | "tangents"
                    Whether to cast rays in a sphere around each node or in a
                    circle orthogonally to the node's tangent vector.
    fallback :      "knn" | None | number
                    If a point is outside or right on the surface of the mesh
                    the raycasting will return nonsense results. We can either
                    ignore those cases (``None``), assign an arbitrary number or
                    we can fall back to radii from k-nearest-neighbors (``knn``).

    :returns radius at point

    """
    agg_map = {'mean': np.mean, 'max': np.max, 'min': np.min,
               'median': np.median, 'percentile75': lambda x: np.percentile(x, 75), 'percentile99': lambda x: np.percentile(x, 99)}
    assert aggregate in agg_map
    agg_func = agg_map[aggregate]

    assert projection in ['sphere', 'tangents']
    assert (fallback == 'knn') or isinstance(fallback, numbers.Number) or isinstance(fallback, type(None))

    # Get max dimension of mesh
    dim = mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)
    radius = max(dim)

    # Vertices for each point on the circle
    sources = np.repeat(np.array([point]), n_rays, axis=0)

    if projection == 'sphere':
        targets = fibonacci_sphere(n_rays, randomize=True) * radius  # Uniform sphere points sphere scaled by radius
        targets = np.tile(targets, (1, 1))  # Reshape to match sources
        targets += sources # Offset onto sources
    else:
        tangents = polyline_tangents(np.array([point]))

        # Follow these steps:
        #  1. Create a unit disk of n_rays points along axes x and y
        #  2. Scale the unit disk by radius
        #  3. Duplicate the disk by the number of points to equal the length of sources: shape [len(points), n_rays, 3]
        #  4. Rotate the unit disk to align with the tangent vector
        #  5. Define a targets array by adding the rotated disk to the sources

        # Step 1
        zero_to_2pi = np.linspace(0, 2 * np.pi, n_rays, endpoint=False)
        disk = np.column_stack((np.cos(zero_to_2pi), np.sin(zero_to_2pi), np.zeros(n_rays)))

        # Step 2
        disk *= radius

        # Step 3
        disk = np.repeat(disk[np.newaxis, :, :], 1, axis=0)

        # Step 4
        for i, tangent in enumerate(tangents):
            disk[i] = rotate_points_to_normal(disk[i], tangent)

        # Step 5
        disk = disk.reshape(-1, 3)
        targets = sources + disk

    # Initialize ncollpyde Volume
    coll = ncollpyde.Volume(mesh.vertices, mesh.faces, validate=False)

    # Get intersections: `ix` points to index of line segment; `loc` is the
    #  x/y/z coordinate of the intersection and `is_backface` is True if
    # intersection happened at the inside of a mesh
    ix, loc, is_backface = coll.intersections(sources, targets)

    # Calculate intersection distances
    dist = np.sqrt(np.sum((sources[ix] - loc) ** 2, axis=1))

    # Map from `ix` back to index of original point
    org_ix = (ix / n_rays).astype(int)

    # Split by original index
    split_ix = np.where(org_ix[:-1] - org_ix[1:])[0]
    split = np.split(dist, split_ix)

    # Aggregate over each original ix
    final_dist = np.zeros(1)
    for l, i in zip(split, np.unique(org_ix)):
        final_dist[i] = agg_func(l)

    if not isinstance(fallback, type(None)):
        # See if any needs fixing
        inside = coll.contains(np.array([point]))
        is_zero = final_dist == 0
        needs_fix = ~inside | is_zero

        if any(needs_fix):
            if isinstance(fallback, numbers.Number):
                final_dist[needs_fix] = fallback
            elif fallback == 'knn':
                final_dist[needs_fix] = get_radius_knn(np.array([point]), mesh, aggregate=aggregate)

    return final_dist
