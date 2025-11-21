# app.py
# Dashboard Streamlit - Qualité de l'air dans la station Châtelet (RER A)

import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIGURATION DE LA PAGE
# =========================

st.set_page_config(
    page_title="Dashboard Qualité de l'air – Châtelet RER A",
    page_icon="🚇",
    layout="wide",
)

# =========================
# 1. CHARGEMENT / PRÉPARATION
# =========================

@st.cache_data
def load_raw_data(csv_path: str) -> pd.DataFrame:
    """
    Charge les données brutes à partir du CSV.
    Le fichier utilise un séparateur ';' et une virgule pour les décimales.
    """
    df = pd.read_csv(csv_path, sep=";")
    return df


def prepare_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Prépare les données pour l'analyse :

    - Conversion des colonnes PM10 / TEMP / HUMI en float
    - Conversion de la colonne date/heure en datetime
    - Gestion des valeurs manquantes (suppression des lignes critiques)
    - Création de variables dérivées :
        * date (aaaa-mm-jj)
        * heure (0–23)
        * jour de la semaine (Lundi, Mardi, …)
        * tranche horaire (Heures de pointe / Journée / Nuit / Soirée)
    """
    df = df_raw.copy()

    # Conversion des colonnes numériques (virgule -> point)
    for col in ["PM10", "TEMP", "HUMI"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "."),
            errors="coerce",
        )

    # Conversion de la date/heure
    df["date_heure"] = pd.to_datetime(
        df["date/heure"],
        errors="coerce",
    )

    # Suppression des lignes sans date ou sans PM10
    df = df.dropna(subset=["date_heure", "PM10"])

    # Variables dérivées
    df["date"] = df["date_heure"].apply(lambda x: x.date())
    df["heure"] = df["date_heure"].apply(lambda x: x.hour)
    df["weekday"] = df["date_heure"].apply(lambda x: x.weekday())

    weekday_map = {
        0: "Lundi",
        1: "Mardi",
        2: "Mercredi",
        3: "Jeudi",
        4: "Vendredi",
        5: "Samedi",
        6: "Dimanche",
    }
    df["jour_semaine"] = df["weekday"].map(weekday_map)

    def tranche_horaire(h: int) -> str:
        """
        Catégorise l'heure :
        - Heures de pointe : 7–9h et 17–19h
        - Journée : 10–16h
        - Nuit / Soirée : le reste
        """
        if 7 <= h <= 9 or 17 <= h <= 19:
            return "Heures de pointe"
        elif 10 <= h <= 16:
            return "Journée"
        else:
            return "Nuit / Soirée"

    df["tranche_horaire"] = df["heure"].apply(tranche_horaire)

    return df


# =========================
# 2. FONCTIONS DE GRAPHIQUES
# =========================

def _style_fig(fig):
    """Applique un style homogène aux graphiques pour la lisibilité."""
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        title_font_size=18,
        xaxis_title_font_size=13,
        yaxis_title_font_size=13,
        legend_title_font_size=12,
    )
    return fig


def plot_evolution_temporelle(df: pd.DataFrame, variable: str):
    """
    Graphique d'évolution temporelle de la variable choisie
    (PM10, TEMP, HUMI) sur la période filtrée.
    """
    df_plot = df.sort_values("date_heure")

    fig = px.line(
        df_plot,
        x="date_heure",
        y=variable,
        labels={"date_heure": "Date / heure", variable: variable},
        title=f"Évolution de {variable} dans le temps",
    )
    return _style_fig(fig)


def plot_box_jour_semaine(df: pd.DataFrame, variable: str):
    """
    Boxplot par jour de la semaine pour visualiser la distribution
    de la variable choisie.
    """
    fig = px.box(
        df,
        x="jour_semaine",
        y=variable,
        category_orders={
            "jour_semaine": [
                "Lundi",
                "Mardi",
                "Mercredi",
                "Jeudi",
                "Vendredi",
                "Samedi",
                "Dimanche",
            ]
        },
        labels={"jour_semaine": "Jour de la semaine", variable: variable},
        title=f"{variable} par jour de la semaine",
    )
    return _style_fig(fig)


def plot_heatmap_tranche_horaire(df: pd.DataFrame):
    """
    Heatmap des PM10 moyens par jour de la semaine et tranche horaire.
    Permet d'identifier les plages horaires plus polluées.
    """
    agg = (
        df.groupby(["jour_semaine", "tranche_horaire"], as_index=False)["PM10"]
        .mean()
    )

    jour_order = [
        "Lundi",
        "Mardi",
        "Mercredi",
        "Jeudi",
        "Vendredi",
        "Samedi",
        "Dimanche",
    ]
    tranche_order = ["Heures de pointe", "Journée", "Nuit / Soirée"]

    agg["jour_semaine"] = pd.Categorical(
        agg["jour_semaine"], categories=jour_order, ordered=True
    )
    agg["tranche_horaire"] = pd.Categorical(
        agg["tranche_horaire"], categories=tranche_order, ordered=True
    )

    fig = px.density_heatmap(
        agg.sort_values(["jour_semaine", "tranche_horaire"]),
        x="tranche_horaire",
        y="jour_semaine",
        z="PM10",
        labels={
            "tranche_horaire": "Tranche horaire",
            "jour_semaine": "Jour de la semaine",
            "PM10": "PM10 moyen (µg/m³)",
        },
        title="PM10 moyen par jour et tranche horaire",
        # Palette plus cohérente : vert = faible, jaune = moyen, rouge = élevé
        color_continuous_scale="RdYlGn_r",
    )

    return _style_fig(fig)


# =========================
# 3. CHARGEMENT EFFECTIF
# =========================

CSV_PATH = "qualite-de-lair-mesuree-dans-la-station-chatelet-rer-a0.csv"

df_raw = load_raw_data(CSV_PATH)
df = prepare_data(df_raw)

# =========================
# 4. INTERFACE UTILISATEUR
# =========================

# ---- Titre / contexte ----
st.title("Qualité de l'air – station Châtelet (RER A)")
st.caption("Données horaires de PM10, température et humidité en station souterraine")

st.markdown(
    """
