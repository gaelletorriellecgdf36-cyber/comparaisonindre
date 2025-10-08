
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Comparateur tarifs Gîtes de France® - MVP", layout="wide")

@st.cache_data
def load_excel(file):
    return {name: pd.read_excel(file, sheet_name=name) for name in pd.ExcelFile(file).sheet_names}

def robust_panel(df, target, params):
    tol_cap = int(params.get("filtre_capacite_plus_moins", 2))
    tol_surf = float(params.get("filtre_surface_plus_moins_m2", 20))
    sigma = float(params.get("seuil_outliers_sigma", 2.0))

    mask = pd.Series(True, index=df.index)
    if target.get("code_postal"):
        mask &= df["code_postal"].astype(str) == str(target["code_postal"])
    if target.get("commune"):
        mask &= df["commune"].str.lower() == str(target["commune"]).lower()

    if pd.notna(target.get("epis_gdf")):
        panel = df[mask & (df["epis_gdf"]==int(target["epis_gdf"]))]
        if len(panel) < 10:
            panel = df[mask & (df["epis_gdf"].between(int(target["epis_gdf"])-1, int(target["epis_gdf"])+1))]
    else:
        panel = df[mask].copy()

    if pd.notna(target.get("capacite")):
        panel = panel[panel["capacite"].between(int(target["capacite"])-tol_cap, int(target["capacite"])+tol_cap)]
    if pd.notna(target.get("surface_m2")):
        panel = panel[panel["surface_m2"].between(float(target["surface_m2"])-tol_surf, float(target["surface_m2"])+tol_surf)]

    if target.get("saison"):
        panel = panel[panel["saison"].str.lower()==str(target["saison"]).lower()]
    if target.get("jour_semaine"):
        panel = panel[panel["jour_semaine"].str.lower()==str(target["jour_semaine"]).lower()]

    if len(panel) >= 5 and "prix_par_nuit_ttc" in panel:
        mu, sd = panel["prix_par_nuit_ttc"].mean(), panel["prix_par_nuit_ttc"].std(ddof=0) or 1.0
        z = (panel["prix_par_nuit_ttc"]-mu)/sd
        panel = panel[(z.abs() <= sigma)]
    return panel

def price_adjustment(base, target, params):
    def pval(key, default=0):
        try: return float(params.get(key, default))
        except: return default
    adjustments = 0.0
    feats = {
        "piscine": pval("facteur_piscine_pct", 12),
        "spa_bain_nordique": pval("facteur_spa_pct", 8),
        "climatisation": pval("facteur_clim_pct", 5),
        "jardin_prive": pval("facteur_jardin_prive_pct", 3),
        "wifi": pval("facteur_wifi_pct", 0),
        "animaux_acceptes": pval("facteur_animaux_pct", -3),
    }
    for col, pct in feats.items():
        if str(target.get(col, 0)) in ["1","True","true"] or target.get(col, 0)==1:
            adjustments += pct/100.0
    return base * (1 + adjustments)

def compute_reco(panel, target, params):
    if len(panel) == 0 or "prix_par_nuit_ttc" not in panel:
        return None
    med = float(panel["prix_par_nuit_ttc"].median())
    q1 = float(panel["prix_par_nuit_ttc"].quantile(0.25))
    q3 = float(panel["prix_par_nuit_ttc"].quantile(0.75))
    return {
        "n": int(len(panel)),
        "median": med,
        "q1": q1,
        "q3": q3,
        "prix_conseille": price_adjustment(med, target, params),
        "fourchette": (price_adjustment(q1, target, params), price_adjustment(q3, target, params)),
    }

st.sidebar.header("Données")
uploaded = st.sidebar.file_uploader("Fichier Excel (modele_webapp_prix_gdf.xlsx)", type=["xlsx"])

if uploaded is None:
    st.info("Aucun fichier chargé. Utilisez le modèle fourni pour tester.")
    st.stop()

