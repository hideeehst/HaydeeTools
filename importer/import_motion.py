from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper

import struct
import binascii
import os

from mathutils import Quaternion, Vector
from ..HaydeeUtils import *

# --------------------------------------------------------------------------------
# .motion importer
# --------------------------------------------------------------------------------


# Helper for commong logic
def read_motion_bones(memData, boneCount, numFrames, TRACK_SIZE, KEY_SIZE,
                      TRACK_OFFSET, KEY_OFFSET):
    unpack_bone = struct.Struct('<32sI').unpack
    unpack_key = struct.Struct('3f4f').unpack
    bones, boneNames = dict(), []
    for n in range(boneCount):
        offset = TRACK_OFFSET + (TRACK_SIZE * n)
        (name, firstKey) = unpack_bone(memData[offset:offset + TRACK_SIZE])
        name = boneRenameBlender(readStrA_term(0, 32, memoryview(name))[0])
        keys = []
        for k in range(firstKey, firstKey + numFrames):
            offset = KEY_OFFSET + (KEY_SIZE * k)
            (x, y, z, qx, qz, qy,
             qw) = unpack_key(memData[offset:offset + KEY_SIZE])
            keys.append((x, y, z, qx, qz, qy, qw))
        bones[name] = keys
        boneNames.append(name)
    return (boneNames, bones)


def read_motion(operator, context, filepath):
    armature = find_armature(operator, context)
    if not armature:
        return {'FINISHED'}

    with open(filepath, "rb") as a_file:
        data = a_file.read()
    mview = memoryview(data)

    (entries, serialSize, assType) = struct.unpack('<ii6s', mview[20:34])
    assType, sig = assType.decode("latin"), sig_check(mview)
    propMap, numFrames = None, None
    unpack_int = struct.Struct('<i').unpack
    unpack_entry = struct.Struct('<32siiii').unpack

    if (sig == Signature.HD_CHUNK and assType == 'motion'):
        print('Signature:', Signature.HD_CHUNK.name)
        propMap = dict(numFrames={'reader': lambda x: unpack_int(x)[0]},
                       duration={'reader': lambda x: unpack_int(x)[0]},
                       numKeys={'reader': lambda x: unpack_int(x)[0]},
                       numTracks={'reader': lambda x: unpack_int(x)[0]},
                       numEvents={'reader': lambda x: unpack_int(x)[0]},
                       keys={'reader': lambda x: True},
                       tracks={'reader': lambda x: True},
                       events={'reader': lambda x: False})

        dataOffset = 28 + (entries * 48)

        for x in range(1, entries):
            sPos = 28 + (x * 48)
            (name, size, offset, numSubs,
             subs) = unpack_entry(mview[sPos:sPos + 48])
            name = readStrA_term(0, 32, memoryview(name))[0]
            propMap[name].update(
                dict(
                    zip(['size', 'offset', 'numSubs', 'subs', 'hasValue'],
                        [size, offset, numSubs, subs, size > 0])))

        for key, value in propMap.items():
            if (value.get("hasValue")):
                (f, lSize, lOff) = (value['reader'], value['size'],
                                    value['offset'])
                lOff = dataOffset + lOff
                value["value"] = f(mview[lOff:lOff + lSize])

        numFrames = propMap['numFrames']['value']
        boneCount = propMap['numTracks']['value']
        trackSize = int(propMap['tracks']['size'] / boneCount)
        keySize = int(propMap['keys']['size'] / propMap['numKeys']['value'])
        trackOffset = 28 + (entries * 48) + int(propMap['tracks']['offset'])
        keyOffset = 28 + (entries * 48) + int(propMap['keys']['offset'])
        (boneNames, bones) = read_motion_bones(mview, boneCount, numFrames,
                                               trackSize, keySize, trackOffset,
                                               keyOffset)

    elif (sig == Signature.HD_MOTION):
        print('Signature:', Signature.HD_MOTION.name)
        KEY_SIZE = 28
        TRACK_SIZE = 36

        (keyCount, boneCount, firstFrame, duration, numFrames,
         dataSize) = struct.unpack('6I', data[20:44])
        keyOffset = 44
        trackOffset = 44 + int(KEY_SIZE * keyCount)
        (boneNames, bones) = read_motion_bones(mview, boneCount, numFrames,
                                               TRACK_SIZE, KEY_SIZE,
                                               trackOffset, keyOffset)

    else:
        print("Unrecognized signature or asset type: [%s], %s" %
              (binascii.hexlify(mview[0:16]), assType))
        operator.report({'ERROR'}, "Unrecognized file format")
        return {'FINISHED'}

    boneNames.reverse()

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    # armature.hide = False
    armature.select_set(state=True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    #animation name. create new action and push it in the nla tracks
    action = bpy.data.actions.new(os.path.basename(filepath))

    object = context.active_object
    object.animation_data_create()
    object.animation_data.action = action

    track = object.animation_data.nla_tracks.new()
    strip = track.strips.new(action.name, int(action.frame_range[0]), action)

    wm = bpy.context.window_manager
    wm.progress_begin(0, numFrames)

    r = Quaternion([0, 0, 1], pi / 2).to_matrix().to_4x4()

    context.scene.frame_start = 1
    context.scene.frame_end = numFrames
    for pose in context.selected_pose_bones:
        pose.bone.select = False
    for frame in range(1, numFrames + 1):
        wm.progress_update(frame - 1)
        context.scene.frame_set(frame)
        for name in boneNames:
            bone_name = name
            if not (bone_name in armature.data.bones):
                print("WARNING: Bone named " + bone_name +
                      " not found in armature")
                continue

            bone = armature.data.bones[bone_name]
            pose = armature.pose.bones[bone_name]
            if not bone:
                continue
            bone.select = True

            (x, y, z, qx, qz, qy, qw) = bones[bone_name][frame - 1]

            origin = Vector([-z, x, y])
            q = Quaternion([qw, -qy, qx, qz])
            m = q.to_matrix().to_4x4()
            m.translation = origin

            if bone.parent:
                m = pose.parent.matrix @ m

            pose.matrix = m

        # Rotate bone not in 'SK_Root' chain
        rootBones = [
            rootBone for rootBone in armature.pose.bones
            if rootBone.parent is None
        ]
        for poseBone in rootBones:
            bone_name = poseBone.name
            data = bones.get(bone_name)
            if data:
                (x, y, z, qx, qz, qy, qw) = bones[bone_name][frame - 1]
                origin = Vector([-z, x, y])
                q = Quaternion([qw, -qy, qx, qz])
                m = q.to_matrix().to_4x4()
                m.translation = origin
                poseBone.matrix = r @ m

        bpy.ops.anim.keyframe_insert(type='Rotation')
        bpy.ops.anim.keyframe_insert(type='Location')
        for name, keys in bones.items():
            if not (bone_name in armature.data.bones):
                continue
            bone = armature.data.bones[bone_name]
            if not bone:
                continue
            bone.select = False

    bpy.ops.object.mode_set(mode='OBJECT')

    object.animation_data.action = None
    strip.frame_end = strip.action.frame_range[1]
    wm.progress_end()
    return {'FINISHED'}


class ImportHaydeeMotion(Operator, ImportHelper):
    bl_idname = "haydee_importer.motion"
    bl_label = "Import Haydee Motion (.motion)"
    bl_description = "Import a Haydee Motion"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".motion"
    directory: StringProperty(subtype='DIR_PATH')
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    filter_glob: StringProperty(
        default="*.motion",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        for filepath in self.files:
            read_motion(self, context,
                        os.path.join(self.directory, filepath.name))
        return {"FINISHED"}
