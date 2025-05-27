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

    # TODO: verify this implementation of tangent interpolation is correct

    accumulated_dist = 0
    for i, point in enumerate(polyline):
        if i < 2 or i == len(polyline) - 1:
            continue

        last_point = polyline[i - 1]
        last_last_point = polyline[i - 2]
        next_point = polyline[i + 1]

        dist = np.linalg.norm(point - last_point)
        accumulated_dist += dist

        if accumulated_dist < dist_along_skel:
            continue

        last_accumulated_dist = accumulated_dist - dist
        additional_dist = dist_along_skel - last_accumulated_dist
        percent_interpolate = additional_dist / dist

        last_point_tangent = point - last_last_point
        this_point_tangent = next_point - last_point

        return lerp(last_point, point, percent_interpolate), lerp(normalize(last_point_tangent), normalize(this_point_tangent), percent_interpolate)

    return polyline[-1], normalize(polyline[-1] - polyline[-2])


def accumulate(polyline: np.ndarray) -> np.ndarray:
    segment_lengths = np.linalg.norm(polyline[1:] - polyline[:-1], axis=1)
    return np.cumsum(segment_lengths)
