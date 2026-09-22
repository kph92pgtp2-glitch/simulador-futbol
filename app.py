import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(page_title="Analytics & Tracker Elite", page_icon="⚽", layout="wide")

st.title("⚽ Analytics & Tracker Elite")
st.caption("Predicciones, Análisis de Jornada y Sistema de Seguimiento de Apuestas (Tracker)")

# Initialize session state for Tracker
if "bets_tracker" not in st.session_state:
    st.session_state["bets_tracker"] = []

# -----------------------------------------------------------------------------
# 1. MENU LATERAL: CONFIGURACION Y TRACKER
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_input = st.text_input(
        "API Key (The Odds API):",
        type="password",
        value=st.session_state.get("ODDS_API_KEY", "")
    )
    if st.button("Guardar Key"):
        st.session_state["ODDS_API_KEY"] = api_key_input.strip()
        st.success("¡Guardado!")

    st.markdown("---")
    st.header("📌 Liga & Filtro")
    deportes = {
        "LaLiga (España)": "soccer_spain_la_liga",
        "Premier League (Inglaterra)": "soccer_epl",
        "UEFA Champions League": "soccer_uefa_champs_league",
        "Liga MX (México)": "soccer_mexico_ligamx",
        "Serie A (Italia)": "soccer_italy_serie_a",
        "Bundesliga (Alemania)": "soccer_germany_bundesliga"
    }
    liga_sel = st.selectbox("Selecciona la Liga:", list(deportes.keys()))
    sport_key = deportes[liga_sel]
    dias_adelante = st.slider("Días a consultar:", min_value=3, max_value=20, value=14)

api_key = st.session_state.get("ODDS_API_KEY", "")

