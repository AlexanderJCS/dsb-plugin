import pickle
from dataclasses import dataclass

import zipfile
import io

import numpy as np
import trimesh



@dataclass(frozen=True)
class Payload:
    dendrite_mesh: trimesh.Trimesh
    head_centers: np.ndarray


def pld_save(pld: Payload, filepath: str) -> None:
    """
    Save the payload to a file.
    :param pld: The payload to save
    :param filepath: The path to save the payload to
    """

    stl_bytes = pld.dendrite_mesh.export(file_type="stl")
    head_centers_bytes = pickle.dumps(pld.head_centers)

    with zipfile.ZipFile(filepath, "w") as zf:
        zf.writestr("mesh.stl", stl_bytes)
        zf.writestr("head_centers.pickle", head_centers_bytes)


def pld_load(filepath: str) -> Payload:
    """
    Load the payload from a file.
    :param filepath: The path to load the payload from
    :return: The loaded payload
    """

    with zipfile.ZipFile(filepath, "r") as zf:
        mesh_bytes = zf.read("mesh.stl")
        head_centers_bytes = zf.read("head_centers.pickle")

    dendrite_mesh = trimesh.load(io.BytesIO(mesh_bytes), force="mesh", file_type="stl")
    head_centers = pickle.loads(head_centers_bytes)

    return Payload(dendrite_mesh=dendrite_mesh, head_centers=head_centers)
