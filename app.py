import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import secrets
import os
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="TONUCOS Gestor", layout="wide")

# --- CSS DE DISEÑO COMPACTO E INDUSTRIAL ---
st.markdown("""
    <style>
    .stApp { background-color: #cfd8dc; }
    .block-container { 
        padding-top: 0rem !important; 
        padding-bottom: 0rem !important;
        max-width: 95% !important;
    }
    header { visibility: hidden; }
    
    .logo-container {
        display: flex;
        justify-content: center;
        margin-top: -20px;
    }

    /* Etiquetas Negras y Fuertes */
    label, .stMarkdown p, .stSelectbox label, .stTextInput label {
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        margin-bottom: 0px !important;
    }
    
    /* Totales Gris Oscuro */
    .total-card { 
        background-color: #263238;
        color: #ffffff; 
        padding: 5px; 
        border-radius: 4px; 
        text-align: center;
        border: 1px solid #000;
    }
    .total-card b { font-size: 16px; color: #fff; }
    .total-card small { font-size: 9px; text-transform: uppercase; color: #cfd8dc; }

    /* REDUCCIÓN DE ESPACIOS (Lo que pediste) */
    .st-emotion-cache-18ni7ve { margin-top: 0px !important; } /* Espacio entre widgets */
    hr { margin: 5px 0px !important; border-top: 1px solid #263238 !important; } /* Línea separadora fina */

    /* Cabeceras de Mesa pegadas */
    .mesa-header { 
        background-color: #000; color: #fff; padding: 4px 10px; 
        font-weight: bold; margin-top: 2px !important; border-radius: 4px; 
        display: flex; justify-content: space-between; align-items: center; 
        font-size: 13px;
    }
    .pers-label { background-color: #fff; color: #000; padding: 0px 6px; border-radius: 8px; font-size: 10px; }

    /* Inputs más compactos */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        border: 2px solid #263238 !important;
        background-color: #ffffff !important;
        height: 32px !important;
    }

    .event-title { text-align: center; font-size: 20px; font-weight: 900; color: #263238; margin-bottom: 5px; }
    #MainMenu, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES NÚCLEO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct: return True
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        st.markdown("<h3 style='text-align:center;'>SISTEMA TONUCOS</h3>", unsafe_allow_html=True)
        pw = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            if pw == st.secrets["access"]["password"]:
                st.session_state.password_correct = True
                st.rerun()
            else: st.error("Clave Incorrecta")
    return False

def conectar_google_sheet(nombre_archivo):
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        s = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(s), scope)
        client = gspread.authorize(creds)
        return client.open(nombre_archivo).worksheet("Invitados")
    except: return None

def cargar_datos(archivo):
    sheet = conectar_google_sheet(archivo)
    if sheet:
        try:
            df = get_as_dataframe(sheet, evaluate_formulas=True, dtype=str).dropna(how='all')
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            for col in ["ID", "Mesa", "Nombre", "Categoria", "Observaciones", "Asistio"]:
                if col not in df.columns: df[col] = ""
            return df.fillna("")
        except: return pd.DataFrame(columns=["ID", "Mesa", "Nombre", "Categoria", "Observaciones", "Asistio"])
    return pd.DataFrame()

def guardar_datos(df_to_save, archivo):
    sheet = conectar_google_sheet(archivo)
    if sheet:
        sheet.clear()
        set_with_dataframe(sheet, df_to_save)

# --- LOGICA DE LA APP ---
if check_password():
    nombre_evento = st.query_params.get("id", "Boda Juan y Marta").replace("_", " ")

    if 'df' not in st.session_state or st.session_state.get('last_event') != nombre_evento:
        st.session_state.df = cargar_datos(nombre_evento)
        st.session_state.last_event = nombre_evento
    
    if "focus_key" not in st.session_state: st.session_state.focus_key = 0

    # LOGO Y TITULO
    st.markdown("<div class='logo-container'>", unsafe_allow_html=True)
    if os.path.exists("logonegro.jpg"): st.image("logonegro.jpg", width=250)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='event-title'>{nombre_evento}</div>", unsafe_allow_html=True)

    # TOTALES COMPACTOS
    df_f = st.session_state.df
    if not df_f.empty:
        t_cols = st.columns(6)
        stats = [("Total", len(df_f)), 
                 ("Mesas", df_f[df_f['Mesa'].astype(str).str.strip() != "0"]['Mesa'].nunique()),
                 ("Mayor", len(df_f[df_f['Categoria']=='MAYOR'])),
                 ("Adol.", len(df_f[df_f['Categoria']=='ADOLESCENTE'])),
                 ("Menor", len(df_f[df_f['Categoria']=='MENOR'])),
                 ("Bebé", len(df_f[df_f['Categoria']=='BEBÉ']))]
        for i, (l, v) in enumerate(stats):
            t_cols[i].markdown(f"<div class='total-card'><small>{l}</small><br><b>{v}</b></div>", unsafe_allow_html=True)

    # FORMULARIO
    with st.expander("➕ AÑADIR REGISTRO", expanded=True):
        with st.form("alta", clear_on_submit=True):
            c1, c2 = st.columns([1, 3])
            f_m = c1.number_input("MESA", min_value=0, step=1, key=f"f_{st.session_state.focus_key}")
            f_n = c2.text_input("APELLIDO y nombre")
            c3, c4 = st.columns(2)
            f_c = c3.selectbox("CATEGORÍA", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"])
            f_o = c4.text_input("OBSERVACIONES")
            if st.form_submit_button("📥 GUARDAR INVITADO", use_container_width=True):
                if f_n:
                    nuevo = pd.DataFrame([{"ID": secrets.token_hex(3).upper(), "Mesa": str(int(f_m)), "Nombre": f_n.upper(), "Categoria": f_c, "Observaciones": f_o.upper(), "Asistio": "NO"}])
                    st.session_state.df = pd.concat([st.session_state.df, nuevo], ignore_index=True)
                    guardar_datos(st.session_state.df, nombre_evento)
                    st.session_state.focus_key += 1
                    st.rerun()

    # AUTOFOCO
    components.html(f"<script>setTimeout(function(){{ window.parent.document.querySelectorAll('input')[0].focus(); }}, 300);</script>", height=0)

    # BUSCADOR Y GUARDAR (UNIDOS)
    st.markdown("<hr>", unsafe_allow_html=True)
    bc1, bc2 = st.columns([3, 1])
    with bc1: s_q = st.text_input("🔍 BUSCAR", placeholder="Nombre...").upper()
    with bc2: 
        st.write("<div style='margin-top:18px'></div>", unsafe_allow_html=True)
        if st.button("💾 GUARDAR", use_container_width=True):
            guardar_datos(st.session_state.df, nombre_evento)
            st.toast("¡Sincronizado!")

    # LISTADO COMPACTO
    df_v = st.session_state.df.copy()
    if s_q: df_v = df_v[df_v['Nombre'].str.contains(s_q, na=False)]

    if not df_v.empty:
        df_v['M_Int'] = pd.to_numeric(df_v['Mesa'], errors='coerce').fillna(0).astype(int)
        cat_colors = {"MAYOR": "#ced4da", "ADOLESCENTE": "#90cdf4", "MENOR": "#9ae6b4", "BEBÉ": "#feb2b2"}
        
        for mesa in sorted(df_v['M_Int'].unique()):
            sub = df_v[df_v['M_Int'] == mesa]
            st.markdown(f"<div class='mesa-header'><span>🪑 MESA {mesa}</span><span class='pers-label'>{len(sub)} PERS.</span></div>", unsafe_allow_html=True)
            for idx, row in sub.iterrows():
                l1, l2, l3, l4, l5 = st.columns([0.6, 2.5, 1.5, 1.5, 0.4])
                
                new_mesa = l1.text_input(f"m_{idx}", row['Mesa'], label_visibility="collapsed")
                new_nome = l2.text_input(f"n_{idx}", row['Nombre'], label_visibility="collapsed")
                
                bg = cat_colors.get(row['Categoria'], "#fff")
                st.markdown(f'<style>div[data-baseweb="select"]:has(input[aria-label*="c_{idx}"]) {{ background-color: {bg} !important; }}</style>', unsafe_allow_html=True)
                new_cat = l3.selectbox(f"c_{idx}", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"], index=["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"].index(row['Categoria']), label_visibility="collapsed")
                
                new_obs = l4.text_input(f"o_{idx}", row['Observaciones'], label_visibility="collapsed")
                
                if l5.button("🗑️", key=f"d_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx)
                    guardar_datos(st.session_state.df, nombre_evento)
                    st.rerun()
                
                st.session_state.df.at[idx, 'Mesa'] = new_mesa
                st.session_state.df.at[idx, 'Nombre'] = new_nome.upper()
                st.session_state.df.at[idx, 'Categoria'] = new_cat
                st.session_state.df.at[idx, 'Observaciones'] = new_obs.upper()