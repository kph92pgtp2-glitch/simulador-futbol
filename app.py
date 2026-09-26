import streamlit as st
import numpy as np
import scipy.stats as stats
import requests

st.set_page_config(page_title="Analytics Fútbol", layout="wide")

# ==========================================
# 1. CLAVE FIJA (Pon tu API Key aquí para no teclearla jamás)
# ==========================================
API_KEY_FIJA = ""  # Pega aquí tu API Key entre las comillas si la tienes

# MAPEO DE LIGAS CON SUS PROMEDIOS HISTÓRICOS CALIBRADOS
LIGAS = {
    "LaLiga (España)": {"id": 140, "prom_goles": 2.50, "prom_corners": 9.5},
    "Premier League (Inglaterra)": {"id": 39, "prom_goles": 2.85, "prom_corners": 10.4},
    "Bundesliga (Alemania)": {"id": 78, "prom_goles": 3.10, "prom_corners": 9.8},
    "Serie A (Italia)": {"id": 135, "prom_goles": 2.60, "prom_corners": 9.3},
    "Ligue 1 (Francia)": {"id": 61, "prom_goles": 2.55, "prom_corners": 9.1},
    "Liga MX (México)": {"id": 262, "prom_goles": 2.45, "prom_corners": 9.2},
    "MLS (EE. UU.)": {"id": 253, "prom_goles": 2.95, "prom_corners": 9.7},
    "Champions League": {"id": 2, "prom_goles": 2.98, "prom_corners": 9.6},
    "Europa League": {"id": 3, "prom_goles": 2.80, "prom_corners": 9.5},
    "Conference League": {"id": 848, "prom_goles": 2.75, "prom_corners": 9.4}
}

# ==========================================
# 2. MENU LATERAL DE LIGAS (Estructura Original)
# ==========================================
st.sidebar.title("⚽ Ligas Disponibles")
liga_seleccionada = st.sidebar.radio("Selecciona una competencia:", list(LIGAS.keys()))

info_liga = LIGAS[liga_seleccionada]
liga_id = info_liga["id"]

st.title(f"📊 Analytics: {liga_seleccionada}")

# ==========================================
# 3. CARGA DE PARTIDOS DEL DÍA / PRÓXIMOS
# ==========================================
nombre_local = "Equipo Local"
nombre_visita = "Equipo Visitante"
partido_cargado = False

if API_KEY_FIJA:
    headers = {"x-apisports-key": API_KEY_FIJA}
    try:
        url = f"https://v3.football.api-sports.io/fixtures?league={liga_id}&next=10"
        res = requests.get(url, headers=headers).json()
        partidos = res.get("response", [])
        
        if partidos:
            opciones = {
                f"{p['teams']['home']['name']} vs {p['teams']['away']['name']} ({p['fixture']['date'][:10]})": p 
                for p in partidos
            }
            partido_sel = st.selectbox("📅 Selecciona un partido de la jornada:", list(opciones.keys()))
            p_data = opciones[partido_sel]
            
            nombre_local = p_data['teams']['home']['name']
            nombre_visita = p_data['teams']['away']['name']
            partido_cargado = True
        else:
            st.info("No hay partidos próximos programados en la API para esta liga. Ingresa los datos abajo.")
    except:
        st.warning("No se pudieron obtener los partidos automáticos. Verifica tu API Key.")

if not partido_cargado:
    col_e1, col_e2 = st.columns(2)
    nombre_local = col_e1.text_input("Equipo Local", value=nombre_local)
    nombre_visita = col_e2.text_input("Equipo Visitante", value=nombre_visita)

# ==========================================
# 4. CONTROLES Y FACTORES DEL JUEGO
# ==========================================
st.markdown("---")
st.subheader(f"⚔️ Análisis: {nombre_local} vs {nombre_visita}")

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"### 🏠 {nombre_local}")
    attack_loc = st.slider(f"Nivel de Ataque ({nombre_local})", 0.5, 2.5, 1.30, 0.05)
    def_loc = st.slider(f"Solidez Defensiva ({nombre_local})", 0.5, 2.5, 0.90, 0.05)
    corners_loc = st.number_input(f"Prom. Córneres a Favor ({nombre_local})", value=5.1, step=0.1)

