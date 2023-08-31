from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import struct
import binascii
from mathutils import Quaternion, Vector
from ..HaydeeUtils import *

# --------------------------------------------------------------------------------
# .skel importer
# --------------------------------------------------------------------------------


def recurBonesOrigin(progress, parentBone, jointNames, mats):
    for childBone in parentBone.children:
        if childBone:
            idx = jointNames.index(childBone.name)
            child_mat = mats[idx]
            # INV row
            x1 = Matrix(
                ((0, 0, -1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
            # INV col
            x2 = Matrix(
                ((0, 1, 0, 0), (0, 0, 1, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))

            childBone.matrix = parentBone.matrix @ (x1 @ child_mat @ x2)
            recurBonesOrigin(progress, childBone, jointNames, mats)
            progress.step()


def rotateNonRootBone(parentBone):
    if ('root' in parentBone.name.lower()):
        return
    r = Quaternion((0, 0, 1), -pi / 2).to_matrix().to_4x4()
    parentBone.matrix = r @ parentBone.matrix
    for childBone in parentBone.children:
        rotateNonRootBone(childBone)


# Parse bone data helper
def read_bone_data(memData, propMap, jointNames, jointParents, mats,
                   dimensions):
    boneCount = propMap['numBones']['value']
    BONE_SIZE = int(propMap['bones']['size'] / boneCount)
    unpack_bone = struct.Struct('<32s16fi3fi').unpack
    for n in range(boneCount):
        offset = (BONE_SIZE * n)
        (name, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13, f14,
         f15, f16, parent, width, height, lenght,
         flags) = unpack_bone(memData[offset:offset + BONE_SIZE])

        name = readStrA_term(0, 32, memoryview(name))[0]
        name = boneRenameBlender(name)
        mat = Matrix(((f1, f5, f9, f13), (f2, f6, f10, f14),
                      (f3, f7, f11, f15), (f4, f8, f12, f16)))
        jointNames.append(name)
        jointParents.append(parent)
        mats.append(mat)
        dimensions.append((width, height, lenght))
    return True


# Parse joint data helper
def read_joint_data(memData, propMap, joint_data):
    joints_count = propMap['numJoints']['value']
    JOINT_SIZE = int(propMap['joints']['size'] / joints_count)
    unpack_joint = struct.Struct('<18f4f').unpack
    for n in range(joints_count):
        offset = (JOINT_SIZE * n)
        (index, parent, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12, f13,
         f14, f15, f16, twistX, twistY, swingX,
         swingY) = unpack_joint(memData[offset:offset + JOINT_SIZE])

        mat = Matrix(((f1, f5, f9, f13), (f2, f6, f10, f14),
                      (f3, f7, f11, f15), (f4, f8, f12, f16)))

        joint_data[index] = {
            'parent': parent,
            'twistX': twistX,
            'twistY': twistY,
            'swingX': swingX,
            'swingY': swingY,
            'matrix': mat
        }
    return True


# Parse fixes data
def read_fixes_data(memData, propMap, fix_data):
    fixes_count = propMap['numFixes']['value']
    FIXES_SIZE = int(propMap['fixes']['size'] / fixes_count)
    unpack_fixes = struct.Struct('<5I').unpack
    for n in range(fixes_count):
        offset = (FIXES_SIZE * n)
        (type, flags, fix1, fix2,
         index) = unpack_fixes(memData[offset:offset + FIXES_SIZE])
        fix_data[index] = ({
            'type': type,
            'flags': flags,
            'fix1': fix1,
            'fix2': fix2
        })
    return True


def read_skel(operator, context, filepath):
    print('skel:', filepath)
    with open(filepath, "rb") as a_file:
        data = a_file.read()
    mview = memoryview(data)

    (entries, serialSize, assType) = struct.unpack('<ii8s', mview[20:36])
    assType = assType.decode("latin")

    if (sig_check(mview) != Signature.HD_CHUNK or assType != 'skeleton'):
        print("Unrecognized signature or asset type: [%s], %s" %
              (binascii.hexlify(mview[0:16]), assType))
        operator.report({'ERROR'}, "Unrecognized file format")
        return {'FINISHED'}

    # Compiled structs
    unpack_int = struct.Struct('<i').unpack
    unpack_entry = struct.Struct('<32siiii').unpack

    # Data
    jointNames, jointParents, mats, dimensions = [], [], [], []
    joint_data, fix_data = {}, {}
    armature_ob = None

    propMap = dict(
        numBones={'reader': lambda x: unpack_int(x)[0]},
        numJoints={'reader': lambda x: unpack_int(x)[0]},
        numFixes={'reader': lambda x: unpack_int(x)[0]},
        numBounds={'reader': lambda x: unpack_int(x)[0]},
        numTrackers={'reader': lambda x: unpack_int(x)[0]},
        numSlots={'reader': lambda x: unpack_int(x)[0]},
        bones={
            'reader':
            lambda x: read_bone_data(x, propMap, jointNames, jointParents,
                                     mats, dimensions)
        },
        fixes={'reader': lambda x: read_fixes_data(x, propMap, fix_data)},
        joints={'reader': lambda x: read_joint_data(x, propMap, joint_data)},
        slots={
            'reader':
            lambda x: print("Skipping slots since this data is irrelevant")
        })

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

    print(fix_data)
    with ProgressReport(context.window_manager) as progReport:
        with ProgressReportSubstep(progReport, 4, "Importing skel",
                                   "Finish Importing skel") as progress:

            # create armature
            if (bpy.context.mode != 'OBJECT'):
                bpy.ops.object.mode_set(mode='OBJECT')
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
                    editBone.length = dimensions[idx][2]
                    progress.step()
                progress.leave_substeps("create bones end")

                # set all bone parents
                progress.enter_substeps(boneCount, "parenting bones")
                for idx, jointParent in enumerate(jointParents):
                    if (jointParent >= 0):
                        editBone = armature_da.edit_bones[idx]
                        editBone.parent = armature_da.edit_bones[jointParent]
                    progress.step()
                progress.leave_substeps("parenting bones end")

                # origins of each bone is relative to its parent
                # recalc all origins
                progress.enter_substeps(boneCount, "aligning bones")
                rootBones = [
                    rootBone for rootBone in armature_da.edit_bones
                    if rootBone.parent is None
                ]

                # swap rows root bones
                swap_rows = Matrix(
                    ((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
                # swap cols root bones
                swap_cols = Matrix(
                    ((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))

                for rootBone in rootBones:
                    idx = jointNames.index(rootBone.name)
                    mat = mats[idx]
                    rootBone.matrix = swap_rows @ mat @ swap_cols
                    recurBonesOrigin(progress, rootBone, jointNames, mats)
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

                # Rotate bone not in 'SK_Root' chain
                for bone in rootBones:
                    rotateNonRootBone(bone)

                bpy.ops.object.mode_set(mode='OBJECT')
                progress.leave_substeps("Build armature end")

            for idx, bone_name in enumerate(jointNames):

                # import JOINT information
                joint = joint_data.get(idx)
                if joint:
                    parent = joint['parent']
                    twistX = joint['twistX']
                    twistY = joint['twistY']
                    swingX = joint['swingX']
                    swingY = joint['swingY']

                    pose_bone = armature_ob.pose.bones.get(bone_name)
                    constraint = pose_bone.constraints.new('LIMIT_ROTATION')
                    constraint.use_limit_x = True

                # TODO:
                # Commented out because does not work properly
                # fix1 index is alway too high, needs reserach
                # import FIX information
                # fix = fix_data.get(idx)
                # if fix:
                #     constraint = None
                #     type = fix['type']
                #     flags = fix['flags']

                #     parent_idx = fix['fix1']
                #     parent_name = jointNames[parent_idx]

                #     target_idx = fix['fix2']
                #     target_name = jointNames[target_idx]

                #     pose_bone = armature_ob.pose.bones.get(bone_name)
                #     pose_bone.bone.layers[1] = True
                #     pose_bone.bone.layers[0] = False

                #     useDrivers = False
                #     if useDrivers:
                #         if (type == 1):  # TARGET
                #             groupName = 'TARGET'
                #             boneGroup = armature_ob.pose.bone_groups.get(groupName)
                #             if not boneGroup:
                #                 boneGroup = armature_ob.pose.bone_groups.new(name=groupName)
                #                 boneGroup.color_set = 'THEME15'
                #             pose_bone.bone_group = boneGroup
                #             XY = bool(flags & 0b0001)  # fix order YZ
                #             XY = bool(flags & 0b0010)  # fix order ZY
                #             constraint = pose_bone.constraints.new('DAMPED_TRACK')
                #             constraint.name = 'Target'
                #             constraint.target = armature_ob
                #             constraint.subtarget = target_name

                #         if (type == 2 and 0 == 1):  # SMOOTH
                #             NEGY = bool(flags & 0b0001)  # fix order NEGY
                #             NEGZ = bool(flags & 0b0010)  # fix order NEGZ
                #             POSY = bool(flags & 0b0011)  # fix order POSY
                #             POSZ = bool(flags & 0b0100)  # fix order POSZ
                #             pose_bone.bone.use_inherit_scale = False
                #             pose_bone.bone.use_inherit_rotation = False

                #             constraint_parent = pose_bone.constraints.new('CHILD_OF')
                #             constraint_parent.name = 'Smooth Parent'
                #             constraint_parent.target = armature_ob
                #             constraint_parent.subtarget = parent_name
                #             constraint_parent.use_location_x = False
                #             constraint_parent.use_location_y = False
                #             constraint_parent.use_location_z = False
                #             matrix = constraint_parent.target.data.bones[constraint_parent.subtarget].matrix_local.inverted()
                #             constraint_parent.inverse_matrix = matrix
                #             constraint_parent.influence = .5

                #             constraint_child = pose_bone.constraints.new('CHILD_OF')
                #             constraint_child.name = 'Smooth Child'
                #             constraint_child.target = armature_ob
                #             constraint_child.subtarget = target_name
                #             constraint_child.use_location_x = False
                #             constraint_child.use_location_y = False
                #             constraint_child.use_location_z = False
                #             matrix = constraint_child.target.data.bones[constraint_child.subtarget].matrix_local.inverted()
                #             constraint_child.inverse_matrix = matrix
                #             constraint_child.influence = .5
                #         if (type == 2):  # SMOOTH
                #             groupName = 'SMOOTH'
                #             boneGroup = armature_ob.pose.bone_groups.get(groupName)
                #             if not boneGroup:
                #                 boneGroup = armature_ob.pose.bone_groups.new(name=groupName)
                #                 boneGroup.color_set = 'THEME14'
                #             pose_bone.bone_group = boneGroup
                #             driver = armature_ob.driver_add(f'pose.bones["{bone_name}"].rotation_quaternion')
                #             expression = '(mld.to_quaternion().inverted() @ mls.to_quaternion() @ mbs.to_quaternion() @ mls.to_quaternion().inverted() @ mld.to_quaternion()).slerp(((1, 0, 0, 0)), .5)'
                #             build_driver(driver, expression, 0, bone_name, target_name)
                #             build_driver(driver, expression, 1, bone_name, target_name)
                #             build_driver(driver, expression, 2, bone_name, target_name)
                #             build_driver(driver, expression, 3, bone_name, target_name)

            armature_ob.select_set(state=True)

    # wm.progress_end()
    return {'FINISHED'}


def build_driver(driver, expression, component, source_bone, target_bone):
    rot_comp = driver[component]
    rot_comp.driver.type = 'SCRIPTED'
    rot_comp.driver.expression = expression + '[' + str(component) + ']'

    var = rot_comp.driver.variables.new()
    var.type = 'SINGLE_PROP'
    var.name = 'mls'
    var.targets[0].id = rot_comp.id_data
    var.targets[0].data_path = 'data.bones["' + target_bone + '"].matrix_local'

    var = rot_comp.driver.variables.new()
    var.type = 'SINGLE_PROP'
    var.name = 'mld'
    var.targets[0].id = rot_comp.id_data
    var.targets[0].data_path = 'data.bones["' + source_bone + '"].matrix_local'

    var = rot_comp.driver.variables.new()
    var.type = 'SINGLE_PROP'
    var.name = 'mbs'
    var.targets[0].id = rot_comp.id_data
    var.targets[0].data_path = 'pose.bones["' + target_bone + '"].matrix_basis'


class ImportHaydeeSkel(Operator, ImportHelper):
    bl_idname = "haydee_importer.skel"
    bl_label = "Import Haydee Skel (.skel/.skeleton)"
    bl_description = "Import a Haydee Skeleton"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".skel"
    filter_glob: StringProperty(
        default="*.skel;*.skeleton",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_skel(self, context, self.filepath)
