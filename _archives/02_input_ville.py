#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Géocoder une ville en France à partir de son nom et d'un numéro de département (ex: 19, 75, 2A).
Utilise Nominatim (OpenStreetMap) via geopy, avec fallback par bounding box du département.

Exemples :
    python geocode_city_by_deptcode.py "Beaulieu-sur-Dordogne" --department 19
    python geocode_city_by_deptcode.py "Valence" --department 26
    python geocode_city_by_deptcode.py "Bastia" --department 2B
"""

import sys
import argparse
from typing import Optional, Tuple, List

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def _make_geocoder():
    # Nominatim exige un user_agent explicite et identifiable
    geolocator = Nominatim(user_agent="m365copilot-geocoder-demo")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)  # respect du service
    return geolocator, geocode


def _try_geocode_department_bbox(
    department_code: str,
    country: str = "France",
    language: str = "fr",
) -> Optional[Tuple[float, float, float, float]]:
    """
    Géocode le département à partir de son code (ex: '19', '2A') et retourne sa bounding box (west, south, east, north).
    On tente plusieurs formulations pour Nominatim.
    """
    _, geocode = _make_geocoder()

    # Variantes de requêtes pour maximiser les chances de trouver le département par code
    queries: List[str] = [
        f"Département {department_code}, {country}",
        f"Department {department_code}, {country}",
        f"Dept {department_code}, {country}",
        f"{department_code} {country} département",
        f"{department_code}, {country} département",
    ]

    for q in queries:
        try:
            d = geocode(q, language=language, addressdetails=True, country_codes="fr", exactly_one=True)
            if d and getattr(d, "raw", None) and d.raw.get("boundingbox"):
                south, north, west, east = map(float, d.raw["boundingbox"])  # [S, N, W, E]
                return (west, south, east, north)
        except Exception:
            # On poursuit avec la prochaine variante
            continue
    return None


def geocode_city_with_department_code(
    city: str,
    department_code: str,
    country: str = "France",
    language: str = "fr",
) -> Optional[Tuple[float, float, str]]:
    """
    Géocode une ville en précisant le département par son code.
    Stratégie :
      1) Essayer des requêtes directes (ville + code département)
      2) Fallback : bornage au périmètre du département via bounding box
    Retourne (lat, lon, label) si trouvé, sinon None.
    """
    geolocator, geocode = _make_geocoder()

    # 1) Essais directs : certaines variantes de requêtes "Ville, Département {code}, France"
    direct_queries = [
        f"{city}, Département {department_code}, {country}",
        f"{city}, Dept {department_code}, {country}",
        f"{city}, Department {department_code}, {country}",
        f"{city}, {department_code}, {country}",
    ]
    for q in direct_queries:
        try:
            loc = geocode(q, language=language, addressdetails=True, country_codes="fr", exactly_one=True)
            if loc:
                return (loc.latitude, loc.longitude, loc.raw.get("display_name", ""))
        except Exception:
            continue

    # 2) Fallback : borner la recherche au département (via sa bbox)
    bbox = _try_geocode_department_bbox(department_code, country=country, language=language)
    if bbox:
        west, south, east, north = bbox
        viewbox = [(west, south), (east, north)]  # geopy accepte [(min_lon, min_lat), (max_lon, max_lat)]
        try:
            loc = geocode(
                city,
                language=language,
                addressdetails=True,
                country_codes="fr",
                viewbox=viewbox,
                bounded=True,       # limite la recherche au viewbox
                exactly_one=True,
                limit=1,
            )
            if loc:
                return (loc.latitude, loc.longitude, loc.raw.get("display_name", ""))
        except Exception:
            pass

    # Aucun résultat
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Récupère latitude/longitude d'une ville en précisant le numéro de département (Nominatim via geopy)."
    )
    parser.add_argument("city", help="Nom de la ville (ex: 'Beaulieu-sur-Dordogne').")
    parser.add_argument(
        "--department", "-d", required=True,
        help="Numéro du département (ex: 19, 75, 2A, 2B, 971...)."
    )
    parser.add_argument(
        "--country", "-c", default="France",
        help="Pays (défaut: France)."
    )
    parser.add_argument(
        "--language", "-l", default="fr",
        help="Langue des résultats (défaut: fr)."
    )
    args = parser.parse_args()

    # Normalisation simple du code (conserve 2A/2B, retire espaces)
    dept_code = args.department.strip().upper()

    result = geocode_city_with_department_code(
        args.city, dept_code, country=args.country, language=args.language
    )

    if result is None:
        print(f"Aucune coordonnée trouvée pour: {args.city}, département {dept_code}, {args.country}")
        sys.exit(1)

    lat, lon, label = result
    print(f"Ville:      {args.city}, département {dept_code}, {args.country}")
    print(f"Latitude:   {lat:.6f}")
    print(f"Longitude:  {lon:.6f}")
    print(f"Résultat:   {label}")


if __name__ == "__main__":
    main()
