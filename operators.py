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

# Operator to refresh the list of layers from QGIS
class QGIS_OT_update_layers(Operator):
    bl_idname = "qgis.update_layers"
    bl_label = "Update Layers"
    bl_description = "Refresh the list of layers from QGIS"

    def execute(self, context):
        bpy.ops.qgis.connect()
        return {'FINISHED'}

# Operator to import a selected layer from QGIS into Blender
class QGIS_OT_import_layer(Operator):
    bl_idname = "qgis.import_layer"
    bl_label = "Import"
    bl_description = "Import selected layer from QGIS"

    layer_id: StringProperty()

    @error_handler
    def execute(self, context):
        # Retrieve layer data from QGIS server
        response = requests.get(f'{context.scene.qgis_server_url}/layer/{self.layer_id}')
        data = response.json()
        if 'error' in data:
            self.report({'ERROR'}, data['error'])
            return {'CANCELLED'}

        features = data.get('features', [])
        layer = next((layer for layer in context.scene.qgis_layers if layer.layer_id == self.layer_id), None)
        if not layer:
            self.report({'ERROR'}, "Layer not found")
            return {'CANCELLED'}

        # Remove existing collection if it exists
        existing_collection = bpy.data.collections.get(layer.name)
        if existing_collection:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in existing_collection.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(existing_collection)

        # Create new collection for the layer
        layer_collection = bpy.data.collections.new(layer.name)
        bpy.context.scene.collection.children.link(layer_collection)

        qgis_offset = context.scene.qgis_offset

        # Retrieve layer style from QGIS server
        style_response = requests.get(f'{context.scene.qgis_server_url}/layerstyle/{self.layer_id}')
        style_data = style_response.json()
        fill_color = style_data.get('color', '#ffffff')
        fill_color_rgba = self.hex_to_rgba(fill_color)

        # Import features based on geometry type
        if layer.type == "Point":
            if layer.make_spheres:
                self.import_as_spheres(context, features, layer.sphere_radius, layer.sphere_u_segments, layer.sphere_v_segments, layer.name, layer_collection, qgis_offset, fill_color_rgba)
            else:
                self.import_as_vertices(context, features, layer.name, layer_collection, qgis_offset, fill_color_rgba)
        elif "LineString" in layer.type:
            self.import_as_lines(context, features, layer.name, layer_collection, qgis_offset, fill_color_rgba)
        elif "Polygon" in layer.type:
            self.import_as_polygons(context, features, layer.name, layer_collection, qgis_offset, fill_color_rgba)

        self.report({'INFO'}, f"Imported {len(features)} features")
        return {'FINISHED'}

    def hex_to_rgba(self, hex_color):
        hex_color = hex_color.lstrip('#')
        lv = len(hex_color)
        if lv == 6:
            return tuple(int(hex_color[i:i + 2], 16) / 255 for i in range(0, 6, 2)) + (1.0,)
        elif lv == 8:
            return tuple(int(hex_color[i:i + 2], 16) / 255 for i in range(0, 8, 2))
        return 1.0, 1.0, 1.0, 1.0  # default white color

    def apply_offset(self, coords, offset):
        return [coords[0] - offset[0], coords[1] - offset[1], coords[2] - offset[2] if len(coords) > 2 else 0]

    def create_material(self, name, color):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = color
        return mat

    def import_as_vertices(self, context, features, layer_name, layer_collection, offset, color):
        mat = self.create_material(f"{layer_name}_material", color)
        for index, feature in enumerate(features):
            coords = self.apply_offset(feature['geometry']['coordinates'], offset)
            mesh = bpy.data.meshes.new(f"{layer_name}.point.{index}")
            obj = bpy.data.objects.new(f"{layer_name}.point.{index}", mesh)
            obj.data.materials.append(mat)
            if 'name' in feature['attributes']:
                obj.name = f"{layer_name}.point.{feature['attributes']['name']}"

            bm = bmesh.new()
            bm.verts.new(coords)
            bm.to_mesh(mesh)
            bm.free()

            layer_collection.objects.link(obj)
            bpy.context.view_layer.update()

            add_custom_properties(obj, feature['attributes'])

    def import_as_spheres(self, context, features, radius, u_segs, v_segs, layer_name, layer_collection, offset, color):
        mat = self.create_material(f"{layer_name}_material", color)
        for index, feature in enumerate(features):
            coords = self.apply_offset(feature['geometry']['coordinates'], offset)
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=v_segs,
                ring_count=u_segs,
                radius=radius,
                location=coords
            )
            sphere_obj = context.active_object
            sphere_obj.data.materials.append(mat)
            sphere_obj.name = f"{layer_name}.point.{index}"
            if 'name' in feature['attributes']:
                sphere_obj.name = f"{layer_name}.point.{feature['attributes']['name']}"

            bpy.context.scene.collection.objects.unlink(sphere_obj)
            layer_collection.objects.link(sphere_obj)
            bpy.context.view_layer.update()

            add_custom_properties(sphere_obj, feature['attributes'])

    def import_as_lines(self, context, features, layer_name, layer_collection, offset, color):
        mat = self.create_material(f"{layer_name}_material", color)
        for index, feature in enumerate(features):
            coords = feature['geometry']['coordinates']
            curve_data = bpy.data.curves.new(name=f"{layer_name}.curve.{index}", type='CURVE')
            curve_data.dimensions = '3D'

            if isinstance(coords[0][0], list):
                for line in coords:
                    polyline = curve_data.splines.new('POLY')
                    polyline.points.add(len(line) - 1)
                    for i, point in enumerate(line):
                        point = self.apply_offset(point, offset)
                        polyline.points[i].co = (point[0], point[1], point[2] if len(point) > 2 else 0, 1.0)
            else:
                polyline = curve_data.splines.new('POLY')
                polyline.points.add(len(coords) - 1)
                for i, point in enumerate(coords):
                    point = self.apply_offset(point, offset)
                    polyline.points[i].co = (point[0], point[1], point[2] if len(point) > 2 else 0, 1.0)

            curve_obj = bpy.data.objects.new(f"{layer_name}.line.{index}", curve_data)
            curve_obj.data.materials.append(mat)
            layer_collection.objects.link(curve_obj)
            bpy.context.view_layer.update()

            if 'name' in feature['attributes']:
                curve_obj.name = f"{layer_name}.line.{feature['attributes']['name']}"

            add_custom_properties(curve_obj, feature['attributes'])

    def import_as_polygons(self, context, features, layer_name, layer_collection, offset, color):
        mat = self.create_material(f"{layer_name}_material", color)
        for index, feature in enumerate(features):
            coords = feature['geometry']['coordinates']
            mesh = bpy.data.meshes.new(f"{layer_name}.polygon.{index}")
            obj = bpy.data.objects.new(f"{layer_name}.polygon.{index}", mesh)
            obj.data.materials.append(mat)
            bm = bmesh.new()

            if isinstance(coords[0][0], (int, float)):
                coords = [coords]

            for poly in coords:
                verts = [bm.verts.new(self.apply_offset(p, offset)) for p in poly[0]]
                bm.faces.new(verts)

            bm.to_mesh(mesh)
            bm.free()

            layer_collection.objects.link(obj)
            bpy.context.view_layer.update()

            if 'name' in feature['attributes']:
                obj.name = f"{layer_name}.polygon.{feature['attributes']['name']}"

            add_custom_properties(obj, feature['attributes'])

