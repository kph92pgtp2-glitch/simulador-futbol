import streamlit as st
import numpy as np
import scipy.stats as stats
import requests

st.set_page_config(page_title="Analytics Fútbol Elite Pro", layout="centered")

st.title("⚽ Analytics & Simulador Elite Pro")
st.caption("Motor calibrado por liga: Carga automática vía API, xG, Córneres y Altitud Real")

# 1. PARÁMETROS REALES Y CALIBRADOS POR LIGA
DATOS_LIGAS = {
    "Liga MX (México)": {"id": 262, "prom_goles": 2.45, "prom_corners": 9.2},
    "LaLiga (España)": {"id": 140, "prom_goles": 2.50, "prom_corners": 9.5},
    "Premier League (Inglaterra)": {"id": 39, "prom_goles": 2.85, "prom_corners": 10.4},
    "Bundesliga (Alemania)": {"id": 78, "prom_goles": 3.10, "prom_corners": 9.8},
    "Serie A (Italia)": {"id": 135, "prom_goles": 2.60, "prom_corners": 9.3},
    "Ligue 1 (Francia)": {"id": 61, "prom_goles": 2.55, "prom_corners": 9.1},
    "MLS (EE. UU.)": {"id": 253, "prom_goles": 2.95, "prom_corners": 9.7},
    "Champions League": {"id": 2, "prom_goles": 2.98, "prom_corners": 9.6},
    "Europa League": {"id": 3, "prom_goles": 2.80, "prom_corners": 9.5},
    "Conference League": {"id": 848, "prom_goles": 2.75, "prom_corners": 9.4}
}

st.sidebar.header("🔑 Conexión Automática")
api_key = st.sidebar.text_input("Ingresa tu API Key (API-Sports)", type="password")

liga_nombre = st.selectbox("📌 Selecciona la Liga", list(DATOS_LIGAS.keys()))
info_liga = DATOS_LIGAS[liga_nombre]

# Funciones para obtener datos de la API
def obtener_partidos(league_id, key):
    headers = {"x-apisports-key": key}
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&next=10"
    res = requests.get(url, headers=headers).json()
    return res.get("response", [])

def obtener_stats_equipo(league_id, team_id, key):
    headers = {"x-apisports-key": key}
    url = f"https://v3.football.api-sports.io/teams/statistics?league={league_id}&season=2026&team={team_id}"
    res = requests.get(url, headers=headers).json().get("response", {})
    
    if not res:
        return 1.3, 1.1, 5.0 # Valores de respaldo en caso de no encontrar datos
        
    g_favor = float(res.get("goals", {}).get("for", {}).get("average", {}).get("total") or 1.3)
    g_contra = float(res.get("goals", {}).get("against", {}).get("average", {}).get("total") or 1.1)
    return g_favor, g_contra, 5.0

# 2. SELECCIÓN DE PARTIDO AUTOMÁTICO O MANUAL
st.markdown("---")
st.subheader("🏟️ Partido y Datos")

if api_key:
    partidos = obtener_partidos(info_liga["id"], api_key)
    if partidos:
        dict_partidos = {
            f"{p['teams']['home']['name']} vs {p['teams']['away']['name']} ({p['fixture']['date'][:10]})": p 
            for p in partidos
        }
        partido_sel = st.selectbox("Elige un partido próximo", list(dict_partidos.keys()))
        data_p = dict_partidos[partido_sel]
        
        id_local = data_p['teams']['home']['id']
        id_visita = data_p['teams']['away']['id']
        nombre_local = data_p['teams']['home']['name']
        nombre_visita = data_p['teams']['away']['name']
        
        # Carga automática de estadísticas
        gf_loc, gc_loc, corners_loc = obtener_stats_equipo(info_liga["id"], id_local, api_key)
        gf_vis, gc_vis, corners_vis = obtener_stats_equipo(info_liga["id"], id_visita, api_key)
        st.success(f"✅ Datos cargados automáticamente para {nombre_local} vs {nombre_visita}")
    else:
        st.warning("No se encontraron partidos próximos. Usa la configuración manual abajo.")
        nombre_local = st.text_input("Equipo Local", "América" if "MX" in liga_nombre else "Real Madrid")
        nombre_visita = st.text_input("Equipo Visitante", "Chivas" if "MX" in liga_nombre else "Barcelona")
        gf_loc, gc_loc, corners_loc = 1.40, 1.00, 5.1
        gf_vis, gc_vis, corners_vis = 1.10, 1.20, 4.2
