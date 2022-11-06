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
from ...vendor import qute
from ... import core

import pymel.core as pm


# ----------------------------------------------------------------------------------------------------------------------
# noinspection PyPep8Naming,PyUnresolvedReferences
class MassGroup(qute.QWidget):
    """
    The mass group widget represents a single mass group and exposes
    all the settings for it
    """
    
    # -- We know that the main tool will want to respond to 
    # -- some of the actions the user does to this widget, so 
    # -- we expose signals to inform that things are chaning 
    IsDeleted = qute.Signal()
    WeightChanged = qute.Signal()

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, massNode, name, parent=None):
        super(MassGroup, self).__init__(parent=parent)

        # -- Store the name and the mass node on the class
        # -- instance
        self.name = name
        self._massNode = massNode

        # -- Define the base layout
        self.setLayout(
            qute.utilities.layouts.slimify(
                qute.QVBoxLayout(),
            ),
        )

        # -- Add in a designer file widget
        self.ui = qute.utilities.designer.load(
            resources.get('mass_group.ui'),
        )
        self.layout().addWidget(self.ui)

        # -- Apply the massimo style to this widget
        qute.utilities.styling.apply(
            [
                resources.get('massimo.css'),
            ],
            apply_to=self,
        )

        # -- Set the name of the group box to be that of the section
        # -- name, so the user knows what section they are interacting
        # -- with
        self.ui.groupBox.setTitle(name)

        # -- Initialise the weight value
        self.ui.massSpinBox.setValue(
            core.get_section_weight(
                self._massNode,
                self.name,
            ),
        )

        # -- Hook up our signals and slots
        self.ui.addInfluenceButton.clicked.connect(self.addInfluence)
        self.ui.removeInfluenceButton.clicked.connect(self.removeInfluence)
        self.ui.renameButton.clicked.connect(self.rename)
        self.ui.deleteButton.clicked.connect(self.delete)
        self.ui.massSpinBox.valueChanged.connect(self.updateWeight)

        # -- Populate the list of influences making up this
        # -- mass section
        self.populateInfluenceList()

    # ------------------------------------------------------------------------------------------------------------------
    def setWeightColor(self, value):
        """
        This will set the colour of the weight attribute of a mass group

        :param value: Value (between zero and one, one being the most intense)
        :type value: float

        :return: None
        """
        # -- We set the colour using a stylesheet, so build the string and apply it
        v = 'QDoubleSpinBox {background-color: rgba(%s, 20, 20, 100);}' % value
        self.ui.massSpinBox.setStyleSheet(v)

    # ------------------------------------------------------------------------------------------------------------------
    def updateWeight(self):
        """
        This is triggered when we need to push our current ui value onto the
        node itself

        :return:
        """
        # -- Apply the value to the node
        core.set_section_weight(
            mass_node=self._massNode,
            section_name=self.name,
            weight=self.ui.massSpinBox.value()
        )

        # -- Emit the fact that we have done this so anything
        # -- else has a chance to respond to it
        self.WeightChanged.emit()

    # ------------------------------------------------------------------------------------------------------------------
    def populateInfluenceList(self):
        """
        Looks at all the influences connected to a section and represents them
        in the mass group

        :return:
        """
        # -- Clear the current list
        self.ui.influenceList.clear()

        # -- Get the list of influences, which returns PyNode's and
        # -- add each one to the list
        for influence in core.get_section_influences(self._massNode, self.name):
            self.ui.influenceList.addItem(influence.name())

    # ------------------------------------------------------------------------------------------------------------------
    def addInfluence(self):
        """
        This will go through the flow of adding an influence to the influence list

        :return:
        """
        # -- If nothing is selected we cannot do anything
        if not pm.selected():
            return

        # -- For each selected item we add the influence
        for item in pm.selected():
            core.add_section_influence(
                mass_node=self._massNode,
                section_name=self.name,
                influence=item,
            )

        # -- Trigger a repopulation of the influence list
        self.populateInfluenceList()

    # ------------------------------------------------------------------------------------------------------------------
    def removeInfluence(self):
        """
        Remove an influence from the influence list

        :return:
        """
        # -- If no influence is selected then we do nothing
        if not self.ui.influenceList.currentItem():
            return

        # -- Take the selected item out of the ui
        item = self.ui.influenceList.takeItem(
            self.ui.influenceList.currentRow(),
        )

        # -- Request that item is removed from the nodes influence
        core.remove_section_influence(
            mass_node=self._massNode,
            section_name=self.name,
            influence=item.text(),
        )

    # ------------------------------------------------------------------------------------------------------------------
    def rename(self):
        """
        Invokes the process which allows the user to rename the given section
        :return:
        """
        # -- Request a new name for the section
        newName = qute.utilities.request.text(
            title='Section Rename',
            label='New name to assign to this section. The name must not already be used by another mass group',
            parent=self,
            text=self.name,
        )

        # -- If the new name already exists, then we cannot assign it
        if newName in core.get_section_names(self._massNode):
            qute.utilities.request.message(
                title='Section Name is not unique',
                label='You must specify a unique section name. This name is already in use',
                parent=self,
            )
            return

        # -- Request the name change
        core.set_section_name(
            mass_node=self._massNode,
            section_name=self.name,
            new_name=newName,
        )

        # -- Update the name defined in the class, as well as the name
        # -- defined in the group box
        self.name = newName
        self.ui.groupBox.setTitle(newName)

    # ------------------------------------------------------------------------------------------------------------------
    def delete(self):
        """
        Invokes the flow to remove a section

        :return:
        """

        # -- This is a big operation, so we must absolutely check that the user
        # -- really wants to remove the section
        confirmation = qute.utilities.request.confirmation(
            title='Delete Section',
            label='Are you sure you want to delete {section_name}'.format(section_name=self.name),
            parent=self,
        )

        # -- If they cancelled, then we do not continue
        if not confirmation:
            return

        # -- Request the mass group be removed
        core.remove_mass_group(
            mass_node=self._massNode,
            section_name=self.name,
        )

        # -- Emit the fact that we have done this to allow
        # -- anything else to react to the event
        self.IsDeleted.emit()
