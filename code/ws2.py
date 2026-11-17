import numpy as _np
_np.in1d=_np.isin
import numpy as np, rasterio, geopandas as gpd, warnings; warnings.filterwarnings('ignore')
from pysheds.grid import Grid
from rasterio import features
from shapely.geometry import shape
from shapely.ops import unary_union
grid=Grid.from_raster('dem10.tif'); dem=grid.read_raster('dem10.tif')
i=grid.resolve_flats(grid.fill_depressions(grid.fill_pits(dem)))
fdir=grid.flowdir(i)
fd=np.load('fd.npy'); A=np.load('acc.npy')
src=rasterio.open('dem10.tif'); T=src.transform
parcel=gpd.read_file('parcel.geojson').to_crs(26910)
nhd=gpd.read_file('nhd.geojson').to_crs(26910)
mat=nhd[nhd.gnis_name=='Mattole River'].buffer(40)
mm=features.rasterize([(g,1) for g in mat],out_shape=fd.shape,transform=T).astype(bool)
pm=features.rasterize([(parcel.geometry.iloc[0],1)],out_shape=fd.shape,transform=T).astype(bool)
dirmap={64:(-1,0),128:(-1,1),1:(0,1),2:(1,1),4:(1,0),8:(1,-1),16:(0,-1),32:(-1,-1)}
pours={}
for r,c in zip(*np.where(pm)):
    pr,pc=r,c
    for _ in range(5000):
        d=fd[r,c]
        if d not in dirmap: break
        dr,dc=dirmap[d]; pr,pc=r,c; r+=dr; c+=dc
        if mm[r,c]: break
    pours[(pr,pc)]=pours.get((pr,pc),0)+1
print({k:(v,A[k]) for k,v in pours.items()})
polys=[]
for (r,c),n in pours.items():
    x,y=T*(c+.5,r+.5)
    cat=grid.catchment(x=x,y=y,fdir=fdir,xytype='coordinate')
    m=np.array(cat).astype('uint8')
    for g,v in features.shapes(m,mask=m.astype(bool),transform=T): polys.append(shape(g))
    print(n, m.sum()*100/4046.86,'ac')
ws=gpd.GeoDataFrame(geometry=[unary_union(polys)],crs=26910)
ws.to_file('watershed.geojson',driver='GeoJSON')
print(ws.area/4046.86, ws.total_bounds, parcel.within(ws.geometry.iloc[0]).all(), parcel.intersection(ws.geometry.iloc[0]).area/parcel.area)
