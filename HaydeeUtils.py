# <pep8 compliant>

import bpy
from bpy.props import EnumProperty
import os
from .HaydeeConstants import *
import codecs
from mathutils import Vector
from bpy_extras.wm_utils.progress_report import (
    ProgressReport,
    ProgressReportSubstep,
)

NAME_LIMIT = 31

file_format_prop = EnumProperty(
    name="File Format",
    description="Select file format Haydee 1 / Haydee 2 (flipped UV)",
    items=(('H1', 'Haydee 1', 'Use Haydee 1 File Format'),
           ('H2', 'Haydee 2', 'Use Haydee 2 File Format'),
        ),
    default='H2',
)


def boneRenameBlender(bone_name):
    name = bone_name
    if name.startswith("SK_R_"):
        name = "SK_" + name[5:] + "_R"
    if name.startswith("SK_L_"):
        name = "SK_" + name[5:] + "_L"
    return stripName(name)


def boneRenameHaydee(bone_name):
    name = bone_name
    if name.startswith("SK_") and name.endswith("_R"):
        name = "SK_R_" + name[3:-2]
    if name.startswith("SK_") and name.endswith("_L"):
        name = "SK_L_" + name[3:-2]
    return stripName(name)[:NAME_LIMIT]


def stripName(name):
    """ Remove invalid characters from a name"""
    out=name.replace(" ", "_").replace("*", "_").replace("-", "_")
    return bpy.path.clean_name(out)


def decodeText(text):
    return text.decode('latin1').split('\0', 1)[0]


def d(number):
    r = ('%.6f' % number).rstrip('0').rstrip('.')
    if r == "-0":
        return "0"
    return r

def hashedN(numbers):
    if type(numbers) is not tuple:
        return hash(tuple(numbers))

    return hash(numbers)
# --------------------------------------------------------------------------------
#  Finds a suitable armature in the current selection or scene
# --------------------------------------------------------------------------------


def find_armature(operator, context):
    armature = None
    checking = "ARMATURE"
    obj_list = [context.active_object, ] if context.active_object.type == checking else None
    if not obj_list:
        obj_list = context.selected_objects
    if not obj_list:
        obj_list = context.scene.objects
    while True:
        for ob in obj_list:
            if ob.type == checking:
                if checking == "MESH":
                    armature = ob.find_armature()
                    if armature:
                        ob = armature
                        break
                    if ob.type != 'ARMATURE':
                        continue
                if armature is not None and armature != ob:
                    operator.report({'ERROR'}, "Multiples armatures found, please select a single one and try again")
                armature = ob
        if armature is not None:
            return armature
        if checking == "ARMATURE":
            checking = "MESH"
        else:
            operator.report({'ERROR'}, "No armature found in scene" if obj_list == context.scene.objects else "No armature or weighted mesh selected")
            return None


def materials_list(a, b):
    materials = {}
    for ob in bpy.context.scene.objects:
        if ob.type == "MESH":
            for material_slot in ob.material_slots:
                materials[material_slot.name] = True
    mat_list = [('__ALL__', 'Export all materials', '')]
    for name in materials.keys():
        mat_list.append((name, name, ''))
    return mat_list


def fit_to_armature():
    """Fit selected armatures to the active armature.

    Replaces selected armature with active armature.
    Also modifies the pose of the meshes.
    """
    active = bpy.context.active_object
    if not (active and active.type == 'ARMATURE'):
        return {'FINISHED'}
    selected = next((armature for armature in bpy.context.selected_objects if (armature.type == 'ARMATURE' and armature != active)), None)
    if not (selected and selected.type == 'ARMATURE'):
        return {'FINISHED'}
    match_to_armature(selected, active)
    apply_pose(selected, active)
    bpy.data.armatures.remove(selected.data, do_unlink=True)
    return {'FINISHED'}


def match_to_armature(armature, target):
    for pose_bone in armature.pose.bones:
        if target.pose.bones.get(pose_bone.name):
            constraint = pose_bone.constraints.new('COPY_TRANSFORMS')
            constraint.target = target
            constraint.subtarget = pose_bone.name


def apply_pose(selected, active):
    objs = [obj for obj in bpy.data.objects if (obj.parent == selected)]
    modifiers = [modif for obj in bpy.data.objects for modif in obj.modifiers if (modif.type == 'ARMATURE' and modif.object == selected)]
    for obj in objs:
        obj.parent = active
    for modif in modifiers:
        obj = modif.id_data
        bpy.context.view_layer.objects.active = obj
        index = obj.modifiers.find(modif.name)
        bpy.ops.object.modifier_copy(modifier=modif.name)
        new_modif_name = obj.modifiers[index + 1].name
        bpy.ops.object.modifier_apply(modifier=new_modif_name)
        modif.object = active
    bpy.context.view_layer.objects.active = active


def fit_to_mesh():
    """Fit selected armatures to active."""
    active = bpy.context.active_object
    if not (active and active.type == 'ARMATURE'):
        return {'FINISHED'}
    selected = next((armature for armature in bpy.context.selected_objects if (armature.type == 'ARMATURE' and armature != active)), None)
    if not (selected and selected.type == 'ARMATURE'):
        return {'FINISHED'}
    match_to_armature(active, selected)
    new_rest_pose(selected, active)
    bpy.data.armatures.remove(selected.data, do_unlink=True)
    return {'FINISHED'}


