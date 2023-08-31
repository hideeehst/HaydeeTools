from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import struct
from mathutils import Quaternion, Vector
from ..HaydeeUtils import *
# --------------------------------------------------------------------------------
# .skin importer
# --------------------------------------------------------------------------------


def read_skin(operator, context, filepath, armature_ob):
    print('Skin:', filepath)
    if not bpy.context.view_layer.objects.active or \
            bpy.context.view_layer.objects.active.type != 'MESH':
        return {'FINISHED'}

    with ProgressReport(context.window_manager) as progReport:
        with ProgressReportSubstep(progReport, 5, "Importing mesh",
                                   "Finish Importing dmesh") as progress:
            if (bpy.context.mode != 'OBJECT'):
                bpy.ops.object.mode_set(mode='OBJECT')

            SIGNATURE_SIZE = 28
            CHUNK_SIZE = 48
            INIT_INFO = 8
            VERT_SIZE = 20
            BONE_SIZE = 112

            print("Importing mesh: %s" % filepath)

            progress.enter_substeps(1, "Read file")
            data = None
            with open(filepath, "rb") as a_file:
                data = a_file.read()
            progress.leave_substeps("Read file end")

            (signature, chunkCount, totalSize) = \
                struct.unpack('20sII', data[0:SIGNATURE_SIZE])
            signature = decodeText(signature)
            print('Signature:', signature)
            if signature != 'HD_CHUNK':
                print("Unrecognized signature: %s" % signature)
                operator.report({'ERROR'}, "Unrecognized file format")
                return {'FINISHED'}

            offset = SIGNATURE_SIZE + (CHUNK_SIZE * chunkCount)
            (vertCount, boneCount) = \
                struct.unpack('II', data[offset:offset + INIT_INFO])

            vert_data = []
            headerSize = SIGNATURE_SIZE + (CHUNK_SIZE * chunkCount) + INIT_INFO
            delta = headerSize
            for n in range(vertCount):
                offset = delta + (VERT_SIZE * n)
                (w1, w2, w3, w4, b1, b2, b3, b4) = \
                    struct.unpack('4f4B', data[offset:offset + VERT_SIZE])

                weights = ((b1, w1), (b2, w2), (b3, w3), (b4, w4))
                vert_data.append(weights)

            bone_data = []

            delta = headerSize + (VERT_SIZE * vertCount)
            for n in range(boneCount):
                offset = delta + (BONE_SIZE * n)
                (name,
                    f1, f2, f3, f4,
                    f5, f6, f7, f8,
                    f9, f10, f11, f12,
                    f13, f14, f15, f16,
                    vx, vy, vz, vw) = \
                    struct.unpack('32s16f4f', data[offset:offset + BONE_SIZE])

                name = decodeText(name)
                name = boneRenameBlender(name)
                mat = Matrix(((f1, f2, f3, f4), (f5, f6, f7, f8),
                              (f9, f10, f11, f12), (f13, f14, f15, f16)))
                vec = Vector((vx, vy, vz, vw))
                bone_data.append({'name': name, 'mat': mat, 'vec': vec})

            mesh_obj = bpy.context.view_layer.objects.active

            for vertIdx, v_data in enumerate(vert_data):
                for boneIdx, vertexWeight in v_data:

                    if (boneIdx != 0 or vertexWeight != 0):
                        boneName = bone_data[boneIdx]['name']
                        vertGroup = mesh_obj.vertex_groups.get(boneName)
                        if not vertGroup:
                            vertGroup = mesh_obj.vertex_groups.new(
                                name=boneName)
                        vertGroup.add([vertIdx], vertexWeight, 'REPLACE')

            if not armature_ob:
                armature_ob = None
                armature_da = bpy.data.armatures.new(ARMATURE_NAME)
                # armature_da.display_type = 'STICK'
                armature_da.show_axes = True
                armature_ob = bpy.data.objects.new(ARMATURE_NAME, armature_da)
                armature_ob.show_in_front = True
                linkToActiveCollection(armature_ob)

            bpy.context.view_layer.objects.active = armature_ob
            bpy.ops.object.mode_set(mode='EDIT')

            # create all Bones
            progress.enter_substeps(boneCount, "create bones")
            # Axis Orientation
            axis_orient = Quaternion((1, 0, 0), -pi / 2).to_matrix().to_4x4()
            # Bone Orientation
            r1 = Quaternion((0, 0, 1), pi / 2).to_matrix().to_4x4()
            r2 = Quaternion((0, 1, 0), -pi / 2).to_matrix().to_4x4()
            bone_orient = r1 @ r2
            for idx, b_data in enumerate(bone_data):
                boneName = b_data['name']
                if not armature_ob.data.edit_bones.get(boneName):
                    mat = b_data['mat']
                    editBone = armature_ob.data.edit_bones.new(boneName)
                    editBone.tail = Vector(editBone.head) + Vector((0, 0, 4))
                    pos = Vector(mat.to_3x3() @ mat.row[3].xyz)
                    mat = mat.to_3x3().to_4x4()
                    mat.translation = pos
                    editBone.matrix = axis_orient @ mat @ bone_orient
                progress.step()

            bpy.ops.object.mode_set(mode='OBJECT')
            progress.leave_substeps("create bones end")

            progress.enter_substeps(1, "parent armature")
            if armature_ob:
                # parent armature
                mesh_obj.parent = armature_ob
                # armature modifier
                mod = mesh_obj.modifiers.new(type="ARMATURE", name="Armature")
                mod.use_vertex_groups = True
                mod.object = armature_ob
            progress.leave_substeps("end parent armature")

    return {'FINISHED'}


class ImportHaydeeSkin(Operator, ImportHelper):
    bl_idname = "haydee_importer.skin"
    bl_label = "Import Haydee Skin (.skin)"
    bl_description = "Import a Haydee Skin (Weigth Information)"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".skin"
    filter_glob: StringProperty(
        default="*.skin",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_skin(self, context, self.filepath, None)
