import os

from OrsPythonPlugins.OrsSurfaceDetermination import OrsSurfaceDetermination

from ORSModel import orsObj
from ORSModel.ors import Channel, ROI
from ORSServiceClass.system.pathServices import OrsPath


def compute_mesh(model: Channel, samplingX: int, samplingY: int, samplingZ: int, mask: ROI, line_edit_isovalue: float, smoothing: bool):
    impl = OrsSurfaceDetermination()

    if samplingX < 1 or samplingY < 1 or samplingZ < 1:
        print("Sampling must be at least 1")
        return

    excludeVoids = True  # TODO: tune this

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
    isovalue = 60.0  # todo: tune this
    contourMesh = impl.generateContourMeshFromAROI(mask, isovalue,
                                                                       samplingX,
                                                                       samplingY, samplingZ)
    if contourMesh is not None:
        contourMesh.setTitle("DSB Surface Mesh")

    # do we want to exclude the voids when working directly on the channel
    elif excludeVoids:
        # get the roi using the threshold value
        minValue = model.getValueConvertedFromPhysicalUnits(line_edit_isovalue)
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
            print(f'initializing surface (dont exlcude voids) with denoised isovalue of: {isovalue} {samplingX} {samplingY} {samplingZ}')
        else:
            isovalue = line_edit_isovalue
            print(f'initializing surface (dont exlcude voids) with isovalue of: {isovalue} {samplingX} {samplingY} {samplingZ}')

        contourMesh = impl.generateALinearContourMeshFromAChannel(inputChannel, isovalue,
                                                                                      samplingX,
                                                                                      samplingY, samplingZ)
    if contourMesh is not None:
        if smoothing:
            print("Smoothing")
            contourMesh.laplacianSmooth(1, 0, 0.9)
        contourMesh.setIsRepresentable(False)
        # self.initialMeshGUID = contourMesh.getGUID()
    # self.updateStatus('')
    # self.initialMeshDirty = False

    return contourMesh