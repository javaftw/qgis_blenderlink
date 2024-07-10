import base64
import bpy
import requests
import math
import bmesh
from bpy.types import Operator
from bpy.props import StringProperty, FloatProperty


class QGIS_OT_displacement_map(Operator):
    bl_idname = "qgis.displacement_map"
    bl_label = "Set displacement"
    bl_description = "Set the QGIS map canvas snapshot as displacement map"

    layer_id: StringProperty()
    displacement_strength: FloatProperty(
        name="Displacement Strength",
        description="Strength of the displacement effect",
        default=1.0,
        min=0.0,
        max=10.0
    )

    def execute(self, context):
        try:
            self.import_as_displacement(context)
            self.report({'INFO'}, "Elevation map from QGIS updated")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error setting displacement map: {str(e)}")
            return {'CANCELLED'}

    def import_as_displacement(self, context):
        extent_obj = bpy.data.objects.get("qgis_extent")
        if not extent_obj:
            raise ValueError("qgis_extent object not found")

        displaced_obj = extent_obj.copy()
        displaced_obj.data = extent_obj.data.copy()
        displaced_obj.name = "qgis_extent_displaced"
        bpy.context.scene.collection.objects.link(displaced_obj)

        response = requests.get(f'{context.scene.qgis_server_url}/snapshot')
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch snapshot: HTTP {response.status_code}")

        data = response.json()
        image_data = base64.b64decode(data['image'])

        image_name = "QGISSnapshot"
        if image_name in bpy.data.images:
            bpy_image = bpy.data.images[image_name]
            bpy_image.scale(data['width'], data['height'])
        else:
            bpy_image = bpy.data.images.new(image_name, width=data['width'], height=data['height'])
        bpy_image.pack(data=image_data, data_len=len(image_data))
        bpy_image.source = 'FILE'
        bpy_image.reload()

        # Calculate subdivisions based on aspect ratio
        width = extent_obj.dimensions.x
        height = extent_obj.dimensions.y
        aspect_ratio = width / height
        min_divisions = 10

        if aspect_ratio >= 1:
            x_divisions = max(min_divisions, math.ceil(min_divisions * aspect_ratio))
            y_divisions = min_divisions
        else:
            x_divisions = min_divisions
            y_divisions = max(min_divisions, math.ceil(min_divisions / aspect_ratio))

        # Create new bmesh
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=x_divisions, y_segments=y_divisions, size=1)

        # Apply bmesh to object
        bm.to_mesh(displaced_obj.data)
        bm.free()

        # Scale to match original dimensions
        displaced_obj.dimensions = (width, height, 0)

        # Ensure proper UV mapping
        bpy.context.view_layer.objects.active = displaced_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.unwrap()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Apply subdivision modifier for additional detail
        subdiv_mod = displaced_obj.modifiers.new(name="Subdivision", type='SUBSURF')
        subdiv_mod.subdivision_type = 'SIMPLE'
        subdiv_mod.levels = 2
        subdiv_mod.render_levels = 4

        # Apply displacement modifier
        disp_mod = displaced_obj.modifiers.new(name="Displacement", type='DISPLACE')
        disp_mod.texture_coords = 'UV'
        disp_mod.strength = self.displacement_strength

        texture = bpy.data.textures.new("DisplacementTexture", type='IMAGE')
        texture.image = bpy_image
        disp_mod.texture = texture

        # Ensure the displaced object matches the extent object's size
        displaced_obj.dimensions = extent_obj.dimensions

        self.report({'INFO'}, "Displacement map applied")


def register():
    bpy.utils.register_class(QGIS_OT_displacement_map)


def unregister():
    bpy.utils.unregister_class(QGIS_OT_displacement_map)


if __name__ == "__main__":
    register()