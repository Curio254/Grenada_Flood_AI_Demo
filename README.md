# Grenada Flood AI Demo

This is a small AI-based demo to predict flood-prone areas in Grenada using satellite imagery.  
The demo uses **NDWI (Normalized Difference Water Index)** combined with a **Random Forest classifier** to detect water/flood areas in a selected AOI (Area of Interest).

## Files
- `flood_ai_local.py` : Main Python demo script
- `requirements.txt` : Python packages needed
- `data/` : Sample AOI shapefile and raster
- `images/` : Optional screenshots or map snapshots
- `outputs/` : Generated flood polygons and interactive map (created when script runs)

## How the AI works
1. NDWI is calculated from the green and NIR bands of the raster to identify water.  
2. A small sample of NDWI values is labeled as water (1) or land (0).  
3. A **Random Forest** model is trained on this sample to predict flood areas across the raster.  
4. The prediction is converted to polygons and visualized on an interactive map.

## How to run the demo locally
1. Install Python 3.10+ and create a virtual environment.  
2. Install dependencies:

```bash
pip install -r requirements.txt
