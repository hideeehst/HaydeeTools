import bpy
from bpy.props import StringProperty, BoolProperty
from bpy.types import Operator
from . import HaydeeMenuIcon
from ..haydee_exporter import *
from ..haydee_importer import *

# --------------------------------------------------------------------------------
#  Exporter Initialization & menu
# --------------------------------------------------------------------------------


class HaydeeExportSubMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_haydee_export_submenu"
    bl_label = "Haydee"

    def draw(self, context):
        layout = self.layout
        layout.operator(ExportHaydeeDMesh.bl_idname,
                        text="Haydee DMesh (.dmesh)")
        layout.operator(ExportHaydeeDSkel.bl_idname,
                        text="Haydee DSkel (.dskel)")
        layout.operator(ExportHaydeeDPose.bl_idname,
                        text="Haydee DPose (.dpose)")
        layout.operator(ExportHaydeeDMotion.bl_idname,
                        text="Haydee DMotion (.dmot)")


def menu_func_export(self:bpy.types.Menu, context):
    my_icon = HaydeeMenuIcon.getHaydeeIconValue()
    self.layout.menu(HaydeeExportSubMenu.bl_idname, icon_value=my_icon)



# --------------------------------------------------------------------------------
# Importer Initialization & menu
# --------------------------------------------------------------------------------


class HaydeeImportSubMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_haydee_import_submenu"
    bl_label = "Haydee"

    def draw(self, context):
        layout = self.layout
        layout.operator(ImportHaydeeMesh.bl_idname, text="Haydee Mesh (.mesh)")
        layout.operator(ImportHaydeeDMesh.bl_idname,
                        text="Haydee DMesh (.dmesh)")
        layout.operator(ImportHaydeeSkel.bl_idname, text="Haydee Skel (.skel)")
        layout.operator(ImportHaydeeDSkel.bl_idname,
                        text="Haydee DSkel (.dskel)")
        layout.operator(ImportHaydeeSkin.bl_idname, text="Haydee Skin (.skin)")
        layout.operator(ImportHaydeeMaterial.bl_idname,
                        text="Haydee Material(.mtl)")
        layout.operator(ImportHaydeeMotion.bl_idname,
                        text="Haydee Motion (.motion)")
        layout.operator(ImportHaydeeDMotion.bl_idname,
                        text="Haydee DMotion (.dmot)")
        layout.operator(ImportHaydeePose.bl_idname, text="Haydee Pose (.pose)")
        layout.operator(ImportHaydeeDPose.bl_idname,
                        text="Haydee DPose (.dpose)")
        layout.operator(ImportHaydeeOutfit.bl_idname,
                        text="Haydee Outfit (.outfit)")


def menu_func_import(self, context):
    my_icon = HaydeeMenuIcon.getHaydeeIconValue()
    self.layout.menu(HaydeeImportSubMenu.bl_idname, icon_value=my_icon)


# --------------------------------------------------------------------------------
# Register
# --------------------------------------------------------------------------------


def register():
    bpy.utils.register_class(HaydeeImportSubMenu)
    bpy.utils.register_class(HaydeeExportSubMenu)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(HaydeeImportSubMenu)
    bpy.utils.unregister_class(HaydeeExportSubMenu)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
