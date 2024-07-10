import base64
import bpy
import requests
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

        # Ensure proper UV mapping
        bpy.context.view_layer.objects.active = displaced_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.unwrap()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Controlled subdivision
        subdivisions = min(6, max(2, int(max(displaced_obj.dimensions.x, displaced_obj.dimensions.y) / 10)))

        subdiv_mod = displaced_obj.modifiers.new(name="Subdivision", type='SUBSURF')
        subdiv_mod.levels = subdivisions
        subdiv_mod.render_levels = subdivisions

        disp_mod = displaced_obj.modifiers.new(name="Displacement", type='DISPLACE')
        disp_mod.texture_coords = 'UV'
        disp_mod.strength = self.displacement_strength

        texture = bpy.data.textures.new("DisplacementTexture", type='IMAGE')
        texture.image = bpy_image
        disp_mod.texture = texture

        self.report({'INFO'}, "Displacement map applied")


def register():
    bpy.utils.register_class(QGIS_OT_displacement_map)


def unregister():
    bpy.utils.unregister_class(QGIS_OT_displacement_map)


if __name__ == "__main__":
    register()