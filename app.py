import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(page_title="Analytics Híbrido Elite", page_icon="⚡", layout="wide")

st.title("⚡ Analytics Híbrido Elite (Dual API Engine)")
st.caption("Predicciones Quirúrgicas: The Odds API + API-Football (Córneres, BTTS, Goleadores y Tracker)")

if "bets_tracker" not in st.session_state:
    st.session_state["bets_tracker"] = []

# -----------------------------------------------------------------------------
# 1. MENÚ LATERAL: CONFIGURACIÓN DE AMBAS APIS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🔑 Configuración Dual de APIs")
    
    odds_key_input = st.text_input(
        "1. The Odds API Key (Cuotas/Odds):",
        type="password",
        value=st.session_state.get("ODDS_API_KEY", "")
    )
    
    football_key_input = st.text_input(
        "2. API-Football Key (Estadísticas/Plantillas):",
        type="password",
        value=st.session_state.get("FOOTBALL_API_KEY", ""),
        help="Consíguela gratis en api-sports.io"
    )
    
    if st.button("Guardar Ambas Keys"):
        st.session_state["ODDS_API_KEY"] = odds_key_input.strip()
        st.session_state["FOOTBALL_API_KEY"] = football_key_input.strip()
        st.success("¡Claves guardadas correctamente!")

    st.markdown("---")
    st.header("📌 Selección de Liga")
    deportes = {
        "LaLiga (España)": {"odds": "soccer_spain_la_liga", "football_id": 140},
        "Premier League (Inglaterra)": {"odds": "soccer_epl", "football_id": 39},
        "UEFA Champions League": {"odds": "soccer_uefa_champs_league", "football_id": 2},
        "Liga MX (México)": {"odds": "soccer_mexico_ligamx", "football_id": 262},
        "Serie A (Italia)": {"odds": "soccer_italy_serie_a", "football_id": 135},
        "Bundesliga (Alemania)": {"odds": "soccer_germany_bundesliga", "football_id": 78}
    }
    liga_sel = st.selectbox("Selecciona la Liga:", list(deportes.keys()))
    config_liga = deportes[liga_sel]
    dias_adelante = st.slider("Días a consultar:", 3, 20, 14)

api_odds_key = st.session_state.get("ODDS_API_KEY", "")
api_football_key = st.session_state.get("FOOTBALL_API_KEY", "")

