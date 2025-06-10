import pickle
from dataclasses import dataclass

import zipfile
import io
import os

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


def pld_save(pld: Payload, filepath: str) -> None:
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


def pld_load(filepath: str) -> Payload:
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


def csv_save(filepath: str, head_name: str, head_idx: int, head_vol: float, beheading_point: np.ndarray, centroid: np.ndarray) -> bool:
    """
    Save the head information to a CSV file.
    :param filepath: The path to save the CSV file to
    :param head_name: The head name of the dendritic spine head
    :param head_idx: The index of the dendritic spine head
    :param head_vol: The volume of the dendritic spine head in μm³
    :param beheading_point: The beheading point of the dendritic spine head in nm
    :param centroid: The centroid of the dendritic spine head in nm
    :return: True if saved successfully, False otherwise
    """

    try:
        # First check if the file exists, and if it doesn't, create it with the appropriate header
        if not os.path.isfile(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8-sig") as f:
                f.write("Head Index,Head Name,Head Volume (μm³),Beheading Point X (nm),Beheading Point Y (nm),Beheading Point Z (nm),Head Centroid X (nm),Head Centroid Y (nm),Head Centroid Z (nm)\n")

        # Now append the new head information to the CSV file
        with open(filepath, "a", encoding="utf-8-sig") as f:
            f.write(f"{head_idx},\"{head_name}\",{head_vol},{beheading_point[0]},{beheading_point[1]},{beheading_point[2]},{centroid[0]},{centroid[1]},{centroid[2]}\n")
    except (FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError, OSError):
        return False

    return True
