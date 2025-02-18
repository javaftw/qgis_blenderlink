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

from .operator_connect import QGIS_OT_connect
from .operator_update_layers import QGIS_OT_update_layers
from .operator_import_layer import QGIS_OT_import_layer
from .operator_snapshot import QGIS_OT_update_snapshot
from .operator_displacement_map import QGIS_OT_displacement_map

from .properties import QGISLayerProperties, QGISProjectProperties
from .panels import QGIS_PT_import_panel


def register():
    bpy.utils.register_class(QGISLayerProperties)
    bpy.utils.register_class(QGISProjectProperties)
    bpy.utils.register_class(QGIS_OT_connect)
    bpy.utils.register_class(QGIS_OT_update_layers)
    bpy.utils.register_class(QGIS_OT_import_layer)
    bpy.utils.register_class(QGIS_PT_import_panel)
    bpy.utils.register_class(QGIS_OT_displacement_map)
    bpy.utils.register_class(QGIS_OT_update_snapshot)

    bpy.types.Scene.qgis_layers = bpy.props.CollectionProperty(type=QGISLayerProperties)
    bpy.types.Scene.qgis_project = bpy.props.CollectionProperty(type=QGISProjectProperties)
    bpy.types.Scene.qgis_displacement = bpy.props.CollectionProperty(type=QGISProjectProperties)
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
    bpy.utils.unregister_class(QGIS_OT_displacement_map)
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
    del bpy.types.Scene.qgis_displacement


if __name__ == "__main__":
    register()
