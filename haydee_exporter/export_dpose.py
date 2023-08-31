from math import pi
from bpy.props import *
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector, Quaternion
from ..HaydeeUtils import *

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
            head = bone.parent.matrix.inverted().to_quaternion() @ (
                bone.head - bone.parent.head)
            head = Vector((-head.y, head.z, head.x))
            q = (bone.parent.matrix.to_3x3().inverted()
                 @ bone.matrix.to_3x3()).to_quaternion()
            q = Quaternion([q.z, -q.y, q.x, -q.w])

        f.write("\ttransform %s %s %s %s %s %s %s %s;\n" %
                (boneRenameHaydee(bone.name), d(-head.x), d(
                    head.y), d(-head.z), d(q.x), d(-q.w), d(q.y), d(q.z)))

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
