from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes, QgsSingleSymbolRenderer, QgsMarkerSymbol, QgsLineSymbol, \
    QgsFillSymbol, QgsCoordinateReferenceSystem
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

from qgis.core import QgsMapSettings, QgsMapRendererCustomPainterJob
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtCore import QSize, QBuffer, QByteArray
import base64


class BlenderLinkRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/project_info':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            project_info = get_project_info()
            self.wfile.write(json.dumps(project_info).encode())
        elif self.path == '/layers':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            layers_info = get_layers_info()
            self.wfile.write(json.dumps(layers_info).encode())
        elif self.path.startswith('/layer/'):
            layer_id = self.path.split('/')[-1]
            layer_data = export_layer_data(layer_id)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(layer_data).encode())
        elif self.path.startswith('/layerstyle/'):
            layer_id = self.path.split('/')[-1]
            style_data = export_layer_style(layer_id)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(style_data).encode())
        elif self.path == '/extent':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            extent_info = get_map_canvas_extent()
            self.wfile.write(json.dumps(extent_info).encode())
        elif self.path == '/snapshot':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            snapshot_data = get_map_snapshot()
            self.wfile.write(json.dumps(snapshot_data).encode())
        else:
            self.send_error(404)


def get_map_snapshot():
    canvas = iface.mapCanvas()
    settings = canvas.mapSettings()

    # Create a QImage with the same dimensions as the map canvas
    img = QImage(QSize(canvas.width(), canvas.height()), QImage.Format_ARGB32)
    img.fill(0)  # Fill with transparent color

    # Create a QPainter to render the map onto the image
    painter = QPainter(img)
    job = QgsMapRendererCustomPainterJob(settings, painter)
    job.start()
    job.waitForFinished()
    painter.end()

    # Convert the image to base64
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QBuffer.WriteOnly)
    img.save(buffer, "PNG")
    img_str = base64.b64encode(byte_array.data()).decode()

    return {
        'image': img_str,
        'width': canvas.width(),
        'height': canvas.height()
    }


def get_project_info():
    project = QgsProject.instance()
    canvas = iface.mapCanvas()

    # Get project CRS
    project_crs = project.crs()

    # Get map units
    map_units = project_crs.mapUnits()

    canvas = iface.mapCanvas()
    project_extent = canvas.extent()

    return {
        'project_name': project.fileName(),
        'project_crs': {
            'auth_id': project_crs.authid(),
            'description': project_crs.description(),
            'is_geographic': project_crs.isGeographic(),
            'proj_definition': project_crs.toProj4()
        },
        'project_extent': {
            'xmin': project_extent.xMinimum(),
            'ymin': project_extent.yMinimum(),
            'xmax': project_extent.xMaximum(),
            'ymax': project_extent.yMaximum()
        },
        'map_units': QgsUnitTypes.toString(map_units),
        'layer_count': len(project.mapLayers()),
        'canvas_size': {
            'width': canvas.width(),
            'height': canvas.height()
        },
        'canvas_scale': canvas.scale()
    }


def get_layers_info():
    project = QgsProject.instance()
    layers = []
    for layer_id, layer in project.mapLayers().items():
        if layer.type() == QgsVectorLayer.VectorLayer:
            layer_crs = layer.crs()
            layer_info = {
                'id': layer_id,
                'name': layer.name(),
                'type': QgsWkbTypes.displayString(layer.wkbType()),
                'feature_count': layer.featureCount(),
                'crs': {
                    'auth_id': layer_crs.authid(),
                    'description': layer_crs.description(),
                    'is_geographic': layer_crs.isGeographic(),
                    'proj_definition': layer_crs.toProj4()
                },
                'extent': {
                    'xmin': layer.extent().xMinimum(),
                    'ymin': layer.extent().yMinimum(),
                    'xmax': layer.extent().xMaximum(),
                    'ymax': layer.extent().yMaximum()
                },
                'style': get_layer_style(layer)
            }
            layers.append(layer_info)
    return {'layers': layers}


