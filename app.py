import streamlit as st
import numpy as np
import scipy.stats as stats

st.set_page_config(page_title="Analytics Fútbol", layout="centered")

st.title("⚽ Analytics & Simulador de Ligas")
st.caption("Motor predictivo probabilístico (xG, Clima, Córneres)")

liga = st.selectbox(
    "Selecciona la Liga",
    ["LaLiga (España)", "Premier League (Inglaterra)", "Bundesliga (Alemania)", 
     "Serie A (Italia)", "Ligue 1 (Francia)", "Liga MX (México)", 
     "MLS (EE. UU.)", "Champions League", "Europa League", "Conference League"]
)

st.subheader("🌧️ Clima y Estadio")
altitud = st.number_input("Altitud del Estadio (m)", min_value=0, max_value=4000, value=2240 if "MX" in liga else 0)
clima_lluvia = st.checkbox("¿Lluvia Intensa?")
temperatura = st.slider("Temperatura (°C)", 0, 40, 22)

st.subheader("📊 Métricas de Equipos")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**🏠 Local**")
    attack_loc = st.number_input("Ataque Local", value=1.45, step=0.05)
    def_loc = st.number_input("Defensa Local", value=0.80, step=0.05)
    corners_loc = st.number_input("Córneres a favor (L)", value=6.2)

with col2:
    st.markdown("**🚀 Visitante**")
    attack_vis = st.number_input("Ataque Visita", value=1.10, step=0.05)
    def_vis = st.number_input("Defensa Visita", value=1.25, step=0.05)
    corners_vis = st.number_input("Córneres a favor (V)", value=4.5)

if st.button("📊 SIMULAR PARTIDO", use_container_width=True):
    factor_loc, factor_vis = 1.0, 1.0
    if altitud > 1500:
        factor_loc *= (1.0 + (altitud - 1500) / 10000 * 0.15)
        factor_vis *= (1.0 - (altitud - 1500) / 10000 * 0.20)
    if clima_lluvia:
        factor_loc *= 0.93
        factor_vis *= 0.93

    xg_local = attack_loc * def_vis * 1.35 * 1.15 * factor_loc
    xg_visita = attack_vis * def_loc * 1.35 * factor_vis

    max_g = 7
    matriz_goles = np.zeros((max_g, max_g))
    for i in range(max_g):
        for j in range(max_g):
            matriz_goles[i, j] = stats.poisson.pmf(i, xg_local) * stats.poisson.pmf(j, xg_visita)

    goles_totales = np.add.outer(np.arange(max_g), np.arange(max_g))
    prob_over_2_5 = (1.0 - np.sum(matriz_goles[goles_totales < 2.5])) * 100
    exp_corners = (corners_loc + corners_vis) * 1.05

    st.divider()
    st.success("🎯 Pronóstico Calculado")
    
    m1, m2 = st.columns(2)
    m1.metric("xG Local", f"{xg_local:.2f}")
    m2.metric("xG Visitante", f"{xg_visita:.2f}")
    
    st.metric("Córneres Esperados", f"{exp_corners:.1f}")
    st.progress(int(prob_over_2_5), text=f"Probabilidad Over 2.5 Goles: {prob_over_2_5:.1f}%")
