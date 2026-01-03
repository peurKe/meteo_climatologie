import os
import sys
import json
import math
import requests
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

class Meteo:
    # Constructeur
    def __init__(self,
                 api_base_url: str = "https://public-api.meteofrance.fr/public/DPClim/v1",
                 api_key: str = None,
                 inputs_file: str = "inputs.json",
                 date_deb: str = None,
                 date_fin: str = None,
                 parameter: str = "temperature",
                 country: str = "France",
                 language: str = "fr",
                 timeout: float = 10.0,
                 force: bool = False):
    # Propriétés
        self.API_BASE_URL = api_base_url
        self.API_KEY = api_key
        self.API_INPUTS_FILE = inputs_file
        self.API_DATE_DEB = date_deb
        self.API_DATE_FIN = date_fin
        self.API_PARAMETER = parameter
        self.API_COUNTRY = country
        self.API_LANGUAGE = language
        self.API_TIMEOUT = timeout
        self.API_FORCE = force

    # Méthodes
    def call_api_list(self, departement: str, parameter: str = 'temperature', timeout: float = 10.0, verify_ssl: bool = False) -> dict:
        if departement is None:
            raise RuntimeError("call_api_list: 'departement' est obligatoire. Vérifiez que chaque ville a un département configuré dans le fichier JSON d'entrée.")

        # # DEBUG
        # print(f"API_BASE_URL = {API_BASE_URL}")
        # print(f"API_KEY = {API_KEY}")
        # print(f"departement = {departement}")
        # print(f"parameter = {parameter}")
        # os._exit(0)

        url = f"{self.API_BASE_URL}/liste-stations/quotidienne"
        headers = {
            "accept": "application/json",
            "apikey": self.API_KEY,
        }
        params = {
            "id-departement": departement,
            "parametre": parameter,
        }

        resp = requests.get(url, headers=headers, params=params, timeout=timeout, verify=verify_ssl)
        resp.raise_for_status()

        try:
            return resp.json()
        except json.JSONDecodeError:
            raise ValueError("La réponse n'est pas un JSON valide.")


    def call_api_command(self, date_deb: str, date_fin: str, timeout: float = 10.0, verify_ssl: bool = False) -> str:
        """
        Appelle l'API DPClim et retourne le JSON.
        """
        url = f"{self.API_BASE_URL}/commande-station/quotidienne"
        headers = {
            "accept": "application/json",
            "apikey": self.API_KEY,
        }
        params = {
            "id-station": self.NEAREST_STATION_ID,
            "date-deb-periode": self.to_iso_midnight_z(date_deb),
            "date-fin-periode": self.to_iso_midnight_z(date_fin),
        }

        resp = requests.get(url, headers=headers, params=params, timeout=timeout, verify=verify_ssl)
        resp.raise_for_status()

        try:
            self.API_COMMAND_ID = resp.json().get('elaboreProduitAvecDemandeResponse', {}).get('return', None)
        except json.JSONDecodeError:
            raise ValueError("La réponse n'est pas un JSON valide.")

        return self.API_COMMAND_ID


    def call_api_download_file(self, city: str, timeout: float = 10.0, verify_ssl: bool = False):
        """
        Télécharge le fichier associé à la commande DPClim.
        """
        url = f"{self.API_BASE_URL}/commande/fichier"
        headers = {
            "accept": "application/json",
            "apikey": self.API_KEY,
        }
        params = {
            "id-cmde": self.API_COMMAND_ID,
        }

        resp = requests.get(url, headers=headers, params=params, timeout=timeout, verify=verify_ssl)
        resp.raise_for_status()

        city_file = Path("cities") / f"{city}.csv"
        city_file.parent.mkdir(parents=True, exist_ok=True)

        # Sauvegarde du contenu binaire
        with open(city_file, "wb") as f:
            f.write(resp.content)


    def to_iso_midnight_z(self, date_str: str) -> str:
        """
        Convertit une date 'AAAA-MM-DD' en 'YYYY-MM-DDT00:00:00Z'.
        Valide le format d'entrée; lève ValueError si invalide.
        """
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Date invalide '{date_str}'. Attendu: AAAA-MM-DD.") from e
        return dt.strftime("%Y-%m-%dT00:00:00Z")


    def _should_write_json(self, path: Path) -> bool:
        if not path.exists():
            return True
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return not (isinstance(data, list) and len(data) > 0)
        except json.JSONDecodeError:
            return True


    def write_stations_by_departement(self, departement: str, parameter: str, force: bool = False, timeout: float = 10.0):
        try:
            data = self.call_api_list(departement, parameter, timeout)
        except requests.HTTPError as e:
            print(f"Erreur HTTP: {e}", file=sys.stderr)
            sys.exit(3)
        except Exception as e:
            print(f"Erreur: {e}", file=sys.stderr)
            sys.exit(4)

        departement_file = Path("departements") / f"{departement}.json"
        departement_file.parent.mkdir(parents=True, exist_ok=True)

        if self._should_write_json(departement_file) or self.API_FORCE or force:
            with open(departement_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Les stations météo pour le département {departement} ont été sauvegardées dans le fichier JSON: {departement_file}")
        else:
            print(f"Les stations météo pour le département {departement} existent déjà dans le répertoire 'departements'.")
            print(f"Utilisez l'argument --force pour forcer la récupération des stations.")


    def _make_geocoder(self):
        # Nominatim exige un user_agent explicite et identifiable
        geolocator = Nominatim(user_agent="m365copilot-geocoder-demo")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)  # respect du service
        return geolocator, geocode


    def _try_geocode_department_bbox(
        self,
        department: str,
        country: str = "France",
        language: str = "fr",
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Géocode le département à partir de son code (ex: '19', '2A') et retourne sa bounding box (west, south, east, north).
        On tente plusieurs formulations pour Nominatim.
        """
        _, geocode = self._make_geocoder()

        # Variantes de requêtes pour maximiser les chances de trouver le département par code
        queries: List[str] = [
            f"Département {department}, {country}",
            f"Department {department}, {country}",
            f"Dept {department}, {country}",
            f"{department} {country} département",
            f"{department}, {country} département",
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


    def geocode_city_with_department(
        self,
        city: str,
        department: str,
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
        geolocator, geocode = self._make_geocoder()

        # 1) Essais directs : certaines variantes de requêtes "Ville, Département {code}, France"
        direct_queries = [
            f"{city}, Département {department}, {country}",
            f"{city}, Dept {department}, {country}",
            f"{city}, Department {department}, {country}",
            f"{city}, {department}, {country}",
        ]
        for q in direct_queries:
            try:
                loc = geocode(q, language=language, addressdetails=True, country_codes="fr", exactly_one=True)
                if loc:
                    self.CITY_NAME = city
                    self.CITY_LATITUDE = loc.latitude
                    self.CITY_LONGITUDE = loc.longitude
                    self.CITY_LABEL = loc.raw.get("display_name", "")
                    return (
                        self.CITY_NAME,
                        self.CITY_LATITUDE,
                        self.CITY_LONGITUDE,
                        self.CITY_LABEL
                    )
            except Exception:
                continue

        # 2) Fallback : borner la recherche au département (via sa bbox)
        bbox = self._try_geocode_department_bbox(department, country=country, language=language)
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
                    self.CITY_NAME = city
                    self.CITY_LATITUDE = loc.latitude
                    self.CITY_LONGITUDE = loc.longitude
                    self.CITY_LABEL = loc.raw.get("display_name", "")
                    return (
                        self.CITY_NAME,
                        self.CITY_LATITUDE,
                        self.CITY_LONGITUDE,
                        self.CITY_LABEL
                    )
            except Exception:
                pass

        # Aucun résultat
        return None


    def _haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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
        self,
        city_lat: float,
        city_lon: float,
        departement: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
        """
        Retourne (station_la_plus_proche, distance_km). Si aucune station valide n'est trouvée, (None, None).
        Une station est considérée valide si elle possède des champs 'lat' et 'lon' numériques.
        """
        file_path = f"departements/{departement}.json"
        stations = self.load_stations_from_file(file_path)
        
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

            d = self._haversine_km(city_lat, city_lon, slat, slon)
            if best_dist is None or d < best_dist:
                best_dist = d
                nearest = st

        self.NEAREST_STATION_ID = nearest['id']
        return nearest, best_dist


    def load_stations_from_file(self, path: str) -> List[Dict[str, Any]]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


    def send_command_station(self):
        try:
            # call_api_command(date_deb, date_fin, timeout, verify_ssl)
            data = self.call_api_command(
                date_deb=self.API_DATE_DEB,
                date_fin=self.API_DATE_FIN,
                timeout=self.API_TIMEOUT
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


    def get_and_download_file(self, city: str):
        self.call_api_download_file(city)
