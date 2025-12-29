# ============================================================ 
# Flood + SOVI Demo (Safe Version with Interactive Map)
# Grenada – NDWI + DEM + Population Exposure
# ============================================================

import os
import ee
import requests
import rasterio
import numpy as np
import folium
from rasterio.warp import reproject, Resampling
import matplotlib.cm as cm
from branca.colormap import linear
from folium.plugins import Fullscreen, MiniMap

# -----------------------------
# CONFIG
# -----------------------------
PROJECT_ID = "aerobic-amphora-482118-j4"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "outputs")
TIFF_DIR = os.path.join(OUT_DIR, "tiffs")

os.makedirs(TIFF_DIR, exist_ok=True)

NDWI_TIF = os.path.join(TIFF_DIR, "ndwi.tif")
DEM_TIF = os.path.join(TIFF_DIR, "dem.tif")
POP_TIF = os.path.join(TIFF_DIR, "population.tif")
RISK_TIF = os.path.join(TIFF_DIR, "flood_risk.tif")

# -----------------------------
# INITIALIZE EARTH ENGINE
# -----------------------------
ee.Initialize(project=PROJECT_ID)
print("✅ Earth Engine initialized with project")

# -----------------------------
# AOI – Grenada
# -----------------------------
aoi = ee.Geometry.Polygon([
    [
        [-61.8, 12.0],
        [-61.8, 12.6],
        [-61.3, 12.6],
        [-61.3, 12.0],
        [-61.8, 12.0]
    ]
])

# -----------------------------
# SAFE DOWNLOAD FUNCTION
# -----------------------------
def ee_download(img, out_path, scale):
    url = img.getDownloadURL({
        "scale": scale,
        "crs": "EPSG:4326",
        "region": aoi,
        "format": "GEO_TIFF",
        "maxPixels": 1e13
    })
    r = requests.get(url, stream=True)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"✅ Downloaded {out_path}")

# -----------------------------
# EARTH ENGINE DATA
# -----------------------------
s2 = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(aoi)
    .filterDate("2023-01-01", "2023-12-31")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    .median()
)
ndwi = s2.normalizedDifference(["B3", "B8"]).rename("NDWI").clip(aoi)
dem = ee.Image("USGS/SRTMGL1_003").clip(aoi)
population = (
    ee.ImageCollection("WorldPop/GP/100m/pop")
    .filterDate("2020-01-01", "2020-12-31")
    .mean()
    .clip(aoi)
)

# -----------------------------
# DOWNLOAD DATA (SAFE SCALES)
# -----------------------------
ee_download(ndwi, NDWI_TIF, scale=60)
ee_download(dem, DEM_TIF, scale=30)
ee_download(population, POP_TIF, scale=100)

# -----------------------------
# ALIGN RASTERS
# -----------------------------
def align_to_ref(src_path, ref_meta):
    with rasterio.open(src_path) as src:
        aligned = np.zeros((ref_meta["height"], ref_meta["width"]), dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=aligned,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_meta["transform"],
            dst_crs=ref_meta["crs"],
            resampling=Resampling.bilinear
        )
    return aligned

with rasterio.open(NDWI_TIF) as ref:
    ref_meta = ref.meta.copy()
    ndwi_arr = ref.read(1)

dem_arr = align_to_ref(DEM_TIF, ref_meta)
pop_arr = align_to_ref(POP_TIF, ref_meta)

# -----------------------------
# FLOOD RISK INDEX (SOVI-style)
# -----------------------------
ndwi_norm = np.clip((ndwi_arr + 1) / 2, 0, 1)
dem_norm = 1 - np.clip((dem_arr - np.nanmin(dem_arr)) / (np.nanmax(dem_arr) - np.nanmin(dem_arr) + 1e-6), 0, 1)
pop_norm = np.clip(pop_arr / (np.nanmax(pop_arr) + 1e-6), 0, 1)

flood_risk = 0.45 * ndwi_norm + 0.35 * dem_norm + 0.20 * pop_norm

# -----------------------------
# EXPORT FLOOD RISK GEOTIFF
# -----------------------------
ref_meta.update(dtype="float32", count=1)
with rasterio.open(RISK_TIF, "w", **ref_meta) as dst:
    dst.write(flood_risk.astype(np.float32), 1)
print("✅ Flood risk GeoTIFF created")

# -----------------------------
# HELPER: CONVERT ARRAY TO COLOR
# -----------------------------
def array_to_colormap(arr, cmap_name="viridis"):
    cmap = cm.get_cmap(cmap_name)
    normed = np.clip(arr, 0, 1)
    rgba = cmap(normed)
    rgb_uint8 = (rgba[:, :, :3] * 255).astype(np.uint8)
    return rgb_uint8

# -----------------------------
# CREATE FOLIUM MAP WITH INTERACTIVITY
# -----------------------------
m = folium.Map(
    location=[12.15, -61.65], 
    zoom_start=10, 
    control_scale=True, 
    zoom_control=True, 
    scrollWheelZoom=True, 
    dragging=True
)

# Add plugins
Fullscreen(position='topright').add_to(m)
MiniMap(toggle_display=True).add_to(m)

# -----------------------------
# ADD RASTER LAYERS
# -----------------------------
def add_raster_colormap(tif_path, name, cmap_name="viridis"):
    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        bounds = src.bounds
        arr_norm = (arr - np.nanmin(arr)) / (np.nanmax(arr) - np.nanmin(arr) + 1e-6)
        img_rgb = array_to_colormap(arr_norm, cmap_name=cmap_name)

    overlay = folium.raster_layers.ImageOverlay(
        image=img_rgb,
        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        opacity=0.7,
        name=name
    )
    overlay.add_to(m)

add_raster_colormap(NDWI_TIF, "NDWI", cmap_name="Blues")
add_raster_colormap(RISK_TIF, "Flood Risk Index", cmap_name="Reds")

# Add layer control for toggling
folium.LayerControl().add_to(m)

# -----------------------------
# ADD INTERACTIVE LEGENDS
# -----------------------------
ndwi_colormap = linear.Blues_09.scale(0, 1)
ndwi_colormap.caption = 'NDWI'
ndwi_colormap.add_to(m)

flood_colormap = linear.Reds_09.scale(0, 1)
flood_colormap.caption = 'Flood Risk'
flood_colormap.add_to(m)

# -----------------------------
# SAVE MAP
# -----------------------------
MAP_HTML = os.path.join(OUT_DIR, "flood_sovi_map.html")
m.save(MAP_HTML)
print("✅ Web map created:", MAP_HTML)
print("🎉 SCRIPT COMPLETED SUCCESSFULLY")
