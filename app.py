import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(
    page_title="COPAG | Dashboard Logistique",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

sns.set_theme(style="whitegrid")

# -----------------------------
# Style
# -----------------------------
st.markdown("""
<style>
    .main {background-color: #f7f9fc;}
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e8edf3;
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,.04);
    }
    .dashboard-title {font-size: 2.2rem; font-weight: 700; margin-bottom: 0;}
    .dashboard-subtitle {color: #667085; margin-top: .2rem; margin-bottom: 1.4rem;}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Chargement + nettoyage
# -----------------------------
@st.cache_data
def load_data(path="dataset.csv"):
    data = pd.read_csv(path)

    # Normalisation des noms
    data.columns = (
        data.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    # Dates
    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"], errors="coerce")

    # Conversion numérique
    numeric_cols = [
        "distance_km", "planned_duration_min", "actual_duration_min",
        "delay_min", "on_time", "temperature_breach",
        "capacity_utilization", "fuel_liters", "co2_kg", "cost_mad",
        "quantity_tons", "lat", "lon", "o_lat", "o_lon", "d_lat", "d_lon"
    ]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # Booléens robustes
    for col in ["on_time", "temperature_breach"]:
        if col in data.columns:
            if data[col].dtype == "object":
                data[col] = (
                    data[col].astype(str).str.strip().str.lower()
                    .map({"true": 1, "false": 0, "yes": 1, "no": 0, "oui": 1, "non": 0})
                )
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # Valeurs aberrantes / impossibles : NaN plutôt que suppression massive
    positive_cols = [
        "distance_km", "planned_duration_min", "actual_duration_min",
        "fuel_liters", "co2_kg", "cost_mad", "quantity_tons"
    ]
    for col in positive_cols:
        if col in data.columns:
            data.loc[data[col] < 0, col] = np.nan

    if "delay_min" in data.columns:
        data.loc[data["delay_min"] < 0, "delay_min"] = 0

    if "capacity_utilization" in data.columns:
        # Les données sont généralement en fraction ; on garde la valeur originale.
        data.loc[data["capacity_utilization"] < 0, "capacity_utilization"] = np.nan

    # Variables dérivées
    if {"origin_hub", "destination_city"}.issubset(data.columns):
        data["lane"] = (
            data["origin_hub"].astype(str) + " → " +
            data["destination_city"].astype(str)
        )

    if {"cost_mad", "distance_km"}.issubset(data.columns):
        data["cost_per_km"] = data["cost_mad"] / data["distance_km"].replace(0, np.nan)

    return data


df = load_data()

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("🚚 COPAG Logistique")
st.sidebar.caption("Analyse des données de transport")

if df.empty:
    st.error("Le fichier dataset.csv est vide.")
    st.stop()

min_date = df["date"].min().date() if "date" in df.columns and df["date"].notna().any() else None
max_date = df["date"].max().date() if "date" in df.columns and df["date"].notna().any() else None

if min_date and max_date:
    date_range = st.sidebar.date_input(
        "Période",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    date_range = None

def multiselect_if_exists(label, column):
    if column not in df.columns:
        return None
    values = sorted(df[column].dropna().astype(str).unique().tolist())
    return st.sidebar.multiselect(label, values, default=values)

selected_hubs = multiselect_if_exists("Hub d'origine", "origin_hub")
selected_regions = multiselect_if_exists("Région de destination", "destination_region")
selected_products = multiselect_if_exists("Catégorie produit", "product_category")
selected_modes = multiselect_if_exists("Mode de transport", "mode")

# Application filtres
filtered = df.copy()

if date_range and isinstance(date_range, tuple) and len(date_range) == 2 and "date" in filtered.columns:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[filtered["date"].between(start, end)]

if selected_hubs is not None and selected_hubs:
    filtered = filtered[filtered["origin_hub"].astype(str).isin(selected_hubs)]
elif selected_hubs == []:
    filtered = filtered.iloc[0:0]

if selected_regions is not None and selected_regions:
    filtered = filtered[filtered["destination_region"].astype(str).isin(selected_regions)]
elif selected_regions == []:
    filtered = filtered.iloc[0:0]

if selected_products is not None and selected_products:
    filtered = filtered[filtered["product_category"].astype(str).isin(selected_products)]
elif selected_products == []:
    filtered = filtered.iloc[0:0]

if selected_modes is not None and selected_modes:
    filtered = filtered[filtered["mode"].astype(str).isin(selected_modes)]
elif selected_modes == []:
    filtered = filtered.iloc[0:0]

# -----------------------------
# Header
# -----------------------------
st.markdown('<div class="dashboard-title">📊 COPAG — Dashboard Logistique</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="dashboard-subtitle">Pilotage de la performance des expéditions, des coûts, des retards et de la chaîne du froid.</div>',
    unsafe_allow_html=True
)

if filtered.empty:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
    st.stop()

# -----------------------------
# KPI
# -----------------------------
shipments = len(filtered)
on_time_rate = filtered["on_time"].mean() * 100 if "on_time" in filtered else np.nan
avg_cost = filtered["cost_mad"].mean() if "cost_mad" in filtered else np.nan
avg_fuel = filtered["fuel_liters"].mean() if "fuel_liters" in filtered else np.nan
avg_co2 = filtered["co2_kg"].mean() if "co2_kg" in filtered else np.nan
avg_delay = filtered["delay_min"].mean() if "delay_min" in filtered else np.nan

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Expéditions", f"{shipments:,}".replace(",", " "))
k2.metric("Taux à l'heure", f"{on_time_rate:.1f} %")
k3.metric("Coût moyen", f"{avg_cost:,.0f} MAD".replace(",", " "))
k4.metric("Carburant moyen", f"{avg_fuel:,.1f} L".replace(",", " "))
k5.metric("CO₂ moyen", f"{avg_co2:,.1f} kg".replace(",", " "))
k6.metric("Retard moyen", f"{avg_delay:,.1f} min".replace(",", " "))

st.divider()

# -----------------------------
# Onglets
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Performance", "💰 Coûts & exploitation",
    "🌱 Environnement & qualité", "🗺️ Flux & données"
])

with tab1:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Performance quotidienne")
        daily = filtered.groupby("date", as_index=False)["on_time"].mean()
        daily["taux"] = daily["on_time"] * 100
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.plot(daily["date"], daily["taux"], linewidth=2)
        ax.set_xlabel("Date")
        ax.set_ylabel("Taux à l'heure (%)")
        ax.set_title("Évolution du taux à l'heure")
        ax.tick_params(axis="x", rotation=35)
        st.pyplot(fig, clear_figure=True)

    with c2:
        st.subheader("Top 10 des routes")
        routes = filtered["lane"].value_counts().head(10).sort_values()
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.barh(routes.index, routes.values)
        ax.set_xlabel("Nombre d'expéditions")
        ax.set_ylabel("Route")
        st.pyplot(fig, clear_figure=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Retard par catégorie produit")
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.boxplot(data=filtered, x="delay_min", y="product_category", ax=ax)
        ax.set_xlabel("Retard (minutes)")
        ax.set_ylabel("Catégorie")
        st.pyplot(fig, clear_figure=True)

    with c4:
        st.subheader("Retard moyen par région")
        delay_region = (
            filtered.groupby("destination_region", as_index=False)["delay_min"]
            .mean().sort_values("delay_min", ascending=True)
        )
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh(delay_region["destination_region"], delay_region["delay_min"])
        ax.set_xlabel("Retard moyen (min)")
        ax.set_ylabel("Région")
        st.pyplot(fig, clear_figure=True)

with tab2:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Coût moyen par kilomètre — région")
        cost_region = (
            filtered.groupby("destination_region", as_index=False)["cost_per_km"]
            .mean().sort_values("cost_per_km", ascending=False)
        )
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(cost_region["destination_region"], cost_region["cost_per_km"])
        ax.set_ylabel("MAD / km")
        ax.tick_params(axis="x", rotation=40)
        st.pyplot(fig, clear_figure=True)

    with c2:
        st.subheader("Coût moyen par catégorie produit")
        cost_product = (
            filtered.groupby("product_category", as_index=False)["cost_mad"]
            .mean().sort_values("cost_mad", ascending=False)
        )
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(cost_product["product_category"], cost_product["cost_mad"])
        ax.set_ylabel("Coût moyen (MAD)")
        ax.tick_params(axis="x", rotation=40)
        st.pyplot(fig, clear_figure=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Distance vs coût")
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.scatterplot(data=filtered, x="distance_km", y="cost_mad", alpha=.6, ax=ax)
        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("Coût (MAD)")
        st.pyplot(fig, clear_figure=True)

    with c4:
        st.subheader("Utilisation de capacité par mode")
        cap = filtered.groupby("mode", as_index=False)["capacity_utilization"].mean()
        # Affichage en % si les valeurs sont des fractions
        vals = cap["capacity_utilization"].copy()
        if vals.max() <= 1.5:
            vals = vals * 100
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(cap["mode"], vals)
        ax.set_ylabel("Utilisation moyenne (%)")
        ax.tick_params(axis="x", rotation=30)
        st.pyplot(fig, clear_figure=True)

with tab3:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Rupture de chaîne du froid par produit")
        breach = filtered.groupby("product_category", as_index=False)["temperature_breach"].mean()
        breach["taux"] = breach["temperature_breach"] * 100
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(breach["product_category"], breach["taux"])
        ax.set_ylabel("Taux de rupture (%)")
        ax.tick_params(axis="x", rotation=35)
        st.pyplot(fig, clear_figure=True)

    with c2:
        st.subheader("Répartition des expéditions par produit")
        counts = filtered["product_category"].value_counts()
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", startangle=90)
        ax.set_title("Part des expéditions")
        st.pyplot(fig, clear_figure=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Distance vs consommation")
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.scatterplot(data=filtered, x="distance_km", y="fuel_liters", alpha=.6, ax=ax)
        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("Carburant (L)")
        st.pyplot(fig, clear_figure=True)

    with c4:
        st.subheader("Distance vs émissions CO₂")
        fig, ax = plt.subplots(figsize=(9, 5))
        sns.scatterplot(data=filtered, x="distance_km", y="co2_kg", alpha=.6, ax=ax)
        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("CO₂ (kg)")
        st.pyplot(fig, clear_figure=True)

    st.subheader("Matrice de corrélation")
    corr_cols = [
        "distance_km", "planned_duration_min", "actual_duration_min",
        "delay_min", "on_time", "temperature_breach",
        "capacity_utilization", "fuel_liters", "co2_kg",
        "cost_mad", "quantity_tons"
    ]
    corr_cols = [c for c in corr_cols if c in filtered.columns]
    corr = filtered[corr_cols].corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(12, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", ax=ax)
    ax.set_title("Corrélation des indicateurs")
    st.pyplot(fig, clear_figure=True)

with tab4:
    st.subheader("Positions géographiques")
    geo_cols = [c for c in ["lat", "lon"] if c in filtered.columns]
    if len(geo_cols) == 2:
        geo = filtered[geo_cols].dropna()
        st.map(geo.rename(columns={"lat": "latitude", "lon": "longitude"}), zoom=5)
    else:
        st.info("Les coordonnées de flotte ne sont pas disponibles.")

    st.subheader("Flux hubs → destinations")
    flow_cols = ["origin_hub", "destination_city", "o_lat", "o_lon", "d_lat", "d_lon"]
    if all(c in filtered.columns for c in flow_cols):
        flows = (
            filtered.groupby(flow_cols, as_index=False).size()
            .rename(columns={"size": "count"})
        )
        fig, ax = plt.subplots(figsize=(11, 8))
        for _, row in flows.iterrows():
            ax.plot(
                [row["o_lon"], row["d_lon"]],
                [row["o_lat"], row["d_lat"]],
                linewidth=max(0.5, row["count"] / 20),
                alpha=.35
            )
        for hub, g in filtered.groupby("origin_hub"):
            x, y = g["o_lon"].iloc[0], g["o_lat"].iloc[0]
            ax.scatter(x, y, s=100)
            ax.text(x, y, str(hub), fontsize=9)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Flux de transport entre hubs et villes")
        ax.grid(True)
        st.pyplot(fig, clear_figure=True)
    else:
        st.info("Les coordonnées des hubs/destinations ne sont pas disponibles.")

    st.subheader("Aperçu des données nettoyées")
    st.dataframe(filtered.head(100), use_container_width=True)

    csv_export = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Télécharger les données filtrées",
        data=csv_export,
        file_name="copag_donnees_filtrees.csv",
        mime="text/csv",
    )

# -----------------------------
# Qualité des données
# -----------------------------
with st.sidebar.expander("🔎 Qualité des données"):
    st.write(f"Lignes initiales : **{len(df):,}**".replace(",", " "))
    st.write(f"Lignes après filtres : **{len(filtered):,}**".replace(",", " "))
    missing = int(filtered.isna().sum().sum())
    st.write(f"Valeurs manquantes : **{missing:,}**".replace(",", " "))
    st.write(f"Colonnes : **{filtered.shape[1]}**")

st.caption("COPAG — Analyse logistique | Python • Pandas • Streamlit • Matplotlib • Seaborn")
