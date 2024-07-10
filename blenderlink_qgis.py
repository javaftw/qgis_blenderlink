from qgis.core import (QgsProject, QgsVectorLayer, QgsMapLayer, QgsWkbTypes, QgsSingleSymbolRenderer, QgsMarkerSymbol, QgsLineSymbol,
                       QgsFillSymbol, QgsCoordinateReferenceSystem, QgsRasterLayer, QgsRasterDataProvider,
                       QgsMapSettings, QgsMapRendererCustomPainterJob, QgsUnitTypes)
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtCore import QSize, QBuffer, QByteArray
from qgis.utils import iface
import json, base64, threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class BlenderLinkRequestHandler(BaseHTTPRequestHandler):
    routes = {
        '/project_info': lambda: get_project_info(),
        '/layers': lambda: get_layers_info(),
        '/extent': lambda: get_map_canvas_extent(),
        '/snapshot': lambda: get_map_snapshot()
    }

    def do_GET(self):
        if self.path in self.routes:
            self.send_json_response(self.routes[self.path]())
        elif self.path.startswith('/layer/'):
            self.send_json_response(export_layer_data(self.path.split('/')[-1]))
        elif self.path.startswith('/layerstyle/'):
            self.send_json_response(export_layer_style(self.path.split('/')[-1]))
        else:
            self.send_error(404)

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def get_map_snapshot():
    canvas = iface.mapCanvas()
    img = QImage(QSize(canvas.width(), canvas.height()), QImage.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    job = QgsMapRendererCustomPainterJob(canvas.mapSettings(), painter)
    job.start()
    job.waitForFinished()
    painter.end()

    buffer = QBuffer()
    buffer.open(QBuffer.WriteOnly)
    img.save(buffer, "PNG")
    img_str = base64.b64encode(buffer.data()).decode()

    return {'image': img_str, 'width': canvas.width(), 'height': canvas.height()}


def get_project_info():
    project = QgsProject.instance()
    canvas = iface.mapCanvas()
    project_crs = project.crs()
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
        'map_units': QgsUnitTypes.toString(project_crs.mapUnits()),
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
        layer_crs = layer.crs()
        common_info = {
            'id': layer_id,
            'name': layer.name(),
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
            }
        }

        if layer.type() == QgsMapLayer.VectorLayer:
            geometry_type = QgsWkbTypes.displayString(layer.wkbType())
            layer_info = {
                **common_info,
                'type': 'vector',
                'geometry_type': geometry_type,
                'feature_count': layer.featureCount(),
                'style': get_layer_style(layer)
            }
        elif layer.type() == QgsMapLayer.RasterLayer:
            provider = layer.dataProvider()
            layer_info = {
                **common_info,
                'type': 'Displacement' if layer.name().lower() in ['displace', 'displacement'] else 'raster',
                'width': provider.xSize(),
                'height': provider.ySize()
            }
        else:
            continue

        layers.append(layer_info)
    return {'layers': layers}


def get_layer_style(layer):
    renderer = layer.renderer()
    if isinstance(renderer, QgsSingleSymbolRenderer):
        symbol = renderer.symbol()
        if isinstance(symbol, QgsMarkerSymbol):
            return {
                'symbol_type': symbol.type(),
                'color': symbol.color().name(),
                'size': symbol.size(),
                'size_unit': str(symbol.sizeUnit()),
                'scale_method': str(symbol.scaleMethod())
            }
        elif isinstance(symbol, QgsLineSymbol):
            return {
                'symbol_type': symbol.type(),
                'color': symbol.color().name(),
                'width': symbol.width()
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

    if layer.type() == QgsMapLayer.VectorLayer:
        features = []
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if geom:
                features.append({
                    "type": QgsWkbTypes.displayString(geom.wkbType()),
                    "geometry": json.loads(geom.asJson()),
                    "attributes": {field.name(): convert_to_python(feature[field.name()]) for field in layer.fields()}
                })
        return {"features": features}
    elif layer.type() == QgsMapLayer.RasterLayer:
        provider = layer.dataProvider()
        return {
            "type": "raster",
            "width": provider.xSize(),
            "height": provider.ySize(),
            "bands": provider.bandCount(),
            "data_type": provider.dataType(1),
            "extent": {
                "xmin": layer.extent().xMinimum(),
                "ymin": layer.extent().yMinimum(),
                "xmax": layer.extent().xMaximum(),
                "ymax": layer.extent().yMaximum()
            }
        }
    else:
        return {"error": "Unsupported layer type"}


def export_layer_style(layer_id):
    layer = QgsProject.instance().mapLayer(layer_id)
    return {"error": "Layer not found"} if not layer else get_layer_style(layer)


def get_map_canvas_extent():
    extent = iface.mapCanvas().extent()
    return {
        'xmin': extent.xMinimum(),
        'xmax': extent.xMaximum(),
        'ymin': extent.yMinimum(),
        'ymax': extent.yMaximum()
    }


def convert_to_python(value):
    return value if isinstance(value, (int, float, str, bool)) else str(value)


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