dfs = load_excel(uploaded)
hebergements = dfs.get("hebergements")
params_df = dfs.get("parametres", pd.DataFrame(columns=["cle","valeur"]))
PARAMS = {row["cle"]: row["valeur"] for _, row in params_df.iterrows()}

st.title("Comparateur de tarifs — MVP")

col1, col2 = st.columns([1,2], gap="large")

with col1:
    st.subheader("Logement à évaluer")
    target = {}
    target["commune"] = st.text_input("Commune", value="")
    target["code_postal"] = st.text_input("Code postal", value="")
    target["epis_gdf"] = st.number_input("Épis Gîtes de France", min_value=1, max_value=5, value=3, step=1)
    target["type_logement"] = st.selectbox("Type de logement", options=sorted(hebergements["type_logement"].dropna().unique()))
    target["capacite"] = st.number_input("Capacité", min_value=1, value=int(hebergements["capacite"].median() if not hebergements.empty else 4))
    target["surface_m2"] = st.number_input("Surface (m²)", min_value=5.0, value=float(hebergements["surface_m2"].median() if not hebergements.empty else 60.0), step=1.0)
    target["saison"] = st.selectbox("Saison", options=sorted(hebergements["saison"].dropna().unique()))
    target["jour_semaine"] = st.selectbox("Semaine / Week-end", options=sorted(hebergements["jour_semaine"].dropna().unique()))

    st.markdown("**Équipements**")
    for c in ["piscine","spa_bain_nordique","climatisation","jardin_prive","wifi","animaux_acceptes"]:
        target[c] = 1 if st.checkbox(c.replace("_"," ").title(), value=False) else 0

    with st.expander("Filtres du panel"):
        PARAMS["filtre_capacite_plus_moins"] = st.number_input("Tolérance capacité (±)", min_value=0, value=int(PARAMS.get("filtre_capacite_plus_moins", 2)))
        PARAMS["filtre_surface_plus_moins_m2"] = st.number_input("Tolérance surface (± m²)", min_value=0, value=int(PARAMS.get("filtre_surface_plus_moins_m2", 20)))
        PARAMS["seuil_outliers_sigma"] = st.number_input("Seuil outliers (σ)", min_value=1.0, value=float(PARAMS.get("seuil_outliers_sigma", 2.0)))

with col2:
    st.subheader("Résultats")
    panel = robust_panel(hebergements, target, PARAMS)
    st.caption(f"Panel: {len(panel)} comparables")
    if len(panel)>0:
        st.dataframe(panel[["nom","commune","epis_gdf","capacite","surface_m2","saison","jour_semaine","prix_par_nuit_ttc"]].sort_values("prix_par_nuit_ttc"))
    reco = compute_reco(panel, target, PARAMS)
    if reco:
        bas, haut = reco["fourchette"]
        st.metric("Prix conseillé (€/nuit)", f"{reco['prix_conseille']:,.0f}".replace(",", " "))
        st.write(f"Fourchette: **{bas:,.0f}€–{haut:,.0f}€**".replace(",", " "))
        st.write(f"Médiane: {reco['median']:.0f}€ — Q1: {reco['q1']:.0f}€ — Q3: {reco['q3']:.0f}€")
        prix_prop = st.number_input("Prix proposé par le propriétaire (€ / nuit)", min_value=0.0, value=float(reco['prix_conseille']))
        if prix_prop < bas:
            st.success("✅ Positionnement: compétitif (en dessous du marché).")
        elif prix_prop > haut:
            st.warning("⚠️ Positionnement: élevé (au-dessus du marché).")
        else:
            st.info("ℹ️ Positionnement: aligné marché.")
    else:
        st.error("Panel vide : élargir les filtres (épis ±1, rayon via CP/commune, etc.).")

st.caption("MVP Streamlit — Colonnes attendues: hebergements(type_logement, capacite, surface_m2, saison, jour_semaine, prix_par_nuit_ttc, ...), parametres(coefficients).")
