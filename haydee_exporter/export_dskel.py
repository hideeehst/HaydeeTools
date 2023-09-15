from math import pi
from bpy.props import *
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from mathutils import Vector, Quaternion
from ..HaydeeUtils import *

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

    def execute(self, context):
        return write_dskel(self, context, self.filepath)
