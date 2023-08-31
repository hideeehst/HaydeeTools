from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import io
from mathutils import Quaternion, Vector
from ..HaydeeUtils import *

# --------------------------------------------------------------------------------
# .dskel importer
# --------------------------------------------------------------------------------


def read_dskel(operator, context, filepath):
    print('dskel:', filepath)
    with ProgressReport(context.window_manager) as progReport:
        with ProgressReportSubstep(progReport, 4, "Importing dskel",
                                   "Finish Importing dskel") as progress:

            data = None
            encoding = find_encoding(filepath)
            with open(filepath, "r", encoding=encoding) as a_file:
                data = io.StringIO(a_file.read())

            line = stripLine(data.readline())
            line_split = line.split()
            line_start = line_split[0]
            signature = line_start

            print('Signature:', signature)
            if signature != 'HD_DATA_TXT':
                print("Unrecognized signature: %s" % signature)
                operator.report({'ERROR'}, "Unrecognized file format")
                return {'FINISHED'}

            level = 0
            boneCount = 0
            jointName = None
            jointNames = []
            jointOrigin = []
            jointAxis = []
            jointParents = []
            jointWidth = []
            jointHeight = []
            jointLength = []

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

                # Joints
                if (line_start == 'skeleton' and level == 0):
                    boneCount = line_split[1]
                if (line_start == 'bone' and level == 1):
                    jointName = line_split[1]
                    jointNames.append(jointName)
                    jointParents.append(None)
                if (line_start == 'parent' and level >= 2):
                    jointParents[len(jointParents) - 1] = line_split[1]
                if (line_start == 'origin' and level >= 2):
                    readVec(line_split, jointOrigin, 3, float)
                if (line_start == 'axis' and level >= 2):
                    readVec(line_split, jointAxis, 4, float)

                if (line_start == 'width' and level >= 2):
                    jointWidth.append(float(line_split[1]))
                if (line_start == 'height' and level >= 2):
                    jointHeight.append(float(line_split[1]))
                if (line_start == 'length' and level >= 2):
                    jointLength.append(float(line_split[1]))

            for idx, name in enumerate(jointNames):
                jointNames[idx] = boneRenameBlender(name)

            for idx, name in enumerate(jointParents):
                if name:
                    jointParents[idx] = boneRenameBlender(name)

            if (bpy.context.mode != 'OBJECT'):
                bpy.ops.object.mode_set(mode='OBJECT')
            print('deselect')
            bpy.ops.object.select_all(action='DESELECT')

            armature_ob = None
            if jointNames:
                boneCount = len(jointNames)
                progress.enter_substeps(boneCount, "Build armature")
                print('Importing Armature', str(boneCount), 'bones')

                armature_da = bpy.data.armatures.new(ARMATURE_NAME)
                # armature_da.display_type = 'STICK'
                armature_ob = bpy.data.objects.new(ARMATURE_NAME, armature_da)
                armature_ob.show_in_front = True

                collection = createCollection(ARMATURE_NAME)
                setActiveCollection(ARMATURE_NAME)
                linkToActiveCollection(armature_ob)

                bpy.context.view_layer.objects.active = armature_ob
                bpy.ops.object.mode_set(mode='EDIT')

                # create all Bones
                progress.enter_substeps(boneCount, "create bones")
                for idx, jointName in enumerate(jointNames):
                    editBone = armature_ob.data.edit_bones.new(jointName)
                    editBone.tail = Vector(editBone.head) + Vector((0, 0, 1))
                    editBone.length = jointLength[idx]
                    progress.step()
                progress.leave_substeps("create bones end")

                # set all bone parents
                progress.enter_substeps(boneCount, "parenting bones")
                for idx, jointParent in enumerate(jointParents):
                    if (jointParent):
                        editBone = armature_da.edit_bones[idx]
                        editBone.parent = armature_da.edit_bones[jointParent]
                    progress.step()
                progress.leave_substeps("parenting bones end")

                # origins of each bone is relative to its parent
                # recalc all origins
                progress.enter_substeps(boneCount, "aligning bones")

                for edit_bone in armature_da.edit_bones:
                    idx = jointNames.index(edit_bone.name)
                    quat = Quaternion(jointAxis[idx])
                    quat = Quaternion((-quat.z, quat.w, quat.y, -quat.x))
                    mat = quat.to_matrix().to_4x4()
                    r = Quaternion([0, 0, 1], pi / 2)
                    boneRot = r.to_matrix().to_4x4()
                    mat = mat @ boneRot
                    pos = Vector(jointOrigin[idx])
                    pos = Vector((-pos.y, -pos.z, pos.x))
                    mat.translation = vectorSwapSkel(pos)
                    edit_bone.matrix = mat
                    progress.step()
                progress.leave_substeps("aligning bones end")

                # lenght of bones
                for bone in armature_da.edit_bones:
                    for child in bone.children:
                        center = child.head
                        proxVec = center - bone.head
                        boneVec = bone.tail - bone.head
                        norm = proxVec.dot(boneVec) / boneVec.dot(boneVec)
                        if (norm > 0.1):
                            proyVec = norm * boneVec
                            dist = (proxVec - proyVec).length
                            if (dist < 0.001):
                                bone.tail = center

            bpy.ops.object.mode_set(mode='OBJECT')
            progress.leave_substeps("Build armature end")

    armature_ob.select_set(state=True)
    return {'FINISHED'}


class ImportHaydeeDSkel(Operator, ImportHelper):
    bl_idname = "haydee_importer.dskel"
    bl_label = "Import Haydee DSkel (.dskel)"
    bl_description = "Import a Haydee DSkeleton"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".dskel"
    filter_glob: StringProperty(
        default="*.dskel",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_dskel(self, context, self.filepath)
