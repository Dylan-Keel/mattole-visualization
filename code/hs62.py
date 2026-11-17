import numpy as np, cv2, rasterio, sys
from PIL import Image
dem=rasterio.open('ref/dem10.tif').read(1)   # 10 m, origin 384000,4468000
def hillshade(az,alt):
    gy,gx=np.gradient(dem,10.0); az=np.radians(az); alt=np.radians(alt)
    # surface normal n=(-dz/dx,-dz/dy,1); dz/dy(north) = -gy (rows increase southward)
    nx=-gx; ny=gy; nz=np.ones_like(dem); nn=np.sqrt(nx*nx+ny*ny+nz*nz)
    sx=np.sin(az)*np.cos(alt); sy=np.cos(az)*np.cos(alt); sz=np.sin(alt)
    return np.clip((nx*sx+ny*sy+nz*sz)/nn,0,1).astype(np.float32)
def crop(n):
    a=np.asarray(Image.open(f'hc/p1b/{n}.jpg').convert('L')); h,w=a.shape; return a[int(h*.07):int(h*.93),int(w*.07):int(w*.93)]
hp=lambda a,s=12:cv2.GaussianBlur(a,(0,0),1.0)-cv2.GaussianBlur(a,(0,0),s)
G=12.5
for n in ([int(x) for x in sys.argv[1:]] if __name__=="__main__" else []):
    t0=crop(n).astype(np.float32); best=[]
    for az in (140,160,180,200):
        H=cv2.resize(hillshade(az,35),None,fx=10/G,fy=10/G,interpolation=cv2.INTER_AREA); Hh=hp(H*255)
        for mpp in (11.5,12.0,12.5,13.0,13.5,14.0):
            t=cv2.resize(t0,None,fx=mpp/G,fy=mpp/G,interpolation=cv2.INTER_AREA); h,w=t.shape
            for rot in range(-12,13,2):
                M=cv2.getRotationMatrix2D((w/2,h/2),rot,1.0); tr=hp(cv2.warpAffine(t,M,(w,h),borderMode=cv2.BORDER_REFLECT))
                m=int(min(h,w)*0.12); tr=tr[m:-m,m:-m]
                res=cv2.matchTemplate(Hh,tr,cv2.TM_CCOEFF_NORMED); _,mx,_,loc=cv2.minMaxLoc(res)
                best.append((mx,az,mpp,rot,384000+(loc[0]+tr.shape[1]/2)*G,4468000-(loc[1]+tr.shape[0]/2)*G))
    best.sort(reverse=True); print('frame',n)
    for b in best[:6]: print('  ncc %.3f az %d mpp %.1f rot %d center %.0f %.0f'%b)
    print('  median %.3f'%np.median([b[0] for b in best]))
