import hashlib
import numpy as np


def hash_to_color(n) -> tuple[float, float, float]:
    hash_bytes = hashlib.md5(str(n).encode()).digest()

    r = (hash_bytes[0] % 128) / 255
    g = (hash_bytes[1] % 128) / 255
    b = (hash_bytes[2] % 128) / 255

    return r, g, b


def lerp(a, b, t):
    return a + t * (b - a)


def normalize(vec: np.ndarray):
    return vec / np.linalg.norm(vec)