def new_rest_pose(selected, active):
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.context.view_layer.objects.active = active
    bpy.ops.object.mode_set(mode='POSE', toggle=False)
    bpy.ops.pose.armature_apply()
    for pose_bone in active.pose.bones:
        for constraint in pose_bone.constraints:
            if constraint.type == 'COPY_TRANSFORMS':
                pose_bone.constraints.remove(constraint)
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    objs = [obj for obj in bpy.data.objects if (obj.parent == selected)]
    modifiers = [modif for obj in bpy.data.objects for modif in obj.modifiers if (modif.type == 'ARMATURE' and modif.object == selected)]
    for obj in objs:
        obj.parent = active
    for modif in modifiers:
        modif.object = active


def haydeeFilepath(mainpath, filepath):
    path = filepath
    if not os.path.isabs(filepath):
        # Current Folder
        currPath = os.path.relpath(filepath, r'outfits')
        basedir = os.path.dirname(mainpath)
        path = os.path.join(basedir, currPath)
        if not (os.path.isfile(path)):
            # Outfit Folder
            path = filepath
            idx = basedir.lower().find(r'\outfit')
            path = basedir[:idx]
            path = os.path.join(path, filepath)
    return path


def coordTransform(coord):
    return [-coord[0], -coord[2], coord[1]]


def readVec(line_split, vec_data, vec_len, func):
    vec = [func(v) for v in line_split[1:]]
    vec_data.append(tuple(vec[:vec_len]))


def readWeights(line_split, vert_data):
    vec = tuple((int(line_split[1]), int(line_split[2]), float(line_split[3])))
    vert_data.append(vec)


def stripLine(line):
    return line.strip().strip(';')


# --------------------------------------------------------------------------------
# binary helpers
# --------------------------------------------------------------------------------


def sig_check(mview):
    result = None
    if (mview[0:8] == (HD_CHUNK)):
        result = Signature.HD_CHUNK
    elif (mview[0:11] == (HD_DATA_TXT)):
        result = Signature.HD_DATA_TXT
    elif (mview[0:24] == (HD_DATA_TXT_BOM)):
        result = Signature.HD_DATA_TXT_BOM
    elif (mview[0:10] == (HD_MOTION)):
        result = Signature.HD_MOTION
    return result


# Read prefixed ANSI/utf8-as-ansi string
def readStrA(start, data):
    len = int.from_bytes(data[start:start + 4], byteorder='little')
    start += 4
    return (data[start:start + len].decode("utf-8"), 4 + len + 1)


# Read property name (until null terminator)
def readStrA_term(start, maxLen, data):
    i, tStr, found = -1, "", False
    while (i < maxLen):
        i += 1
        if (data[start + i] <= 0):
            found = True
            break
    if (found):
        tStr = codecs.decode(data[start:start + i], "latin")
    return (tStr, i)


# Read UTF16/wide string
def readStrW(start, data):
    i = int.from_bytes(data[start:start + 4], byteorder='little')
    len = (i * 2)
    start += 4
    return (codecs.decode(data[start:start + len], "utf-16-le"), 4 + len + 2)


# Vector from Haydee format to Blender
def vectorSwapSkel(vec):
    return Vector((-vec.z, vec.y, -vec.x))


def createCollection(name="Haydee Model"):
    # Create a collection with specific name
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def linkToActiveCollection(obj):
    # link object to active collection
    bpy.context.collection.objects.link(obj)


def recurLayerCollection(layerColl, collName):
    # transverse the layer_collection tree looking for a collection named collName
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found


def setActiveCollection(collName):
    # set collName as the active collection
    layer_collection = bpy.context.view_layer.layer_collection
    layerColl = recurLayerCollection(layer_collection, collName)
    if layerColl:
        bpy.context.view_layer.active_layer_collection = layerColl



def find_encoding(filepath)->str:
    """Find File enoding using charset_normalizer """
    import charset_normalizer
    with (open(filepath, 'rb')) as f:
        encoding = charset_normalizer.detect(f.read())['encoding']
    return encoding

class HaydeeToolFitArmature_Op(bpy.types.Operator):
    bl_idname = 'haydee_tools.fit_to_armature'
    bl_label = 'Cycles'
    bl_description = 'Select the mesh armature then the haydee Skel. Raplces the Armature with the skel. Uses the Skel pose'
    bl_options = {'PRESET',"UNDO"}

    def execute(self, context):
        fit_to_armature()
        return {'FINISHED'}


class HaydeeToolFitMesh_Op(bpy.types.Operator):
    bl_idname = 'haydee_tools.fit_to_mesh'
    bl_label = 'Cycles'
    bl_description = 'Select the mesh armature then the haydee Skel. Raplces the Armature with the skel. Uses the Armature pose'
    bl_options = {'PRESET',"UNDO"}

    def execute(self, context):
        fit_to_mesh()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(HaydeeToolFitArmature_Op)
    bpy.utils.register_class(HaydeeToolFitMesh_Op)


def unregister():
    bpy.utils.unregister_class(HaydeeToolFitArmature_Op)
    bpy.utils.unregister_class(HaydeeToolFitMesh_Op)
