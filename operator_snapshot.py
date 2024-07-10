import base64

import bpy
import requests
from bpy.types import Operator


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
    bpy.utils.register_class(QGIS_OT_update_snapshot)


def unregister():
    bpy.utils.unregister_class(QGIS_OT_update_snapshot)


if __name__ == "__main__":
    register()
