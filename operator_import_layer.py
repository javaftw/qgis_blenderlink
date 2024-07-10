import bmesh
import bpy
import requests
import base64
from bpy.props import StringProperty
from bpy.types import Operator

from .utils import error_handler, add_custom_properties

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
                bpy.context.view_layer.objects.active = obj
                obj.select_set(True)
                bpy.ops.object.delete()
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

        # Import features based on type
        if "displacement" in layer.type.lower():
            self.import_as_displacement(context)
        elif "point" in layer.type.lower():
            if layer.make_spheres:
                self.import_as_spheres(context, features, layer.sphere_radius, layer.sphere_u_segments,
                                       layer.sphere_v_segments, layer.name, layer_collection, qgis_offset,
                                       fill_color_rgba)
            else:
                self.import_as_vertices(context, features, layer.name, layer_collection, qgis_offset, fill_color_rgba)
        elif "linestring" in layer.type.lower():
            self.import_as_lines(context, features, layer.name, layer_collection, qgis_offset, fill_color_rgba)
        elif "polygon" in layer.type.lower():
            self.import_as_polygons(context, features, layer.name, layer_collection, qgis_offset, fill_color_rgba)
        elif "raster" in layer.type.lower():
            self.report({'INFO'}, "Raster layers are not imported directly")
            return {'CANCELLED'}
        else:
            self.report({'WARNING'}, f"Unsupported layer type: {layer.type}")
            return {'CANCELLED'}

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

        if layer_collection.name not in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.link(layer_collection)

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

            for coll in sphere_obj.users_collection:
                coll.objects.unlink(sphere_obj)
            layer_collection.objects.link(sphere_obj)

            sphere_obj.name = f"{layer_name}.point.{index}"
            if 'name' in feature['attributes']:
                sphere_obj.name = f"{layer_name}.point.{feature['attributes']['name']}"

            add_custom_properties(sphere_obj, feature['attributes'])

        bpy.context.view_layer.update()

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

    def import_as_displacement(self, context):
        extent_obj = bpy.data.objects.get("qgis_extent")
        if not extent_obj:
            self.report({'ERROR'}, "qgis_extent object not found")
            return {'CANCELLED'}

        displaced_obj = extent_obj.copy()
        displaced_obj.data = extent_obj.data.copy()
        displaced_obj.name = "qgis_extent_displaced"
        bpy.context.scene.collection.objects.link(displaced_obj)

        response = requests.get(f'{context.scene.qgis_server_url}/snapshot')
        data = response.json()
        image_data = base64.b64decode(data['image'])

        image_name = "QGISSnapshot"
        if image_name in bpy.data.images:
            bpy_image = bpy.data.images[image_name]
        else:
            bpy_image = bpy.data.images.new(image_name, width=data['width'], height=data['height'])
        bpy_image.pack(data=image_data, data_len=len(image_data))
        bpy_image.source = 'FILE'
        bpy_image.reload()

        width = displaced_obj.dimensions.x
        height = displaced_obj.dimensions.y
        aspect_ratio = width / height
        subdivisions = max(int(aspect_ratio * 10), int(10 / aspect_ratio))

        bpy.context.view_layer.objects.active = displaced_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.loopcut_slide(number=subdivisions, edge_index=2)
        bpy.ops.mesh.loopcut_slide(number=subdivisions, edge_index=0)
        bpy.ops.object.mode_set(mode='OBJECT')

        subdiv_mod = displaced_obj.modifiers.new(name="Subdivision", type='SUBSURF')
        subdiv_mod.levels = 2
        subdiv_mod.render_levels = 2

        disp_mod = displaced_obj.modifiers.new(name="Displacement", type='DISPLACE')
        disp_mod.texture_coords = 'UV'
        disp_mod.strength = 1.0

        texture = bpy.data.textures.new("DisplacementTexture", type='IMAGE')
        texture.image = bpy_image
        disp_mod.texture = texture

        self.report({'INFO'}, "Displacement map applied")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(QGIS_OT_import_layer)

def unregister():
    bpy.utils.unregister_class(QGIS_OT_import_layer)

if __name__ == "__main__":
    register()