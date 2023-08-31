from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import io
import os
from ..HaydeeUtils import *

from .import_mesh import read_mesh
from .import_material import read_material
from .import_skin import read_skin

# --------------------------------------------------------------------------------
# .outfit importer
# --------------------------------------------------------------------------------


def read_outfit(operator, context, filepath, file_format):
    print('Outfit:', filepath)
    with ProgressReport(context.window_manager) as progReport:
        with ProgressReportSubstep(progReport, 4, "Importing outfit",
                                   "Finish Importing outfit") as progress:

            data = None
            encoding = find_encoding(filepath)
            with open(filepath,
                      "r",
                      encoding=encoding,
                      errors="surrogateescape") as a_file:
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
            outfitName = None

            meshFiles = []
            skinFiles = []
            materialFiles = []

            # steps = len(data.getvalue().splitlines()) - 1
            progress.enter_substeps(1, "Parse Data")
            # Read model data
            for lineData in data:
                line = stripLine(lineData)
                line_split = line.split(maxsplit=1)
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

                if (line_start == 'outfit' and level == 0
                        and len(line_split) > 1):
                    outfitName = line_split[1].replace('"', '')

                # Joints
                if (line_start == 'name' and level == 1):
                    outfitName = line_split[1].replace('"', '')

                if (line_start == 'mesh' and level == 2):
                    meshFiles.append(line_split[1].replace('"', ''))
                    skinFiles.append(None)
                    materialFiles.append(None)
                if (line_start == 'skin' and level == 2):
                    skinFiles[len(meshFiles) - 1] = line_split[1].replace(
                        '"', '')
                if (line_start == 'material' and level == 2):
                    materialFiles[len(meshFiles) - 1] = line_split[1].replace(
                        '"', '')

            combo = []
            for idx in range(len(meshFiles)):
                mesh = meshFiles[idx]
                skin = skinFiles[idx]
                matr = materialFiles[idx]
                obj = {'mesh': mesh, 'skin': skin, 'matr': matr}
                if obj not in combo:
                    combo.append(obj)

            basedir = os.path.dirname(filepath)
            armature_obj = None
            imported_meshes = []

            collection = createCollection(outfitName)
            setActiveCollection(outfitName)

            for obj in combo:
                meshpath = None
                skinpath = None
                matrpath = None
                meshpath = haydeeFilepath(filepath, obj['mesh'])
                if obj['skin']:
                    skinpath = haydeeFilepath(filepath, obj['skin'])
                if obj['matr']:
                    matrpath = haydeeFilepath(filepath, obj['matr'])

                # Create Mesh
                if meshpath and os.path.exists(meshpath):
                    read_mesh(operator, context, meshpath, outfitName,
                              file_format)
                    imported_meshes.append(
                        bpy.context.view_layer.objects.active)
                else:
                    filename = os.path.splitext(os.path.basename(meshpath))[0]
                    print('File not found:', filename, meshpath)

                # Create Material
                if matrpath and os.path.exists(matrpath):
                    read_material(operator, context, matrpath)
                else:
                    if matrpath:
                        filename = os.path.splitext(
                            os.path.basename(matrpath))[0]
                        print('File not found:', filename, matrpath)

                # Create Skin (bone weights/bones)
                if skinpath and os.path.exists(skinpath):
                    read_skin(operator, context, skinpath, armature_obj)
                else:
                    if skinpath:
                        filename = os.path.splitext(
                            os.path.basename(skinpath))[0]
                        print('File not found:', filename, skinpath)

                # Find armature
                active_obj = bpy.context.view_layer.objects.active
                if (not armature_obj and active_obj
                        and active_obj.type == 'ARMATURE'):
                    armature_obj = active_obj

            for obj in imported_meshes:
                obj.select_set(state=True)
            if armature_obj:
                armature_obj.select_set(state=True)

    return {'FINISHED'}


class ImportHaydeeOutfit(Operator, ImportHelper):
    bl_idname = "haydee_importer.outfit"
    bl_label = "Import Haydee Outfit (.outfit)"
    bl_description = "Import a Haydee Outfit (Meshes, Materials, Skins)"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".outfit"
    filter_glob: StringProperty(
        default="*.outfit",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    file_format: file_format_prop

    def execute(self, context):
        return read_outfit(self, context, self.filepath, self.file_format)
