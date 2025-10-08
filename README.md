# MVP - Comparateur de tarifs Gîtes de France®

## Lancer localement
```bash
pip install -r requirements.txt
streamlit run app_tarifs_gdf.py
```

## Données
- Importez un Excel suivant `modele_webapp_prix_gdf.xlsx` (feuilles `hebergements`, `parametres`).
- **Ne poussez pas** vos bases privées : mettez-les dans `data/` (ignoré par git) et chargez-les via l’app.

## Déploiement (Streamlit Cloud)
1. Poussez ce repo sur GitHub.
2. Créez une app sur Streamlit Cloud et pointez sur `app_tarifs_gdf.py`.
3. Ajoutez `requirements.txt`.
