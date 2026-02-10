import numpy as np
import skeletor as sk
import trimesh

from ORSModel.ors import FaceVertexMesh, Annotation, ROI, MultiROI
import ORSModel


def get_points_from_annotation(ann: Annotation):
    points = []
    for i in range(ann.getControlPointCount(0)):
        pos = ann.getControlPointPositionAtIndex(i, 0, None)
        points.append(np.array([pos.getX(), pos.getY(), pos.getZ()], dtype=np.float64) * 1e9)  # m -> nm

    return points


def get_labels_from_annotation(ann: Annotation):
    labels = []
    for i in range(ann.getControlPointCount(0)):
        labels.append(ann.getControlPointCaptionAtIndex(i, 0))

    return labels


def get_point_label_pairs_from_annotation(ann: Annotation):
    labels = get_labels_from_annotation(ann)
    points = get_points_from_annotation(ann)

    return list(zip(points, labels))


def get_multiroi_names(multiroi: MultiROI) -> list[str]:
    return [multiroi.getLabelName(label) for label in range(1, multiroi.getLabelCount() + 1)]


def get_multiroi_locations(multiroi: MultiROI) -> list[np.ndarray]:
    locations = []
    for label in range(1, multiroi.getLabelCount() + 1):
        # Copy the ROI
        copy_roi: ORSModel.ors.ROI = ORSModel.ors.ROI()
        copy_roi.copyShapeFromStructuredGrid(multiroi)
        multiroi.addToVolumeROI(copy_roi, label)

        # Get the center of mass
        center = copy_roi.getCenterOfMass(0)
        locations.append(np.array([center.getX(), center.getY(), center.getZ()], dtype=np.float64) * 1e9)  # m -> nm

        # Clean up
        copy_roi.deleteObjectAndAllItsChildren()

    return locations


def get_point_name_pairs_from_multiroi(multiroi: MultiROI) -> list[tuple[np.ndarray, str]]:
    names = get_multiroi_names(multiroi)
    locations = get_multiroi_locations(multiroi)

    return list(zip(locations, names))


def ors_to_trimesh(ors_mesh: FaceVertexMesh) -> trimesh.Trimesh:
    """
    Converts a Dragonfly ORS mesh to a trimesh mesh.
    :param ors_mesh: The ORS mesh to convert
    :return: The trimesh mesh
    """
    vertices = ors_mesh.getVertices(0).getNDArray().reshape(-1, 3) * 1e9  # Convert from m to nm
    edges = ors_mesh.getEdges(0).getNDArray().reshape(-1, 3)

    return trimesh.Trimesh(vertices=vertices, faces=edges)


def roi_to_cubic_mesh(roi: ROI):
    dragonfly_mesh = roi.getAsCubicMesh(True, None, None)
    mesh = ors_to_trimesh(dragonfly_mesh)
    dragonfly_mesh.deleteObjectAndAllItsChildren()

    return mesh


def multiroi_to_mesh(multiroi: ORSModel.ors.MultiROI) -> trimesh.Trimesh:
    """
    Converts a Dragonfly MultiROI to a trimesh mesh.
    :param multiroi: The MultiROI to convert
    :return: The trimesh mesh
    """

    meshes = []

    for label in range(1, multiroi.getLabelCount() + 1):
        copy_roi: ORSModel.ors.ROI = ORSModel.ors.ROI()
        copy_roi.copyShapeFromStructuredGrid(multiroi)
        multiroi.addToVolumeROI(copy_roi, label)

        meshes.append(roi_to_cubic_mesh(copy_roi))

        copy_roi.deleteObjectAndAllItsChildren()

    return trimesh.util.concatenate(meshes, trimesh.Trimesh())


def mesh_to_ors(mesh: trimesh.Trimesh) -> FaceVertexMesh:
    """
    Converts a processing.mesh.Mesh object to a Dragonfly ORS mesh. Used for displaying the final mesh to the user.
    Precondition: The mesh is not none

    :param mesh: The mesh to convert
    :return: The Dragonfly ORS mesh
    """

    np_vertices = np.asarray(mesh.vertices, dtype=np.float64).flatten()
    np_indices = np.asarray(mesh.faces).flatten()

    # divide vertices by 1e9 to get meters instead of nanometers
    np_vertices = np_vertices / 1e9

    ors_mesh = FaceVertexMesh()
    ors_mesh.setTSize(1)  # set the time dimension

    ors_mesh_vertices = ors_mesh.getVertices(0)
    ors_mesh_vertices.setSize(len(np_vertices))

    for i in range(len(np_vertices)):
        ors_mesh_vertices.atPut(i, np_vertices[i])

    ors_indices = ors_mesh.getEdges(0)
    ors_indices.setSize(len(np_indices))

    for i in range(len(np_indices)):
        ors_indices.atPut(i, np_indices[i])

    return ors_mesh


def vector3_to_np(vector3: ORSModel.Vector3) -> np.array:
    return np.array([vector3.getX(), vector3.getY(), vector3.getZ()], dtype=np.float64)


def annotations_to_list(annotations: ORSModel.Annotation) -> list[tuple[np.array, str]]:
    control_points = annotations.getControlPointCount(0)

    output = []
    for i in range(control_points):
        output.append((
            vector3_to_np(annotations.getControlPointPositionAtIndex(i, 0, None)) * 1e9,
            annotations.getControlPointCaptionAtIndex(i, 0)
        ))

    return output


def skeletonize_mesh(mesh: trimesh.Trimesh) -> sk.Skeleton:
    skel = sk.skeletonize.by_wavefront(mesh, origins=None, waves=1, step_size=1)
    sk.post.remove_bristles(skel, los_only=False, inplace=True)
    sk.post.clean_up(skel, inplace=True, theta=1)
    sk.post.despike(skel, inplace=True)

    return skel

