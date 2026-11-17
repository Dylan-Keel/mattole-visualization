python3 loc.py '^CVL-(7|9|6|10)N-' 3 hc/loc_cvl.jsonl
python3 loc.py '^CDF2-' 3 hc/loc_cdf2.jsonl
python3 loc.py '^HU\d' 3 hc/loc_hu.jsonl
python3 loc.py '^(HS ?\d|HSO)' 3 hc/loc_hs.jsonl
python3 loc.py '^(HC74|HC \d|CDF ALL|HUMBOLDT CO|86076|978|MK|GS-VCZP)' 3 hc/loc_misc.jsonl
echo done > hc/runA.done
