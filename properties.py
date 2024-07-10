import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty
from bpy.types import PropertyGroup

class QGISLayerProperties(PropertyGroup):
    name: StringProperty(name="Layer Name")
    layer_id: StringProperty(name="Layer ID")
    type: StringProperty(name="Layer Type")
    feature_count: StringProperty(name="Feature Count")
    make_spheres: BoolProperty(
        name="As spheres",
        description="Import points as spheres",
        default=False,
    )
    sphere_radius: FloatProperty(
        name="Sphere radius",
        description="Radius of the spheres",
        default=0.1,
        min=0.0001,
        max=10.0,
    )
    sphere_u_segments: IntProperty(
        name="U Segments",
        default=4,
        min=3,
        max=10
    )
    sphere_v_segments: IntProperty(
        name="V Segments",
        default=8,
        min=6,
        max=20
    )
    is_expanded: BoolProperty(default=True)


class QGISProjectProperties(PropertyGroup):
    label: StringProperty(name="Project Info")
    name: StringProperty(name="Project Name")
    crs: StringProperty(name="Project CRS")
    xmin: FloatProperty(name="xMin")
    xmax: FloatProperty(name="xMax")
    ymin: FloatProperty(name="yMin")
    ymax: FloatProperty(name="yMax")
    map_units: StringProperty(name="Map Units")
    canvas_width: IntProperty(name="Map Canvas Width")
    canvas_height: IntProperty(name="Map Canvas Height")
    canvas_scale: FloatProperty(name="Map Canvas Scale")
    is_expanded: BoolProperty(default=True)
    