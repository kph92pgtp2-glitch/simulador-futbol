import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(
    page_title="Analytics & Simulador Elite",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Analytics & Simulador Elite")
st.caption("Predicciones automáticas con API: Probabilidades, Poisson, Valor y Análisis de Jornada")

# -----------------------------------------------------------------------------
# 1. MENÚ LATERAL: API KEY Y CONFIGURACIÓN
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración de API")
    api_key_input = st.text_input(
        "Ingresa tu API Key de The Odds API:",
        type="password",
        value=st.session_state.get("ODDS_API_KEY", "")
    )
    
    if st.button("Guardar y Actualizar"):
        st.session_state["ODDS_API_KEY"] = api_key_input.strip()
        st.success("¡API Key guardada correctamente!")

    st.markdown("---")
    st.subheader("📌 Selección de Liga")
    deportes = {
        "LaLiga (España)": "soccer_spain_la_liga",
        "Premier League (Inglaterra)": "soccer_epl",
        "UEFA Champions League": "soccer_uefa_champs_league",
        "Liga MX (México)": "soccer_mexico_ligamx",
        "Serie A (Italia)": "soccer_italy_serie_a",
        "Bundesliga (Alemania)": "soccer_germany_bundesliga"
    }
    liga_seleccionada = st.selectbox("Selecciona la Liga:", list(deportes.keys()))
    sport_key = deportes[liga_seleccionada]

api_key = st.session_state.get("ODDS_API_KEY", "")

if not api_key:
    st.info("💡 Ingresa tu API Key en el menú lateral para cargar partidos y análisis de la jornada automáticos.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. FUNCIONES DE API Y SIMULACIÓN ESTADÍSTICA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800)
def obtener_partidos_8_dias(key, sport):
    """Consulta la API solicitando el rango de eventos de los próximos 8 días."""
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
    params = {
        "apiKey": key,
        "regions": "eu,us",
        "markets": "h2h,totals",
        "dateFormat": "iso"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al conectar con la API (Código HTTP {response.status_code})")
        return None

def calcular_probabilidades_implicitas(odd_home, odd_draw, odd_away):
    """Calcula la probabilidad real removiendo el overround de la casa de apuestas."""
    p_home = 1 / odd_home if odd_home > 0 else 0
    p_draw = 1 / odd_draw if odd_draw > 0 else 0
    p_away = 1 / odd_away if odd_away > 0 else 0
    total = p_home + p_draw + p_away
    return (p_home / total), (p_draw / total), (p_away / total)

def simulacion_poisson(prob_home, prob_away, max_goles=5):
    """Calcula la matriz de probabilidad de marcadores usando la Distribución de Poisson."""
    # Estimación básica de expectativas de goles según la probabilidad
    exp_goles_local = 1.35 * (prob_home / (prob_home + prob_away + 1e-5)) * 2
    exp_goles_visita = 1.10 * (prob_away / (prob_home + prob_away + 1e-5)) * 2
    
    matriz = np.zeros((max_goles + 1, max_goles + 1))
    for i in range(max_goles + 1):
        for j in range(max_goles + 1):
            matriz[i][j] = poisson.pmf(i, exp_goles_local) * poisson.pmf(j, exp_goles_visita)
            
    p_over25 = np.sum(np.triu(matriz, 3)) + np.sum(np.diag(matriz)[3:]) # Aproximación de >2.5 goles
    p_btts = np.sum(matriz[1:, 1:])
    
    return exp_goles_local, exp_goles_visita, matriz, p_over25, p_btts

# -----------------------------------------------------------------------------
# 3. PROCESAMIENTO Y ANÁLISIS DE LA JORNADA
# -----------------------------------------------------------------------------
datos_partidos = obtener_partidos_8_dias(api_key, sport_key)

if not datos_partidos:
    st.warning("No se encontraron partidos próximos para esta liga en los próximos 8 días.")
else:
    partidos_lista = []
    
    for evento in datos_partidos:
        fecha_utc = datetime.fromisoformat(evento["commence_time"].replace("Z", "+00:00"))
        # Filtrar dentro del rango de los próximos 8 días
        if fecha_utc <= datetime.now().astimezone() + timedelta(days=8):
            home = evento["home_team"]
            away = evento["away_team"]
            
            # Extraer momios/cuotas
            odd_h, odd_d, odd_a = None, None, None
            if evento.get("bookmakers"):
                bm = evento["bookmakers"][0]
                for market in bm.get("markets", []):
                    if market["key"] == "h2h":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home:
                                odd_h = outcome["price"]
                            elif outcome["name"] == away:
                                odd_a = outcome["price"]
                            else:
                                odd_d = outcome["price"]
            
            if odd_h and odd_d and odd_a:
                prob_h, prob_d, prob_a = calcular_probabilidades_implicitas(odd_h, odd_d, odd_a)
                partidos_lista.append({
                    "id": evento["id"],
                    "fecha": fecha_utc.strftime("%d/%m/%Y %H:%M"),
                    "local": home,
                    "visitante": away,
                    "odd_h": odd_h,
                    "odd_d": odd_d,
                    "odd_a": odd_a,
                    "prob_h": prob_h,
                    "prob_d": prob_d,
                    "prob_a": prob_a,
                    "etiqueta": f"{fecha_utc.strftime('%d/%m')} | {home} vs {away}"
                })

    if not partidos_lista:
        st.warning("No hay encuentros con cuotas disponibles dentro del rango de 8 días.")
    else:
        st.subheader(f"📅 Partidos de la Jornada (Próximos 8 Días) - {len(partidos_lista)} Encuentros")
        
        # Selector de partido específico
        opciones_partidos = {p["etiqueta"]: p for p in partidos_lista}
        partido_sel_label = st.selectbox("Selecciona un partido para analizar:", list(opciones_partidos.keys()))
        p_sel = opciones_partidos[partido_sel_label]
        
        st.markdown("---")
        
        # -----------------------------------------------------------------------------
        # 4. DESPLIEGUE DEL ANÁLISIS DETALLADO Y PREDECISIÓN
        # -----------------------------------------------------------------------------
        col1, col2, col3 = st.columns([2, 1, 2])
        
        with col1:
            st.markdown(f"### 🏠 {p_sel['local']}")
            st.metric("Cuota Directa", f"{p_sel['odd_h']:.2f}")
            st.progress(p_sel["prob_h"], text=f"Probabilidad de Victoria: {p_sel['prob_h']*100:.1f}%")
            
        with col2:
            st.markdown("### ⚖️ Empate")
            st.metric("Cuota Empate", f"{p_sel['odd_d']:.2f}")
            st.progress(p_sel["prob_d"], text=f"Probabilidad: {p_sel['prob_d']*100:.1f}%")
            
        with col3:
            st.markdown(f"### 🚀 {p_sel['visitante']}")
            st.metric("Cuota Directa", f"{p_sel['odd_a']:.2f}")
            st.progress(p_sel["prob_a"], text=f"Probabilidad de Victoria: {p_sel['prob_a']*100:.1f}%")

        # Ejecutar Modelo de Poisson
        exp_h, exp_a, matriz_p, p_over, p_btts = simulacion_poisson(p_sel["prob_h"], p_sel["prob_a"])

        st.markdown("---")
        st.subheader("📊 Análisis de Goles y Pronóstico Poisson")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("xG Esperado Local", f"{exp_h:.2f} goles")
        with col_b:
            st.metric("xG Esperado Visitante", f"{exp_a:.2f} goles")
        with col_c:
            st.metric("Probabilidad Ambos Anotan (BTTS)", f"{p_btts*100:.1f}%")

        # Determinar marcador más probable de la matriz
        idx_max = np.unravel_index(np.argmax(matriz_p, axis=None), matriz_p.shape)
        marcador_probable = f"{idx_max[0]} - {idx_max[1]}"
        prob_marcador = matriz_p[idx_max[0]][idx_max[1]] * 100

        st.info(f"💡 **Pronóstico Principal del Algoritmo:** Marcador más probable: **{marcador_probable}** (Confianza estimada: {prob_marcador:.1f}%)")
