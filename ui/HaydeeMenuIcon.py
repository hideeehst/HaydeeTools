# <pep8 compliant>
# https://docs.blender.org/api/current/bpy.utils.previews.html

from pathlib import Path
import bpy.utils.previews

# --------------------------------------------------------------------------------
#  Custom Icons
# --------------------------------------------------------------------------------
custom_icons = {}

def getHaydeeIconValue()-> bpy.utils.previews.ImagePreviewCollection:
    col_main=custom_icons["main"]
    iid = col_main["haydee_icon"].icon_id
    return iid

def register():
    #register custom icon
    global custom_icons
    icons_dir =Path(__file__).joinpath("../../icons")
    pcoll = bpy.utils.previews.new()
    pcoll.load("haydee_icon", str(icons_dir.joinpath("icon.png")), 'IMAGE')
    custom_icons["main"] = pcoll


def unregister():
    #unregister custom icon
    global  custom_icons
    for pcoll in custom_icons.values():
        bpy.utils.previews.remove(pcoll)
    custom_icons.clear()
