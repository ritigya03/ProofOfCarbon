
import fiona
import geopandas as gpd
import os

print(f"Fiona version: {fiona.__version__}")
print(f"GDAL version: {fiona.env.get_gdal_release_name()}")

# Check supported drivers
drivers = fiona.supported_drivers
print("\nSupported Drivers (checking KML/LIBKML):")
print(f"KML: {drivers.get('KML')}")
print(f"LIBKML: {drivers.get('LIBKML')}")

# Update them
fiona.drvsupport.supported_drivers["KML"] = "rw"
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"

print("\nAfter update:")
print(f"KML in supported_drivers: {'KML' in fiona.supported_drivers}")
print(f"LIBKML in supported_drivers: {'LIBKML' in fiona.supported_drivers}")

# Try to list layers of a dummy KML if drivers are missing
try:
    from tools.kmz_parser import parse_kmz
    path = os.path.join("data", "sample_claims", "varaha_arr_project.kmz")
    print(f"\nTesting parse_kmz on: {path}")
    gdf = parse_kmz(path)
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
