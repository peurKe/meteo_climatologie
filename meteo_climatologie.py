#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from meteo import Meteo

def main():
    parser = argparse.ArgumentParser(description="Appel API Météo-France DPClim (SSL désactivé).")
    parser.add_argument("--api-url", "-u", default=os.environ.get("METEOFRANCE_API_URL"), help="API URL Meteo France.")
    parser.add_argument("--api-key", "-a", default=os.environ.get("METEOFRANCE_API_KEY"), help="Clé API Meteo France.")
    parser.add_argument("--inputs-file", default="inputs.json", help="Fichier JSON contenant la liste de dictionnaire avec les informations des villes à traiter.")
    parser.add_argument("--date-deb", required=True, help="Début de période au format AAAA-MM-DD.")
    parser.add_argument("--date-fin", required=True, help="Fin de période au format AAAA-MM-DD.")
    parser.add_argument("--country", "-c", default="France", help="Pays (défaut: France).")
    parser.add_argument("--language", "-l", default="fr", help="Langue des résultats (défaut: fr).")
    parser.add_argument("--parameter", "-p", default="temperature", help="Paramètre de climatologie.")
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="Timeout en secondes.")
    parser.add_argument("--force", "-f", action="store_true", help="Force la mise à jour de toutes les données.")
    args = parser.parse_args()
        
    # # DEBUG
    # print(f"args.api_url = {args.api_url}")
    # print(f"args.api_key = {args.api_key}")
    # os._exit(0)

    # Validation API URL et Key
    if not args.api_url:
        print("Erreur: fournissez METEOFRANCE_API_URL ou --api-url ou -u", file=sys.stderr)
        print("API URL Météo France introuvable dans les variables d'environnement utilisateur.")
        sys.exit(2)
    if not args.api_key:
        print("Erreur: fournissez METEOFRANCE_API_KEY ou --api-key ou -a", file=sys.stderr)
        print("Clé API Météo France introuvable dans les variables d'environnement utilisateur.")
        sys.exit(3)
    # Validation simple des dates (et conversion se fait dans call_api)
    for label, d in (("--date-deb", args.date_deb), ("--date-fin", args.date_fin)):
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            print(f"Erreur: {label} invalide '{d}'. Format attendu: AAAA-MM-DD.", file=sys.stderr)
            sys.exit(4)

    # Vérifier que date_deb <= date_fin
    if args.date_deb > args.date_fin:
        print("Erreur: date-deb doit être antérieure ou égale à date-fin.", file=sys.stderr)
        sys.exit(5)

    meteo = Meteo(
        api_base_url=args.api_url,
        api_key=args.api_key,
        inputs_file=args.inputs_file,
        date_deb=args.date_deb,
        date_fin=args.date_fin,
        parameter=args.parameter,
        country=args.country,
        language=args.language,
        timeout=args.timeout,
        force=args.force
    )

    # # DEBUG
    # print(f"API_BASE_URL = {meteo.API_BASE_URL}")
    # print(f"API_KEY = {meteo.API_KEY}")
    # print(f"API_DATE_DEB = {meteo.API_DATE_DEB}")
    # print(f"API_DATE_FIN = {meteo.API_DATE_FIN}")
    # print(f"API_FORCE = {meteo.API_FORCE}")
    # os._exit(0)

    cities_file = Path(args.inputs_file)
    if cities_file.exists():
        with cities_file.open("r", encoding="utf-8") as f:
            cities = json.load(f)
            if not isinstance(cities, list):
                raise ValueError("Le fichier JSON ne contient pas une liste")
    else:
        print("Erreur: fournissez --inputs-file", file=sys.stderr)
        raise RuntimeError("Fichier JSON contenant la liste de dictionnaire avec les informations des villes à traiter introuvable.")
        
    # # DEBUG
    # print(f"cities = {json.dumps(cities, ensure_ascii=False, indent=2)}")
    # os._exit(0)

    for city in cities:
        city_name = city.get('name')
        city_departement = city.get('departement')
        city_country = city.get('country', 'France')
        city_language = city.get('language', 'fr')
        city_parameter = city.get('parameter', 'temperature')
        city_force = city.get('force', False)

        # # DEBUG
        # print(f"city_name = {city_name}")
        # print(f"city_departement = {city_departement}")
        # print(f"city_country = {city_country}")
        # print(f"city_language = {city_language}")
        # print(f"city_parameter = {city_parameter}")
        # print(f"city_force = {city_force}")
        # os._exit(0)

        meteo.write_stations_by_departement(city_departement, city_parameter, city_force)

        result = meteo.geocode_city_with_department(city_name, city_departement, city_country, city_language)
        if result is None:
            print(f"Aucune coordonnée trouvée pour: {city_name}, département {city_departement}, country {city_country}")
            sys.exit(1)
        city, lat, lon, label = result
    
        # # DEBUG
        # print(f"Ville:      {city}, département {city_departement}, {city_country}")
        # print(f"Latitude:   {lat:.6f}")
        # print(f"Longitude:  {lon:.6f}")
        # print(f"Résultat:   {label}")

        nearest = meteo.find_nearest_station(lat, lon, city_departement)
        print(nearest)

        meteo.send_command_station()
        meteo.get_and_download_file(city_name)


if __name__ == "__main__":
    # Désactive l'avertissement InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
