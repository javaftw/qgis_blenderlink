import bpy
import requests
import bmesh
import base64
from bpy.props import StringProperty
from bpy.types import Operator
from .utils import error_handler, add_custom_properties

# Operator to connect to QGIS and retrieve available layers
class QGIS_OT_connect(Operator):
    bl_idname = "qgis.connect"
    bl_label = "Link"
    bl_description = "Connect to QGIS and retrieve available layers"

    @error_handler
    def execute(self, context):
        # Fetch project and layer information from QGIS server
        response_layer_info = requests.get(f'{context.scene.qgis_server_url}/layers')
        data_layer_info = response_layer_info.json()
        
        response_project_info = requests.get(f'{context.scene.qgis_server_url}/project_info')
        data_project_info = response_project_info.json()

        # Update project info and layers in Blender
        self.update_project_info(context, data_project_info)
        self.update_layers(context, data_layer_info)

        # Create or replace QGIS camera and rectangle
        self.create_or_replace_qgis_camera(context, data_project_info)

        context.scene.qgis_linked = True
        self.report({'INFO'}, f"Retrieved {len(context.scene.qgis_layers)} layers")
        return {'FINISHED'}

    def create_or_replace_qgis_camera(self, context, project_info):
        # Remove existing qgis_camera and qgis_extent objects if they exist
        for obj_name in ["qgis_camera", "qgis_extent"]:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)
        
        # Set up camera and rectangle to match QGIS project
        canvas_width = project_info['canvas_size']['width']
        canvas_height = project_info['canvas_size']['height']
        extent = project_info['project_extent']

        context.scene.render.resolution_x = canvas_width
        context.scene.render.resolution_y = canvas_height
        context.scene.render.resolution_percentage = 100

        # Create orthographic camera
        cam_data = bpy.data.cameras.new(name="qgis_camera")
        cam_object = bpy.data.objects.new("qgis_camera", cam_data)
        context.scene.collection.objects.link(cam_object)
        cam_data.type = 'ORTHO'

        # Create rectangle representing QGIS extent
        bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, location=(0, 0, 0))
        rect = context.active_object
        rect.name = "qgis_extent"

        rect_width = extent['xmax'] - extent['xmin']
        rect_height = extent['ymax'] - extent['ymin']
        rect.scale = (rect_width, rect_height, 1)
        cam_data.ortho_scale = max(rect_width, rect_height)

        cam_height = max(rect_width, rect_height)
        cam_object.location = (0, 0, cam_height)

        center_x = (extent['xmax'] + extent['xmin']) / 2
        center_y = (extent['ymax'] + extent['ymin']) / 2
        context.scene.qgis_offset = (center_x, center_y, 0)

        context.scene.camera = cam_object

    def update_project_info(self, context, data):
        # Update project information in Blender
        context.scene.qgis_project.clear()
        item = context.scene.qgis_project.add()
        item.label = "Project Information"
        item.name = data.get('project_name', 'Unnamed project')
        item.crs = data.get('project_crs', '').get('auth_id', 'Unspecified CRS')
        item.xmin = data.get('project_extent', '').get('xmin', 0)
        item.xmax = data.get('project_extent', '').get('xmax', 0)
        item.ymin = data.get('project_extent', '').get('ymin', 0)
        item.ymax = data.get('project_extent', '').get('ymax', 0)
        item.canvas_width = data.get('canvas_size', '').get('width', 0)
        item.canvas_height = data.get('canvas_size', '').get('height', 0)
        item.canvas_scale = data.get('canvas_scale', 1.0)

    def update_layers(self, context, data):
        # Update layers in Blender
        context.scene.qgis_layers.clear()
        layers = data.get('layers', [])
        for layer in layers:
            item = context.scene.qgis_layers.add()
            item.name = layer.get('name', 'Unnamed Layer')
            item.layer_id = layer.get('id', '')
            item.type = layer.get('type', 'Unknown')
            item.feature_count = str(layer.get('feature_count', 0))


def register():
    bpy.utils.register_class(QGIS_OT_connect)

def unregister():
    bpy.utils.unregister_class(QGIS_OT_connect)

if __name__ == "__main__":
    register()