La RATP surveille la **qualité de l’air** dans plusieurs stations souterraines.
Ce dashboard se concentre sur la **station Châtelet – RER A**.

Les capteurs mesurent en continu :
- les **particules fines PM10** (qualité de l’air),
- la **température**,
- l’**humidité relative**.

Les mesures sont regroupées en **moyennes par heure**.

L’objectif est de :
- suivre l’évolution de la qualité de l’air dans le temps,
- comparer les niveaux selon les **jours de la semaine**,
- observer les différences entre **plages horaires** (heures de pointe, journée, soirée / nuit).
"""
)

st.markdown("---")

# ---- Filtres dans la sidebar ----
st.sidebar.header("⚙️ Filtres")

# Période
min_date = df["date"].min()
max_date = df["date"].max()

date_range = st.sidebar.date_input(
    "Période d'analyse",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Tranches horaires
tranches_disponibles = df["tranche_horaire"].unique().tolist()
tranches_selectionnees = st.sidebar.multiselect(
    "Tranches horaires",
    options=tranches_disponibles,
    default=tranches_disponibles,
)

# Variable à analyser
variable_principale = st.sidebar.selectbox(
    "Variable principale",
    options=["PM10", "TEMP", "HUMI"],
    index=0,
)

# Application des filtres
if isinstance(date_range, tuple):
    date_debut, date_fin = date_range
else:
    date_debut = date_fin = date_range

df_filtered = df[
    (df["date"] >= date_debut)
    & (df["date"] <= date_fin)
    & (df["tranche_horaire"].isin(tranches_selectionnees))
].copy()

if df_filtered.empty:
    st.warning(
        "Aucune donnée pour cette combinaison de filtres. "
        "Élargis la période ou les tranches horaires."
    )
    st.stop()

# =========================
# 5. KPIs (indicateurs)
# =========================

st.subheader("🔍 Indicateurs clés sur la période sélectionnée")

pm10_moyen = df_filtered["PM10"].mean()
pm10_median = df_filtered["PM10"].median()
pm10_min = df_filtered["PM10"].min()
pm10_max = df_filtered["PM10"].max()
pm10_std = df_filtered["PM10"].std()

SEUIL_PM10 = 50  # µg/m³

if pm10_moyen < 20:
    couleur_pm10 = "#2ecc40"  # vert
    phrase_pm10 = "Air de bonne qualité"
elif pm10_moyen < SEUIL_PM10:
    couleur_pm10 = "#ffdc00"  # jaune
    phrase_pm10 = "Air moyen"
else:
    couleur_pm10 = "#ff4136"  # rouge
    phrase_pm10 = "Dépassement du seuil recommandé"

# Ligne 1 de KPIs
kpi_row1 = st.columns(3)

with kpi_row1[0]:
    st.metric(
        "PM10 moyen",
        f"{pm10_moyen:.1f} µg/m³",
    )
    st.markdown(
        f"<span style='color:{couleur_pm10};font-weight:bold;'>{phrase_pm10}</span>",
        unsafe_allow_html=True,
    )

with kpi_row1[1]:
    st.metric(
        "PM10 médiane",
        f"{pm10_median:.1f} µg/m³",
    )

with kpi_row1[2]:
    st.metric(
        "PM10 min / max",
        f"{pm10_min:.1f} / {pm10_max:.1f} µg/m³",
    )

# Ligne 2 de KPIs
kpi_row2 = st.columns(3)

with kpi_row2[0]:
    st.metric(
        "PM10 écart-type",
        f"{pm10_std:.1f} µg/m³",
    )

with kpi_row2[1]:
    st.metric(
        "Nombre de mesures",
        f"{len(df_filtered):,}".replace(",", " "),
    )

with kpi_row2[2]:
    st.metric(
        "Période analysée",
        f"{date_debut} → {date_fin}",
    )

st.markdown("---")

# =========================
# 6. VISUALISATIONS
# =========================

tab1, tab2, tab3 = st.tabs(
    [
        "Évolution temporelle",
        "Par jour de la semaine",
        "Heatmap horaires (PM10)",
    ]
)

with tab1:
    st.markdown("#### Évolution dans le temps")
    fig_time = plot_evolution_temporelle(df_filtered, variable_principale)
    st.plotly_chart(fig_time, use_container_width=True)

with tab2:
    st.markdown("#### Comparaison entre les jours")
    fig_box = plot_box_jour_semaine(df_filtered, variable_principale)
    st.plotly_chart(fig_box, use_container_width=True)

with tab3:
    st.markdown("#### PM10 par jour et tranche horaire")
    fig_heat = plot_heatmap_tranche_horaire(df_filtered)
    st.plotly_chart(fig_heat, use_container_width=True)

# Scatter plot corrélation
with st.expander("🔗 Corrélation PM10 / Température / Humidité"):
    st.markdown("Visualisation de la relation entre PM10, température et humidité.")
    fig_scatter = px.scatter(
        df_filtered,
        x="TEMP",
        y="PM10",
        color="HUMI",
        labels={
            "TEMP": "Température (°C)",
            "PM10": "PM10 (µg/m³)",
            "HUMI": "Humidité (%)",
        },
        title="Corrélation PM10 / Température / Humidité",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(_style_fig(fig_scatter), use_container_width=True)

st.markdown("---")

# =========================
# 7. TABLE DES DONNÉES FILTRÉES
# =========================

st.subheader("📋 Données filtrées")

st.dataframe(
    df_filtered[
        ["date_heure", "PM10", "TEMP", "HUMI", "jour_semaine", "tranche_horaire"]
    ].sort_values("date_heure"),
    use_container_width=True,
)

def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")

csv = convert_df(df_filtered)
st.download_button(
    label="📥 Télécharger les données filtrées (CSV)",
    data=csv,
    file_name="donnees_filtrees_chatelet.csv",
    mime="text/csv",
)

# =========================
# 8. RÉSUMÉ EXPLICATIF
# =========================

with st.expander("📝 Résumé des choix de visualisation et interprétation"):
    st.markdown(
        """
### Choix de visualisations

- **Courbe temporelle** : pour suivre l'évolution de la pollution (PM10),
  de la température et de l'humidité.
- **Boxplot par jour de la semaine** : pour comparer les distributions entre les jours.
- **Heatmap PM10 par jour / tranche horaire** : pour repérer visuellement les périodes
  où les PM10 sont plus élevés.
- **Scatter plot PM10 / Température / Humidité** : pour explorer les liens entre les variables.

### Seuils de lecture pour les PM10 (ordre de grandeur)

- < 20 µg/m³ : air plutôt bon
- 20–50 µg/m³ : air moyen
- > 50 µg/m³ : niveau à surveiller

### Contexte

Les données proviennent de la **station Châtelet – RER A**, en souterrain.
Elles permettent d'illustrer la surveillance de la qualité de l'air
dans un environnement de transport très fréquenté.
"""
    )