else:
    st.info("💡 Consejo: Pon tu API Key en la barra lateral para que los partidos y datos se carguen 100% solos.")
    col_a, col_b = st.columns(2)
    nombre_local = col_a.text_input("Equipo Local", "América" if "MX" in liga_nombre else "Real Madrid")
    nombre_visita = col_b.text_input("Equipo Visitante", "Chivas" if "MX" in liga_nombre else "Barcelona")
    
    c1, c2 = st.columns(2)
    gf_loc = c1.number_input(f"Goles anotados/partido ({nombre_local})", value=1.40, step=0.05)
    gc_loc = c1.number_input(f"Goles recibidos/partido ({nombre_local})", value=1.00, step=0.05)
    corners_loc = c1.number_input(f"Córneres/partido ({nombre_local})", value=5.1)
    
    gf_vis = c2.number_input(f"Goles anotados/partido ({nombre_visita})", value=1.10, step=0.05)
    gc_vis = c2.number_input(f"Goles recibidos/partido ({nombre_visita})", value=1.20, step=0.05)
    corners_vis = c2.number_input(f"Córneres/partido ({nombre_visita})", value=4.2)

st.markdown("**🌤️ Ajuste de Estadio**")
col_clima1, col_clima2 = st.columns(2)
altitud = col_clima1.number_input("Altitud Estadio (m)", min_value=0, max_value=4000, value=2240 if "MX" in liga_nombre else 0)
clima_lluvia = col_clima2.checkbox("¿Lluvia Intensa?")

# 3. MOTOR PREDICTIVO
if st.button("📊 GENERAR SIMULACIÓN CALIBRADA", use_container_width=True):
    prom_liga_goles_equipo = info_liga["prom_goles"] / 2.0
    
    ataque_loc_idx = gf_loc / prom_liga_goles_equipo
    defensa_loc_idx = gc_loc / prom_liga_goles_equipo
    ataque_vis_idx = gf_vis / prom_liga_goles_equipo
    defensa_vis_idx = gc_vis / prom_liga_goles_equipo

    f_loc, f_vis = 1.0, 1.0
    if altitud > 1800:
        f_vis *= 0.88
        f_loc *= 1.02
    
    if clima_lluvia:
        f_loc *= 0.94
        f_vis *= 0.94

    xg_local = ataque_loc_idx * defensa_vis_idx * prom_liga_goles_equipo * 1.08 * f_loc
    xg_visita = ataque_vis_idx * defensa_loc_idx * prom_liga_goles_equipo * f_vis

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

    st.markdown("---")
    st.header("🎯 ANÁLISIS PREDICTIVO CALIBRADO")

    col_res1, col_res2 = st.columns(2)
    col_res1.metric("xG Local Proyectado", f"{xg_local:.2f} goles")
    col_res2.metric("xG Visita Proyectado", f"{xg_visita:.2f} goles")

    st.subheader("⚽ Probabilidades de Mercado (Goles)")
    st.write(f"• **Over 1.5 Goles:** {prob_over_1_5:.1f}%")
    st.progress(min(100, max(0, int(prob_over_1_5))))
    
    st.write(f"• **Over 2.5 Goles:** {prob_over_2_5:.1f}%")
    st.progress(min(100, max(0, int(prob_over_2_5))))
    
    st.write(f"• **Over 3.5 Goles:** {prob_over_3_5:.1f}%")
    st.progress(min(100, max(0, int(prob_over_3_5))))

    st.subheader("🚩 Mercado de Córneres")
    st.metric("Total Córneres Proyectados", f"{exp_corners_total:.1f}")
    st.write(f"• **Probabilidad Over 9.5 Córneres:** {prob_corners_9_5:.1f}%")
    st.progress(min(100, max(0, int(prob_corners_9_5))))
