
import sys
import os
import logging

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to path to import tools
sys.path.append(os.getcwd())

try:
    from tools.kmz_parser import parse_kmz
    path = os.path.join("data", "sample_claims", "varaha_arr_project.kmz")
    print(f"Testing file: {path}")
    
    if not os.path.exists(path):
        print(f"ERROR: File does not exist at {path}")
        sys.exit(1)
        


    import geopandas as gpd
    import fiona
    print(f"Geopandas version: {gpd.__version__}")
    try:
        import pyogrio
        print(f"Pyogrio version: {pyogrio.__version__}")
    except ImportError:
        print("Pyogrio not installed")
        
    print(f"Fiona version: {fiona.__version__}")
    print(f"Supported drivers: {fiona.drvsupport.supported_drivers.get('KML')}")
    
    # Simulate the temp dir extraction in parse_kmz
    import zipfile
    import tempfile
    from pathlib import Path
    
    with zipfile.ZipFile(path, "r") as kmz:
        with tempfile.TemporaryDirectory() as tmpdir:
            kmz.extractall(tmpdir)
            kml_files = list(Path(tmpdir).glob("**/*.kml"))
            kml_path = str(kml_files[0])
            print(f"Extracted KML path: {kml_path}")
            
            print("Checking layers via fiona.listlayers...")
            layers = fiona.listlayers(kml_path)
            print(f"Layers found: {layers}")
            
            gdf = parse_kmz(path)
            print("\nSUCCESS!")
    print(f"Features found: {len(gdf)}")
    print("\nGeometry details:")
    print(gdf.geometry)
    print("\nCoordinate System:")
    print(gdf.crs)

except Exception as e:
    print(f"\nFAILURE: {str(e)}")
    import traceback
    traceback.print_exc()