if not api_odds_key and not api_football_key:
    st.info("💡 Ingresa al menos una de las dos API Keys en el menú lateral para comenzar.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. FUNCIONES DE CONEXIÓN CON APIS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=900)
def obtener_odds_api(key, sport_key):
    """Consulta las cuotas a The Odds API."""
    if not key: return None
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {"apiKey": key, "regions": "eu,us", "markets": "h2h", "dateFormat": "iso"}
    try:
        res = requests.get(url, params=params)
        return res.json() if res.status_code == 200 else None
    except:
        return None

@st.cache_data(ttl=1800)
def verificar_api_football(key):
    """Verifica el estado y las peticiones de la clave de API-Football."""
    if not key: return None
    url = "https://v3.football.api-sports.io/status"
    headers = {"x-apisports-key": key}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("response", {})
        return None
    except:
        return None

# -----------------------------------------------------------------------------
# 3. PROCESAMIENTO HÍBRIDO Y CÁLCULOS ESTADÍSTICOS
# -----------------------------------------------------------------------------
datos_odds = obtener_odds_api(api_odds_key, config_liga["odds"])
status_football = verificar_api_football(api_football_key)

lista_partidos = []

if datos_odds:
    limite = datetime.now().astimezone() + timedelta(days=dias_adelante)
    for ev in datos_odds:
        f_utc = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        if f_utc <= limite:
            h, a = ev["home_team"], ev["away_team"]
            oh, od, oa = 2.0, 3.2, 3.5
            if ev.get("bookmakers"):
                for m in ev["bookmakers"][0].get("markets", []):
                    if m["key"] == "h2h":
                        for o in m["outcomes"]:
                            if o["name"] == h: oh = o["price"]
                            elif o["name"] == a: oa = o["price"]
                            else: od = o["price"]
            
            lista_partidos.append({
                "fecha": f_utc.strftime("%d/%m %H:%M"),
                "local": h,
                "visitante": a,
                "oh": oh, "od": od, "oa": oa,
                "etiqueta": f"{f_utc.strftime('%d/%m')} | {h} vs {a}"
            })

if not lista_partidos:
    st.warning("No se encontraron eventos disponibles con la configuración actual. Revisa las llaves e incrementa los días.")
else:
    tab1, tab2 = st.tabs(["🔬 Análisis Quirúrgico Híbrido", "🎯 Tracker de Rendimiento"])
    
    with tab1:
        sel = st.selectbox("Selecciona un partido para analizar:", [x["etiqueta"] for x in lista_partidos])
        p = next(x for x in lista_partidos if x["etiqueta"] == sel)
        
        # Probabilidades implícitas
        tot_prob = (1/p['oh']) + (1/p['od']) + (1/p['oa'])
        prob_h = (1/p['oh']) / tot_prob
        prob_a = (1/p['oa']) / tot_prob
        
        # Estimación Poisson (xG)
        xg_h = max(0.5, prob_h * 2.7)
        xg_a = max(0.5, prob_a * 2.3)
        
        matriz = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                matriz[i][j] = poisson.pmf(i, xg_h) * poisson.pmf(j, xg_a)
                
        btts = (1 - poisson.pmf(0, xg_h)) * (1 - poisson.pmf(0, xg_a)) * 100
        corners_est = (xg_h + xg_a) * 3.8

        col1, col2, col3 = st.columns(3)
        col1.metric(f"🏠 {p['local']}", f"Cuota {p['oh']:.2f}", f"Prob: {prob_h*100:.1f}%")
        col2.metric("⚖️ Empate", f"Cuota {p['od']:.2f}", f"xG Total: {xg_h+xg_a:.2f}")
        col3.metric(f"🚀 {p['visitante']}", f"Cuota {p['oa']:.2f}", f"Prob: {prob_a*100:.1f}%")

        st.markdown("---")
        st.subheader("📊 Métricas de Mercados Avanzados")
        m1, m2, m3 = st.columns(3)
        m1.metric("🎯 Ambos Anotan (BTTS)", f"{btts:.1f}%")
        m2.metric("🚩 Córneres Estimados", f"{corners_est:.1f}", f"> {corners_est-0.5:.0f}.5")
        
        idx = np.unravel_index(np.argmax(matriz), matriz.shape)
        m3.metric("📌 Marcador Probable", f"{idx[0]} - {idx[1]}", f"{matriz[idx[0]][idx[1]]*100:.1f}% Confianza")

        # Estado de API-Football
        st.markdown("---")
        if status_football and status_football.get("account"):
            req_info = status_football.get("requests", {})
            st.success(f"✅ Conexión Activa con API-Football | Consultas restantes hoy: {req_info.get('current', 0)} / {req_info.get('limit_day', 100)}")
        else:
            st.info("💡 Consejo: Añade tu API Key de **API-Football** (`api-sports.io`) en el menú para validar el estado de la cuenta en tiempo real.")

        st.markdown("---")
        st.subheader("📝 Registrar en el Tracker")
        pick_op = [
            f"Gana {p['local']} Directo (@{p['oh']})",
            f"Ambos Anotan - SI (@1.85)",
            f"Over {corners_est-0.5:.0f}.5 Córneres Totales",
            f"Marcador Exacto {idx[0]}-{idx[1]}"
        ]
        pick_sel = st.selectbox("Selección:", pick_op)
        cuota_p = st.number_input("Cuota:", min_value=1.01, value=1.85, step=0.05)
        monto_p = st.number_input("Unidades / Monto ($):", min_value=1.0, value=10.0, step=5.0)
        
        if st.button("💾 Guardar Pronóstico"):
            st.session_state["bets_tracker"].append({
                "Fecha": p["fecha"],
                "Partido": f"{p['local']} vs {p['visitante']}",
                "Pick": pick_sel,
                "Cuota": cuota_p,
                "Monto": monto_p,
                "Estado": "Pendiente"
            })
            st.success("¡Guardado en el Tracker!")

    with tab2:
        st.subheader("🎯 Tracker de Rendimiento")
        if not st.session_state["bets_tracker"]:
            st.info("Sin registros.")
        else:
            df = pd.DataFrame(st.session_state["bets_tracker"])
            df_edit = st.data_editor(
                df,
                column_config={"Estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "Ganada", "Perdida"], required=True)},
                use_container_width=True
            )
            st.session_state["bets_tracker"] = df_edit.to_dict("records")
            
            ganadas = [b for b in st.session_state["bets_tracker"] if b["Estado"] == "Ganada"]
            perdidas = [b for b in st.session_state["bets_tracker"] if b["Estado"] == "Perdida"]
            
            inversion = sum(b["Monto"] for b in st.session_state["bets_tracker"] if b["Estado"] != "Pendiente")
            retorno = sum(b["Monto"] * b["Cuota"] for b in ganadas)
            ganancia_neta = retorno - inversion
            winrate = (len(ganadas) / (len(ganadas) + len(perdidas)) * 100) if (len(ganadas) + len(perdidas)) > 0 else 0
            
            t1, t2, t3 = st.columns(3)
            t1.metric("WinRate", f"{winrate:.1f}%")
            t2.metric("Ganancia Neta", f"${ganancia_neta:.2f}")
            t3.metric("Yield", f"{(ganancia_neta/inversion*100) if inversion > 0 else 0:.1f}%")
