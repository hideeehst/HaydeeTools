from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import io
from mathutils import Quaternion, Vector
from ..HaydeeUtils import *

# --------------------------------------------------------------------------------
# .dpose importer
# --------------------------------------------------------------------------------


def read_dpose(operator, context, filepath):
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
            transformsCount = None
            level = 0

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

                # Transforms
                if (line_start == 'numTransforms' and level >= 1):
                    transformsCount = int(line_split[1])

                # Transforms
                if (line_start == 'transform' and level >= 1):
                    boneName = boneRenameBlender(line_split[1])
                    posX, posY, posZ, quatX, quatZ, quatY, quatW = map(
                        float, line_split[2:9])
                    bonePose = (posX, posY, posZ, -quatX, -quatZ, -quatY,
                                -quatW)
                    bones[boneName] = bonePose

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            # armature.hide = False
            armature.select_set(state=True)
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='DESELECT')

            wm = bpy.context.window_manager
            wm.progress_begin(0, transformsCount)

            r = Quaternion([0, 0, 1], pi / 2)

            for i, (bone_name, bone_pose) in enumerate(bones.items()):
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


class ImportHaydeeDPose(Operator, ImportHelper):
    bl_idname = "haydee_importer.dpose"
    bl_label = "Import Haydee DPose (.dpose)"
    bl_description = "Import a Haydee DPose"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".dpose"
    filter_glob: StringProperty(
        default="*.dpose",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_dpose(self, context, self.filepath)
