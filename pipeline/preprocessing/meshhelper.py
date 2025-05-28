import numpy as np
import skeletor as sk
import trimesh

from ORSModel.ors import ROI, FaceVertexMesh


def roi_to_mesh(roi: ROI):
    """
    Does all the preprocessing required to convert a Dragonfly ROI to a trimesh mesh with smoothing applied.
    :return: The Trimesh mesh
    """

    # progress = Progress()
    # progress.startWorkingProgressWithCaption("Converting to mesh", False)
    dragonfly_mesh = roi.getAsMarchingCubesMesh(
        isovalue=0.5,
        bSnapToContour=False,
        flipNormal=False,
        timeStep=0,
        xSample=10,  # For anisotropic datasets xSample and ySample are larger than zSample
        ySample=10,  # TODO: remove hard-coding
        zSample=2,
        pNearest=False,
        pWorld=True,
        IProgress=None,
        pMesh=None
    )

    if 0 in (dragonfly_mesh.getVertexCount(0), dragonfly_mesh.getEdgeCount(0)):
        # TODO: handle this edge case better
        return trimesh.Trimesh()

    # Smooth the mesh
    dragonfly_mesh.laplacianSmooth(2, 0, 0.3)

    # Convert to trimesh
    vertices = dragonfly_mesh.getVertices(0).getNDArray() * 1e9  # Convert from m to nm
    vertices = vertices.reshape(-1, 3)  # [[x1, y1, z1], [x2, y2, z2], ...]
    edges = dragonfly_mesh.getEdges(0).getNDArray()
    faces = edges.reshape(-1, 3)

    dragonfly_mesh.deleteObjectAndAllItsChildren()

    return trimesh.Trimesh(vertices=vertices, faces=faces)


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


def skeletonize_mesh(mesh: trimesh.Trimesh) -> sk.Skeleton:
    skel = sk.skeletonize.by_wavefront(mesh, origins=None, waves=1, step_size=1, radius_agg="percentile25")
    sk.post.remove_bristles(skel, los_only=False, inplace=True)
    sk.post.clean_up(skel, inplace=True, theta=1)
    sk.post.despike(skel, inplace=True)

    return skel

