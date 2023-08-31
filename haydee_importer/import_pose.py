from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import struct
from mathutils import Quaternion, Vector
from ..HaydeeUtils import *

# --------------------------------------------------------------------------------
# .pose importer
# --------------------------------------------------------------------------------


def read_pose(operator, context, filepath):

    armature = find_armature(operator, context)
    if not armature:
        return {'FINISHED'}

    with open(filepath, "rb") as a_file:
        data = a_file.read()

    SIGNATURE_SIZE = 28
    CHUNK_SIZE = 48
    SIZE2 = 60

    (signature, chunkCount, totalSize) = struct.unpack('20sII',
                                                       data[0:SIGNATURE_SIZE])
    signature = decodeText(signature)
    print("Signature:", signature)
    if signature != 'HD_CHUNK':
        print("Unrecognized signature: %s" % signature)
        operator.report({'ERROR'}, "Unrecognized file format")
        return {'FINISHED'}

    offset = SIGNATURE_SIZE + (CHUNK_SIZE * chunkCount)
    boneCount = struct.unpack('I', data[offset:offset + 4])
    boneCount = boneCount[0]

    bones = {}
    boneNames = []
    delta = SIGNATURE_SIZE + (CHUNK_SIZE * chunkCount) + 4
    for n in range(boneCount):
        offset = delta + (SIZE2 * n)
        (x, y, z, qx, qz, qy, qw,
         name) = struct.unpack('3f4f32s', data[offset:offset + SIZE2])
        bonePose = (x, y, z, qx, qz, qy, qw)
        name = decodeText(name)
        name = boneRenameBlender(name)
        bones[name] = bonePose
        boneNames.append(name)

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    # armature.hide = False
    armature.select_set(state=True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')

    wm = bpy.context.window_manager
    wm.progress_begin(0, boneCount)

    r = Quaternion([0, 0, 1], pi / 2)

    for i, bone_name in enumerate(boneNames):
        wm.progress_update(i)
        if not (bone_name in armature.data.bones):
            print("WARNING: Bone named " + bone_name +
                  " not found in armature")
            continue

        bone = armature.data.bones.get(bone_name)
        pose = armature.pose.bones.get(bone_name)
        if not bone:
            continue
        bone.select = True

        (x, y, z, qx, qz, qy, qw) = bones[bone_name]

        origin = Vector([-z, x, y])
        q = Quaternion([qw, -qy, qx, qz])
        m = q.to_matrix().to_4x4()
        m.translation = origin

        if bone.parent:
            m = pose.parent.matrix @ m
        else:
            origin = Vector([-x, -z, y])
            m.translation = origin
            m = m @ r.to_matrix().to_4x4()

        pose.matrix = m

    bpy.ops.object.mode_set(mode='OBJECT')
    wm.progress_end()
    return {'FINISHED'}


class ImportHaydeePose(Operator, ImportHelper):
    bl_idname = "haydee_importer.pose"
    bl_label = "Import Haydee Pose (.pose)"
    bl_description = "Import a Haydee Pose"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".pose"
    filter_glob: StringProperty(
        default="*.pose",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_pose(self, context, self.filepath)
