"""Create the Trees for Farmers Sonbhadra KMZ test file."""
import zipfile, os

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Trees for Farmers Carbon Neutrality Project</name>
    <Placemark>
      <name>Trees for Farmers Project (Sonbhadra, UP)</name>
      <description>
        Agroforestry ARR Project in Sonbhadra district, Uttar Pradesh.
        Implemented by Pangea EcoNetAssets Pvt. Ltd. under VCS standard to
        generate verified carbon credits via tree planting and carbon sequestration.
      </description>
      <Point>
        <coordinates>82.5920,24.1930,0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Approx Project Area</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              82.585,24.185,0
              82.600,24.185,0
              82.600,24.200,0
              82.585,24.200,0
              82.585,24.185,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""

outpath = os.path.join("data", "sample_claims", "trees_for_farmers_sonbhadra.kmz")
with zipfile.ZipFile(outpath, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("doc.kml", KML)

print(f"Created: {outpath} ({os.path.getsize(outpath)} bytes)")
