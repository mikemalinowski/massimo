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
from .. import resources
from ... import core

from .settings import MassimoNodeSettings
from ..widgets.mass_group import MassGroup
from ...vendor import qute
from ...defaults import Defaults

import os
import pymel.core as pm


# ----------------------------------------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class MassimoWidget(qute.QWidget):
    """
    This represents the main functional widget of the tool
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(MassimoWidget, self).__init__(parent=parent)
        
        # -- We need to refresh the ui whenever the user makes or
        # -- opens a new scene, therefore we define our script jobs 
        # -- immediately.
        self.scriptJobIDs = list()
        self._registerScriptJobs()

        # -- This list is where we store a list of mass groups currently
        # -- assigned
        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )
        
        # -- Load in our ui file
        self.ui = qute.utilities.designer.load(
            resources.get('massimo.ui'),
        )
        self.layout().addWidget(self.ui)
        
        # -- Hook up our signals and slots
        self.ui.saveButton.clicked.connect(self.save)
        self.ui.loadButton.clicked.connect(self.load)
        self.ui.newMassimoNode.clicked.connect(self.addMassimoNode)
        self.ui.addMassGroupButton.clicked.connect(self.addMassGroup)
        self.ui.settingsButton.clicked.connect(self.editSettings)
        
        self.ui.filterText.textChanged.connect(self.refreshMassGroupList)
        self.ui.massimoNodes.currentIndexChanged.connect(self.refreshMassGroupList)
        self.ui.sortOrder.currentIndexChanged.connect(self.refreshMassGroupList)
        
        # -- Set our button icons to be paths relative to the 
        # -- install location
        self.ui.settingsButton.setIcon(
            qute.QIcon(
                resources.get('settings.png')
            )
        )
        
        # -- Populate our mass nodes and trigger a population 
        # -- of our group list
        self.populateMassimoNodes()
        self.refreshMassGroupList()

    # ------------------------------------------------------------------------------------------------------------------
    def _getMassNode(self):
        """
        This will attempt to get the mass node defined in the massimoNodes
        combo
        
        :return: pm.nt.PyNode or None 
        """
        massNodeName = self.ui.massimoNodes.currentText()
        
        if not massNodeName:
            return None
        
        if not pm.objExists(massNodeName):
            return None
        
        return pm.PyNode(self.ui.massimoNodes.currentText())
    
    # ------------------------------------------------------------------------------------------------------------------
    def editSettings(self):
        """
        This will trigger a dialog to open which allows the user to 
        alter some of the settings of the mass node
        
        :return: 
        """
        # -- Get the mass node, if one could not be resolved we 
        # -- do nothing
        massimoNode = self._getMassNode()
        
        if not massimoNode:
            return
        
        # -- Instance the dialog and cause it to block
        dialog = MassimoNodeSettings(massimoNode, parent=self)
        dialog.exec_()

    # ------------------------------------------------------------------------------------------------------------------
    def _registerScriptJobs(self):
        """
        Register any script jobs which allow the ui to react to the changing
        state of maya
        
        :return: 
        """
        # -- Only register if they are not already registered
        if self.scriptJobIDs:
            return

        # -- Define the list of events we will register a refresh
        # -- with
        events = [
            'NewSceneOpened',
            'SceneOpened',
        ]

        for event in events:
            self.scriptJobIDs.append(
                pm.scriptJob(
                    event=[
                        event,
                        self.populateMassimoNodes,
                    ]
                )
            )

    # ------------------------------------------------------------------------------------------------------------------
    def _unregisterScriptJobs(self):
        """
        We want to unregister our script jobs when this window is not active
        
        :return: 
        """
        
        # -- Cycle all our registered script jobs and kill them
        for identifier in self.scriptJobIDs:
            pm.scriptJob(
                kill=identifier,
                force=True,
            )

        # -- Clear all our job ids
        self.scriptJobIDs = list()

    # ------------------------------------------------------------------------------------------------------------------
    def save(self):
        """
        This allows the node state to be saved to a serialised (file) form

        :return:
        """
        # -- Get the mass node, if one could not be resolved we 
        # -- do nothing
        massimoNode = self._getMassNode()

        if not massimoNode:
            return

        # -- Ask for a save location
        saveLocation = qute.utilities.request.filepath(
            title='Save Massimo File',
            filter_='*.mass (*.mass)',
            parent=self,
        )

        # -- If the user cancelled then we do not continnue
        if not saveLocation:
            return

        core.serialise(
            mass_node=massimoNode,
            filepath=saveLocation,
        )

    # ------------------------------------------------------------------------------------------------------------------
    def load(self):
        """
        This will create a new mass node based on the file form given

        :return:
        """

        # -- Open a file browser for the user
        filepath = qute.utilities.request.filepath(
            title='Open Massimo File',
            save=False,
            filter_='.mass (*.mass)',
            parent=self,
        )

        # -- If the user cancelled then we do not continue
        if not filepath:
            return

        # -- Call the function to create the new mass node
        core.deserialise(filepath)

        # -- Trigger the UI to refresh
        self.populateMassimoNodes()

    # ------------------------------------------------------------------------------------------------------------------
    def populateMassimoNodes(self):
        """
        This will look for all the mass nodes in the scene and rebuild the mass node list

        :return:
        """

        # -- Get the current entry so we can restore it if it still exists
        _current = self.ui.massimoNodes.currentText()

        # -- Clear the list
        self.ui.massimoNodes.clear()

        # -- This variable will be used to store the matched item if it
        # -- is found
        matchedIndex = 0

        # -- We will increment this index each time we look at an item
        currentIndex = 0

        # -- Cycle all the massimo nodes in teh scene
        for node in core.massimo_nodes():
            self.ui.massimoNodes.addItem(node.name())

            # -- If the name of this node matches the item that was active
            # -- before we cleared the list, we store the index so we can set
            # -- it as the active index when we are done
            if node.name() == _current:
                matchedIndex = currentIndex

            currentIndex += 1

        # -- Set the current item to be the matched index, which is zero
        # -- if one was not found
        self.ui.massimoNodes.setCurrentIndex(matchedIndex)

    # ------------------------------------------------------------------------------------------------------------------
    def refreshMassGroupList(self):
        """
        This will trigger a rebuild of the mass groups

        :return:
        """
        # -- Start by clearing the list - this removes all the widgets
        # -- within it
        qute.utilities.layouts.empty(self.ui.MassListLayout)

        # -- Get the mass node, if one could not be resolved we
        # -- do nothing
        massimoNode = self._getMassNode()

        if not massimoNode:
            return

        # -- Read the filter text, which allows the user to filter the amount
        # -- of items they see
        filterText = self.ui.filterText.text()

        # -- Get the sections we need to represent
        sectionNames = core.get_section_names(massimoNode)

        # -- Depending on how we sort, this logic will change
        sortOrder = self.ui.sortOrder.currentText()

        if sortOrder == 'Weight':

            # -- If we need to sort by weight, we need to get the weight values
            # -- and the sort the names vial the value getter of the dictionary
            sectionWeights = core.get_normalised_weights(mass_node=massimoNode)
            sectionNames = sorted(sectionWeights, key=sectionWeights.get, reverse=True)

        else:
            # -- To sort by names is nice and easy!
            sectionNames = sorted(sectionNames)

        # -- Cycle the section names we need to add
        for sectionName in sectionNames:

            # -- If we have a filter and that filter does not match then we do
            # -- not show the item
            if filterText and filterText.lower() not in sectionName.lower():
                continue

            # -- Create a mass group widget
            massWidget = MassGroup(
                massimoNode,
                sectionName
            )

            # -- Hook up the mass widgets signals so our window can
            # -- respond to its interactions
            massWidget.IsDeleted.connect(self.refreshMassGroupList)
            massWidget.WeightChanged.connect(self.applyWeightColouring)

            # -- Add it the to the ui layout
            self.ui.MassListLayout.addWidget(massWidget)

        # -- We now can apply weight colouring - this colours the weight
        # -- widget based on its normalised colours
        self.applyWeightColouring()

    # ------------------------------------------------------------------------------------------------------------------
    def applyWeightColouring(self):
        """
        This will cycle over all the mass group widgets and colour them
        based on how much normalised weight they have
        :return:
        """
        # -- Get the mass node, if one could not be resolved we 
        # -- do nothing
        massimoNode = self._getMassNode()

        if not massimoNode:
            return

        # -- Get the normalised weight values
        normalisedWeights = core.get_normalised_weights(massimoNode)

        # -- Cycle each item in the mass list layout
        for idx in range(self.ui.MassListLayout.count()):

            # -- Get the widget
            widget = self.ui.MassListLayout.itemAt(idx).widget()

            # -- Only act on it if its a mass group widget
            if isinstance(widget, MassGroup):

                # -- If we have a recognised section, request a colour change based
                # -- on the given normalised weight
                if widget.name in normalisedWeights:
                    widget.setWeightColor(int(normalisedWeights[widget.name] * 255))

    # ------------------------------------------------------------------------------------------------------------------
    def addMassimoNode(self):
        """
        This will add a new mass node to the scene

        :return:
        """
        # -- Ask the user for a mass group name
        result = qute.utilities.request.text(
            title='Add Mass Node',
            label='Please give a name for this mass node',
            parent=self,
        )

        # -- If the user cancelled then we do not continue
        if not result:
            return

        # -- Request a new mass node to be generated
        core.new(result)

        # -- Re-populate our mass node list
        self.populateMassimoNodes()

    # ------------------------------------------------------------------------------------------------------------------
    def addMassGroup(self):
        """
        This will walk the user through the steps of adding a new mass group
        :return:
        """
        # -- Get the mass node, if one could not be resolved we 
        # -- do nothing
        massimoNode = self._getMassNode()

        if not massimoNode:
            return
        
        # -- Ask the user for a mass group name
        sectionName = qute.utilities.request.text(
            title='Add Mass Group',
            label='Please give a name for this mass group',
            parent=self,
        )

        # -- If no name was given, we assume a cancellation
        if not sectionName:
            return

        # -- Cycle all the widgets and add them providing they match the filter
        # -- if one is given
        core.add_mass_group(
            mass_node=massimoNode,
            name=sectionName,
        )

        # -- Attempt to set a default likely weight
        core.set_section_weight(
            mass_node=massimoNode,
            section_name=sectionName,
            weight=Defaults.get(sectionName),
        )

        # -- If we have a selection at the time of adding a mass
        # -- group then we assume that the selected items want
        # -- to be added as influences
        if pm.selected():
            for node in pm.selected():
                core.add_section_influence(
                    mass_node=massimoNode,
                    section_name=sectionName,
                    influence=node,
                )

        # -- Now we have added a mass group, trigger a repopulation
        # -- of the mass list
        self.refreshMassGroupList()

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def showEvent(self, event):
        """
        Maya re-uses UI's, so we regsiter our events whenever the ui
        is shown
        """
        self._registerScriptJobs()

    # --------------------------------------------------------------------------
    # noinspection PyUnusedLocal
    def hideEvent(self, event):
        """
        Maya re-uses UI's, so we unregister the script job events whenever
        the ui is not visible.
        """
        self._unregisterScriptJobs()


# ----------------------------------------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences
class MassimoWindow(qute.QMainWindow):
    """
    This is the window which hosts the mass widget. We place it in a window so we can
    make it dockable etc.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, parent=None):
        super(MassimoWindow, self).__init__(parent=parent)

        # -- Set the central widget of the mass node
        self.setCentralWidget(
            MassimoWidget(),
        )

        # -- Apply a consistent styling across the tool
        qute.utilities.styling.apply(
            [
                'space',
            ],
            apply_to=self,
            _FOREGROUND_='50, 50, 70'
        )

        # -- Set the title and icon (branding) of the tool
        self.setWindowTitle('Massimo')
        self.setWindowIcon(
            qute.QIcon(
                resources.get('massimo.png')
            )
        )


# ----------------------------------------------------------------------------------------------------------------------
def launch():
    """
    Entry point for launching the massimo tool

    :return:
    """
    # -- Ensure the plugin is loaded
    pm.loadPlugin(
        'massimo_runtime.py',
    )

    w = MassimoWindow(parent=qute.utilities.windows.mainWindow())
    w.show()
