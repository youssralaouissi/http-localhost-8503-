# COPAG — Dashboard Logistique Streamlit

## Structure

```text
copag_streamlit_project/
├── app.py
├── dataset.csv
├── requirements.txt
└── README.md
```

## Installation

```bash
python -m venv .venv
```

Windows :
```bash
.venv\Scripts\activate
```

Linux / macOS :
```bash
source .venv/bin/activate
```

Puis :

```bash
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

Le dashboard est construit à partir du dataset COPAG fourni et reprend les analyses du notebook :
- nettoyage et conversion des dates/types ;
- gestion des valeurs aberrantes simples ;
- KPI : expéditions, taux à l'heure, coût, carburant, CO2, retard ;
- filtres par période, hub, région, produit et mode ;
- performance quotidienne ;
- top routes ;
- retards par produit/région ;
- coûts par km et par produit ;
- capacité par mode ;
- chaîne du froid ;
- corrélations ;
- consommation et émissions ;
- positions géographiques et flux ;
- export CSV des données filtrées.
