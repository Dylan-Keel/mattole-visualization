import json,base64,io,rasterio,numpy as np,re
from PIL import Image
t=open('page.tpl').read(); D=json.loads(open('site/data.json').read())
SZ={'w':(1600,1800),'p':(1500,2062),'d':(1400,1050)}
IMG={}
for f in D['frames']:
    for k in ('w','p','d'):
        im=Image.open(f'site/frames/{k}_{f["id"]}.jpg').convert('RGB').resize(SZ[k],Image.LANCZOS)
        b=io.BytesIO(); im.save(b,'JPEG',quality=78,optimize=True,progressive=True); IMG[f'{k}_{f["id"]}']='data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
def rep(a,b):
    global t
    assert a in t, a[:70]; t=t.replace(a,b)
rep("im.src='frames/'+view+'s_'+f.id+'.jpg'","im.src=IMG[view+'_'+f.id]")
rep("  if(Z.s<1.4||timer) return;","  return;")
a=t.index("/*SAVE-BEGIN*/"); b=t.index("/*SAVE-END*/")
save='''$('save').onclick=async()=>{
  const msg=$('msg'), f=F[idx], v=V[view]; play(false);
  try{ const c=renderStill(await loadImg(IMG[view+'_'+f.id]));
    const blob=await new Promise(r=>c.toBlob(r,'image/jpeg',0.93)); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='cooskie_'+v.name.toLowerCase()+'_'+f.id+'.jpg'; document.body.appendChild(a); a.click(); a.remove();
    msg.textContent='Saved '+f.label+'.';
  }catch(e){ msg.textContent='Could not save this frame. Right-click the image and choose Save image.'; }
};
'''
t=t[:a]+save+t[b:]
rep('<p class="meta">Stills save at full resolution: <span id="fullres"></span>. Pinch, scroll or drag the image to zoom and pan. Zooming in swaps in the full-resolution frame.</p>','<p class="meta">Pinch, scroll or drag the image to zoom and pan. This standalone copy embeds each frame at about two-thirds of full resolution to keep the file size down. <span id="fullres" hidden></span></p>')
t=t.replace('<link rel="preconnect" href="https://fonts.googleapis.com">\n','').replace(re.search(r'<link href="https://fonts.googleapis.com[^>]*>\n',t).group(0),'')
t=t.replace('const DATA=__DATA__;','const DATA='+json.dumps(D)+';\nconst IMG='+json.dumps(IMG)+';')
open('Cooskie_Ridge_Aerial_Flipbook.html','w').write(t)
import os; print(os.path.getsize('Cooskie_Ridge_Aerial_Flipbook.html')/1e6,'MB')
