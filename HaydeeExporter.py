# <pep8 compliant>

import bpy
from . import HaydeeMenuIcon
from .exporter.export_dskel import ExportHaydeeDSkel
from .exporter.export_dmesh import ExportHaydeeDMesh
from .exporter.export_dmotion import ExportHaydeeDMotion
from .exporter.export_dpose import ExportHaydeeDPose

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.


# --------------------------------------------------------------------------------
#  Initialization & menu
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


def menu_func_export(self, context):
    my_icon = HaydeeMenuIcon.custom_icons["main"]["haydee_icon"]
    self.layout.menu(HaydeeExportSubMenu.bl_idname, icon_value=my_icon.icon_id)


# --------------------------------------------------------------------------------
#  Register
# --------------------------------------------------------------------------------
def register():
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.haydee_exporter.motion('INVOKE_DEFAULT')
