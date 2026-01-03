 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Trouve la station météo la plus proche d'un point (lat, lon) parmi une liste de stations (JSON).
Usage 1 (avec fichier) :
    python nearest_station.py --lat 47.321189 --lon -0.332695 --json-file stations.json

Usage 2 (sans fichier, en dur dans le script) :
    - Modifiez la variable STATIONS_JSON ci-dessous puis :
    python nearest_station.py --lat 47.321189 --lon -0.332695
"""

import json
import math
import argparse
from typing import List, Dict, Any, Tuple, Optional

# Exemple de données si vous ne passez pas de fichier.
# Remplacez/complétez si besoin.
STATIONS_JSON = [
  {
    "id": "49007003",
    "nom": "ANGERS ECOLE NORMALE",
    "posteOuvert": False,
    "typePoste": 4,
    "lon": -0.555,
    "lat": 47.47,
    "alt": 45,
    "postePublic": True
  },
  {
    "id": "49007004",
    "nom": "ANGERS JARDIN DES PLANTES",
    "posteOuvert": False,
    "typePoste": 4,
    "lon": -0.555,
    "lat": 47.47,
    "alt": 38,
    "postePublic": True
  },
  {
    "id": "49007005",
    "nom": "ANGERS BAUMETTE",
    "posteOuvert": False,
    "typePoste": 4,
    "lon": -0.555,
    "lat": 47.47,
    "alt": 37,
    "postePublic": True
  }
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distance grand cercle (Haversine) entre deux points (en km).
    """
    R = 6371.0088  # rayon moyen de la Terre (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_station(
    city_lat: float,
    city_lon: float,
    stations: List[Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
    """
    Retourne (station_la_plus_proche, distance_km). Si aucune station valide n'est trouvée, (None, None).
    Une station est considérée valide si elle possède des champs 'lat' et 'lon' numériques.
    """
    nearest: Optional[Dict[str, Any]] = None
    best_dist: Optional[float] = None

    for st in stations:
        if not st['posteOuvert']:
            continue
        try:
            slat = float(st["lat"])
            slon = float(st["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        d = haversine_km(city_lat, city_lon, slat, slon)
        if best_dist is None or d < best_dist:
            best_dist = d
            nearest = st

    return nearest, best_dist


def load_stations_from_file(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Trouve la station météo la plus proche d'une position.")
    parser.add_argument("--lat", type=float, required=True, help="Latitude de la ville (ex: 47.321189)")
    parser.add_argument("--lon", type=float, required=True, help="Longitude de la ville (ex: -0.332695)")
    parser.add_argument("--json-file", type=str, default=None, help="Chemin du fichier JSON des stations.")
    parser.add_argument("--top", type=int, default=1, help="Nombre de stations les plus proches à afficher (défaut: 1).")

    args = parser.parse_args()

    if args.json_file:
        stations = load_stations_from_file(args.json_file)
    else:
        stations = STATIONS_JSON

    # Nettoyage minimal : conserver uniquement celles ayant lat/lon
    stations = [s for s in stations if isinstance(s, dict) and "lat" in s and "lon" in s]

    if not stations:
        print("Aucune station valide (avec lat/lon) n'a été trouvée.")
        return

    # Tri par distance croissante
    stations_with_dist = []
    for s in stations:
        if not s['posteOuvert']:
            continue
        d = haversine_km(args.lat, args.lon, float(s["lat"]), float(s["lon"]))
        stations_with_dist.append((s, d))
    stations_with_dist.sort(key=lambda x: x[1])

    # Affiche la meilleure (ou le top-N demandé)
    top_n = max(1, args.top)
    best = stations_with_dist[:top_n]

    if top_n == 1:
        station, dist_km = best[0]
        print(json.dumps(station, ensure_ascii=False, indent=2))
        print(f"Distance_km: {dist_km:.3f}")
    else:
        result = []
        for s, d in best:
            out = dict(s)
            out["_distance_km"] = round(d, 3)
            result.append(out)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()