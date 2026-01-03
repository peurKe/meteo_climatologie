 #!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Télécharge le fichier d'une commande DPClim via l'API Météo-France.
Endpoint : /public/DPClim/v1/commande/fichier?id-cmde=XXXX

Exemples :
    python meteofrance_get_file.py --api-key "XXXXXX" --id-cmde "2025023633107" --output fichier.zip

    # Clé via variable d'environnement
    export METEOFRANCE_API_KEY="XXXXXX"
    python meteofrance_get_file.py --id-cmde 2025023633107 --output fichier.zip

    # Mode non sécurisé (désactive SSL)
    python meteofrance_get_file.py --id-cmde 2025023633107 --output fichier.zip --insecure
"""

import os
import sys
import argparse
import requests

API_BASE_URL = "https://public-api.meteofrance.fr/public/DPClim/v1"
ENDPOINT = "commande/fichier"


def download_file(api_key: str, id_cmde: str, output_path: str, timeout: float, verify_ssl: bool):
    """
    Télécharge le fichier associé à la commande DPClim.
    """
    url = f"{API_BASE_URL}/{ENDPOINT}"
    headers = {
        "accept": "*/*",
        "apikey": api_key,
    }
    params = {
        "id-cmde": id_cmde,
    }

    proxies = {
        "http": os.environ.get("HTTP_PROXY"),
        "https": os.environ.get("HTTPS_PROXY"),
    }

    resp = requests.get(url, headers=headers, params=params, timeout=timeout, proxies=proxies, verify=verify_ssl)
    resp.raise_for_status()

    # Sauvegarde du contenu binaire
    with open(output_path, "wb") as f:
        f.write(resp.content)


def main():
    parser = argparse.ArgumentParser(description="Télécharge le fichier d'une commande DPClim (Météo-France).")
    parser.add_argument("--api-key", default=os.environ.get("METEOFRANCE_API_KEY"),
                        help="Clé API Météo-France (ou via METEOFRANCE_API_KEY).")
    parser.add_argument("--id-cmde", required=True, help="Identifiant de commande (ex: 2025023633107).")
    parser.add_argument("--output", required=True, help="Chemin du fichier de sortie (ex: fichier.zip).")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout en secondes (défaut: 30).")
    parser.add_argument("--insecure", action="store_true", help="Désactive la vérification SSL (non sécurisé).")

    args = parser.parse_args()

    if not args.api_key:
        print("Erreur: aucune clé API fournie. Passez --api-key ou définissez METEOFRANCE_API_KEY.", file=sys.stderr)
        sys.exit(2)

    verify_ssl = not args.insecure
    if not verify_ssl:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

    try:
        download_file(args.api_key, args.id_cmde, args.output, args.timeout, verify_ssl)
        print(f"Fichier téléchargé avec succès: {args.output}")
    except requests.exceptions.SSLError as e:
        print("Erreur SSL/TLS lors de la vérification du certificat.", file=sys.stderr)
        print(f"Détails: {e}", file=sys.stderr)
        print("Astuce: réexécutez avec --insecure pour tester (non recommandé en production).", file=sys.stderr)
        sys.exit(6)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "N/A"
        content = e.response.text if e.response else ""
        print(f"Erreur HTTP {status}: {e}\nContenu: {content}", file=sys.stderr)
        sys.exit(3)
    except requests.RequestException as e:
        print(f"Erreur de requête: {e}", file=sys.stderr)
        sys.exit(4)
    except OSError as e:
        print(f"Erreur lors de l'écriture du fichier '{args.output}': {e}", file=sys.stderr)
        sys.exit(5)


if __name__ == "__main__":
    main()