def get_layers_info():
    project = QgsProject.instance()
    layers = []
    for layer_id, layer in project.mapLayers().items():
        if layer.type() == QgsVectorLayer.VectorLayer:
            layer_crs = layer.crs()
            layer_info = {
                'id': layer_id,
                'name': layer.name(),
                'type': QgsWkbTypes.displayString(layer.wkbType()),
                'feature_count': layer.featureCount(),
                'crs': {
                    'auth_id': layer_crs.authid(),
                    'description': layer_crs.description(),
                    'is_geographic': layer_crs.isGeographic(),
                    'proj_definition': layer_crs.toProj4()
                },
                'extent': {
                    'xmin': layer.extent().xMinimum(),
                    'ymin': layer.extent().yMinimum(),
                    'xmax': layer.extent().xMaximum(),
                    'ymax': layer.extent().yMaximum()
                },
                'style': get_layer_style(layer)
            }
            layers.append(layer_info)
    return {'layers': layers}


def get_layer_style(layer):
    renderer = layer.renderer()
    if isinstance(renderer, QgsSingleSymbolRenderer):
        symbol = renderer.symbol()
        if isinstance(symbol, QgsMarkerSymbol):
            color = symbol.color().name()
            size = symbol.size()
            size_unit = symbol.sizeUnit()
            scale_method = symbol.scaleMethod()
            return {
                'symbol_type': symbol.type(),
                'color': color,
                'size': size,
                'size_unit': str(size_unit),
                'scale_method': str(scale_method)
            }
        elif isinstance(symbol, QgsLineSymbol):
            color = symbol.color().name()
            width = symbol.width()
            return {
                'symbol_type': symbol.type(),
                'color': color,
                'width': width
            }
        elif isinstance(symbol, QgsFillSymbol):
            fill_color = symbol.color().name()
            border_color = "N/A"
            for i in range(symbol.symbolLayerCount()):
                symbol_layer = symbol.symbolLayer(i)
                if hasattr(symbol_layer, 'borderColor'):
                    border_color = symbol_layer.borderColor().name()
                    break
            return {
                'symbol_type': symbol.type(),
                'color': fill_color,
                'border_color': border_color
            }
    return {}


def export_layer_data(layer_id):
    layer = QgsProject.instance().mapLayer(layer_id)
    if not layer:
        return {"error": "Layer not found"}

    features = layer.getFeatures()
    data = []
    for feature in features:
        geom = feature.geometry()
        if geom:
            geom_type = QgsWkbTypes.displayString(geom.wkbType())
            attributes = {field.name(): convert_to_python(feature[field.name()]) for field in layer.fields()}
            feature_data = {
                "type": geom_type,
                "geometry": json.loads(geom.asJson()),
                "attributes": attributes
            }
            data.append(feature_data)
    return {"features": data}


def export_layer_style(layer_id):
    layer = QgsProject.instance().mapLayer(layer_id)
    if not layer:
        return {"error": "Layer not found"}

    style = get_layer_style(layer)
    return style


def get_map_canvas_extent():
    canvas = iface.mapCanvas()
    extent = canvas.extent()
    return {
        'xmin': extent.xMinimum(),
        'xmax': extent.xMaximum(),
        'ymin': extent.yMinimum(),
        'ymax': extent.yMaximum()
    }


def convert_to_python(value):
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def run_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, BlenderLinkRequestHandler)
    print("BlenderLink server running on port 8000")
    httpd.serve_forever()


def blenderlink_button():
    action = QAction("BlenderLink Active", iface.mainWindow())
    action.setCheckable(True)
    action.setChecked(True)
    action.triggered.connect(lambda checked: print("BlenderLink server is", "active" if checked else "inactive"))
    iface.addToolBarIcon(action)


# Start the server in a separate thread
server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# Add the BlenderLink button to the QGIS interface
blenderlink_button()

print("BlenderLink QGIS script loaded successfully")
