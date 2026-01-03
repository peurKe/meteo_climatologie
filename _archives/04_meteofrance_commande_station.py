#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Interroge l'API Météo-France DPClim: commande-station/quotidienne.

Exemples:
  python meteofrance_commande_station.py \
    --api-key "XXXXXX" \
    --id-station "49191001" \
    --date-deb "2025-12-21" \
    --date-fin "2025-12-22" \
    --output result.json

  # Clé via variable d'environnement
  export METEOFRANCE_API_KEY="XXXXXX"
  python meteofrance_commande_station.py --id-station 49191001 --date-deb 2025-12-21 --date-fin 2025-12-22

  # Mode non sécurisé (désactive la vérification SSL - à éviter en prod)
  python meteofrance_commande_station.py --id-station 49191001 --date-deb 2025-12-21 --date-fin 2025-12-22 --insecure
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("Le module 'requests' est requis. Installez-le avec: pip install requests", file=sys.stderr)
    sys.exit(1)

API_BASE_URL = "https://public-api.meteofrance.fr/public/DPClim/v1"
ENDPOINT = "commande-station/quotidienne"


def to_iso_midnight_z(date_str: str) -> str:
    """
    Convertit une date 'AAAA-MM-DD' en 'YYYY-MM-DDT00:00:00Z'.
    Valide le format d'entrée; lève ValueError si invalide.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Date invalide '{date_str}'. Attendu: AAAA-MM-DD.") from e
    return dt.strftime("%Y-%m-%dT00:00:00Z")


def call_api(api_key: str, id_station: str, date_deb: str, date_fin: str, timeout: float = 10.0, verify_ssl: bool = False) -> Dict[str, Any]:
    """
    Appelle l'API DPClim et retourne le JSON.
    """
    url = f"{API_BASE_URL}/{ENDPOINT}"
    headers = {
        "accept": "*/*",
        "apikey": api_key,
    }
    params = {
        "id-station": id_station,
        "date-deb-periode": to_iso_midnight_z(date_deb),
        "date-fin-periode": to_iso_midnight_z(date_fin),
    }

    # Proxies pris des variables d'environnement si présents
    proxies = {
        "http": os.environ.get("HTTP_PROXY"),
        "https": os.environ.get("HTTPS_PROXY"),
    }

    resp = requests.get(url, headers=headers, params=params, timeout=timeout, proxies=proxies, verify=verify_ssl)
    resp.raise_for_status()

    try:
        return resp.json()
    except json.JSONDecodeError:
        raise ValueError("La réponse n'est pas un JSON valide.")


def main():
    parser = argparse.ArgumentParser(
        description="Exécute une requête DPClim 'commande-station/quotidienne' avec id-station et période."
    )
    parser.add_argument("--api-key", default=os.environ.get("METEOFRANCE_API_KEY"),
                        help="Clé API Météo-France (ou via METEOFRANCE_API_KEY).")
    parser.add_argument("--id-station", required=True, help="Identifiant de station (ex: 49191001).")
    parser.add_argument("--date-deb", required=True, help="Début de période au format AAAA-MM-DD.")
    parser.add_argument("--date-fin", required=True, help="Fin de période au format AAAA-MM-DD.")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout de la requête en secondes (défaut: 15).")
    parser.add_argument("--output", default=None, help="Chemin de sortie pour enregistrer le JSON (optionnel).")
    parser.add_argument("--insecure", action="store_true", help="Désactive la vérification SSL (non sécurisé).")

    args = parser.parse_args()

    if not args.api_key:
        print("Erreur: aucune clé API fournie. Passez --api-key ou définissez METEOFRANCE_API_KEY.", file=sys.stderr)
        sys.exit(2)

    # Validation simple des dates (et conversion se fait dans call_api)
    for label, d in (("date-deb", args.date_deb), ("date-fin", args.date_fin)):
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except ValueError:
            print(f"Erreur: {label} invalide '{d}'. Format attendu: AAAA-MM-DD.", file=sys.stderr)
            sys.exit(2)

    # Optionnel: vérifier que date_deb <= date_fin
    if args.date_deb > args.date_fin:
        print("Erreur: date-deb doit être antérieure ou égale à date-fin.", file=sys.stderr)
        sys.exit(2)

    verify_ssl = not args.insecure

    # Désactiver l'avertissement si --insecure
    if not verify_ssl:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

    try:
        data = call_api(
            api_key=args.api_key,
            id_station=args.id_station,
            date_deb=args.date_deb,
            date_fin=args.date_fin,
            timeout=args.timeout,
            verify_ssl=verify_ssl,
        )
    except requests.SSLError as e:
        print("Erreur SSL/TLS lors de la vérification du certificat.", file=sys.stderr)
        print(f"Détails: {e}", file=sys.stderr)
        print("Astuce: réexécutez avec --insecure pour tester (non recommandé en production).", file=sys.stderr)
        sys.exit(6)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "N/A"
        content = e.response.text if e.response else ""
        print(f"Erreur HTTP {status}: {e}\nContenu: {content}", file=sys.stderr)
        sys.exit(3)
    except (requests.RequestException, ValueError) as e:
        print(f"Erreur de requête: {e}", file=sys.stderr)
        sys.exit(4)

    # Affiche la réponse JSON
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # Enregistre si demandé
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"JSON enregistré dans: {args.output}")
        except OSError as e:
            print(f"Impossible d'écrire le fichier '{args.output}': {e}", file=sys.stderr)
            sys.exit(5)


if __name__ == "__main__":
    main()
