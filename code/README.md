# Processing code

Scripts used to build the Cooskie Ridge aerial flipbook in this repository. They were written step by step during the project and are kept as a record of the method, not as a packaged tool. Paths are hard-coded to the working directory they ran in, and several scripts expect files produced by earlier ones.

## Main steps

| Step | Scripts |
|---|---|
| Watershed delineation from the 10 m 3DEP elevation model | `ws.py`, `ws2.py`, `streams.py` |
| Modern imagery (NAIP, Esri World Imagery) | `naip_pc.py`, `wide.py` |
| Catalog harvest and frame location for the Cal Poly Humboldt collection | `oai.py`, `oai2.py`, `loc.py`, `loc2.py`, `hits.py`, `seq.py`, `strip.py`, `stripmatch.py` |
| Orthorectification of scanned frames against a simulated hillshade | `ortho.py`, `fit42.py`, `hs62.py`, `og.py`, `full.py`, `yb.py`, `mk.py` |
| 1941 open-ground mapping and KMZ export | `prairie41.py`, `prairie41b.py`, `kmz41.py` |
| 3D view rendering | `r3d.py` |
| Flipbook assembly | `build.py`, `page.tpl`, `export.py` |
| Page screenshots for checking | `shot.py`, `shot2.py`, `shot3.py`, `shot4.py` |

The remaining scripts (`coarse42*.py`, `demmatch*.py`, `grid42.py`, `stereo42.py`, `view42.py`, `ortho41.py`) are earlier attempts at registering the 1940s frames, kept for reference.

## Requirements

Python 3 with numpy, opencv-python, rasterio, geopandas, shapely, pyproj, pysheds, Pillow, requests, pystac-client, planetary-computer and playwright.

## Data sources

Full-resolution scans from the Humboldt County Aerial Photograph Collection are not included. They can be downloaded from Cal Poly Humboldt Digital Commons.
