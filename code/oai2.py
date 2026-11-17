import requests,re,json,html
base="https://digitalcommons.humboldt.edu/do/oai/"
params={"verb":"ListRecords","metadataPrefix":"oai_dc","set":"publication:hcapc_aerial"}
out=open('hc/oai.jsonl','w'); n=0
while True:
    for k in range(4):
        try:
            t=requests.get(base,params=params,timeout=90,headers={"User-Agent":"Mozilla/5.0"}).text; break
        except Exception as e: t=''
    for rec in re.findall(r'<record>(.*?)</record>',t,flags=re.S):
        d={}
        for tag in ['title','date','subject','description','identifier','coverage','source']:
            d[tag]=[html.unescape(x) for x in re.findall(rf'<dc:{tag}>(.*?)</dc:{tag}>',rec,flags=re.S)]
        out.write(json.dumps(d)+'\n')
    out.flush()
    m=re.search(r'<resumptionToken[^>]*>([^<]+)</resumptionToken>',t)
    if not m: break
    params={"verb":"ListRecords","resumptionToken":m.group(1)}
open('hc/oai.done','w').write('done')