# Operator to update the QGIS map snapshot
class QGIS_OT_update_snapshot(Operator):
    bl_idname = "qgis.update_snapshot"
    bl_label = "Update Snapshot"
    bl_description = "Update the QGIS map snapshot"

    @classmethod
    def poll(cls, context):
        return context.scene.qgis_linked

    def execute(self, context):
        # Fetch the snapshot from the QGIS server
        response = requests.get(f'{context.scene.qgis_server_url}/snapshot')
        data = response.json()

        # Decode the base64 image
        image_data = base64.b64decode(data['image'])

        # Create or get the image in Blender
        image_name = "QGISSnapshot"
        if image_name in bpy.data.images:
            bpy_image = bpy.data.images[image_name]
        else:
            bpy_image = bpy.data.images.new(image_name, width=8, height=8)  # Dummy size

        # Pack the image data
        bpy_image.pack(data=image_data, data_len=len(image_data))

        # Switch to file source so it uses the packed file
        bpy_image.source = 'FILE'

        # Reload to refresh
        bpy_image.reload()

        # Create material and assign it to the QGIS extent rectangle
        mat_name = "QGISSnapshotMaterial"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True

        # Set up the material nodes
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = bpy_image

        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        output_node = nodes.new(type='ShaderNodeOutputMaterial')

        links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        # Assign the material to the QGIS extent rectangle
        rect = bpy.data.objects.get("qgis_extent")
        if rect:
            if len(rect.data.materials) == 0:
                rect.data.materials.append(mat)
            else:
                rect.data.materials[0] = mat

        # Force update of the viewport
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

        self.report({'INFO'}, "QGIS snapshot updated")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(QGIS_OT_connect)
    bpy.utils.register_class(QGIS_OT_update_layers)
    bpy.utils.register_class(QGIS_OT_import_layer)
    bpy.utils.register_class(QGIS_OT_update_snapshot)

def unregister():
    bpy.utils.unregister_class(QGIS_OT_connect)
    bpy.utils.unregister_class(QGIS_OT_update_layers)
    bpy.utils.unregister_class(QGIS_OT_import_layer)
    bpy.utils.unregister_class(QGIS_OT_update_snapshot)

if __name__ == "__main__":
    register()
