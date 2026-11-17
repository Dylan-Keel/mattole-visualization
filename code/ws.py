import numpy as _np
_np.in1d=_np.isin
import numpy as np, rasterio, geopandas as gpd, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pysheds.grid import Grid
from shapely.geometry import shape, Point
from rasterio import features
grid=Grid.from_raster('dem10.tif'); dem=grid.read_raster('dem10.tif')
p=grid.fill_pits(dem); f=grid.fill_depressions(p); i=grid.resolve_flats(f)
fdir=grid.flowdir(i); acc=grid.accumulation(fdir)
parcel=gpd.read_file('parcel.geojson').to_crs(26910)
nhd=gpd.read_file('nhd.geojson').to_crs(26910)
src=rasterio.open('dem10.tif'); T=src.transform
pm=features.rasterize([(parcel.geometry.iloc[0],1)],out_shape=dem.shape,transform=T).astype(bool)
# trace downstream from each parcel cell; record path
dirmap={64:(-1,0),128:(-1,1),1:(0,1),2:(1,1),4:(1,0),8:(1,-1),16:(0,-1),32:(-1,-1)}
fd=np.array(fdir); A=np.array(acc)
rows,cols=np.where(pm)
# exit points: follow until acc > threshold steps
ends={}
for r,c in zip(rows[::7],cols[::7]):
    path=[]
    for _ in range(3000):
        d=fd[r,c]
        if d not in dirmap: break
        dr,dc=dirmap[d]; r+=dr; c+=dc
        if not(0<=r<fd.shape[0] and 0<=c<fd.shape[1]): break
        path.append((r,c,A[r,c]))
    # record acc milestones along path
    key=tuple((rr,cc) for rr,cc,a in path if a>20000)[:1]
    ends[key]=ends.get(key,0)+1
print(ends)
np.save('acc.npy',A); np.save('fd.npy',fd)
fig,ax=plt.subplots(figsize=(12,12))
ext=[T.c,T.c+T.a*dem.shape[1],T.f+T.e*dem.shape[0],T.f]
ls=np.gradient(np.array(dem)); hs=-(ls[0]+ls[1])
ax.imshow(hs,cmap='gray',extent=ext,vmin=-15,vmax=15)
ax.imshow(np.where(A>500,1,np.nan),extent=ext,cmap='cool',alpha=.8,interpolation='nearest')
parcel.boundary.plot(ax=ax,color='red'); 
for n,g in nhd[nhd.gnis_name.notna()].dissolve('gnis_name').iterrows():
    c=g.geometry.representative_point(); ax.text(c.x,c.y,n,color='yellow',fontsize=8)
ax.set_xlim(388000,398000); ax.set_ylim(4453000,4463000); ax.grid(alpha=.3)
plt.savefig('ws_overview.png',dpi=90,bbox_inches='tight')