with col2:
    st.markdown(f"### 🚀 {nombre_visita}")
    attack_vis = st.slider(f"Nivel de Ataque ({nombre_visita})", 0.5, 2.5, 1.10, 0.05)
    def_vis = st.slider(f"Solidez Defensiva ({nombre_visita})", 0.5, 2.5, 1.10, 0.05)
    corners_vis = st.number_input(f"Prom. Córneres a Favor ({nombre_visita})", value=4.2, step=0.1)

st.markdown("---")
st.markdown("### 🌤️ Condición de Altitud y Clima")
c_alt, c_lluvia = st.columns(2)
altitud = c_alt.number_input("Altitud del Estadio (metros)", min_value=0, max_value=4000, value=2240 if "MX" in liga_seleccionada else 0)
clima_lluvia = c_lluvia.checkbox("¿Lluvia Intensa?")

# ==========================================
# 5. MOTOR PREDICTIVO Y RESULTADOS
# ==========================================
if st.button("📊 CALCULAR PROBABILIDADES DEL PARTIDO", use_container_width=True):
    base_goles = info_liga["prom_goles"] / 2.0
    
    # Ajustes por altitud/clima
    f_loc, f_vis = 1.0, 1.0
    if altitud > 1800:
        f_vis *= 0.88
        f_loc *= 1.02
    if clima_lluvia:
        f_loc *= 0.94
        f_vis *= 0.94

    # xG Proyectado
    xg_local = attack_loc * def_vis * base_goles * 1.08 * f_loc
    xg_visita = attack_vis * def_loc * base_goles * f_vis

    # Matriz Poisson
    max_g = 7
    matriz_goles = np.zeros((max_g, max_g))
    for i in range(max_g):
        for j in range(max_g):
            matriz_goles[i, j] = stats.poisson.pmf(i, xg_local) * stats.poisson.pmf(j, xg_visita)

    goles_totales = np.add.outer(np.arange(max_g), np.arange(max_g))
    prob_over_1_5 = (1.0 - np.sum(matriz_goles[goles_totales < 1.5])) * 100
    prob_over_2_5 = (1.0 - np.sum(matriz_goles[goles_totales < 2.5])) * 100
    prob_over_3_5 = (1.0 - np.sum(matriz_goles[goles_totales < 3.5])) * 100

    exp_corners_total = corners_loc + corners_vis
    prob_corners_9_5 = (1.0 - stats.poisson.cdf(9, exp_corners_total)) * 100

    # PANTALLA DE RESULTADOS VISUALES
    st.markdown("---")
    st.header("🎯 PREDICCIÓN Y MERCADOS")

    res1, res2 = st.columns(2)
    res1.metric(f"Goles Esperados {nombre_local}", f"{xg_local:.2f}")
    res2.metric(f"Goles Esperados {nombre_visita}", f"{xg_visita:.2f}")

    st.subheader("⚽ Mercados de Goles")
    st.write(f"• **Over 1.5 Goles:** {prob_over_1_5:.1f}%")
    st.progress(min(100, max(0, int(prob_over_1_5))))
    
    st.write(f"• **Over 2.5 Goles:** {prob_over_2_5:.1f}%")
    st.progress(min(100, max(0, int(prob_over_2_5))))
    
    st.write(f"• **Over 3.5 Goles:** {prob_over_3_5:.1f}%")
    st.progress(min(100, max(0, int(prob_over_3_5))))

    st.subheader("🚩 Mercado de Córneres")
    st.metric("Total Córneres Esperados", f"{exp_corners_total:.1f}")
    st.write(f"• **Probabilidad Over 9.5 Córneres:** {prob_corners_9_5:.1f}%")
    st.progress(min(100, max(0, int(prob_corners_9_5))))
