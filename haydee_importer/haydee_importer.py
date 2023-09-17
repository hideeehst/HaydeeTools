from .import_dmesh import ImportHaydeeDMesh
from .import_dmotion import ImportHaydeeDMotion
from .import_dpose import ImportHaydeeDPose
from .import_dskel import ImportHaydeeDSkel
from .import_material import ImportHaydeeMaterial
from .import_mesh import ImportHaydeeMesh
from .import_motion import ImportHaydeeMotion
from .import_outfit import ImportHaydeeOutfit
from .import_pose import ImportHaydeePose
from .import_skeleton import ImportHaydeeSkel
from .import_skin import ImportHaydeeSkin

_classes = [
    ImportHaydeeDMesh,
    ImportHaydeeDMotion,
    ImportHaydeeDPose,
    ImportHaydeeDSkel,
    ImportHaydeeMaterial,
    ImportHaydeeMesh,
    ImportHaydeeMotion,
    ImportHaydeeOutfit,
    ImportHaydeePose,
    ImportHaydeeSkel,
    ImportHaydeeSkin,
]


def register():
    from bpy.utils import register_class
    for cls in _classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(_classes):
        unregister_class(cls)
