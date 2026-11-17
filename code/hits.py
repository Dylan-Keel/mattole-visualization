import json,glob,re,collections,sys
B=(392000,4456700,394400,4459400); cxp,cyp=393200,4458050
rows=[]
for f in glob.glob('hc/loc_*.jsonl'):
    for l in open(f):
        r=json.loads(l); r['file']=f.split('loc_')[1][:-6]; rows.append(r)
print('frames scanned',len(rows), {k:v for k,v in collections.Counter(r['file'] for r in rows).items()})
zmin=float(sys.argv[1]) if len(sys.argv)>1 else 6.2
hits=[r for r in rows if r['z']>=zmin and not (r['x']<389000 and r['y']<4454500)]
by=collections.defaultdict(list)
for r in hits:
    roll=re.sub(r'[-_ ]?\d+[A-Za-z]?(_\d+)?$','',r['title']); by[(r['file'],roll)].append(r)
for k,v in sorted(by.items()):
    v.sort(key=lambda r:[int(x) if x.isdigit() else x for x in re.split(r'(\d+)',r['title'])])
    print(k,len(v))
    for r in v:
        half=r['mpp']*170; near=abs(r['x']-cxp)<half+1200 and abs(r['y']-cyp)<half+1350
        print('   ',r['title'],r['date'],'z',r['z'],'mpp',r['mpp'],'rot',r['rot'],r['x'],r['y'],'<<< near parcel' if near else '')
