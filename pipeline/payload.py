import pickle
from dataclasses import dataclass

import zipfile
import io

import numpy as np
import skeletor as sk
import trimesh

from typing import Optional


@dataclass(frozen=True)
class Payload:
    dendrite_mesh: trimesh.Trimesh
    skeleton: sk.Skeleton
    annotations: list[tuple[np.ndarray, str]] | None
    psds: Optional[trimesh.Trimesh | None]


def save(pld: Payload, filepath: str) -> None:
    """
    Save the payload to a file.
    :param pld: The payload to save
    :param filepath: The path to save the payload to
    """

    stl_bytes = pld.dendrite_mesh.export(file_type="stl")
    skeleton_bytes = pickle.dumps(pld.skeleton)
    annotations_bytes = pickle.dumps(pld.annotations)
    psds_stl_bytes = pld.psds.export(file_type="stl") if pld.psds is not None else b""

    with zipfile.ZipFile(filepath, "w") as zf:
        zf.writestr("mesh.stl", stl_bytes)
        zf.writestr("skeleton.pickle", skeleton_bytes)
        zf.writestr("annotations.pickle", annotations_bytes)
        zf.writestr("psds.stl", psds_stl_bytes)


def load(filepath: str) -> Payload:
    """
    Load the payload from a file.
    :param filepath: The path to load the payload from
    :return: The loaded payload
    """

    with zipfile.ZipFile(filepath, "r") as zf:
        mesh_bytes = zf.read("mesh.stl")
        skel_bytes = zf.read("skeleton.pickle")
        annotations_bytes = zf.read("annotations.pickle")
        psds_bytes = zf.read("psds.stl")

    dendrite_mesh = trimesh.load(io.BytesIO(mesh_bytes), force="mesh", file_type="stl")
    spine_skeletons = pickle.loads(skel_bytes)
    annotations = pickle.loads(annotations_bytes)
    psds = trimesh.load(io.BytesIO(psds_bytes), force="mesh", file_type="stl") if psds_bytes else None

    return Payload(dendrite_mesh=dendrite_mesh,
                   skeleton=spine_skeletons,
                   annotations=annotations,
                   psds=psds)
