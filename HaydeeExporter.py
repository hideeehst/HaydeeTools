# <pep8 compliant>

import bpy
import os
import re
from .HaydeeUtils import d, find_armature, file_format_prop
from .HaydeeUtils import boneRenameHaydee, materials_list, stripName, NAME_LIMIT
from .exporter import export_dmesh
from . import HaydeeMenuIcon
from bpy_extras.wm_utils.progress_report import (
    ProgressReport,
    ProgressReportSubstep,
)

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from mathutils import Quaternion, Vector, Matrix
from math import pi


# ------------------------------------------------------------------------------
#  .dskel exporter
# ------------------------------------------------------------------------------

def write_dskel(operator, context, filepath):
    armature = find_armature(operator, context)
    if armature is None:
        return {'FINISHED'}

    bones = armature.data.bones

    f = open(filepath, 'w', encoding='utf-8')
    f.write("HD_DATA_TXT 300\n\n")
    f.write("skeleton %d\n{\n" % len(bones))
    r = Quaternion([0, 0, 1], -pi / 2)
    for bone in bones:
        head = bone.head_local.xzy
        q = bone.matrix_local.to_quaternion()
        q = (q @ r)
        q = Quaternion([-q.w, q.x, q.y, -q.z])

        bone_name = boneRenameHaydee(bone.name)

        bone_side = bone.length / 4
        f.write("\tbone %s\n\t{\n" % bone_name)
        f.write("\t\twidth %s;\n" % d(bone_side))
        f.write("\t\theight %s;\n" % d(bone_side))
        f.write("\t\tlength %s;\n" % d(bone.length))

        if bone.parent:
            parent_name = boneRenameHaydee(bone.parent.name)
            f.write("\t\tparent %s;\n" % parent_name)
            head = bone.head_local
            head = Vector((head.x, head.z, head.y))

        head = Vector((-head.x, head.y, -head.z))
        q = Quaternion([q.x, q.z, q.y, q.w])
        f.write("\t\torigin %s %s %s;\n" % (d(head.x), d(head.y), d(head.z)))
        f.write("\t\taxis %s %s %s %s;\n" % (d(q.w), d(q.x), d(q.y), d(q.z)))
        f.write("\t}\n")

    f.write("}\n")
    f.close()
    return {'FINISHED'}


