import requests,re,json,time,html
base="https://digitalcommons.humboldt.edu/do/oai/"
params={"verb":"ListRecords","metadataPrefix":"oai_dc","set":"publication:hcapc_aerial"}
recs=[]; n=0
while True:
    r=requests.get(base,params=params,timeout=90,headers={"User-Agent":"Mozilla/5.0"})
    t=r.text
    if n==0: print(r.status_code,t[:500])
    for rec in re.findall(r'<record>(.*?)</record>',t,flags=re.S):
        d={}
        for tag in ['title','date','subject','description','identifier','coverage','source','format']:
            d[tag]=[html.unescape(x) for x in re.findall(rf'<dc:{tag}>(.*?)</dc:{tag}>',rec,flags=re.S)]
        recs.append(d)
    m=re.search(r'<resumptionToken[^>]*>([^<]+)</resumptionToken>',t)
    n+=1
    if not m: break
    params={"verb":"ListRecords","resumptionToken":m.group(1)}
    if n%10==0: print(n,len(recs),flush=True)
json.dump(recs,open('hc/oai.json','w'))
print(len(recs))
