import pystac_client, planetary_computer as pc, rasterio, numpy as np, collections
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from pyproj import Transformer
X0,Y0,X1,Y1=392000,4456700,394400,4459400; RES=0.5
W,H=int((X1-X0)/RES),int((Y1-Y0)/RES); T=from_origin(X0,Y1,RES,RES)
tr=Transformer.from_crs(26910,4326,always_xy=True)
lo=tr.transform(X0,Y0); hi=tr.transform(X1,Y1)
c=pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=pc.sign_inplace)
items=list(c.search(collections=["naip"],bbox=[lo[0],lo[1],hi[0],hi[1]]).items())
by=collections.defaultdict(list)
for it in items: by[it.datetime.year].append(it)
for y,its in sorted(by.items()):
    print(y,[(i.id,str(i.datetime.date())) for i in its],flush=True)
    out=np.zeros((4,H,W),'uint8')
    for it in its:
        with rasterio.open(it.assets['image'].href) as s:
            tmp=np.zeros((s.count,H,W),'uint8')
            reproject(rasterio.band(s,list(range(1,s.count+1))),tmp,dst_transform=T,dst_crs='EPSG:26910',resampling=Resampling.cubic)
            m=(tmp[:3].sum(0)>0)&(out[:3].sum(0)==0)
            out[:s.count][:,m]=tmp[:,m]
    with rasterio.open(f'master/naip_{y}.tif','w',driver='GTiff',width=W,height=H,count=4,dtype='uint8',crs='EPSG:26910',transform=T,compress='deflate',tiled=True) as d: d.write(out)
    print(y,'cov',(out[:3].sum(0)>0).mean())
