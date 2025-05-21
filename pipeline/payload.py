import pickle
from dataclasses import dataclass

import zipfile
import io

import skeletor as sk
import trimesh


@dataclass(frozen=True)
class Payload:
    dendrite_mesh: trimesh.Trimesh
    skeleton: sk.Skeleton


def save(pld: Payload, filepath: str) -> None:
    """
    Save the payload to a file.
    :param pld: The payload to save
    :param filepath: The path to save the payload to
    """

    stl_bytes = pld.dendrite_mesh.export(file_type="stl")
    skeleton_bytes = pickle.dumps(pld.skeleton)

    with zipfile.ZipFile(filepath, "w") as zf:
        zf.writestr("mesh.stl", stl_bytes)
        zf.writestr("skeleton.pickle", skeleton_bytes)


def load(filepath: str) -> Payload:
    """
    Load the payload from a file.
    :param filepath: The path to load the payload from
    :return: The loaded payload
    """

    with zipfile.ZipFile(filepath, "r") as zf:
        mesh_bytes = zf.read("mesh.stl")
        skel_bytes = zf.read("skeleton.pickle")

    dendrite_mesh = trimesh.load(io.BytesIO(mesh_bytes), force="mesh", file_type="stl")
    spine_skeletons = pickle.loads(skel_bytes)

    return Payload(dendrite_mesh=dendrite_mesh, skeleton=spine_skeletons)
