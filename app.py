import streamlit as st
import numpy as np
import scipy.stats as stats
import requests

# Configuración móvil e interfaz clara
st.set_page_config(page_title="Analytics Fútbol Elite", layout="centered")

st.title("⚽ Analytics & Simulador Elite")
st.caption("Predicciones automáticas con API: Goles, Córneres, Clima y Rachas")

# 1. AUTENTICACIÓN API
st.sidebar.header("🔑 Conexión de Datos")
api_key = st.sidebar.text_input("Ingresa tu API Key (api-sports.io)", type="password")

# MAPEO DE LIGAS (IDs Oficiales)
LIGAS = {
    "LaLiga (España)": 140,
    "Premier League (Inglaterra)": 39,
    "Bundesliga (Alemania)": 78,
    "Serie A (Italia)": 135,
    "Ligue 1 (Francia)": 61,
    "Liga MX (México)": 262,
    "MLS (EE. UU.)": 253,
    "Champions League": 2,
    "Europa League": 3,
    "Conference League": 848
}

liga_nombre = st.selectbox("📌 Selecciona la Liga", list(LIGAS.keys()))
liga_id = LIGAS[liga_nombre]

# 2. SELECCIÓN DE PARTIDO Y DATOS
st.subheader("🏟️ Configuración del Partido")

if api_key:
    headers = {"x-apisports-key": api_key}
    # Obtener partidos próximos
    try:
        url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={liga_id}&next=10"
        res_fix = requests.get(url_fixtures, headers=headers).json()
        partidos = res_fix.get("response", [])
        
        if partidos:
            opciones_partidos = {
                f"{p['teams']['home']['name']} vs {p['teams']['away']['name']} ({p['fixture']['date'][:10]})": p 
                for p in partidos
            }
            partido_sel = st.selectbox("Elige un partido próximo", list(opciones_partidos.keys()))
            partido_data = opciones_partidos[partido_sel]
            
            nombre_local = partido_data['teams']['home']['name']
            nombre_visita = partido_data['teams']['away']['name']
        else:
            st.warning("No se encontraron partidos próximos. Usa el modo simulación manual.")
            nombre_local, nombre_visita = "Local", "Visitante"
    except:
        st.error("Error al conectar con la API. Verifica tu clave.")
        nombre_local, nombre_visita = "Local", "Visitante"
else:
    st.info("💡 Ingresa tu API Key en el menú lateral para cargar partidos en vivo automáticos.")
    col_a, col_b = st.columns(2)
    nombre_local = col_a.text_input("Equipo Local", value="Real Madrid")
    nombre_visita = col_b.text_input("Equipo Visitante", value="Barcelona")

# 3. DATOS Y CONTEXTO
st.markdown("---")
st.subheader("⚙️ Factores del Juego")

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"**🏠 {nombre_local}**")
    attack_loc = st.slider(f"Fuerza Ataque {nombre_local}", 0.5, 2.5, 1.45, 0.05)
    def_loc = st.slider(f"Fortaleza Defensiva {nombre_local}", 0.5, 2.5, 0.80, 0.05)
    corners_loc = st.number_input(f"Prom. Córneres {nombre_local}", value=6.2)

with c2:
    st.markdown(f"**🚀 {nombre_visita}**")
    attack_vis = st.slider(f"Fuerza Ataque {nombre_visita}", 0.5, 2.5, 1.10, 0.05)
    def_vis = st.slider(f"Fortaleza Defensiva {nombre_visita}", 0.5, 2.5, 1.25, 0.05)
    corners_vis = st.number_input(f"Prom. Córneres {nombre_visita}", value=4.5)

st.markdown("**🌤️ Clima y Altitud**")
col_clima1, col_clima2 = st.columns(2)
altitud = col_clima1.number_input("Altitud Estadio (m)", min_value=0, max_value=4000, value=2240 if "MX" in liga_nombre else 0)
clima_lluvia = col_clima2.checkbox("¿Lluvia Intensa?")

# 4. BOTÓN Y MOTOR PREDICTIVO
if st.button("📊 GENERAR ANÁLISIS COMPLETO", use_container_width=True):
    # Factor Clima/Altitud
    f_loc, f_vis = 1.0, 1.0
    if altitud > 1500:
        f_loc *= (1.0 + (altitud - 1500) / 10000 * 0.15)
        f_vis *= (1.0 - (altitud - 1500) / 10000 * 0.20)
    if clima_lluvia:
        f_loc, f_vis = f_loc * 0.93, f_vis * 0.93

    # xG Proyectado
    xg_local = attack_loc * def_vis * 1.35 * 1.15 * f_loc
    xg_visita = attack_vis * def_loc * 1.35 * f_vis

    # Matriz de Poisson Goles
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
    exp_corners_total = (corners_loc + corners_vis) * 1.05
    prob_corners_9_5 = min(99.0, max(1.0, (exp_corners_total / 9.5 - 0.5) * 100))

    # PRESENTACIÓN DE RESULTADOS CLAROS Y ENTENDIBLES
    st.markdown("---")
    st.header("🎯 RESULTADOS DEL ANÁLISIS")

    # Tarjetas Métricas
    col_res1, col_res2 = st.columns(2)
    col_res1.metric("Goles Esperados Local", f"{xg_local:.2f}")
    col_res2.metric("Goles Esperados Visita", f"{xg_visita:.2f}")

    st.subheader("⚽ Mercados de Goles")
    st.write(f"• **Over 1.5 Goles:** {prob_over_1_5:.1f}% de probabilidad")
    st.progress(int(prob_over_1_5))
    
    st.write(f"• **Over 2.5 Goles:** {prob_over_2_5:.1f}% de probabilidad")
    st.progress(int(prob_over_2_5))
    
    st.write(f"• **Over 3.5 Goles:** {prob_over_3_5:.1f}% de probabilidad")
    st.progress(int(prob_over_3_5))

    st.subheader("🚩 Mercado de Córneres")
    st.metric("Tiros de Esquina Totales Proyectados", f"{exp_corners_total:.1f}")
    st.write(f"• **Probabilidad Over 9.5 Córneres:** {prob_corners_9_5:.1f}%")
    st.progress(int(prob_corners_9_5))

    st.subheader("⭐ Jugador Candidato a Gol (xG Individual)")
    prob_gol_goleador = min(85.0, (xg_local if xg_local > xg_visita else xg_visita) * 35.0)
    equipo_favorito = nombre_local if xg_local > xg_visita else nombre_visita
    st.info(f"El delantero principal de **{equipo_favorito}** tiene un **{prob_gol_goleador:.1f}%** de probabilidad de anotar gol según la proyección de xG.")
