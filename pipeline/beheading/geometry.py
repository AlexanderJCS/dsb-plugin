import numpy as np


def lerp(a, b, t):
    return a + t * (b - a)


def normalize(vec: np.ndarray):
    return vec / np.linalg.norm(vec, axis=-1, keepdims=True)


def compute_polyline_vertex_tangents(vertices: np.ndarray) -> np.ndarray:
    """
    Computes the tangents for each vertex in a polyline.

    :param vertices: The vertices of the polyline (shape: [N, 3])
    :return: Tangents for each vertex (shape: [N, 3])
    """

    tangents = np.empty_like(vertices, dtype=np.float64)
    tangents[1:-1] = normalize(vertices[2:] - vertices[:-2])
    tangents[0] = normalize(vertices[1] - vertices[0])
    tangents[-1] = normalize(vertices[-1] - vertices[-2])

    return tangents



def accumulate(polyline: np.ndarray) -> np.ndarray:
    segment_lengths = np.linalg.norm(polyline[1:] - polyline[:-1], axis=1)
    return np.cumsum(segment_lengths)


def point_and_tangent_along_polyline(polyline, dist_along_skel) -> tuple[np.ndarray, np.ndarray]:
    tangents = compute_polyline_vertex_tangents(polyline)
    cumulative = np.concatenate([[0], accumulate(polyline)])

    index = np.searchsorted(cumulative, dist_along_skel, side="right")
    index = np.clip(index, 1, len(polyline) - 1)

    prev_tangent = tangents[index - 1]
    prev_vert = polyline[index - 1]
    prev_cumulative = cumulative[index - 1]
    this_tangent = tangents[index]
    this_vert = polyline[index]
    this_cumulative = cumulative[index]

    overshot_by = dist_along_skel - prev_cumulative
    percent_interpolate = overshot_by / (this_cumulative - prev_cumulative)

    return lerp(prev_vert, this_vert, percent_interpolate), lerp(prev_tangent, this_tangent, percent_interpolate)
