# <pep8 compliant>

# Native imports

# Blender and own imports
import bpy
from . import HaydeeMenuIcon

#Importers
from .importer.import_dskel import ImportHaydeeDSkel
from .importer.import_dmesh import ImportHaydeeDMesh
from .importer.import_dmotion import ImportHaydeeDMotion
from .importer.import_dpose import ImportHaydeeDPose
from .importer.import_material import ImportHaydeeMaterial
from .importer.import_mesh import ImportHaydeeMesh
from .importer.import_motion import ImportHaydeeMotion
from .importer.import_outfit import ImportHaydeeOutfit
from .importer.import_pose import ImportHaydeePose
from .importer.import_skeleton import ImportHaydeeSkel
from .importer.import_skin import ImportHaydeeSkin

# --------------------------------------------------------------------------------
# Initialization & menu
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
    my_icon = HaydeeMenuIcon.custom_icons["main"]["haydee_icon"]
    self.layout.menu(HaydeeImportSubMenu.bl_idname, icon_value=my_icon.icon_id)


# --------------------------------------------------------------------------------
# Register
# --------------------------------------------------------------------------------
def register():
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.haydee_importer.motion('INVOKE_DEFAULT')
