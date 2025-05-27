from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from scipy.signal import find_peaks
from sklearn.linear_model import Ridge
import numpy as np

from . import geometry as geom
from . import skel_helper


def smooth(x, y, x_points: np.ndarray | int | None = None, degree=15, alpha=0.01) -> tuple[np.ndarray, np.ndarray]:
    """
    Smooth the data using a polynomial regression.

    :param x: The x-coordinates of the data points.
    :param y: The y-coordinates of the data points.
    :param x_points: The x-coordinates of the points to evaluate the polynomial at. If None, use the original
                    x-coordinates. If an integer, create that many points between the min and max of x. If a np.ndarray,
                    use that as the x-coordinates.
    :param degree: The degree of the polynomial to fit.
    :param alpha: The regularization parameter for Ridge regression.
    :return: A tuple of (x_points, y_points) where y_points are the smoothed y-coordinates.
    """

    ridge_poly = make_pipeline(PolynomialFeatures(degree), StandardScaler(), Ridge(alpha=alpha))

    if x_points is None:
        x_points = x
    elif isinstance(x_points, int):
        x_points = np.linspace(x[0], x[-1], x_points)
    elif not isinstance(x_points, np.ndarray):
        raise ValueError(f"x_points must be None, an integer, or a numpy array, not {type(x_points)}")

    ridge_poly.fit(x.reshape(-1, 1), y)

    smoothed_y = ridge_poly.predict(x_points.reshape(-1, 1))

    return x_points, smoothed_y


def rightmost_local_max_idx(y_values: np.ndarray) -> int:
    """
    Finds the index of the rightmost local maximum. Used for finding the center of the dendritic spine head.

    :param y_values: The y-values of the signal.
    :return: The index of the rightmost local maximum.
    """

    local_maxima, _ = find_peaks(y_values, distance=10)
    local_maxima = sorted(local_maxima, reverse=True)

    if len(local_maxima) == 0:
        return -1

    return local_maxima[0]


def find_neck_point_from_head_radius(polyline: np.ndarray, dendrite_mesh, cumulative_len: np.ndarray, radii_tangents) -> float:
    smoothed_x, smoothed_y = smooth(cumulative_len, radii_tangents[1:], degree=15, alpha=0.001, x_points=600)

    # Find the local max (center point of the head) then subtract by the radius to get the start of the neck
    head_center_idx = rightmost_local_max_idx(smoothed_y)
    head_point_1d = smoothed_x[head_center_idx]

    head_point_3d, _ = geom.point_and_tangent_along_polyline(polyline, head_point_1d)

    # head_radius_spheres should be the radii_spheres radius at distance head_point_1d
    head_radius_spheres = skel_helper.get_radius_point(head_point_3d, dendrite_mesh, n_rays=500, aggregate="percentile99", projection="sphere")[0]

    neck_point = head_point_1d - head_radius_spheres * 1.25

    return cumulative_len[-1] - neck_point
