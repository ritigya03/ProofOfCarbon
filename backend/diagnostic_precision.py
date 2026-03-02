import requests
import json
import os

bbox = {'min_lon': 75.697838, 'min_lat': 12.322216, 'max_lon': 75.788065, 'max_lat': 12.393089}
# Expand bbox by 0.1 deg (~10km) for context
w, s, e, n = bbox['min_lon'] - 0.1, bbox['min_lat'] - 0.1, bbox['max_lon'] + 0.1, bbox['max_lat'] + 0.1

query = f"""
[out:json][timeout:60];
(
  way["natural"~"wood|scrub"]({s},{w},{n},{e});
  way["landuse"~"forest|orchard"]({s},{w},{n},{e});
  way["leisure"="nature_reserve"]({s},{w},{n},{e});
  way["boundary"~"forest|forest_reserve|protected_area"]({s},{w},{n},{e});
  relation["natural"~"wood|scrub"]({s},{w},{n},{e});
  relation["landuse"~"forest|orchard"]({s},{w},{n},{e});
  relation["leisure"="nature_reserve"]({s},{w},{n},{e});
  relation["boundary"~"forest_reserve|protected_area"]({s},{w},{n},{e});
);
out geom;
"""

url = "https://overpass-api.de/api/interpreter"
print(f"Fetching Overpass for Precision BBox: {w, s, e, n}...")
r = requests.post(url, data={"data": query})
if r.status_code == 200:
    data = r.json()
    elements = data.get("elements", [])
    print(f"Elements found in Buffer BBox: {len(elements)}")
    
    for el in elements[:10]:
        tags = el.get("tags", {})
        print(f"- ID: {el['id']}, Name: {tags.get('name', 'N/A')}, Type: {tags.get('natural') or tags.get('landuse') or tags.get('boundary')}")
        
    # Total area calculation would need geometry processing, but count alone tells us if it worked.
else:
    print(f"Overpass failed: {r.status_code}")