class ExportHaydeeDSkel(Operator, ExportHelper):
    bl_idname = "haydee_exporter.dskel"
    bl_label = "Export Haydee DSkel (.dskel)"
    bl_options = {'REGISTER'}
    filename_ext = ".dskel"
    filter_glob: StringProperty(
        default="*.dskel",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return write_dskel(self, context, self.filepath)


# --------------------------------------------------------------------------------
#  .dpose exporter
# --------------------------------------------------------------------------------

def write_dpose(operator, context, filepath):
    armature = find_armature(operator, context)
    if armature is None:
        return {'FINISHED'}

    bones = armature.pose.bones

    f = open(filepath, 'w', encoding='utf-8')
    f.write("HD_DATA_TXT 300\n\n")
    f.write("pose\n{\n\tnumTransforms %d;\n" % len(bones))
    r = Quaternion([0, 0, 1], pi / 2)
    for bone in bones:
        head = bone.head.xzy
        q = bone.matrix.to_quaternion()
        q = -(q @ r)
        if bone.parent:
            head = bone.parent.matrix.inverted().to_quaternion() @ (bone.head - bone.parent.head)
            head = Vector((-head.y, head.z, head.x))
            q = (bone.parent.matrix.to_3x3().inverted() @ bone.matrix.to_3x3()).to_quaternion()
            q = Quaternion([q.z, -q.y, q.x, -q.w])

        f.write("\ttransform %s %s %s %s %s %s %s %s;\n" % (
            boneRenameHaydee(bone.name),
            d(-head.x), d(head.y), d(-head.z),
            d(q.x), d(-q.w), d(q.y), d(q.z)))

    f.write("}\n")
    f.close()
    return {'FINISHED'}


class ExportHaydeeDPose(Operator, ExportHelper):
    bl_idname = "haydee_exporter.dpose"
    bl_label = "Export Haydee DPose (.dpose)"
    bl_options = {'REGISTER'}
    filename_ext = ".dpose"
    filter_glob: StringProperty(
        default="*.dpose",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return write_dpose(self, context, self.filepath)


# --------------------------------------------------------------------------------
#  .dmot exporter
# --------------------------------------------------------------------------------

def write_dmot(operator, context, filepath):
    armature = find_armature(operator, context)
    if armature is None:
        return {'FINISHED'}

    bones = armature.pose.bones
    keyframeCount = bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1
    previousFrame = bpy.context.scene.frame_current
    wm = bpy.context.window_manager

    lines = {}
    for bone in bones:
        name = boneRenameHaydee(bone.name)
        lines[name] = []

    r = Quaternion([0, 0, 1], pi / 2)
    wm.progress_begin(0, keyframeCount)
    for frame in range(keyframeCount):
        wm.progress_update(frame)
        context.scene.frame_set(frame + bpy.context.scene.frame_start)
        for bone in bones:

            head = bone.head.xzy
            q = bone.matrix.to_quaternion()
            q = -(q @ r)
            if bone.parent:
                head = bone.parent.matrix.inverted().to_quaternion() @ (bone.head - bone.parent.head)
                head = Vector((-head.y, head.z, head.x))
                q = (bone.parent.matrix.to_3x3().inverted() @ bone.matrix.to_3x3()).to_quaternion()
                q = Quaternion([-q.z, -q.y, q.x, -q.w])

            name = boneRenameHaydee(bone.name)
            lines[name].append("\t\tkey %s %s %s %s %s %s %s;\n" % (
                d(-head.x), d(head.y), d(-head.z),
                d(q.x), d(q.w), d(q.y), d(q.z)))
    wm.progress_end()

    context.scene.frame_set(previousFrame)

    f = open(filepath, 'w', encoding='utf-8')
    f.write("HD_DATA_TXT 300\n\n")
    f.write("motion\n{\n")
    f.write("\tnumTracks %d;\n" % len(bones))
    f.write("\tnumFrames %d;\n" % keyframeCount)
    f.write("\tframeRate %g;\n" % context.scene.render.fps)
    for bone in bones:
        name = boneRenameHaydee(bone.name)
        f.write("\ttrack %s\n\t{\n" % name)
        f.write("".join(lines[name]))
        f.write("\t}\n")
    f.write("}\n")
    f.close()
    return {'FINISHED'}


class ExportHaydeeDMotion(Operator, ExportHelper):
    bl_idname = "haydee_exporter.dmot"
    bl_label = "Export Haydee DMotion (.dmot)"
    bl_options = {'REGISTER'}
    filename_ext = ".dmot"
    filter_glob: StringProperty(
        default="*.dmot",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return write_dmot(self, context, self.filepath)


# --------------------------------------------------------------------------------
#  .dmesh exporter
# --------------------------------------------------------------------------------

def write_dmesh(operator, context, filepath, export_skeleton,
                apply_modifiers, selected_only, separate_files,
                ignore_hidden, SELECTED_MATERIAL, file_format):

    return export_dmesh.write_dmesh(operator, context, filepath, export_skeleton,
                apply_modifiers, selected_only, separate_files,
                ignore_hidden, SELECTED_MATERIAL, file_format)

class ExportHaydeeDMesh(Operator, ExportHelper):
    bl_idname = "haydee_exporter.dmesh"
    bl_label = "Export Haydee dmesh"
    bl_options = {'REGISTER'}
    filename_ext = ".dmesh"
    filter_glob: StringProperty(
        default="*.dmesh",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    file_format: file_format_prop

    selected_only: BoolProperty(
        name="Selected only",
        description="Export only selected objects (if nothing is selected, full scene will be exported regardless of this setting)",
        default=True,
    )
    separate_files: BoolProperty(
        name="Export to Separate Files",
        description="Export each object to a separate file",
        default=False,
    )
    ignore_hidden: BoolProperty(
        name="Ignore hidden",
        description="Ignore hidden objects",
        default=True,
    )
    apply_modifiers: BoolProperty(
        name="Apply modifiers",
        description="Apply modifiers before exporting",
        default=True,
    )
    export_skeleton: BoolProperty(
        name="Export skeleton",
        description="Export skeleton and vertex weights",
        default=True,
    )
    material: EnumProperty(
        name="Material",
        description="Material to export",
        items=materials_list
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        return write_dmesh(self, context, self.filepath, self.export_skeleton,
                           self.apply_modifiers, self.selected_only, self.separate_files,
                           self.ignore_hidden, self.material, self.file_format)


# --------------------------------------------------------------------------------
#  Initialization & menu
# --------------------------------------------------------------------------------
class HaydeeExportSubMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_haydee_export_submenu"
    bl_label = "Haydee"

    def draw(self, context):
        layout = self.layout
        layout.operator(ExportHaydeeDMesh.bl_idname, text="Haydee DMesh (.dmesh)")
        layout.operator(ExportHaydeeDSkel.bl_idname, text="Haydee DSkel (.dskel)")
        layout.operator(ExportHaydeeDPose.bl_idname, text="Haydee DPose (.dpose)")
        layout.operator(ExportHaydeeDMotion.bl_idname, text="Haydee DMotion (.dmot)")


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
