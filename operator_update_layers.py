import bpy
import requests
import bmesh
import base64
from bpy.props import StringProperty
from bpy.types import Operator
from .utils import error_handler, add_custom_properties

# Operator to refresh the list of layers from QGIS
class QGIS_OT_update_layers(Operator):
    bl_idname = "qgis.update_layers"
    bl_label = "Update Layers"
    bl_description = "Refresh the list of layers from QGIS"

    def execute(self, context):
        bpy.ops.qgis.connect()
        return {'FINISHED'}

def register():
    bpy.utils.register_class(QGIS_OT_update_layers)

def unregister():
    bpy.utils.unregister_class(QGIS_OT_update_layers)

if __name__ == "__main__":
    register()
