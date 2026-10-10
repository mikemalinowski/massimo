"""
MIT License

Copyright (c) 2022 Michael Malinowski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import re
import json

from maya import cmds

# -- These regexes are constant, so rather than recompile them each time
# -- we need them, we do it once at the module level
_REGEX_SECTIONS = re.compile('inputs\[(.*)\]\.')
_REGEX_BOUNDS = re.compile('inputs\[(.*)\]\.pointsOfBounds\[(.*)\]')


# ----------------------------------------------------------------------------------------------------------------------
class MassimoCache(object):
    """
    Because we need to iterate over section indices a lot, testing names
    etc it can be slow. Therefore, we cache this information and only rebuild
    it when the data becomes dirty
    """
    _SECTION_INDICES = dict()
    _SECTION_CACHE_IS_DIRTY = True

    # ------------------------------------------------------------------------------------------------------------------
    @classmethod
    def invalidate_section_cache(cls):
        MassimoCache._SECTION_CACHE_IS_DIRTY = True

    # ------------------------------------------------------------------------------------------------------------------
    @classmethod
    def cache_sections(cls, mass_node, value):
        MassimoCache._SECTION_INDICES[mass_node] = value
        MassimoCache._SECTION_CACHE_IS_DIRTY = False

    # ------------------------------------------------------------------------------------------------------------------
    @classmethod
    def section_cache(cls, mass_node):
        if MassimoCache.is_section_cache_dirty():
            return dict()

        if mass_node not in MassimoCache._SECTION_INDICES:
            return dict()

        return MassimoCache._SECTION_INDICES[mass_node]

    # ------------------------------------------------------------------------------------------------------------------
    @classmethod
    def is_section_cache_dirty(cls):
        return MassimoCache._SECTION_CACHE_IS_DIRTY


# ------------------------------------------------------------------------------------------------------------------
def _get_used_influence_indices(mass_node, section_idx):
    """
    Influences are connected into a multi attribute, so we need to know the indicies
    of the connections. This function will return all the indicies of the plugs being
    used as part of the calculation

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_idx: The index of the section to inspect
    :type section_idx: int

    :return: List of integers
    """
    indicies = dict()

    for n in cmds.listAttr(mass_node, multi=True, inUse=True) or []:
        result = _REGEX_BOUNDS.search(n)

        if result:
            found_section = result.groups()[0]

            if int(found_section) == int(section_idx):
                indicies[int(result.groups()[1])] = None

    return list(indicies.keys())


# ----------------------------------------------------------------------------------------------------------------------
def _get_used_section_indices(mass_node):
    """
    Sections are defined on a multi attribute, so we often need to know the
    plug indicies that are being used in the calculation so we can determine which
    sections we can interact wtih.

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :return: List of integers
    """
    # -- This function is called a lot, and whilst its quite quick the time
    # -- accumulates given how often its called. Therefore we cache this information
    # -- and pull the data from the cache if its valid, and only rebuild it if
    # -- we need to
    cached_info = MassimoCache.section_cache(mass_node)
    if cached_info:
        return cached_info


    # -- Declare a variable to scoop all the index information into
    indicies = dict()

    # -- Cycle all the multi attributes on the mass node which are
    # -- currently in use
    for n in cmds.listAttr(mass_node, multi=True, inUse=True) or []:

        # -- If we match this one as a section attribute we
        # -- can start to pull information from it
        result = _REGEX_SECTIONS.search(n)

        # -- We only care about the index, and we want it to be
        # -- unique, so we use a dict here rather than doing
        # -- the whole list(set([])) approach
        if result:
            indicies[int(result.groups()[0])] = None

    # -- Pull out the keys
    result = list(indicies.keys())

    # -- Cache this information so that we do not have to generate
    # -- it again unless something changes
    MassimoCache.cache_sections(mass_node, result)

    return result


# ----------------------------------------------------------------------------------------------------------------------
def _get_section_idx_from_name(mass_node, name):
    """
    This will determine the section id of the section with a given name.

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param name: The name of the section we want to look up the id for
    :type name: str

    :return: integer
    """

    # -- Cycle all our section indices, and look at the sectionIdentifier attribute
    # -- so we can compare it to the name we're looking for
    for idx in _get_used_section_indices(mass_node):
        if cmds.getAttr('{}.inputs[{}].sectionIdentifier'.format(mass_node, idx)) == name:
            return idx

    # -- If we could not find a section with the expected
    # -- name then we return a negative value
    return -1


# ----------------------------------------------------------------------------------------------------------------------
def _get_name_from_section_idx(mass_node, section_idx):
    """
    This will determine the name of a section using the section id as the look up

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_idx: The section integer to inspect
    :type section_idx: int

    :return: str
    """

    # -- If the integer we have been given is not valid then we return None
    if section_idx not in _get_used_section_indices(mass_node):
        return None

    # -- Return the value of the sectionIdentifier which is within the
    # -- input plug with the given section id
    return cmds.getAttr('{}.inputs[{}].sectionIdentifier'.format(mass_node, section_idx))


# ----------------------------------------------------------------------------------------------------------------------
def get_normalised_weights(mass_node):
    """
    This function will return a dictionary where the keys are the section names
    and the values are normalised values based on the weights of each section.

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :return: dict(section_name: normalised weight value)
    """

    # -- Declare a variable to scoop all our weight information into
    weights = dict()

    # -- Cycle our sections, and get the weight value of each section
    for section_name in get_section_names(mass_node):
        weights[section_name] = get_section_weight(mass_node, section_name)

    # -- In order to calculate the normalsied value we need to know
    # -- the sum value
    total_weight = sum([v for v in list(weights.values())])

    # -- Now we declare our output variable where we will store all the
    # -- normalised values
    factored_weights = dict()

    # -- Cycle our weight information and divide each weight by the
    # -- total weight
    for section_name, weight in weights.items():
        factored_weights[section_name] = weight / total_weight

    return factored_weights


# ----------------------------------------------------------------------------------------------------------------------
def get_section_names(mass_node):
    """
    This returns a list of all the sections defined in the massimo node

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :return: list(str, str, str, ...)
    """

    # -- Get a list of the indices being used in the mass node
    section_indices = _get_used_section_indices(mass_node)

    # -- Declare our output variable
    names = []

    # -- Cycle each section and get the name, adding it to the
    # -- output variable
    for section_idx in section_indices:
        names.append(_get_name_from_section_idx(mass_node, section_idx))

    return names


# ----------------------------------------------------------------------------------------------------------------------
def set_section_name(mass_node, section_name, new_name):
    """
    Switches the section with the given name to a new name

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_name: Name of the section which is to be renamed
    :type section_name: str

    :param new_name: The new name to assign to the section
    :type new_name: str

    :return: None
    """


    # -- If this name already exists then we should not reuse it
    if new_name in get_section_names(mass_node):
        print('Cannot use a currently in use section name')
        return None

    # -- Get the id of the section from the name, this is because
    # -- we need to edit the sectionIdentifier value directly
    section_idx = _get_section_idx_from_name(mass_node, section_name)

    # -- If the value was below zero then we could not find a section
    # -- with the given name, and therefore cannot rename it
    if section_idx < 0:
        print('Could not resolve section with name {}'.format(section_name))
        return

    # -- Perform the rename
    cmds.setAttr(
        '{}.inputs[{}].sectionIdentifier'.format(mass_node, section_idx),
        new_name,
        type='string',
    )


# ----------------------------------------------------------------------------------------------------------------------
def set_section_weight(mass_node, section_name, weight):
    """
    Sets the weight/mass value of the given section

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_name: The name of the section we need to change the weight value of
    :type section_name: str

    :param weight: The weight value to assign
    :type weight: float

    :return: None
    """

    # -- Get the id of the section from the name, this is because
    # -- we need to edit the mass value directly
    section_idx = _get_section_idx_from_name(mass_node, section_name)

    # -- If the value was below zero then we could not find a section
    # -- with the given name, and therefore cannot alter the weight value for it
    if section_idx < 0:
        print('Could not resolve section with name {}'.format(section_name))
        return

    # -- Perform the weight value change
    cmds.setAttr('{}.inputs[{}].mass'.format(mass_node, section_idx), weight)


# ----------------------------------------------------------------------------------------------------------------------
def get_section_weight(mass_node, section_name):
    """
    Returns the weight/mass value assigned to the given section

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_name: The name of the section we want to retrieve the weight value for
    :type section_name: str

    :return: float
    """

    # -- Get the id of the section from the name, this is because
    # -- we need to read the value directly from the plug
    section_idx = _get_section_idx_from_name(mass_node, section_name)

    # -- If the value was below zero then we could not find a section
    # -- with the given name, and therefore cannot get a value for it
    if section_idx < 0:
        print('Could not resolve section with name {}'.format(section_name))
        return 0

    # -- Read the value
    return cmds.getAttr(
        '{mass_node}.inputs[{section_idx}].mass'.format(
            mass_node=mass_node,
            section_idx=section_idx,
        ),
    )


# ----------------------------------------------------------------------------------------------------------------------
def add_section_influence(mass_node, section_name, influence):
    """
    This will connect a node into the influence list for a given section, altering that sections
    center, and thus affecting the final output position of the center of mass calculation

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_name: The name of the section we want to add an influence to
    :type section_name: str

    :param influence: The influence object we want to include into the calculation
    :type influence: str

    :return: None
    """

    # -- Check the influence exists
    if not cmds.objExists(influence):
        print('no influence')
        return None

    # -- Ensure the node has a world matrix attr
    if not cmds.objExists('{}.worldMatrix[0]'.format(influence)):
        print('no influence with a world matrix')
        print('{}.worldMatrix[0]]'.format(influence))
        return None

    # -- Get the id of the section from the name, this is because
    # -- we need to access the plug structure directly
    section_idx = _get_section_idx_from_name(mass_node, section_name)

    # -- If the value was below zero then we could not find a section
    # -- with the given name
    if section_idx < 0:
        print('Could not resolve section with name {}'.format(section_name))
        return

    # -- Get a list of the used_influence indices, this is to ensure
    # -- we do not accidentally stomp over the connection of an already
    # -- in use influence
    used_influence_indices = _get_used_influence_indices(mass_node, section_idx)

    # -- Start the counter at zero
    counter = 0

    # -- Cycle the counter whilst we look for an available slot to connect
    # -- into
    while True:

        # -- If this counter is not used, we can use it
        if counter not in used_influence_indices:

            # -- Hook up the worldMatrix attribute of the influence into the mass node
            cmds.connectAttr(
                '{}.worldMatrix[0]'.format(influence),
                '{mass_node}.inputs[{section_idx}].pointsOfBounds[{influence_idx}]'.format(
                    mass_node=mass_node,
                    section_idx=section_idx,
                    influence_idx=counter,
                )
            )
            return counter

        # -- Increment the counter so we can test the next plug index
        counter += 1


# ----------------------------------------------------------------------------------------------------------------------
def remove_section_influence(mass_node, section_name, influence):
    """
    Removes the given influence from the section with the given section name

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_name: Name of the section we want to remove the influence from
    :type section_name: str

    :param influence: The influence we want to remove
    :type influence: str

    :return:
    """
    # -- If the influence does not exist, we cannot do anything
    if not cmds.objExists(influence):
        return

    # -- As we will need to interact with the mass node plugs directly we need
    # -- to know the id of the section to affect
    section_idx = _get_section_idx_from_name(mass_node, section_name)

    # -- If we could not resolve the id then it means the section does not
    # -- exist, and therefore we cannot do anything
    if section_idx < 0:
        print('Could not resolve section with name {}'.format(section_name))
        return

    # --Get a list of the outputs for the influences worldMatrix plug
    driven_plugs = cmds.listConnections(
        '{}.worldMatrix[0]'.format(influence),
        source=False,
        destination=True,
        plugs=True,
    ) or []

    for plug in driven_plugs:

        # -- Check if this is a plug we should keep looking at
        if 'inputs[{}]'.format(section_idx) in plug:

            # -- Test the plug name more fully
            plug_match = _REGEX_BOUNDS.search(plug)

            if plug_match:

                # -- Get the index of the plug from the regex lookup
                plug_idx = plug_match.groups()[1]

                # -- Remove the connection as well as the plug itself to ensure it does not
                # -- keep being calculated
                cmds.removeMultiInstance(
                    '{mass_node}.inputs[{section_idx}].pointsOfBounds[{plug_idx}]'.format(
                        mass_node=mass_node,
                        section_idx=section_idx,
                        plug_idx=plug_idx,
                    ),
                    b=True
                )


# ----------------------------------------------------------------------------------------------------------------------
def get_section_influences(mass_node, section_name):
    """
    Returns a list of influences being used by the section with the given name

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_name: Name of the section we want to retrieve a lost of influences for
    :type section_name: str

    :return: list(str, ..)
    """

    # -- Declare our output variable
    influences = list()

    # -- We need to read from a section plug directly, so we need to request the given
    # -- plug index
    section_idx = _get_section_idx_from_name(mass_node, section_name)

    # -- Cycle all the plug indices
    for influence_idx in _get_used_influence_indices(mass_node, section_idx):
        bounds_attr = '{mass_node}.inputs[{section_idx}].pointsOfBounds[{influence_idx}]'.format(
            mass_node=mass_node,
            section_idx=section_idx,
            influence_idx=influence_idx,
        )

        # -- Get the inputs (i.e, the nodes driving these plugs)
        driving_nodes = cmds.listConnections(
            bounds_attr,
            source=True,
            destination=False,
        ) or []

        for driving_node in driving_nodes:
            influences.append(driving_node)

    return influences


# ----------------------------------------------------------------------------------------------------------------------
def add_mass_group(mass_node, name=''):
    """
    Add a new mass group section to the mass node

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param name: The name to assign to the section. This name must not be shared with any other section
        on the mass node.
    :type name: str

    :return: section index (int)
    """
    # -- Dirty the cache to ensure its rebuilt next time any data
    # -- is requested
    MassimoCache.invalidate_section_cache()


    # -- Initialise a new section with the given name
    section_idx = _initialise_mass_section(mass_node, name=name)

    return section_idx


# ----------------------------------------------------------------------------------------------------------------------
def remove_mass_group(mass_node, section_name):
    """
    Removes a mass section with the given name from the mass node

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param section_name: The name of the section you want to remove
    :type section_name: str

    :return: None
    """

    # -- We need to read from a section plug directly, so we need to request the given
    # -- plug index
    section_idx = _get_section_idx_from_name(mass_node, section_name)

    # -- If we have a value below zero then we have been given a section
    # -- name which does not exist
    if section_idx < 0:
        print('Could not resolve section with name {}'.format(section_name))
        return

    # -- Remove the section attribute which in turn disconnects all incoming
    # -- connections at the same time ( the 'b' flag does this)
    cmds.removeMultiInstance(
        '{mass_node}.inputs[{section_idx}]'.format(
            mass_node=mass_node,
            section_idx=section_idx,
        ),
        b=True
    )

    # -- Dirty the cache to ensure its rebuilt next time any data
    # -- is requested
    MassimoCache.invalidate_section_cache()


# ----------------------------------------------------------------------------------------------------------------------
def _initialise_mass_section(mass_node, name='new_section'):
    """
    Initialises a pose section, and returns the index of the initialized section

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param name: The name to assign to the section upon initialisation
    :type name: str

    :return: index of the pose (int)
    """
    counter = 0

    while True:
        # -- Getting the value of an attribute will initialise it - but will return None
        # -- if its the first time its initialised. Love Maya.
        result = cmds.getAttr('{}.inputs[{}].sectionIdentifier'.format(mass_node, counter))

        # -- If we get a None value then we have initialised a new section, so we can set the name and
        # -- be done!
        if not result:
            cmds.setAttr(
                '{}.inputs[{}].sectionIdentifier'.format(mass_node, counter),
                name,
                type='string',
            )
            return counter

        counter += 1


# ----------------------------------------------------------------------------------------------------------------------
def massimo_nodes():
    """
    Returns a list of all the massimo nodes in the scene
    :return:
    """
    return cmds.ls(type='CenterOfMass')


# ----------------------------------------------------------------------------------------------------------------------
def new(name='massimo'):
    """
    Create a new massimo node

    :param name: Name to assign to the transform of the massimo node. Note that 'Settings' will be
        appended to the name of the actual shape node
    :type name: str

    :return: str
    """
    transform = cmds.createNode('transform', name=name)
    return cmds.createNode('CenterOfMass', name=name + 'Settings', parent=transform)


# ----------------------------------------------------------------------------------------------------------------------
def serialise(mass_node, filepath=None):
    """
    This will read all the information from the mass node and store it in
    JSON format. If a filepath is given then it will also be saved to disk

    :param mass_node: The mass node to inspect
    :type mass_node: str

    :param filepath: Optional filepath (absolute) where this file should be saved
    :type filepath: str

    :return: dict
    """

    # -- Declare our output dictionary
    data = dict(
        name=mass_node,
        sections=list(),
        settings=dict(
            calculate=cmds.getAttr('{}.calculate'.format(mass_node)),
            drawDebuggingLines=cmds.getAttr('{}.drawDebuggingLines'.format(mass_node)),
            drawSphere=cmds.getAttr('{}.drawSphere'.format(mass_node)),
            drawVerticalLine=cmds.getAttr('{}.drawVerticalLine'.format(mass_node)),
            sphereSize=cmds.getAttr('{}.sphereSize'.format(mass_node)),
        ),
    )

    # -- Cycle each section name in the mass node
    for section_name in get_section_names(mass_node):

        # -- Build up a block of data to represent this section
        section_data = dict(
            name=section_name,
            weight=get_section_weight(mass_node, section_name),
            influences=get_section_influences(mass_node, section_name),
        )

        # -- Add the section data to the main data block
        data['sections'].append(section_data)

    # -- If we are given a filepath then we store the data
    # -- in the file using json
    if filepath:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True)

    return data


# ----------------------------------------------------------------------------------------------------------------------
def deserialise(filepath):
    """
    Generates a new CenterOfMass node with the data from the given filepath

    :param filepath: Absolute path to the .mass file
    :type filepath: str

    :return: str
    """
    # -- Read the filepath and load it as json
    with open(filepath, 'r') as f:
        data = json.load(f)

    # -- Create a new CenterOfMass node
    mass_node = new(data['name'])

    if 'settings' in data:
        cmds.setAttr('{}.calculate'.format(mass_node), data['settings']['calculate'])
        cmds.setAttr('{}.drawDebuggingLines'.format(mass_node), data['settings']['drawDebuggingLines'])
        cmds.setAttr('{}.drawSphere'.format(mass_node), data['settings']['drawSphere'])
        cmds.setAttr('{}.drawVerticalLine'.format(mass_node), data['settings']['drawVerticalLine'])
        cmds.setAttr('{}.sphereSize'.format(mass_node), data['settings']['sphereSize'])

    # -- Cycle all the stored sections
    for section in data['sections']:

        # -- Definea new mass group
        add_mass_group(
            mass_node,
            name=section['name'],
        )

        # -- Set the weight of the group
        set_section_weight(
            mass_node,
            section_name=section['name'],
            weight=section['weight'],
        )

        # -- Now add in each influence
        for influence in section['influences']:

            # -- if the influence does not exist, check under namespaces
            if not cmds.objExists(influence):
                influence = influence.split(':')[-1]

                # -- Attempt to find the influence under namespaces
                influences = cmds.ls(influence, recursive=True)

                if not influences:
                    continue

                influence = influences[0]

            # -- Add the influence
            add_section_influence(
                mass_node=mass_node,
                section_name=section['name'],
                influence=influence,
            )
