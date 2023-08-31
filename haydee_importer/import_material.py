from math import pi
import bpy
from bpy.types import Operator
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
import io
import struct
import binascii
import os
from io import BytesIO
from mathutils import Quaternion, Vector
from ..HaydeeUtils import *
from ..HaydeeNodeMat import create_material


# --------------------------------------------------------------------------------
# .material importer
# --------------------------------------------------------------------------------
def read_material(operator, context, filepath):
    print('Material:', filepath)
    if not bpy.context.view_layer.objects.active or \
            bpy.context.view_layer.objects.active.type != 'MESH':
        return {'FINISHED'}

    class MatType(Enum):
        OPAQUE = 0
        MASK = 1
        HAIR = 2

    with open(filepath, "rb") as a_file:
        data = a_file.read()
    mview = memoryview(data)

    with ProgressReport(context.window_manager) as progReport:
        with ProgressReportSubstep(progReport, 4, "Importing outfit",
                                   "Finish Importing outfit") as progress:

            propMap = None
            sig = sig_check(mview)

            if (sig == Signature.HD_CHUNK):
                print("Signature: %s" % sig.name)

                unpack_int = struct.Struct('<I').unpack
                unpack_float = struct.Struct('<f').unpack
                unpack_entry = struct.Struct('<32siiii').unpack
                (entries, serialSize,
                 assType) = struct.unpack('<ii8s', mview[20:36])

                if (assType.decode('latin') != 'material'):
                    print("Unrecognized signature or asset type: [%s], %s" %
                          (binascii.hexlify(mview[0:16]), assType))
                    operator.report({'ERROR'}, "Unrecognized file format")
                    return {'FINISHED'}

                propMap = dict(
                    type={'reader': lambda x: unpack_int(x)[0]},
                    twoSided={'reader': lambda x: unpack_int(x)[0]},
                    width={'reader': lambda x: unpack_float(x)[0]},
                    height={'reader': lambda x: unpack_float(x)[0]},
                    autouv={'reader': lambda x: unpack_int(x)[0]},
                    diffuseMap={'reader': lambda x: readStrW(0, x)[0]},
                    normalMap={'reader': lambda x: readStrW(0, x)[0]},
                    specularMap={'reader': lambda x: readStrW(0, x)[0]},
                    emissionMap={'reader': lambda x: readStrW(0, x)[0]},
                    censorMap={'reader': lambda x: readStrW(0, x)[0]},
                    maskMap={'reader': lambda x: readStrW(0, x)[0]},
                    surface={'reader': lambda x: readStrA_term(0, 64, x)[0]},
                    speculars={'reader': lambda x: struct.unpack('<3f', x)})
                dataOffset = 28 + (entries * 48)

                for x in range(1, entries):
                    sPos = 28 + (x * 48)
                    (name, size, offset, numSubs,
                     subs) = unpack_entry(mview[sPos:sPos + 48])
                    name = readStrA_term(0, 32, name)[0]
                    propMap[name].update(
                        dict(
                            zip([
                                'size', 'offset', 'numSubs', 'subs', 'hasValue'
                            ], [size, offset, numSubs, subs, size > 0])))

                for value in propMap.values():
                    if (value.get("hasValue")):
                        (f, lSize, lOff) = (value['reader'], value['size'],
                                            value['offset'])
                        lOff = dataOffset + lOff
                        value["value"] = f(mview[lOff:lOff + lSize])

            elif (sig == Signature.HD_DATA_TXT
                  or sig == Signature.HD_DATA_TXT_BOM):
                encoding = find_encoding(filepath)
                mview = io.TextIOWrapper(BytesIO(data), encoding=encoding)
                print("Signature: %s" % sig.name)

                propMap = dict(
                    type={'reader': lambda s: MatType[s]},
                    twoSided={'reader': lambda s: s.lower() == 'true'},
                    width={'reader': lambda s: float(s)},
                    height={'reader': lambda s: float(s)},
                    autouv={'reader': lambda s: int(s)},
                    diffuseMap={'reader': lambda s: s.strip('"')},
                    normalMap={'reader': lambda s: s.strip('"')},
                    specularMap={'reader': lambda s: s.strip('"')},
                    emissionMap={'reader': lambda s: s.strip('"')},
                    censorMap={'reader': lambda s: s.strip('"')},
                    maskMap={'reader': lambda s: s.strip('"')},
                    surface={'reader': lambda s: s},
                    speculars={
                        'reader':
                        lambda s: tuple([float(val) for val in s.split()])
                    })

                line = mview.readline()
                c = 0
                while (line != '{' and c < 50):
                    line = mview.readline().strip()
                    c = c + 1
                c = 0
                while (line != '}' and c < 50):
                    c = c + 1
                    line = mview.readline().strip().strip(';')
                    if (line == '}'): break
                    key = line[0:line.index(' ')]
                    value = line[line.index(' ') + 1:]
                    propMap[key]["value"] = propMap[key]["reader"](value)
            else:
                print("Unrecognized signature or asset type: %s" %
                      (binascii.hexlify(mview[0:16])))
                operator.report({'ERROR'}, "Unrecognized file format")
                return {'FINISHED'}

            # Ready to create material
            obj = bpy.context.view_layer.objects.active
            basedir = os.path.dirname(filepath)
            matName = os.path.basename(filepath)
            matName = os.path.splitext(matName)[0]

            for key, value in propMap.items():
                if ('Map') in key:
                    vMap = value.get("value")
                    if (vMap):
                        value["value"] = material_path(basedir, vMap)

            useAlpha = (propMap.get("type") and propMap["type"]["value"] == 1)
            create_material(obj, useAlpha, matName,
                            propMap['diffuseMap'].get('value'),
                            propMap['normalMap'].get('value'),
                            propMap['specularMap'].get('value'),
                            propMap['emissionMap'].get('value'))

    return {'FINISHED'}


class ImportHaydeeMaterial(Operator, ImportHelper):
    bl_idname = "haydee_importer.material"
    bl_label = "Import Haydee Material (.mtl)"
    bl_description = "Import a Haydee Material to active Object"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".mtl"
    filter_glob: StringProperty(
        default="*.mtl",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return read_material(self, context, self.filepath)


def material_path(mainpath, filepath):
    path = filepath
    if not os.path.isabs(filepath):
        if (filepath.rfind('\\') < 0):
            # Current Folder
            path = os.path.join(mainpath, filepath)
        else:
            newMain = None
            oldMain = mainpath
            c = 0
            while (True and c < 50):
                newMain = os.path.split(oldMain)[0]
                newFull = os.path.join(newMain, filepath)
                if (os.path.isfile(newFull) or newMain == oldMain):
                    path = newFull
                    break
                oldMain = newMain
                c = c + 1
    return path
