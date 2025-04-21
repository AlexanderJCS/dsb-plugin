import trimesh
from ORSModel.ors import ROI, Progress


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

    # Smooth the mesh
    dragonfly_mesh.laplacianSmooth(2, 0, 0.3)

    # Convert to trimesh
    vertices = dragonfly_mesh.getVertices(0).getNDArray() * 1e9  # Convert from m to nm
    vertices = vertices.reshape(-1, 3)  # [[x1, y1, z1], [x2, y2, z2], ...]
    edges = dragonfly_mesh.getEdges(0).getNDArray()
    faces = edges.reshape(-1, 3)

    dragonfly_mesh.deleteObjectAndAllItsChildren()

    return trimesh.Trimesh(vertices=vertices, faces=faces)
