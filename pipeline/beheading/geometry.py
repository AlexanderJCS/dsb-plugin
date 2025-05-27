import numpy as np


def lerp(a, b, t):
    return a + t * (b - a)


def normalize(vec: np.ndarray):
    return vec / np.linalg.norm(vec)


def point_and_tangent_along_polyline(polyline, dist_along_skel) -> tuple[np.ndarray, np.ndarray]:
    """
    Finds the point along a polyline that is n distance from the start. Linearly interpolates the points.

    :param polyline: The polyline
    :param dist_along_skel: The distance from the start
    :return: (the 3D point, the normal)
    """

    accumulated_dist = 0
    for point, last_point in zip(polyline[1:], polyline[:-1]):
        dist = np.linalg.norm(point - last_point)
        accumulated_dist += dist

        if accumulated_dist < dist_along_skel:
            continue

        last_accumulated_dist = accumulated_dist - dist
        additional_dist = dist_along_skel - last_accumulated_dist
        percent_interpolate = additional_dist / dist

        return lerp(last_point, point, percent_interpolate), normalize(point - last_point)

    return polyline[-1], normalize(polyline[-1] - polyline[-2])


def accumulate(polyline: np.ndarray) -> np.ndarray:
    segment_lengths = np.linalg.norm(polyline[1:] - polyline[:-1], axis=1)
    return np.cumsum(segment_lengths)
