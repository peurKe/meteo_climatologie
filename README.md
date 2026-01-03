# meteo_climatologie
Récupération information climatologie

# Prerequisites
```
pip install requests geopy pandas openpyxl pywin32
```

# Usage
Renseigner les informations des villes à traiter dans le fichier d'entrées '**inputs.json**' sous la forme :
```
[
  {
    "name": "Grezillé",
    "departement": 49,
    "county": "Maine-et-Loire",
    "country": "France",
    "language": "fr",
    "parameter": "temperature",
    "force": false
  },
  {
    "name": "Brignais",
    "departement": 69,
    "county": "Rhone"
  }
]
```
Pour chaque élément ville :
- '**name**' est **obligatoire**.
- '**departement**' est **obligatoire**.
- '**county**' est **obligatoire**.
- '**country**' est facultatif (valeur par défaut "**France**") / Permet de préciser le pays de la ville.
- '**language**' est facultatif (valeur par défaut "**fr**") / Permet de préciser le language du pays de la ville.
- '**parameter**' est facultatif (valeur par défaut "**temperature**") / Permet de préciser le type d'information climatique à récupérer.
- '**force**' est facultatif (valeur par défaut "**false**") / Permet de forcer la mise à jour de toutes les informations, mêmes celles déjà récupérées.

Exécuter l'une des 2 commandes suivantes pour récupérer les valeurs climatiques de toutes les villes spécifiées dans le fichier d'entrées '**inputs.json**' :
```
# Récupérer tout depuis la date de début jusqu'à la date du jour
python -m meteo_climatologie --date-deb 2026-01-01

# Récupérer tout depuis la date de début jusqu'à la date de fin spécifiées
python -m meteo_climatologie --date-deb 2026-01-01 --date-fin 2026-12-31
```
