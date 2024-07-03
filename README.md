# BlenderLink :: QGIS-Blender coupler

## Overview

BlenderLink connects QGIS with Blender, allowing easy import of geographic data and layers from QGIS into Blender.

- **blenderlink_qgis.py**: Handles requests for project info, layers, and map snapshots.
- **Blender Addon**: Communicates with the BlenderLink server from QGIS and imports data into Blender, supporting various geometry types (points, lines, polygons, rasters).

## Installation

1. **QGIS**:
   - Plugins > Python Console > Editor > load **blenderlink_qgis.py** from the location of the cloned repo (or wherever you copied it to), then modify if/as necessary and run the server script
   - A **BlenderLink Active** button is added to the toolbar when the server starts up succesfully. Clicking it will stop the server.
2. **Blender**:
   - Clone the repository, create a `blenderlink` directory in the Blender addons directory and copy the ```.py``` files to there.
   - Add it to Blender via `Edit > Preferences > Add-ons` then search for `blenderlink` under `Import/Export`, select and activate the addon.
   - The tool is accessible via the 3D view `QGIS BlenderLink` tab