if not api_key:
    st.info("💡 Ingresa tu API Key en el menú lateral para cargar datos.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. FUNCIONES DE API Y SIMULACION
# -----------------------------------------------------------------------------
@st.cache_data(ttl=900)
def obtener_partidos(key, sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
    params = {
        "apiKey": key,
        "regions": "eu,us",
        "markets": "h2h",
        "dateFormat": "iso"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None

def calcular_probabilidades(odd_h, odd_d, odd_a):
    if not (odd_h and odd_d and odd_a):
        return 0.45, 0.25, 0.30 # Valores por defecto si la casa aún no publica cuotas
    p_h, p_d, p_a = 1/odd_h, 1/odd_d, 1/odd_a
    total = p_h + p_d + p_a
    return p_h/total, p_d/total, p_a/total

def simulacion_poisson(prob_h, prob_a):
    exp_h = max(0.5, prob_h * 2.8)
    exp_a = max(0.5, prob_a * 2.4)
    matriz = np.zeros((6, 6))
    for i in range(6):
        for j in range(6):
            matriz[i][j] = poisson.pmf(i, exp_h) * poisson.pmf(j, exp_a)
    return exp_h, exp_a, matriz

# -----------------------------------------------------------------------------
# 3. PROCESAMIENTO DE PARTIDOS
# -----------------------------------------------------------------------------
eventos = obtener_partidos(api_key, sport_key)

if not eventos:
    st.warning("⚠️ No se pudieron obtener datos. Verifica tu conexión o API Key.")
else:
    lista_partidos = []
    fecha_limite = datetime.now().astimezone() + timedelta(days=dias_adelante)
    
    for ev in eventos:
        fecha_utc = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        if fecha_utc <= fecha_limite:
            home = ev["home_team"]
            away = ev["away_team"]
            
            odd_h, odd_d, odd_a = None, None, None
            if ev.get("bookmakers"):
                bm = ev["bookmakers"][0]
                for mkt in bm.get("markets", []):
                    if mkt["key"] == "h2h":
                        for out in mkt["outcomes"]:
                            if out["name"] == home: odd_h = out["price"]
                            elif out["name"] == away: odd_a = out["price"]
                            else: odd_d = out["price"]
            
            prob_h, prob_d, prob_a = calcular_probabilidades(odd_h, odd_d, odd_a)
            
            lista_partidos.append({
                "fecha": fecha_utc.strftime("%d/%m/%Y %H:%M"),
                "local": home,
                "visitante": away,
                "odd_h": odd_h if odd_h else 2.0,
                "odd_d": odd_d if odd_d else 3.2,
                "odd_a": odd_a if odd_a else 3.5,
                "prob_h": prob_h,
                "prob_d": prob_d,
                "prob_a": prob_a,
                "etiqueta": f"{fecha_utc.strftime('%d/%m')} | {home} vs {away}"
            })

    if not lista_partidos:
        st.warning(f"No hay encuentros agendados en los próximos {dias_adelante} días para esta liga. Intenta aumentar el rango de días en el menú lateral.")
    else:
        # Pestañas principales de navegación
        tab1, tab2 = st.tabs(["📊 Análisis y Simulador", "🎯 Tracker de Probabilidades / Apuestas"])
        
        with tab1:
            st.subheader(f"📅 Partidos Encontrados ({len(lista_partidos)})")
            partido_sel_label = st.selectbox("Selecciona un partido para analizar:", [p["etiqueta"] for p in lista_partidos])
            p_sel = next(p for p in lista_partidos if p["etiqueta"] == partido_sel_label)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"🏠 {p_sel['local']}", f"Cuota: {p_sel['odd_h']:.2f}")
                st.progress(p_sel["prob_h"], text=f"Victoria Local: {p_sel['prob_h']*100:.1f}%")
            with col2:
                st.metric("⚖️ Empate", f"Cuota: {p_sel['odd_d']:.2f}")
                st.progress(p_sel["prob_d"], text=f"Empate: {p_sel['prob_d']*100:.1f}%")
            with col3:
                st.metric(f"🚀 {p_sel['visitante']}", f"Cuota: {p_sel['odd_a']:.2f}")
                st.progress(p_sel["prob_a"], text=f"Victoria Visita: {p_sel['prob_a']*100:.1f}%")
            
            # Algoritmo de Poisson
            exp_h, exp_a, matriz = simulacion_poisson(p_sel["prob_h"], p_sel["prob_a"])
            idx = np.unravel_index(np.argmax(matriz), matriz.shape)
            
            st.markdown("---")
            st.subheader("🤖 Pronóstico y Guardado")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.success(f"**Marcador Probable:** {idx[0]} - {idx[1]} ({matriz[idx[0]][idx[1]]*100:.1f}% probabilidad)")
                st.info(f"**Expectativa de Goles (xG):** {p_sel['local']} ({exp_h:.2f}) - {p_sel['visitante']} ({exp_a:.2f})")
            
            with col_p2:
                st.markdown("#### 📝 Guardar en Tracker")
                pick_opciones = [f"Gana {p_sel['local']}", "Empate", f"Gana {p_sel['visitante']}", f"Marcador Exacto {idx[0]}-{idx[1]}"]
                pick_elegido = st.selectbox("Selección sugerida:", pick_opciones)
                monto_apuesta = st.number_input("Monto / Unidades apostadas:", min_value=1.0, value=10.0, step=5.0)
                
                if st.button("➕ Añadir al Tracker"):
                    st.session_state["bets_tracker"].append({
                        "Fecha": p_sel["fecha"],
                        "Partido": f"{p_sel['local']} vs {p_sel['visitante']}",
                        "Pick": pick_elegido,
                        "Monto": monto_apuesta,
                        "Estado": "Pendiente"
                    })
                    st.success("¡Pronóstico guardado en tu Tracker!")

        with tab2:
            st.subheader("🎯 Seguimiento de Resultados (Tracker)")
            if not st.session_state["bets_tracker"]:
                st.info("Aún no has guardado pronósticos. Ve a la pestaña 'Análisis y Simulador' para agregar partidos.")
            else:
                df_tracker = pd.DataFrame(st.session_state["bets_tracker"])
                
                # Permite editar el estado directamente (Ganada, Perdida, Pendiente)
                edited_df = st.data_editor(
                    df_tracker,
                    column_config={
                        "Estado": st.column_config.SelectboxColumn(
                            "Estado del Pronóstico",
                            options=["Pendiente", "Ganada", "Perdida"],
                            required=True
                        )
                    },
                    use_container_width=True,
                    num_rows="dynamic"
                )
                
                # Actualizar la sesión
                st.session_state["bets_tracker"] = edited_df.to_dict("records")
                
                # Métricas del Tracker
                ganadas = sum(1 for b in st.session_state["bets_tracker"] if b["Estado"] == "Ganada")
                total_finalizadas = sum(1 for b in st.session_state["bets_tracker"] if b["Estado"] in ["Ganada", "Perdida"])
                win_rate = (ganadas / total_finalizadas * 100) if total_finalizadas > 0 else 0.0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Pronósticos Ganados", f"{ganadas} / {total_finalizadas}")
                m2.metric("% Efectividad (Win Rate)", f"{win_rate:.1f}%")
                m3.metric("Pendientes", sum(1 for b in st.session_state["bets_tracker"] if b["Estado"] == "Pendiente"))
