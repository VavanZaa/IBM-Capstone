"""Derive reproducible map points from the saved OpenStreetMap extract.

The nearest point on each line is approximated in a local equirectangular
projection. Distances in the notebook are great-circle distances to those
points. "Nearest" is restricted to the feature types/radii in the saved query.
"""
import csv
import json
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    hav = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    hav = min(1.0, max(0.0, hav))
    return 6373.0 * 2 * atan2(sqrt(hav), sqrt(1 - hav))


def closest_point(origin, geometry):
    """Find a point on a nearby polyline, not merely its closest mapped node."""
    scale = cos(radians(origin[0]))
    points = [(point["lat"], point["lon"]) for point in geometry]
    candidates = list(points)
    for a, b in zip(points, points[1:]):
        ax, ay = (a[1] - origin[1]) * scale, a[0] - origin[0]
        bx, by = (b[1] - origin[1]) * scale, b[0] - origin[0]
        dx, dy = bx - ax, by - ay
        denominator = dx * dx + dy * dy
        t = max(0.0, min(1.0, -(ax * dx + ay * dy) / denominator)) if denominator else 0.0
        candidates.append((origin[0] + ay + t * dy, origin[1] + (ax + t * dx) / scale))
    if not candidates:
        raise ValueError("Feature geometry is empty.")
    return min(candidates, key=lambda point: distance_km(origin, point))


def main():
    with (ROOT / "data/spacex_launch_geo.csv").open(newline="") as source:
        site = next(row for row in csv.DictReader(source) if row["Launch Site"] == "CCAFS LC-40")
    origin = (float(site["Lat"]), float(site["Long"]))
    snapshot = json.loads((ROOT / "data/launch_site_osm_features.json").read_text())
    groups = {"Coastline": [], "Railway": [], "Major road": [], "City/town centre": []}
    for element in snapshot["data"]["elements"]:
        tags = element.get("tags", {})
        if tags.get("natural") == "coastline":
            kind = "Coastline"
        elif tags.get("railway") == "rail":
            kind = "Railway"
        elif tags.get("highway") in {"motorway", "trunk", "primary", "secondary"}:
            kind = "Major road"
        elif element["type"] == "node" and tags.get("place") in {"city", "town"}:
            kind = "City/town centre"
        else:
            continue
        point = ((element["lat"], element["lon"]) if element["type"] == "node"
                 else closest_point(origin, element["geometry"]))
        groups[kind].append({
            "Feature": kind,
            "Name": tags.get("name", tags.get("ref",
                        "Rail spur" if tags.get("service") == "spur" else kind)),
            "Latitude": point[0],
            "Longitude": point[1],
            "Source": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
            "OSM_timestamp": snapshot["data"]["osm3s"]["timestamp_osm_base"],
        })
    selected = []
    for kind, records in groups.items():
        if not records:
            raise ValueError(f"No {kind} features in the saved extract.")
        selected.append(min(records, key=lambda row: distance_km(origin, (row["Latitude"], row["Longitude"]))))
    output = ROOT / "data/launch_site_proximity_points.csv"
    with output.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)
    for row in selected:
        distance = distance_km(origin, (row["Latitude"], row["Longitude"]))
        print(f"{row['Feature']}: {row['Name']} — {distance:.3f} km — {row['Source']}")


if __name__ == "__main__":
    main()
