import operator
import maya.api.OpenMaya as OpenMaya

import maya.api.OpenMayaUI as OpenMayaUI
import maya.api.OpenMayaRender as OpenMayaRender

import pymel.core as pm

# -- We're using Maya Python API 2.0, so we have to flag this plugin
maya_useNewAPI = True


# ------------------------------------------------------------------------------
def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass


# ------------------------------------------------------------------------------
class CenterOfMassNode(OpenMayaUI.MPxLocatorNode):
    """
    This node allows you to see/visualise the center of mass of a skeleton
    or group of objects. Each entry can take in multiple points to define
    the bounds of the entry (such as two bones for a bone length) along with
    a mass value in order to give different areas of the skeleton different
    weights/influences of the mass.
    """
    # -- Define the compound attribute which collates
    # -- all our inputs
    aCompound = OpenMaya.MObject()

    # -- Settings attributes
    aCalculate = OpenMaya.MObject()
    aDrawSphere = OpenMaya.MObject()
    aDrawVerticalLine = OpenMaya.MObject()
    aDrawDebugLines = OpenMaya.MObject()
    aSphereSize = OpenMaya.MObject()

    # -- Define our indiviual input attributes
    aConsiderInCalculation = OpenMaya.MObject()
    aPointsOfBounds = OpenMaya.MObject()
    aMass = OpenMaya.MObject()
    aIdentfier = OpenMaya.MObject()
    aSectionIdentifier = OpenMaya.MObject()

    # -- This is our final output attribute
    aCenterOfMass = OpenMaya.MObject()
    aTranslateX = OpenMaya.MObject()
    aTranslateY = OpenMaya.MObject()
    aTranslateZ = OpenMaya.MObject()

    # -- Static class variables which will never change
    TypeName = "CenterOfMass"
    NodeId = OpenMaya.MTypeId(0x00132601)
    drawDbClassification = "drawdb/geometry/CenterOfMassNode"
    drawRegistrantId = "CenterOfMassNodePlugin"

    # --------------------------------------------------------------------------
    def __init__(self):
        super(CenterOfMassNode, self).__init__()
        # OpenMaya.MPxNode.__init__(self)

    # --------------------------------------------------------------------------
    def compute(self, plug, data):
        """
        Called whenever a dirty plug requests evaluation.

        :param plug: MPlug
        :param data: MDataBlock

        :return: MStatus
        """
        # -- If we're not an output plug we do not need to compute
        # -- anything
        # if plug not in output_plugs:
        #     return

        if plug == CenterOfMassNode.aTranslateX or plug == CenterOfMassNode.aTranslateY or plug == CenterOfMassNode.aTranslateZ or plug == CenterOfMassNode.aCenterOfMass:

            calculate = data.inputValue(CenterOfMassNode.aCalculate).asBool()

            # -- If we're told not to calculate, then skip any more work
            if not calculate:
                data.setClean(CenterOfMassNode.aTranslateX)
                data.setClean(CenterOfMassNode.aTranslateY)
                data.setClean(CenterOfMassNode.aTranslateZ)
                return

            # -- We need to read the inputs of the node so we can collate and
            # -- organise
            array_handler = data.inputArrayValue(CenterOfMassNode.aCompound)
            item_count = len(array_handler)

            # -- Collect all the data which we will get during the iteration
            # -- of the inputs. These we will later use to determine the
            # -- center point
            collated_data = list()

            # -- Cycle each input block and collate
            for i in range(0, item_count):

                # -- Jump to the next item in the list of inputs
                try:
                    array_handler.jumpToPhysicalElement(i)
                except: continue

                # -- The compound hander gives us access to the sub-attributes
                # -- such as the mass etc.
                compound_handler = array_handler.inputValue()

                # -- Get the first variables which we can filter our
                # -- calculations down by
                mass_handle = compound_handler.child(CenterOfMassNode.aMass)
                weighting = mass_handle.asFloat()
                consider_in_calculation = compound_handler.child(CenterOfMassNode.aConsiderInCalculation).asBool()

                # -- If the weighting is zero then we do not need to
                # -- include it
                if weighting == 0.0 or not consider_in_calculation:
                    continue

                # -- Now we need to get all the points and determine the
                # -- center point
                bounds_handler = OpenMaya.MArrayDataHandle(compound_handler.child(CenterOfMassNode.aPointsOfBounds))
                bounds_count = len(bounds_handler)

                # -- Collate a list of all the positions of the bound
                # -- items
                positions = list()

                # -- Cycle each bounds object coming into this input
                for j in range(0, bounds_count):
                    # -- Get the matrix input
                    bounds_handler.jumpToPhysicalElement(j)
                    matrix = bounds_handler.inputValue().asMatrix()

                    # -- Extract the position only from the matrix
                    positions.append([n for n in matrix][12:15])

                # -- Calculate the center from all the given positions and
                # -- store it along with the mass value
                collated_data.append(
                    [
                        weighting,
                        self.center(positions),
                    ]
                )

            # -- Sort the collated data by the mass value
            collated_data = sorted(
                collated_data,
                key=lambda v: v[0]
            )

            # -- Calculate the center of the overall mass
            running_mass = 0
            current_location = None

            for mass, location in collated_data:

                # -- Collate the running mass, as we will use this
                # -- to determine how much to move the center point
                running_mass += mass

                # -- If this is the first, and most influential node
                # -- then we just accept it
                if not current_location:
                    current_location = location
                    continue

                # -- Lerp toward the new center based on the factor of
                # -- how much mass this particular input has
                current_location = self.lerp_vector(
                    current_location,
                    location,
                    (mass / running_mass),
                )

            if not current_location:
                current_location = [0, 0, 0]

            # -- Now we can set the output values
            x = current_location[0]
            y = current_location[1]
            z = current_location[2]

            # -- Set the output plugs
            data.outputValue(CenterOfMassNode.aTranslateX).setFloat(x)
            data.outputValue(CenterOfMassNode.aTranslateY).setFloat(y)
            data.outputValue(CenterOfMassNode.aTranslateZ).setFloat(z)

            # -- Clean the plugs so they do not get re-evaluated
            data.setClean(CenterOfMassNode.aTranslateX)
            data.setClean(CenterOfMassNode.aTranslateY)
            data.setClean(CenterOfMassNode.aTranslateZ)
            # data.setClean(CenterOfMassNode.aCenterOfMass)

    # --------------------------------------------------------------------------
    @staticmethod
    def center(positions):
        """
        Given a list of positions, this will return the center of those
        positions.

        :param positions: list of positions
        :type positions: [[0, 0, 0], [1, 1, 1]]

        :return: list(x, y, z)
        """
        result = [0, 0, 0]

        if not positions:
            return result

        result = None  # positions[0]

        for position in positions:

            if not result:
                result = position
                continue

            result = list(map(operator.add, result, position))

        result = [
            v / float(len(positions))
            for v in result
        ]

        return result

    # --------------------------------------------------------------------------
    @staticmethod
    def lerp_float(a, b, percent):
        """
        Lerps between two floats based on the given percentage value.

        :param a: Value to lerp from
        :type a: float

        :param b: Value to lerp to
        :type b: float

        :param percent: Percentage of how far to blend between
            the two float values

        :return: float
        """
        return ((b - a) * percent) + a

    # --------------------------------------------------------------------------
    @staticmethod
    def lerp_vector(a, b, percent):
        """
        Lerps between two vectors of length 3 (x, y, z).

        :param a: The vector to lerp from
        :type a: list(x, y, z)

        :param b: The vector to lerp to
        :type b: list(x, y, z)

        :param percent: Percentage of how far to blend
            between the two vectors

        :return: list(x, y, z)
        """
        x = CenterOfMassNode.lerp_float(a[0], b[0], percent)
        y = CenterOfMassNode.lerp_float(a[1], b[1], percent)
        z = CenterOfMassNode.lerp_float(a[2], b[2], percent)

        return [x, y, z]

    # --------------------------------------------------------------------------
    @staticmethod
    def creator():
        """
        Creates a pointer to the newly generated node instance

        :return: MPxPtr
        """
        return CenterOfMassNode()

    # --------------------------------------------------------------------------
    @staticmethod
    def initialize():
        """
        Initialises the node with all the attributes. The input construction
        ends up looking like this:

        [
            [
                considerInCalculation,
                weighting,
                [
                    point,
                    point,
                    point,
                    ...,
                ],
            ],
            [
                considerInCalculation,
                weighting,
                [
                    point,
                    point,
                    point,
                    ...,
                ],
            ]
        ]

        The output is a translation vector.

        :return: MStatus
        """
        # -- Define the numeric fn object to generate our
        # -- numerical attributes with
        numeric_fn = OpenMaya.MFnNumericAttribute()
        matrix_fn = OpenMaya.MFnMatrixAttribute()
        compound_fn = OpenMaya.MFnCompoundAttribute()
        typed_fn = OpenMaya.MFnTypedAttribute()

        CenterOfMassNode.aCalculate = numeric_fn.create(
            'calculate',
            'cal',
            OpenMaya.MFnNumericData.kBoolean,
            True,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aCalculate)

        CenterOfMassNode.aDrawDebugLines = numeric_fn.create(
            'drawDebuggingLines',
            'cad',
            OpenMaya.MFnNumericData.kBoolean,
            True,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aDrawDebugLines)

        CenterOfMassNode.aDrawSphere = numeric_fn.create(
            'drawSphere',
            'dsp',
            OpenMaya.MFnNumericData.kBoolean,
            True,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aDrawSphere)

        CenterOfMassNode.aDrawVerticalLine = numeric_fn.create(
            'drawVerticalLine',
            'xvl',
            OpenMaya.MFnNumericData.kBoolean,
            1.0,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aDrawVerticalLine)

        CenterOfMassNode.aSphereSize = numeric_fn.create(
            'sphereSize',
            'sps',
            OpenMaya.MFnNumericData.kFloat,
            10.0,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aSphereSize)

        # -- Always add an identifier - we expect this to be unique
        CenterOfMassNode.aIdentfier = typed_fn.create(
            'identifier',
            'idf',
            OpenMaya.MFnData.kString,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aIdentfier)

        # -- Always add an identifier - we expect this to be unique
        CenterOfMassNode.aSectionIdentifier = typed_fn.create(
            'sectionIdentifier',
            'sid',
            OpenMaya.MFnData.kString,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aSectionIdentifier)

        # -- This attribute is used to determine whether we should
        # -- ignore this input or not
        CenterOfMassNode.aConsiderInCalculation = numeric_fn.create(
            'considerInCalculation',
            'cic',
            OpenMaya.MFnNumericData.kBoolean,
            1.0,
        )
        numeric_fn.storable = True
        numeric_fn.keyable = True
        numeric_fn.array = False
        CenterOfMassNode.addAttribute(CenterOfMassNode.aConsiderInCalculation)

        # -- This is the weighting this input should be given
        CenterOfMassNode.aMass = numeric_fn.create(
            'mass',
            'mas',
            OpenMaya.MFnNumericData.kFloat,
            1.0,
        )
        numeric_fn.storable = True
        numeric_fn.keyable = True
        numeric_fn.array = False
        CenterOfMassNode.addAttribute(CenterOfMassNode.aMass)

        # -- We now need to define the input matrices. We use the matrix
        # -- rather than a vector because its easier to plug in a world
        # -- matrix rather than have a user decompose every attribute
        CenterOfMassNode.aPointsOfBounds = matrix_fn.create(
            'pointsOfBounds',
            'pob',
        )
        matrix_fn.storable = True
        matrix_fn.keyable = True
        matrix_fn.array = True
        CenterOfMassNode.addAttribute(CenterOfMassNode.aPointsOfBounds)

        # -- Create the compound which binds all the attributes
        # -- together
        CenterOfMassNode.aCompound = compound_fn.create('inputs', 'inp')
        compound_fn.array = True
        compound_fn.readable = True
        compound_fn.usesArrayDataBuilder = True

        compound_fn.addChild(CenterOfMassNode.aSectionIdentifier)
        compound_fn.addChild(CenterOfMassNode.aConsiderInCalculation)
        compound_fn.addChild(CenterOfMassNode.aMass)
        compound_fn.addChild(CenterOfMassNode.aPointsOfBounds)

        CenterOfMassNode.addAttribute(CenterOfMassNode.aCompound)

        # -- Now add in our output plug
        CenterOfMassNode.aTranslateX = numeric_fn.create(
            'comTranslateX',
            'cox',
            OpenMaya.MFnNumericData.kFloat,
            1.0,
        )
        numeric_fn.storable = False
        numeric_fn.keyable = False
        CenterOfMassNode.addAttribute(CenterOfMassNode.aTranslateX)

        CenterOfMassNode.aTranslateY = numeric_fn.create(
            'comTranslateY',
            'coy',
            OpenMaya.MFnNumericData.kFloat,
            1.0,
        )
        numeric_fn.storable = False
        numeric_fn.keyable = False
        CenterOfMassNode.addAttribute(CenterOfMassNode.aTranslateY)

        CenterOfMassNode.aTranslateZ = numeric_fn.create(
            'comTranslateZ',
            'coz',
            OpenMaya.MFnNumericData.kFloat,
            1.0,
        )
        numeric_fn.storable = False
        numeric_fn.keyable = False
        CenterOfMassNode.addAttribute(CenterOfMassNode.aTranslateZ)

        # --
        CenterOfMassNode.aCenterOfMass = numeric_fn.create(
            'comTranslation',
            'cot',
            CenterOfMassNode.aTranslateX,
            CenterOfMassNode.aTranslateY,
            CenterOfMassNode.aTranslateZ,
        )
        CenterOfMassNode.addAttribute(CenterOfMassNode.aCenterOfMass)

        # -- Set up the attribution affecting
        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aCalculate,
            CenterOfMassNode.aCenterOfMass,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aConsiderInCalculation,
            CenterOfMassNode.aCenterOfMass,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aMass,
            CenterOfMassNode.aCenterOfMass,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aPointsOfBounds,
            CenterOfMassNode.aCenterOfMass,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aCalculate,
            CenterOfMassNode.aTranslateX,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aConsiderInCalculation,
            CenterOfMassNode.aTranslateX,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aMass,
            CenterOfMassNode.aTranslateX,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aPointsOfBounds,
            CenterOfMassNode.aTranslateX,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aCalculate,
            CenterOfMassNode.aTranslateY,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aConsiderInCalculation,
            CenterOfMassNode.aTranslateY,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aMass,
            CenterOfMassNode.aTranslateY,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aPointsOfBounds,
            CenterOfMassNode.aTranslateY,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aCalculate,
            CenterOfMassNode.aTranslateZ,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aConsiderInCalculation,
            CenterOfMassNode.aTranslateZ,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aMass,
            CenterOfMassNode.aTranslateZ,
        )

        CenterOfMassNode.attributeAffects(
            CenterOfMassNode.aPointsOfBounds,
            CenterOfMassNode.aTranslateZ,
        )


