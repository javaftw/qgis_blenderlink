import bpy
from bpy.types import Panel
from .operator_connect import QGIS_OT_connect
from .operator_update_layers import QGIS_OT_update_layers
from .operator_import_layer import QGIS_OT_import_layer
from .operator_snapshot import QGIS_OT_update_snapshot
from .operator_displacement_map import QGIS_OT_displacement_map


# Define a new panel in the 3D Viewport UI
class QGIS_PT_import_panel(Panel):
    # Panel label that will be displayed in the UI
    bl_label = "QGIS BlenderLink"
    # Unique identifier for the panel
    bl_idname = "QGIS_PT_import_panel"
    # Specify that this panel should appear in the 3D Viewport
    bl_space_type = 'VIEW_3D'
    # Specify that this panel should be in the UI region (the tool shelf)
    bl_region_type = 'UI'
    # Define the category/tab in which this panel will appear
    bl_category = 'QGIS BlenderLink'

    def draw(self, context):
        # Reference to the panel's layout object
        layout = self.layout

        # Add a property field for the QGIS server URL
        layout.prop(context.scene, "qgis_server_url")

        # Check if the QGIS connection is active
        if context.scene.qgis_linked:
            # If linked, display the "Linked" button and the "Update Layers" button
            layout.operator(QGIS_OT_connect.bl_idname, text="Linked")
            layout.separator()
            for proj in context.scene.qgis_project:
                project_box = layout.box()
                project_row = project_box.row()
                project_row.prop(proj, "is_expanded", icon="TRIA_DOWN" if proj.is_expanded else "TRIA_RIGHT",
                                 icon_only=True, emboss=True)
                project_row.label(text=f"{proj.label}")
                if proj.is_expanded:
                    project_box.row().label(text=f"Location: {proj.name}")
                    project_box.row().label(text=f"CRS: {proj.crs}")
                    project_box.row().label(text=f"xMin: {proj.xmin}, xMax: {proj.xmax}")
                    project_box.row().label(text=f"yMin: {proj.ymin}, yMax: {proj.ymax}")
                    project_box.row().label(text=f"Map Scale: {proj.canvas_scale}")
                    project_box.row().label(text=f"Map Units: {proj.map_units}")
                    project_box.row().label(text=f"Map Canvas (px): {proj.canvas_width}, {proj.canvas_height}")
            layout.separator()
            layout.operator(QGIS_OT_update_layers.bl_idname, text="Update Layers")
            layout.separator()
            layout.operator(QGIS_OT_update_snapshot.bl_idname, text="Update from canvas")
        else:
            # If not linked, display the "Link" button to establish the connection
            layout.operator(QGIS_OT_connect.bl_idname, text="Link")

        # Add a separator line for better UI organization
        layout.separator()

        # Loop through each layer in the QGIS layers collection
        for layer in context.scene.qgis_layers:
            # Create a box layout for each layer
            box = layout.box()
            # Create a row within the box
            row = box.row()
            # Add a property to expand/collapse layer details with an arrow icon
            row.prop(layer, "is_expanded", icon="TRIA_DOWN" if layer.is_expanded else "TRIA_RIGHT", icon_only=True,
                     emboss=False)
            # Display the layer's name
            row.label(text=layer.name)
            # Add an "Import" button for each layer except rasters/displacement
            if layer.type.lower() not in ["raster", "displacement"]:
                row.operator(QGIS_OT_import_layer.bl_idname, text="Import").layer_id = layer.layer_id
            if layer.type.lower() == "displacement":
                row.operator(QGIS_OT_displacement_map.bl_idname, text="Displace").layer_id = layer.layer_id

            # If the layer is expanded, show additional details
            if layer.is_expanded:
                # Display the type of the layer (e.g., Point, Line, Polygon)
                box.label(text=f"Type: {layer.type}")
                # Display the feature count of the layer
                box.label(text=f"Feature count: {layer.feature_count}")
                # If the layer type is "Point", provide additional options for importing as spheres
                if layer.type.lower() == "point":
                    # Add a checkbox for making spheres
                    box.prop(layer, "make_spheres")
                    # If making spheres, provide additional properties to configure sphere geometry
                    if layer.make_spheres:
                        box.prop(layer, "sphere_radius")
                        box.prop(layer, "sphere_u_segments")
                        box.prop(layer, "sphere_v_segments")
