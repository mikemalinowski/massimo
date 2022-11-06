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
import os
import sys
import shutil

import maya.cmds as mc
import maya.mel as mm


# ----------------------------------------------------------------------------------------------------------------------
# noinspection PyPep8Naming
def onMayaDroppedPythonFile(obj):

    # -- Start by ensuring that we're actually running in maya
    if 'maya.exe' not in sys.executable:
        return

    # -- Ensure we have the massimo module block and the mod file
    new_massimo_module = os.path.join(
        os.path.dirname(__file__),
        'massimo',
    )

    if not os.path.exists(new_massimo_module):
        message = 'Could not locate massimo module. This should sit next to the install file. Expected location : %s' % new_massimo_module
        mc.confirmDialog(
            title='Massimo Install Error',
            message=message,
            button='OK',
        )
        mc.warning(message)
        return

    # -- Check we have the mod file
    new_mod_file = os.path.join(
        os.path.dirname(__file__),
        'massimo.mod',
    )

    if not os.path.exists(new_mod_file):
        message = 'Could not locate the massimo mod file. This should sit next to the install file. Expected location : %s' % new_mod_file
        mc.confirmDialog(
            title='Massimo Install Error',
            message=message,
            button='OK',
        )
        mc.warning(message)
        return

    # -- Ensure we can construct the destination location
    modules_location = os.path.join(
        os.environ['MAYA_APP_DIR'],
        'modules',
    )

    massimo_destination = os.path.join(
        modules_location,
        'massimo',
    )
    mod_file_desintation = os.path.join(
        modules_location,
        'massimo.mod',
    )

    # -- Check if the massimo plugin already exists, and if it does we need to remove
    # -- it
    if os.path.exists(massimo_destination) or os.path.exists(mod_file_desintation):

        result = mc.confirmDialog(
            title='Massimo Install',
            message='A previous version has been detected, if you proceed this will remove the old version. Continue?',
            button=['Yes', 'No'],
            defaultButton='Yes',
            cancelButton='No',
            dismissString='No',
        )

        if result == 'No':
            return

        # -- Remove the locations
        if os.path.exists(mod_file_desintation):
            os.remove(mod_file_desintation)

        if os.path.exists(massimo_destination):
            shutil.rmtree(massimo_destination)

    if os.path.exists(massimo_destination) or os.path.exists(mod_file_desintation):
        message = 'Could not remove the old install. It may be because the plugin is loaded. Please close maya and delete it manually'
        mc.confirmDialog(
            title='Massimo Install Error',
            message=message,
            button='OK',
        )
        mc.warning(message)
        return

    # -- We can now start coping our files
    shutil.copytree(
        new_massimo_module,
        massimo_destination,
    )
    shutil.copy(
        new_mod_file,
        mod_file_desintation,
    )

    try:

        # -- Load the module
        mc.loadModule(load=mod_file_desintation)
        mc.loadModule(allModules=True)

        # -- Update the paths, because the loadModule funciton does not do this for us!?
        os.environ['MAYA_SCRIPT_PATH'] = os.environ['MAYA_SCRIPT_PATH'] + ';' + os.path.join(
            massimo_destination,
            'scripts'
        )

        sys.path.append(
            os.path.join(
                massimo_destination,
                'scripts'
            )
        )

        os.environ['MAYA_PLUG_IN_PATH'] = os.environ['MAYA_PLUG_IN_PATH'] + ';' + os.path.join(
            massimo_destination,
            'plug-ins'
        )

        # -- Lets register massimo in the menu
        mm.eval('source \"massimo_menu.mel\";RegisterMassimoMenu();')

        # -- On first install we have to put this in the path. Maya will do this
        if 'massimo' in sys.modules:
            del sys.modules['massimo']

        # -- Lets launch our tool!
        import massimo
        mc.loadPlugin("massimo_runtime.py")
        massimo.launch()

        message = 'The install completed. You can launch Massimo from the Animation/Visualize menu'
        mc.confirmDialog(
            title='Massimo Install Completed',
            message=message,
            button='OK',
        )
        mc.warning(message)

    except:
        print(str(sys.exc_info()))
        message = 'The install completed but massimo could not launch. Please try restarting Maya.'
        mc.confirmDialog(
            title='Massimo Install Error',
            message=message,
            button='OK',
        )
        mc.warning(message)
