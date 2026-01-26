import os

from OrsPythonPlugins.OrsSurfaceDetermination import OrsSurfaceDetermination

from ORSModel import orsObj
from ORSModel.ors import Channel, ROI
from ORSServiceClass.system.pathServices import OrsPath

import math


def getIsoValueFromLineEdit(channel, threshold):
    model = channel
    if model is None:
        return 0
    isovalue = threshold

    # we need to convert the isovalue to physical
    isovaluePhysical = model.getValueConvertedFromPhysicalUnits(isovalue) if isinstance(model, Channel) else isovalue
    return isovaluePhysical


def compute_initial_mesh(impl: OrsSurfaceDetermination, model: Channel, samplingX: int, samplingY: int, samplingZ: int, mask: ROI, line_edit_isovalue: float, smoothing: bool):
    if samplingX < 1 or samplingY < 1 or samplingZ < 1:
        print("Sampling must be at least 1")
        return

    # Remove holes in mask because it will create voids that will mess up skeletonization
    mask_copy = mask.copy()
    mask_copy.fillInnerHoles(0, False)

    # Also exclude voids from the channel data
    excludeVoids = True

    inputChannel = model
    # check if we need to denoise the data
    needDenoising = False  # TODO: tune this
    if needDenoising:
        print('Denoising dataset...')
        tempChannel = Channel()
        tempChannel.setIsRepresentable(False)
        tempChannel.setTitle(inputChannel.getTitle())
        filterName = 'filter_bilateral2D.comp'
        args = {'sigmaColor': 8.0, 'sigmaSpatial': 8.0}

        path = OrsPath.getApplicationRoot()
        fullpath = os.path.join(path, 'modules', 'gpgpu', filterName)
        model.executeGPGPUCommand(tempChannel, fullpath, 1, 1, args, 3)
        inputChannel = orsObj(tempChannel.getGUID())

    # start the actual job
    print('Initializing surface...')

    # are we using a ROI mask ? must be checked and a valid ROI must be selected
    isovalue = 60.0  # this is a magic number from Dragonfly's source code. I dare not touch it.
    contourMesh = impl.generateContourMeshFromAROI(mask_copy, isovalue,
                                                   samplingX,
                                                   samplingY, samplingZ)
    if contourMesh is not None:
        contourMesh.setTitle("DSB Surface Mesh")

    # do we want to exclude the voids when working directly on the channel
    elif excludeVoids:
        # get the roi using the threshold value
        minValue = getIsoValueFromLineEdit(inputChannel, 100)
        maxValue = inputChannel.getMaximumValue()
        print(f'ROI to exclude void range : {minValue} {maxValue}')
        aROI = inputChannel.getAsROIWithinRange(minValue, maxValue, None, None)

        # fill inner areas
        if aROI is not None:
            print(f'fillInnerHoles')
            aROI.fillInnerHoles(0, False)

            # generate the contour
            isovalue = 60.0
            print(f'initializing surface with isovalue of: {isovalue} {samplingX} {samplingY} {samplingZ}')
            contourMesh = impl.generateContourMeshFromAROI(aROI, isovalue,
                                                           samplingX,
                                                           samplingY, samplingZ)
            aROI.deleteObject()
            if contourMesh is not None:
                contourMesh.setTitle("Surface Mesh ({})".format(inputChannel.getTitle()))

    else:
        # note: if we denoise the channel, it might be a good idea to use the otsu value for the denoised channel
        # instead of the original otsu value
        use_otsu = True
        if needDenoising and use_otsu:
            isovalue = model.getOtsu()
            print(
                f'initializing surface (dont exlcude voids) with denoised isovalue of: {isovalue} {samplingX} {samplingY} {samplingZ}')
        else:
            isovalue = line_edit_isovalue
            print(
                f'initializing surface (dont exlcude voids) with isovalue of: {isovalue} {samplingX} {samplingY} {samplingZ}')

        contourMesh = impl.generateALinearContourMeshFromAChannel(inputChannel, isovalue,
                                                                  samplingX,
                                                                  samplingY, samplingZ)
    if contourMesh is not None:
        if smoothing:
            print("Smoothing")
            contourMesh.laplacianSmooth(1, 0, 0.9)
        contourMesh.setIsRepresentable(False)

    # Free mask copy
    mask_copy.deleteObject()

    return contourMesh


def refine_mesh(impl: OrsSurfaceDetermination, mesh, model):

    # snap to the gradient according to the search distance
    # searchDistance = self.ui.inputSearchDistance.value()
    searchDistance = 8
    searchDistance *= model.getXSpacing()

    # falloffFactor = self.ui.inputFalloffFactor.value()
    falloffFactor = 0.5
    # relaxation = self.ui.inputRelaxation.value()
    relaxation = 1.0
    mergeVertices = True
    invertSearch = False

    iteration = math.ceil(1.0 / relaxation)
    # autoAdjustFalloff = self.ui.cboAutoAdjustFalloff.isChecked()
    autoAdjustFalloff = True
    smoothIteration = 2.0  # 2.0 for smoothing (don't preserve details), 0.0 for no smoothing
    smoothingRelaxationFactor = 1.0
    # log.info(f"about to snap for {iteration} iterations")

    impl.snapMeshToGradient(mesh, model, searchDistance, relaxation, iteration,
                                                smoothIteration, smoothingRelaxationFactor, falloffFactor,
                                                mergeVertices, autoAdjustFalloff, invertSearch)

    return mesh


def compute_mesh(model: Channel, samplingX: int, samplingY: int, samplingZ: int, mask: ROI, line_edit_isovalue: float, smoothing: bool):
    impl = OrsSurfaceDetermination()

    mesh = compute_initial_mesh(impl, model, samplingX, samplingY, samplingZ, mask, line_edit_isovalue, smoothing)

    # snap to gradient
    if mesh is not None:
        refine_mesh(impl, mesh, model)

        # remesh the surface is necessary
        # if self.ui.cbRemesh.isChecked():
        #     self.processRemeshedSurface()
        #     remeshLevel = self.ui.cbRemeshLevel.currentIndex()
        #     SavedState.setStringStateData("LastSurfaceDeterminationRemeshLevel", str(remeshLevel))

    return mesh
