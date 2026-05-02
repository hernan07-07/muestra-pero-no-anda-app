import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import secrets
import os
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN
st.set_page_config(page_title="TONUCOS Gestor", layout="wide")

# --- NUESTRO CSS DE SIEMPRE (Mantenemos la estética y los colores) ---
st.markdown("""
    <style>
    .stApp { background-color: #cfd8dc; }
    .block-container { padding-top: 0rem !important; max-width: 95% !important; }
    header { visibility: hidden; }
    
    input { caret-color: #ff0000 !important; } 
    .stTextInput input:focus {
        border: 2px solid #1e88e5 !important;
        box-shadow: 0 0 5px rgba(30, 136, 229, 0.5) !important;
    }

    /* Fix Desplegables */
    div[data-baseweb="popover"], ul[role="listbox"] { background-color: #ffffff !important; }
    li[role="option"] span { color: #000000 !important; font-weight: 800 !important; }
    li[role="option"]:hover { background-color: #263238 !important; }

    /* Etiquetas */
    label, .stMarkdown p { color: #000000 !important; font-weight: 800 !important; }
    .stTextInput input { border: 2px solid #263238 !important; background-color: #ffffff !important; color: #000000 !important; }

    /* Estética General */
    .logo-container { display: flex; justify-content: center; margin-top: -15px; }
    .event-title { text-align: center; font-size: 20px; font-weight: 900; color: #263238; margin-top: -10px; margin-bottom: 5px; }
    .total-card { background-color: #263238; color: #ffffff; padding: 5px; border-radius: 4px; text-align: center; border: 1px solid #000; }
    .total-card b { font-size: 16px; }
    hr { margin: 2px 0px !important; border-top: 1px solid #263238 !important; }
    .mesa-header { background-color: #000; color: #fff; padding: 4px 10px; font-weight: bold; margin-top: 5px !important; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
    .pers-label { background-color: #fff; color: #000; padding: 0px 6px; border-radius: 8px; font-size: 10px; }
    
    div.row-widget.stRadio > div { flex-direction: row; justify-content: center; }
    #MainMenu, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE DATOS ---
def conectar_google_sheet(nombre_archivo):
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        s = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(s), scope)
        return gspread.authorize(creds).open(nombre_archivo).worksheet("Invitados")
    except: return None

def cargar_datos(archivo):
    sheet = conectar_google_sheet(archivo)
    if sheet:
        df = get_as_dataframe(sheet, evaluate_formulas=True, dtype=str).dropna(how='all')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        for col in ["ID", "Mesa", "Nombre", "Categoria", "Observaciones", "Asistio"]:
            if col not in df.columns: df[col] = ""
        return df.fillna("")
    return pd.DataFrame()

def guardar_datos(df_to_save, archivo):
    sheet = conectar_google_sheet(archivo)
    if sheet: sheet.clear(); set_with_dataframe(sheet, df_to_save)

# --- INICIO APP ---
nombre_evento = st.query_params.get("id", "Boda Juan y Marta").replace("_", " ")

if 'df' not in st.session_state:
    st.session_state.df = cargar_datos(nombre_evento)
    st.session_state.focus_key = 0

# LOGO Y TITULO
st.markdown("<div class='logo-container'>", unsafe_allow_html=True)
if os.path.exists("logonegro.jpg"): st.image("logonegro.jpg", width=220)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown(f"<div class='event-title'>{nombre_evento}</div>", unsafe_allow_html=True)

# TOTALES
df_f = st.session_state.df
if not df_f.empty:
    t_cols = st.columns(6)
    stats = [("Total", len(df_f)), ("Mesas", df_f[df_f['Mesa'].astype(str).str.strip() != "0"]['Mesa'].nunique()), ("Mayor", len(df_f[df_f['Categoria']=='MAYOR'])), ("Adol.", len(df_f[df_f['Categoria']=='ADOLESCENTE'])), ("Menor", len(df_f[df_f['Categoria']=='MENOR'])), ("Bebé", len(df_f[df_f['Categoria']=='BEBÉ']))]
    for i, (l, v) in enumerate(stats):
        t_cols[i].markdown(f"<div class='total-card'><small>{l}</small><br><b>{v}</b></div>", unsafe_allow_html=True)

# ... (Mantené todo tu código de arriba igual: CSS, Funciones, etc.) ...

# --- SECCIÓN: AÑADIR REGISTRO ---
with st.expander("➕ AÑADIR REGISTRO", expanded=True):
    c1, c2, c3, c4, c5 = st.columns([0.6, 2.5, 1.5, 1.5, 0.4])
    
    # IMPORTANTE: Le puse etiquetas simples "M", "N", etc.
    f_m = c1.text_input("M", placeholder="MESA", key=f"f_m_{st.session_state.focus_key}", label_visibility="collapsed")
    f_n = c2.text_input("N", placeholder="APELLIDO y nombre", key=f"f_n_{st.session_state.focus_key}", label_visibility="collapsed")
    f_c = c3.selectbox("C", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"], key=f"f_c_{st.session_state.focus_key}", label_visibility="collapsed")
    f_o = c4.text_input("O", placeholder="Observaciones", key=f"f_o_{st.session_state.focus_key}", label_visibility="collapsed")
    
    if c5.button("💾", key="btn_add"):
        if f_n:
            nuevo = pd.DataFrame([{"ID": secrets.token_hex(3).upper(), "Mesa": f_m, "Nombre": f_n.upper(), "Categoria": f_c, "Observaciones": f_o.upper(), "Asistio": "NO"}])
            st.session_state.df = pd.concat([st.session_state.df, nuevo], ignore_index=True)
            guardar_datos(st.session_state.df, nombre_evento)
            
            # Subimos el contador para limpiar campos
            st.session_state.focus_key += 1
            st.rerun()

# --- SCRIPT DE FOCO "NINJA" (Copia esto tal cual) ---
components.html(f"""
    <script>
    const focusMesa = () => {{
        // Accedemos al documento principal desde el iframe de Streamlit
        const mainDoc = window.parent.document;
        
        // Buscamos TODOS los inputs
        const inputs = Array.from(mainDoc.querySelectorAll('input'));
        
        // Buscamos específicamente el que tiene el placeholder "MESA"
        const target = inputs.find(i => i.placeholder === 'MESA');

        if (target) {{
            target.focus();
            target.click(); // Algunos celulares necesitan el click para abrir teclado
            
            // Si tiene un valor (como un 0), lo seleccionamos para sobreescribir rápido
            if (target.value !== "") {{
                target.setSelectionRange(0, target.value.length);
            }}
        }}
    }};

    // Intentos repetidos en milisegundos clave para ganarle a la carga del celular
    setTimeout(focusMesa, 200);  
    setTimeout(focusMesa, 500);  
    setTimeout(focusMesa, 1000); 
    </script>
""", height=0)

# ... (El resto del listado sigue igual) ...

# BUSCADOR
bc1, bc2, bc3 = st.columns([2, 1.5, 1])
with bc1: s_q = st.text_input("🔍 BUSCAR", placeholder="Nombre...").upper()
with bc2: 
    st.write("<div style='margin-top:22px'></div>", unsafe_allow_html=True)
    orden_vista = st.radio("ORDEN", ["🪑 Mesas", "🔤 A-Z"], label_visibility="collapsed", horizontal=True)
with bc3: 
    st.write("<div style='margin-top:22px'></div>", unsafe_allow_html=True)
    if st.button("💾 GUARDAR", use_container_width=True):
        guardar_datos(st.session_state.df, nombre_evento)
        st.toast("¡Sincronizado!")

# LISTADO (Mantenemos tu lógica de Mesas / A-Z)
df_v = st.session_state.df.copy()
if s_q: df_v = df_v[df_v['Nombre'].str.contains(s_q, na=False)]

if not df_v.empty:
    df_v['M_Int'] = pd.to_numeric(df_v['Mesa'], errors='coerce').fillna(0).astype(int)
    cat_colors = {"MAYOR": "#ced4da", "ADOLESCENTE": "#90cdf4", "MENOR": "#9ae6b4", "BEBÉ": "#feb2b2"}
    
    if orden_vista == "🪑 Mesas":
        for mesa in sorted(df_v['M_Int'].unique()):
            sub = df_v[df_v['M_Int'] == mesa]
            st.markdown(f"<div class='mesa-header'><span>🪑 MESA {mesa}</span><span class='pers-label'>{len(sub)} PERS.</span></div>", unsafe_allow_html=True)
            for idx, row in sub.iterrows():
                l1, l2, l3, l4, l5 = st.columns([0.6, 2.5, 1.5, 1.5, 0.4])
                st.session_state.df.at[idx, 'Mesa'] = l1.text_input(f"m_{idx}", row['Mesa'], label_visibility="collapsed")
                st.session_state.df.at[idx, 'Nombre'] = l2.text_input(f"n_{idx}", row['Nombre'], label_visibility="collapsed").upper()
                st.session_state.df.at[idx, 'Categoria'] = l3.selectbox(f"c_{idx}", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"], index=["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"].index(row['Categoria']), label_visibility="collapsed")
                st.session_state.df.at[idx, 'Observaciones'] = l4.text_input(f"o_{idx}", row['Observaciones'], label_visibility="collapsed").upper()
                if l5.button("🗑️", key=f"d_{idx}"):
                    st.session_state.df = st.session_state.df.drop(idx); guardar_datos(st.session_state.df, nombre_evento); st.rerun()
    else:
        # Lógica A-Z simplificada
        df_az = df_v.sort_values("Nombre")
        st.markdown(f"<div class='mesa-header'><span>🔤 ORDEN ALFABÉTICO</span><span class='pers-label'>{len(df_az)} PERS.</span></div>", unsafe_allow_html=True)
        for idx, row in df_az.iterrows():
            l1, l2, l3, l4, l5 = st.columns([0.6, 2.5, 1.5, 1.5, 0.4])
            st.session_state.df.at[idx, 'Mesa'] = l1.text_input(f"ma_{idx}", row['Mesa'], label_visibility="collapsed")
            st.session_state.df.at[idx, 'Nombre'] = l2.text_input(f"na_{idx}", row['Nombre'], label_visibility="collapsed").upper()
            st.session_state.df.at[idx, 'Categoria'] = l3.selectbox(f"ca_{idx}", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"], index=["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"].index(row['Categoria']), label_visibility="collapsed")
            st.session_state.df.at[idx, 'Observaciones'] = l4.text_input(f"oa_{idx}", row['Observaciones'], label_visibility="collapsed").upper()
            if l5.button("🗑️", key=f"da_{idx}"):
                st.session_state.df = st.session_state.df.drop(idx); guardar_datos(st.session_state.df, nombre_evento); st.rerun()