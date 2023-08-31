import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ExportHelper
from ..HaydeeUtils import *
from mathutils import Quaternion, Vector
from math import pi
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
                head = bone.parent.matrix.inverted().to_quaternion() @ (
                    bone.head - bone.parent.head)
                head = Vector((-head.y, head.z, head.x))
                q = (bone.parent.matrix.to_3x3().inverted()
                     @ bone.matrix.to_3x3()).to_quaternion()
                q = Quaternion([-q.z, -q.y, q.x, -q.w])

            name = boneRenameHaydee(bone.name)
            lines[name].append("\t\tkey %s %s %s %s %s %s %s;\n" %
                               (d(-head.x), d(head.y), d(-head.z), d(
                                   q.x), d(q.w), d(q.y), d(q.z)))
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
