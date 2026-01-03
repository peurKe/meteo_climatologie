#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
import requests
from pathlib import Path

API_BASE_URL = "https://public-api.meteofrance.fr/public/DPClim/v1"
ENDPOINT = "liste-stations/quotidienne"
# API_KEY = os.getenv("METEOFRANCE_API_KEY")

def call_api(api_key: str, departement: str, parametre: str, timeout: float) -> dict:
    url = f"{API_BASE_URL}/{ENDPOINT}"
    headers = {
        "accept": "*/*",
        "apikey": api_key,
    }
    params = {
        "id-departement": departement,
        "parametre": parametre,
    }

    # Désactivation de la vérification SSL
    resp = requests.get(url, headers=headers, params=params, timeout=timeout, verify=False)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser(description="Appel API Météo-France DPClim (SSL désactivé).")
    parser.add_argument("--api-key", "-a", default=os.environ.get("METEOFRANCE_API_KEY"), help="Clé API.")
    parser.add_argument("--departement", "-d", default="49", help="ID du département.")
    parser.add_argument("--parametre", "-p", default="temperature", help="Paramètre.")
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="Timeout en secondes.")
    parser.add_argument("--output", "-o", default=None, help="Fichier de sortie JSON.")
    args = parser.parse_args()

    if not args.api_key:
        print("Erreur: fournissez METEOFRANCE_API_KEY ou --api-key ou -a", file=sys.stderr)
        raise RuntimeError("Clé API Météo France introuvable dans les variables d'environnement utilisateur.")
    
    print("Clé chargée correctement depuis les variables d'environnement utilisateur.")

    try:
        data = call_api(args.api_key, args.departement, args.parametre, args.timeout)
    except requests.HTTPError as e:
        print(f"Erreur HTTP: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Erreur: {e}", file=sys.stderr)
        sys.exit(4)

    json_file = Path("departements") / f"{args.departement}.json"
    json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"JSON enregistré dans: {json_file}")
    # print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # Désactive l'avertissement InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
