bl_info = {
    "name": "QGIS BlenderLink",
    "author": "Your Name",
    "version": (1, 2),
    "blender": (4, 1, 0),
    "location": "View3D > Sidebar > QGIS BlenderLink",
    "description": "Links QGIS and Blender",
    "category": "Import-Export",
}

import bpy
from .operators import QGIS_OT_connect, QGIS_OT_update_layers, QGIS_OT_import_layer, QGIS_OT_update_snapshot
from .properties import QGISLayerProperties, QGISProjectProperties
from .panels import QGIS_PT_import_panel

def register():
    bpy.utils.register_class(QGISLayerProperties)
    bpy.utils.register_class(QGISProjectProperties)
    bpy.utils.register_class(QGIS_OT_connect)
    bpy.utils.register_class(QGIS_OT_update_layers)
    bpy.utils.register_class(QGIS_OT_import_layer)
    bpy.utils.register_class(QGIS_PT_import_panel)
    bpy.utils.register_class(QGIS_OT_update_snapshot)
    
    bpy.types.Scene.qgis_layers = bpy.props.CollectionProperty(type=QGISLayerProperties)
    bpy.types.Scene.qgis_project = bpy.props.CollectionProperty(type=QGISProjectProperties)
    bpy.types.Scene.qgis_linked = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.qgis_server_url = bpy.props.StringProperty(
        name="QGIS Server URL",
        default="http://localhost:8000",
        description="URL of the QGIS server"
    )
    bpy.types.Scene.qgis_offset = bpy.props.FloatVectorProperty(
        name="QGIS Offset",
        description="Offset between QGIS map center and Blender view center",
        size=3,
        default=(0, 0, 0)
    )

def unregister():
    bpy.utils.unregister_class(QGIS_PT_import_panel)
    bpy.utils.unregister_class(QGIS_OT_import_layer)
    bpy.utils.unregister_class(QGIS_OT_update_layers)
    bpy.utils.unregister_class(QGIS_OT_connect)
    bpy.utils.unregister_class(QGISProjectProperties)
    bpy.utils.unregister_class(QGISLayerProperties)
    bpy.utils.unregister_class(QGIS_OT_update_snapshot)
    
    del bpy.types.Scene.qgis_layers
    del bpy.types.Scene.qgis_project
    del bpy.types.Scene.qgis_linked
    del bpy.types.Scene.qgis_server_url
    del bpy.types.Scene.qgis_offset

if __name__ == "__main__":
    register()
