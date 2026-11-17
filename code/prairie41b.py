import numpy as np, cv2, rasterio, geopandas as gpd, json, zipfile
from rasterio import features
from rasterio.transform import from_origin
from shapely.geometry import shape, LineString
b=(392000,4456700,394400,4459400)
a=rasterio.open('master/full_1941.tif').read(1); a=cv2.resize(a,(2400,2700),interpolation=cv2.INTER_AREA).astype(np.float32)  # 1 m
mean=cv2.GaussianBlur(a,(0,0),4); sq=cv2.GaussianBlur(a*a,(0,0),4); sd=np.sqrt(np.maximum(sq-mean*mean,0))
print('mean pct',np.percentile(mean,[10,50,80,90,95,99]),'sd pct',np.percentile(sd,[10,50,80,90]))
np.save('p41_mean.npy',mean); np.save('p41_sd.npy',sd)
import sys
TM=float(sys.argv[1]); TS=float(sys.argv[2])
m=((mean>TM)&(sd<TS)).astype(np.uint8)
m=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))
m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(15,15)))
cv2.imwrite('p41_mask.png',m*255)
c=cv2.cvtColor(a.astype(np.uint8),cv2.COLOR_GRAY2BGR); cs,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE); cv2.drawContours(c,cs,-1,(0,220,255),2)
cv2.imwrite('p41_chk.jpg',cv2.resize(c,(1200,1350),interpolation=cv2.INTER_AREA)); print('open frac',m.mean())
