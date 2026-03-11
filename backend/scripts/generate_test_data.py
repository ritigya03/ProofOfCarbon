import zipfile
import os
from pathlib import Path

def create_kml(filename, name, coordinates):
    kml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <Placemark>
      <name>{name} Boundary</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
{coordinates}
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(kml_template)

def zip_to_kmz(kml_filename, kmz_filename):
    with zipfile.ZipFile(kmz_filename, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(kml_filename, arcname=os.path.basename(kml_filename))

def main():
    base_path = Path("data/sample_claims")
    base_path.mkdir(parents=True, exist_ok=True)

    # 1. Valid REDD+ Claim (Karnataka High Forest - Coorg)
    redd_coords = """              75.750000,12.420000,0 
              75.760000,12.420000,0 
              75.760000,12.430000,0 
              75.750000,12.430000,0 
              75.750000,12.420000,0"""
    create_kml(base_path / "redd_valid_forest.kml", "REDD+ High Forest Project", redd_coords)
    zip_to_kmz(base_path / "redd_valid_forest.kml", base_path / "redd_valid_forest.kmz")

    # 2. Valid ARR Claim (Bagepalli Area - Semi-arid)
    arr_coords = """              77.750000,13.750000,0 
              77.820000,13.750000,0 
              77.820000,13.820000,0 
              77.750000,13.820000,0 
              77.750000,13.750000,0"""
    create_kml(base_path / "arr_valid_reforestation.kml", "ARR Reforestation Project", arr_coords)
    zip_to_kmz(base_path / "arr_valid_reforestation.kml", base_path / "arr_valid_reforestation.kmz")

    # 3. Failing REDD+ (Claiming forest where none exists - Bangalore city center)
    redd_fail_coords = """              77.580000,12.970000,0 
              77.590000,12.970000,0 
              77.590000,12.980000,0 
              77.580000,12.980000,0 
              77.580000,12.970000,0"""
    create_kml(base_path / "redd_fail_low_overlap.kml", "REDD+ Fraudulent Claim", redd_fail_coords)
    zip_to_kmz(base_path / "redd_fail_low_overlap.kml", base_path / "redd_fail_low_overlap.kmz")

    # 4. Failing ARR (Additionality fail - planting trees in already dense forest)
    arr_fail_coords = """              75.500000,12.400000,0 
              75.510000,12.400000,0 
              75.510000,12.410000,0 
              75.500000,12.410000,0 
              75.500000,12.400000,0"""
    create_kml(base_path / "arr_fail_additionality.kml", "ARR Baseline Inflation", arr_fail_coords)
    zip_to_kmz(base_path / "arr_fail_additionality.kml", base_path / "arr_fail_additionality.kmz")

    # 5. Andhra Pradesh REDD+ (Testing cross-state registry)
    ap_redd_coords = """              81.450000,17.450000,0 
              81.460000,17.450000,0 
              81.460000,17.460000,0 
              81.450000,17.460000,0 
              81.450000,17.450000,0"""
    create_kml(base_path / "andhra_redd_project.kml", "Andhra Pradesh Forest Protection", ap_redd_coords)
    zip_to_kmz(base_path / "andhra_redd_project.kml", base_path / "andhra_redd_project.kmz")

    print("✨ Comprehensive test data generated in data/sample_claims/")

if __name__ == "__main__":
    main()
