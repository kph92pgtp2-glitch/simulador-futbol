import streamlit as st
import numpy as np
import scipy.stats as stats

st.set_page_config(page_title="Analytics Fútbol Elite", layout="centered")

st.title("⚽ Analytics & Simulador Fútbol")
st.caption("Predicciones claras de Goles, Córneres y Altitud calibradas por liga")

# 1. PARÁMETROS CALIBRADOS POR LIGA (PROMEDIOS REALES)
DATOS_LIGAS = {
    "Liga MX (México)": {"prom_goles": 2.45, "prom_corners": 9.2},
    "LaLiga (España)": {"prom_goles": 2.50, "prom_corners": 9.5},
    "Premier League (Inglaterra)": {"prom_goles": 2.85, "prom_corners": 10.4},
    "Bundesliga (Alemania)": {"prom_goles": 3.10, "prom_corners": 9.8},
    "Serie A (Italia)": {"prom_goles": 2.60, "prom_corners": 9.3},
    "Ligue 1 (Francia)": {"prom_goles": 2.55, "prom_corners": 9.1},
    "MLS (EE. UU.)": {"prom_goles": 2.95, "prom_corners": 9.7},
    "Champions League": {"prom_goles": 2.98, "prom_corners": 9.6},
    "Europa League": {"prom_goles": 2.80, "prom_corners": 9.5},
    "Conference League": {"prom_goles": 2.75, "prom_corners": 9.4}
}

# SELECCIÓN DE LIGA
liga_nombre = st.selectbox("📌 Selecciona la Liga", list(DATOS_LIGAS.keys()))
info_liga = DATOS_LIGAS[liga_nombre]

st.markdown("---")
st.subheader("🏟️ Configuración del Partido")

col_a, col_b = st.columns(2)
nombre_local = col_a.text_input("Equipo Local", value="", placeholder="Ej. Local")
nombre_visita = col_b.text_input("Equipo Visitante", value="", placeholder="Ej. Visitante")

# Nombres dinámicos para los controles
lbl_local = nombre_local.strip() if nombre_local.strip() else "Local"
lbl_visita = nombre_visita.strip() if nombre_visita.strip() else "Visitante"

st.markdown("---")
st.subheader("⚙️ Nivel de los Equipos")

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"**🏠 {lbl_local}**")
    attack_loc = st.slider(f"Ataque {lbl_local}", 0.5, 2.5, 1.30, 0.05)
    def_loc = st.slider(f"Defensa {lbl_local}", 0.5, 2.5, 0.90, 0.05)
    corners_loc = st.number_input(f"Prom. Córneres {lbl_local}", value=5.1, step=0.1)

with c2:
    st.markdown(f"**🚀 {lbl_visita}**")
    attack_vis = st.slider(f"Ataque {lbl_visita}", 0.5, 2.5, 1.10, 0.05)
    def_vis = st.slider(f"Defensa {lbl_visita}", 0.5, 2.5, 1.10, 0.05)
    corners_vis = st.number_input(f"Prom. Córneres {lbl_visita}", value=4.2, step=0.1)

st.markdown("**🌤️ Clima y Altitud**")
col_clima1, col_clima2 = st.columns(2)
altitud = col_clima1.number_input("Altitud Estadio (m)", min_value=0, max_value=4000, value=2240 if "MX" in liga_nombre else 0)
clima_lluvia = col_clima2.checkbox("¿Lluvia Intensa?")

# MOTOR PREDICTIVO DIRECTO
if st.button("📊 GENERAR ANÁLISIS COMPLETO", use_container_width=True):
    base_goles = info_liga["prom_goles"] / 2.0
    
    # Factor Altitud
    f_loc, f_vis = 1.0, 1.0
    if altitud > 1800:
        f_vis *= 0.88
        f_loc *= 1.02
    
    if clima_lluvia:
        f_loc *= 0.94
        f_vis *= 0.94

    # Goles esperados (xG)
    xg_local = attack_loc * def_vis * base_goles * 1.08 * f_loc
    xg_visita = attack_vis * def_loc * base_goles * f_vis

    # Matriz de Poisson
    max_g = 7
    matriz_goles = np.zeros((max_g, max_g))
    for i in range(max_g):
        for j in range(max_g):
            matriz_goles[i, j] = stats.poisson.pmf(i, xg_local) * stats.poisson.pmf(j, xg_visita)

    goles_totales = np.add.outer(np.arange(max_g), np.arange(max_g))
    prob_over_1_5 = (1.0 - np.sum(matriz_goles[goles_totales < 1.5])) * 100
    prob_over_2_5 = (1.0 - np.sum(matriz_goles[goles_totales < 2.5])) * 100
    prob_over_3_5 = (1.0 - np.sum(matriz_goles[goles_totales < 3.5])) * 100

    # Córneres
    exp_corners_total = corners_loc + corners_vis
    prob_corners_9_5 = (1.0 - stats.poisson.cdf(9, exp_corners_total)) * 100

    # PRESENTACIÓN
    st.markdown("---")
    st.header(f"🎯 RESULTADOS: {lbl_local} vs {lbl_visita}")

    col_res1, col_res2 = st.columns(2)
    col_res1.metric(f"Goles Esperados {lbl_local}", f"{xg_local:.2f}")
    col_res2.metric(f"Goles Esperados {lbl_visita}", f"{xg_visita:.2f}")

    st.subheader("⚽ Mercados de Goles")
    st.write(f"• **Over 1.5 Goles:** {prob_over_1_5:.1f}% de probabilidad")
    st.progress(min(100, max(0, int(prob_over_1_5))))
    
    st.write(f"• **Over 2.5 Goles:** {prob_over_2_5:.1f}% de probabilidad")
    st.progress(min(100, max(0, int(prob_over_2_5))))
    
    st.write(f"• **Over 3.5 Goles:** {prob_over_3_5:.1f}% de probabilidad")
    st.progress(min(100, max(0, int(prob_over_3_5))))

    st.subheader("🚩 Mercado de Córneres")
    st.metric("Tiros de Esquina Proyectados", f"{exp_corners_total:.1f}")
    st.write(f"• **Probabilidad Over 9.5 Córneres:** {prob_corners_9_5:.1f}%")
    st.progress(min(100, max(0, int(prob_corners_9_5))))
