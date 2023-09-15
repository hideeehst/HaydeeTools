from . import HaydeeMenuIcon
from . import HaydeeMenus
from . import HaydeePanels

_classes = [
    HaydeeMenuIcon,
    HaydeeMenus,
    HaydeePanels
]


def register():
    for cls in _classes:
        cls.register()


def unregister():
    for cls in reversed(_classes):
        cls.unregister()