# ------------------------------------------------------------------------------
class CenterOfMassData(OpenMaya.MUserData):
    """
    This is the data block which we use to read between the node drawing the preparing for drawing
    and the actual draw. This is because we cannot read object attributes directly during the
    draw stage
    """
    def __init__(self):
        OpenMaya.MUserData.__init__(self, False)  # -- don't delete after draw

        self.position = [0, 0, 0]
        self.floor = [0, 0, 0]
        self.ceil = [0, 0, 0]

        self.sphereSize = 10.0
        self.drawSphere = True
        self.drawVerticalLine = True
        self.drawDebugLines = False


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming,PyMethodMayBeStatic
class CenterOfMassDrawOverride(OpenMayaRender.MPxDrawOverride):
    """
    This defines how we draw the visualisation
    """

    # --------------------------------------------------------------------------
    @staticmethod
    def creator(obj):
        return CenterOfMassDrawOverride(obj)

    # --------------------------------------------------------------------------
    @staticmethod
    def draw(context, data):
        return

    # --------------------------------------------------------------------------
    def __init__(self, obj):
        OpenMayaRender.MPxDrawOverride.__init__(self, obj, CenterOfMassDrawOverride.draw)

    # --------------------------------------------------------------------------
    def supportedDrawAPIs(self):
        return OpenMayaRender.MRenderer.kOpenGL | OpenMayaRender.MRenderer.kDirectX11 | OpenMayaRender.MRenderer.kOpenGLCoreProfile

    # --------------------------------------------------------------------------
    def prepareForDraw(self, objPath, cameraPath, frameContext, oldData):

        # -- Get the data, and ensure its center of mass data
        data = oldData
        if not isinstance(data, CenterOfMassData):
            data = CenterOfMassData()

        # -- Get the node
        node = objPath.node()

        # -- Read the position data
        comVector = self.getCOM(node)

        data.position = [
            comVector[0],
            comVector[1],
            comVector[2],
        ]

        # -- Build the information for the top and bottom of the line to be drawn
        if pm.upAxis(q=True, axis=True) == 'z':
            data.floor = [
                comVector[0],
                comVector[1],
                0,
            ]
            data.ceil = [
                comVector[0],
                comVector[1],
                comVector[2] * 2.0,
            ]
        else:
            data.floor = [
                comVector[0],
                0,
                comVector[2],
            ]
            data.ceil = [
                comVector[0],
                comVector[1] * 2.0,
                comVector[2],
            ]

        data.sphereSize = OpenMaya.MPlug(node, CenterOfMassNode.aSphereSize).asFloat()
        data.drawSphere = OpenMaya.MPlug(node, CenterOfMassNode.aDrawSphere).asBool()
        data.drawVerticalLine = OpenMaya.MPlug(node, CenterOfMassNode.aDrawVerticalLine).asBool()
        data.drawDebugLines = OpenMaya.MPlug(node, CenterOfMassNode.aDrawDebugLines).asBool()

        return data

    # --------------------------------------------------------------------------
    def hasUIDrawables(self):
        return True

    # --------------------------------------------------------------------------
    def addUIDrawables(self, objPath, drawManager, frameContext, data):

        if not isinstance(data, CenterOfMassData):
            return

        drawManager.beginDrawable()

        color = OpenMaya.MColor((1.0, 0.0, 0.0))
        drawManager.setColor(color)

        if data.drawSphere:
            drawManager.sphere(
                OpenMaya.MPoint(*data.position),
                data.sphereSize,
                True,
            )

        if data.drawVerticalLine:
            drawManager.line(
                OpenMaya.MPoint(
                    *data.floor,
                ),
                OpenMaya.MPoint(
                    *data.ceil,
                )
            )

        drawManager.endDrawable()

    # --------------------------------------------------------------------------
    @classmethod
    def getCOM(cls, node):
        xPlug = OpenMaya.MPlug(node, CenterOfMassNode.aTranslateX)
        yPlug = OpenMaya.MPlug(node, CenterOfMassNode.aTranslateY)
        zPlug = OpenMaya.MPlug(node, CenterOfMassNode.aTranslateZ)

        if xPlug.isNull or yPlug.isNull or zPlug.isNull:
            return [0.0, 0.0, 0.0]

        return [
            xPlug.asFloat(),
            yPlug.asFloat(),
            zPlug.asFloat(),
        ]


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming
def initializePlugin(mobject):
    """
    Initialises the plugin and registers all the nodes/commands
    """
    mplugin = OpenMaya.MFnPlugin(mobject)

    try:
        nodes = [
            CenterOfMassNode,
        ]

        for node_class in nodes:
            mplugin.registerNode(
                node_class.TypeName,
                node_class.NodeId,
                node_class.creator,
                node_class.initialize,
                OpenMaya.MPxNode.kLocatorNode,
                node_class.drawDbClassification,
            )

    except RuntimeError:
        print("Failed to register node: %s" % CenterOfMassNode.TypeName)
        raise

    try:
        OpenMayaRender.MDrawRegistry.registerDrawOverrideCreator(
            CenterOfMassNode.drawDbClassification,
            CenterOfMassNode.drawRegistrantId,
            CenterOfMassDrawOverride.creator,
        )
    except:
        print("Failed to register override\n")
        raise


# ------------------------------------------------------------------------------
# noinspection PyPep8Naming
def uninitializePlugin(mobject):
    """
    Unregisters any nodes/commands registered during the initializePlugin
    call.
    """
    mplugin = OpenMaya.MFnPlugin(mobject)

    try:
        nodes = [
            CenterOfMassNode,
        ]

        for node_class in nodes:
            mplugin.deregisterNode(node_class.NodeId)

    except RuntimeError:
        print("Failed to deregister node: %s" % CenterOfMassNode.TypeName)
        raise

    try:
        OpenMayaRender.MDrawRegistry.deregisterDrawOverrideCreator(
            CenterOfMassNode.drawDbClassification,
            CenterOfMassNode.drawRegistrantId,
        )
    except:
        print("Failed to deregister override\n")
        pass
