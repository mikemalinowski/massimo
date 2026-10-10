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
from maya import cmds

from ...vendor import qtility
from Qt import QtGui, QtWidgets
from .. import resources


# ----------------------------------------------------------------------------------------------------------------------
# noinspection PyUnresolvedReferences,PyPep8Naming
class MassimoNodeSettings(QtWidgets.QDialog):
    """
    The settings dialog allows the user to interact and alter the state of the
    massimo node
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, massNode, parent=None):
        super(MassimoNodeSettings, self).__init__(parent=parent)

        # -- Store our mass node
        self._massNode = massNode

        # -- Set our branding
        self.setWindowTitle('Massimo Node Settings')

        self.setWindowIcon(
            QtGui.QIcon(
                resources.get('massimo.png')
            )
        )

        # -- Generate the default layout
        self.setLayout(
            qtility.layouts.slimify(
                QtWidgets.QVBoxLayout(),
            ),
        )

        # -- Load in the ui file
        self.ui = qtility.designer.load(
            resources.get('settings.ui'),
        )
        self.layout().addWidget(self.ui)

        # -- Populate the settings based on the node
        self.readSettings()

        # -- Define our signals and slots, so we always store the change
        self.ui.calculateCheckBox.stateChanged.connect(self.serialiseSettings)
        self.ui.drawSphereCheckBox.stateChanged.connect(self.serialiseSettings)
        self.ui.drawVerticalLineCheckBox.stateChanged.connect(self.serialiseSettings)
        self.ui.drawDebugLinesCheckBox.stateChanged.connect(self.serialiseSettings)
        self.ui.sphereSizeSpinBox.valueChanged.connect(self.serialiseSettings)

    # ------------------------------------------------------------------------------------------------------------------
    def serialiseSettings(self):
        """
        In this function we read the UI and apply it to the node in the maya scene

        :return:
        """
        cmds.setAttr('{}.drawSphere'.format(self._massNode), self.ui.drawSphereCheckBox.isChecked())
        cmds.setAttr('{}.drawVerticalLine'.format(self._massNode), self.ui.drawVerticalLineCheckBox.isChecked())
        cmds.setAttr('{}.drawDebuggingLines'.format(self._massNode), self.ui.drawDebugLinesCheckBox.isChecked())
        cmds.setAttr('{}.calculate'.format(self._massNode), self.ui.calculateCheckBox.isChecked())
        cmds.setAttr('{}.sphereSize'.format(self._massNode), self.ui.sphereSizeSpinBox.value())

    # ------------------------------------------------------------------------------------------------------------------
    def readSettings(self):
        """
        In this function we read the node within the scene and update all the values in the ui
        :return:
        """
        self.ui.drawSphereCheckBox.setChecked(cmds.getAttr('{}.drawSphere'.format(self._massNode)))
        self.ui.drawVerticalLineCheckBox.setChecked(cmds.getAttr('{}.drawVerticalLine'.format(self._massNode)))
        self.ui.drawDebugLinesCheckBox.setChecked(cmds.getAttr('{}.drawDebuggingLines'.format(self._massNode)))
        self.ui.calculateCheckBox.setChecked(cmds.getAttr('{}.calculate'.format(self._massNode)))
        self.ui.sphereSizeSpinBox.setValue(cmds.getAttr('{}.sphereSize'.format(self._massNode)))
