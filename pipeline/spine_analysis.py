from typing import Optional

from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, RobustScaler
from scipy.signal import find_peaks
from sklearn.linear_model import Ridge
from scipy.signal import butter, filtfilt
import numpy as np

from . import geometry as geom


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

    ridge_poly = make_pipeline(PolynomialFeatures(degree), RobustScaler(), Ridge(alpha=alpha))

    if x_points is None:
        x_points = x
    elif isinstance(x_points, int):
        x_points = np.linspace(x[0], x[-1], x_points)
    elif not isinstance(x_points, np.ndarray):
        raise ValueError(f"x_points must be None, an integer, or a numpy array, not {type(x_points)}")

    ridge_poly.fit(x.reshape(-1, 1), y)

    smoothed_y = ridge_poly.predict(x_points.reshape(-1, 1))

    return x_points, smoothed_y


def lowpass_filter(x, y, cutoff, order=3):
    """
    Apply a zero-phase Butterworth low-pass filter to 1D data.

    Parameters
    ----------
    x : array-like, shape (n,)
        Independent variable (must be strictly increasing).
    y : array-like, shape (n,)
        Dependent variable to be smoothed.
    cutoff : float
        Cutoff frequency in the same units as 1/(x[1] – x[0]).
        (e.g. if x is time in seconds, cutoff is in Hz)
    order : int, optional
        Order of the Butterworth filter.  Default is 3.

    Returns
    -------
    y_filtered : ndarray, shape (n,)
        The smoothed data.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size:
        raise ValueError("x and y must be 1D arrays of the same length")

    # estimate sampling frequency
    dx = np.diff(x)
    if not np.all(dx > 0):
        raise ValueError("x must be strictly increasing")
    fs = 1.0 / np.mean(dx)  # samples per unit in x
    nyq = 0.5 * fs  # Nyquist frequency

    # normalized cutoff
    wn = cutoff / nyq
    if not 0 < wn < 1:
        raise ValueError("cutoff must be between 0 and Nyquist (fs/2)")

    # design Butterworth filter
    b, a = butter(order, wn, btype='low', analog=False)
    # apply zero‑phase filtering
    y_filtered = filtfilt(b, a, y)
    return x, y_filtered


def spine_head_center_idx(x_values: np.ndarray, y_values: np.ndarray) -> int | None:
    """
    :param x_values: The x-coordinates of the data points.
    :param y_values: The y-coordinates of the data points.
    :return: The index of the rightmost local maximum.
    """

    local_maxima, _ = find_peaks(y_values, distance=10)

    maxima_x = x_values[local_maxima]
    maxima_y = y_values[local_maxima]

    mask = maxima_x > x_values[-1] * 0.5
    maxima_y = maxima_y[mask]
    local_maxima = local_maxima[mask]

    if len(maxima_y) > 0:
        return local_maxima[np.argmax(maxima_y)]

    return None


def find_head_point(polyline: np.ndarray, cumulative_len: np.ndarray, radii_tangents, smoothness: float = 0.004, filename: Optional[str] = None) -> tuple[float, np.ndarray]:
    """
    Finds the head radius of the dendritic spine.

    :param polyline: The polyline describing the dendritic spine.
    :param cumulative_len: The cumulative length of the dendrite.
    :param radii_tangents: The radii of the dendritic spine.
    :param smoothness: The parameter to smooth the data to.
    :param filename: The filename to save the results raw, smoothed data to. Used for spine classification. None if not saved.
    """

    # smoothed_x, smoothed_y = smooth(cumulative_len, radii_tangents[1:], degree=12, alpha=0.0001, x_points=600)
    smoothed_x, smoothed_y = lowpass_filter(cumulative_len, radii_tangents[1:], cutoff=smoothness)

    if filename is not None:
        np.savez_compressed(filename, arr=np.array([smoothed_x, smoothed_y]))

    # Find the local max (center point of the head) then subtract by the radius to get the start of the neck
    head_center_idx = spine_head_center_idx(smoothed_x, smoothed_y)
    if head_center_idx is None:  # Fallback to a less smoothed version
        less_smoothed_x, less_smoothed_y = lowpass_filter(cumulative_len, radii_tangents[1:], cutoff=smoothness + 0.001)
        head_center_idx = spine_head_center_idx(less_smoothed_x, less_smoothed_y)

    if head_center_idx is None:  # Fallback to an unsmoothed version
        head_center_idx = spine_head_center_idx(cumulative_len, radii_tangents[1:])

    if head_center_idx is None:  # Fallback again to the last point
        head_center_idx = len(cumulative_len) - 1

    head_point_1d = smoothed_x[head_center_idx]

    head_point_3d, _ = geom.point_and_tangent_along_polyline(polyline, head_point_1d)

    # plt.plot(cumulative_len, radii_tangents[1:], label="Unsmoothed Radii", linestyle="--", color="gray")
    # plt.plot(smoothed_x, smoothed_y, label="Smoothed Radii", color="blue")
    # plt.axvline(x=head_point_1d, color="k", linestyle="--", label="Head Center")
    # plt.legend()
    # plt.xlabel("Cumulative Length (nm)")
    # plt.ylabel("Radius (nm)")
    # plt.savefig("graph.png", dpi=300, bbox_inches="tight")
    # plt.show()

    # head_radius_spheres should be the radii_spheres radius at distance head_point_1d
    return head_point_3d
