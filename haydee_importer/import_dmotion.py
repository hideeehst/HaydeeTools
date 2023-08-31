from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import io
from mathutils import Quaternion, Vector
from ..HaydeeUtils import *

# --------------------------------------------------------------------------------
# .dmot importer
# --------------------------------------------------------------------------------


def read_dmotion(operator, context, filepath):
    armature = find_armature(operator, context)
    if not armature:
        return {'FINISHED'}

    print('dpose:', filepath)
    with ProgressReport(context.window_manager) as progReport:
        with ProgressReportSubstep(progReport, 4, "Importing dpose",
                                   "Finish Importing dpose") as progress:
            if (bpy.context.mode != 'OBJECT'):
                bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.select_all(action='DESELECT')
            print("Importing dpose: %s" % filepath)

            progress.enter_substeps(1, "Read file")
            data = None
            encoding = find_encoding(filepath)
            with open(filepath, "r", encoding=encoding) as a_file:
                data = io.StringIO(a_file.read())
            progress.leave_substeps("Read file end")

            line = stripLine(data.readline())
            line_split = line.split()
            line_start = line_split[0]
            signature = line_start

            print('Signature:', signature)
            if signature != 'HD_DATA_TXT':
                print("Unrecognized signature: %s" % signature)
                operator.report({'ERROR'}, "Unrecognized file format")
                return {'FINISHED'}

            contextName = None
            bones = {}
            level = 0
            numTracks = None
            numFrames = None
            frameRate = None
            track = None
            boneName = None

            # steps = len(data.getvalue().splitlines()) - 1
            progress.enter_substeps(1, "Parse Data")
            # Read model data
            for lineData in data:
                line = stripLine(lineData)
                line_split = line.split()
                line_start = None
                i = len(line_split)
                if (i == 0):
                    continue
                line_start = line_split[0]
                if (line_start in ('{')):
                    level += 1
                if (line_start in ('}')):
                    level -= 1
                    contextName = None

                # info
                if (level >= 1):
                    if (line_start == 'numTracks'):
                        numTracks = int(line_split[1])
                    if (line_start == 'numFrames'):
                        numFrames = int(line_split[1])
                    if (line_start == 'frameRate'):
                        frameRate = int(line_split[1])
                    if (line_start == 'track'):
                        boneName = boneRenameBlender(line_split[1])
                        bones[boneName] = []

                # motion
                if (level >= 2):
                    if (line_start == 'key'):
                        posX, posY, posZ, quatX, quatZ, quatY, quatW = map(
                            float, line_split[1:8])
                        bonePose = (posX, posY, posZ, quatX, quatZ, quatY,
                                    quatW)
                        frame = len(bones[boneName])
                        bones[boneName].append(bonePose)

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            # armature.hide = False
            armature.select_set(state=True)
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')

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
                for name in bones.keys():
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
                    else:
                        origin = Vector([-x, -z, y])
                        m.translation = origin
                        m = m @ r

                    pose.matrix = m

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
            wm.progress_end()
    return {'FINISHED'}


class ImportHaydeeDMotion(Operator, ImportHelper):
    bl_idname = "haydee_importer.dmot"
    bl_label = "Import Haydee DMotion (.dmot)"
    bl_description = "Import a Haydee DMotion"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".dmot"
    filter_glob: StringProperty(
        default="*.dmot",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_dmotion(self, context, self.filepath)
