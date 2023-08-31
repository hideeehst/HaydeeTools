# <pep8 compliant>

"""Blender Addon. Haydee 1 & 2 importer/exporter."""

bl_info = {
    "name": "Haydee 1 & 2 I/O Scripts",
    "author": "johnzero7, Pooka, Kein",
    "version": (1, 3, 1),
    "blender": (2, 80, 0),
    "location": "File > Import-Export > HaydeeTools",
    "description": "Import-Export scripts for Haydee",
    "warning": "",
    "wiki_url": "https://github.com/johnzero7/HaydeeTools",
    "tracker_url": "https://github.com/johnzero7/HaydeeTools/issues",
    "category": "Import-Export",
}

import bpy
from . import haydee_importer as HaydeeImporter
from . import haydee_exporter as HaydeeExporter
from . import HaydeePreferences
from .ui import HaydeeMenuIcon
from .ui import HaydeePanels
from .ui import HaydeeMenus
from . import HaydeeUtils
from . import addon_updater_ops

# Modules with register and unregister functions
modulesToRegister = [
    HaydeeUtils, HaydeePanels, HaydeeMenus, HaydeePreferences, HaydeeMenuIcon,HaydeeImporter,HaydeeExporter
]

def register():
    """Register addon classes."""

    try:unregister()
    except:pass

    for module in modulesToRegister:
        module.register()

    addon_updater_ops.register(bl_info)


def unregister():
    """Unregister addon classes."""
    for module in reversed(modulesToRegister):
        module.unregister()

    addon_updater_ops.unregister()
