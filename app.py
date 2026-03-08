import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe
import secrets
import unicodedata
import os
import streamlit.components.v1 as components
from io import BytesIO

# Librerías para PDF
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="TONUCOS Gestor", layout="wide")

# --- FUNCIONES NÚCLEO ---

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', texto)
                  if unicodedata.category(c) != 'Mn')

def conectar_google_sheet(nombre_archivo):
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        s = st.secrets["gcp_service_account"]
        p_key = s["private_key"].replace("\\n", "\n")
        creds_info = {
            "type": s["type"], "project_id": s["project_id"],
            "private_key_id": s["private_key_id"], "private_key": p_key,
            "client_email": s["client_email"], "client_id": s["client_id"],
            "auth_uri": s["auth_uri"], "token_uri": s["token_uri"],
            "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
            "client_x509_cert_url": s["client_x509_cert_url"]
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        return client.open(nombre_archivo).worksheet("Invitados")
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def cargar_datos(archivo):
    sheet = conectar_google_sheet(archivo)
    cols = ["ID", "Mesa", "Nombre", "Categoria", "Observaciones", "Asistio"]
    if sheet:
        try:
            datos = sheet.get_all_records()
            if not datos: return pd.DataFrame(columns=cols)
            df = pd.DataFrame(datos)
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            for col in cols:
                if col not in df.columns: df[col] = ""
            return df.fillna("")
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def guardar_datos(df_to_save, archivo):
    sheet = conectar_google_sheet(archivo)
    if sheet:
        sheet.clear()
        df_final = df_to_save.drop(columns=['Mesa_Num', 'Mesa_Int'], errors='ignore')
        set_with_dataframe(sheet, df_final)

# --- FUNCIÓN GENERAR PDF ---
def generar_pdf(df, titulo_evento, orden="mesa"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título personalizado
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=18, spaceAfter=20)
    elements.append(Paragraph(f"LISTA DE INVITADOS: {titulo_evento.upper()}", title_style))
    
    # Lógica de Ordenamiento
    df_pdf = df.copy()
    if orden == "mesa":
        df_pdf['Mesa_Int'] = pd.to_numeric(df_pdf['Mesa'], errors='coerce').fillna(0).astype(int)
        df_pdf = df_pdf.sort_values(by=['Mesa_Int', 'Nombre'])
        elements.append(Paragraph("Ordenado por: Número de Mesa", styles['Normal']))
    else:
        df_pdf = df_pdf.sort_values(by='Nombre')
        elements.append(Paragraph("Ordenado por: Orden Alfabético", styles['Normal']))
    
    elements.append(Spacer(1, 12))

    # Preparar tabla
    data = [["Mesa", "Invitado", "Categoría", "Observaciones"]]
    for _, row in df_pdf.iterrows():
        data.append([row['Mesa'], row['Nombre'], row['Categoria'], row['Observaciones']])

    # Estilo de la tabla
    t = Table(data, colWidths=[40, 220, 80, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

# --- DISEÑO CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #cfd8dc; } 
    .block-container { padding-top: 1rem !important; }
    .total-black { background-color: #000; color: #fff; padding: 5px; border-radius: 4px; text-align: center; }
    .total-grey { background-color: #ffffff; border: 2px solid #000; padding: 5px; border-radius: 4px; text-align: center; color: #000; font-weight: bold; }
    .mesa-header { background-color: #000; color: #fff; padding: 6px 15px; font-weight: bold; margin-top: 15px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
    .event-title { text-align: center; font-size: 24px; font-weight: bold; color: #000; margin-bottom: 10px; text-transform: uppercase; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- LOGIN ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.write("<br><br>", unsafe_allow_html=True)
        with st.form("login"):
            st.subheader("🔒 Acceso al Gestor")
            pw = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                if pw == st.secrets["access"]["password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Incorrecta")
    return False

if check_password():
    # --- LÓGICA EVENTO ---
    query_params = st.query_params
    nombre_evento = query_params.get("id", "Boda Juan y Marta").replace("_", " ")

    if 'df' not in st.session_state or st.session_state.get('last_event') != nombre_evento:
        st.session_state.df = cargar_datos(nombre_evento)
        st.session_state.last_event = nombre_evento

    if "focus_key" not in st.session_state: st.session_state.focus_key = 0

    # --- CABECERA ---
    c_l, c_c, c_r = st.columns([1, 1, 1])
    with c_c:
        if os.path.exists("logonegro.jpg"): st.image("logonegro.jpg", width=120)
    st.markdown(f"<div class='event-title'>{nombre_evento}</div>", unsafe_allow_html=True)

    # --- PANEL TOTALES ---
    df_full = st.session_state.df
    if not df_full.empty:
        mesas_cont = df_full[df_full['Mesa'].astype(str).str.strip() != "0"]['Mesa'].nunique()
        t_cols = st.columns(6)
        t_labels = [("MESAS", mesas_cont, "grey"), ("TOTAL", len(df_full), "black"), 
                    ("MAYOR", len(df_full[df_full['Categoria']=='MAYOR']), "grey"),
                    ("ADOL.", len(df_full[df_full['Categoria']=='ADOLESCENTE']), "grey"),
                    ("MENOR", len(df_full[df_full['Categoria']=='MENOR']), "grey"),
                    ("BEBÉ", len(df_full[df_full['Categoria']=='BEBÉ']), "grey")]
        for i, (lab, val, style) in enumerate(t_labels):
            t_cols[i].markdown(f"<div class='total-{style}'><small>{lab}</small><br><b>{val}</b></div>", unsafe_allow_html=True)

    # --- FORMULARIO ---
    with st.expander("➕ AÑADIR NUEVO INVITADO", expanded=True):
        with st.form("alta_form", clear_on_submit=True):
            r1, r2 = st.columns([1, 3])
            f_m = r1.number_input("N° MESA", min_value=0, step=1, format="%d", key=f"foc_{st.session_state.focus_key}")
            f_n = r2.text_input("APELLIDO y nombre")
            r3, r4 = st.columns(2)
            f_c = r3.selectbox("CATEGORÍA", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"])
            f_o = r4.text_input("OBSERVACIONES")
            if st.form_submit_button("📥 AÑADIR", use_container_width=True):
                if f_n:
                    nuevo = pd.DataFrame([{"ID": secrets.token_hex(3).upper(), "Mesa": str(int(f_m)), 
                                          "Nombre": f_n.upper(), "Categoria": f_c, "Observaciones": f_o.upper(), "Asistio": "NO"}])
                    st.session_state.df = pd.concat([st.session_state.df, nuevo], ignore_index=True)
                    guardar_datos(st.session_state.df, nombre_evento)
                    st.session_state.focus_key += 1
                    st.rerun()

    # --- BUSCADOR Y EXPORTACIÓN ---
    st.markdown("---")
    b_col1, b_col2, b_col3, b_col4 = st.columns([2, 1, 1, 1])
    
    with b_col1:
        busqueda = normalizar_texto(st.text_input("🔍 BUSCAR INVITADO"))
    
    with b_col2:
        st.write("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        if st.button("💾 GUARDAR", use_container_width=True):
            guardar_datos(st.session_state.df, nombre_evento)
            st.toast("¡Guardado!")

    with b_col3:
        st.write("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        pdf_mesa = generar_pdf(st.session_state.df, nombre_evento, "mesa")
        st.download_button("📄 PDF x MESA", pdf_mesa, f"Mesa_{nombre_evento}.pdf", "application/pdf", use_container_width=True)

    with b_col4:
        st.write("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        pdf_alfa = generar_pdf(st.session_state.df, nombre_evento, "alfa")
        st.download_button("📄 PDF ALFA", pdf_alfa, f"Alfa_{nombre_evento}.pdf", "application/pdf", use_container_width=True)

    # --- LISTADO ---
    def actualizar_celda(index, columna, nueva_clave):
        if nueva_clave in st.session_state:
            valor = st.session_state[nueva_clave]
            if columna == "Nombre": valor = str(valor).upper()
            st.session_state.df.at[index, columna] = valor

    df_list = st.session_state.df.copy()
    if busqueda:
        df_list = df_list[df_list['Nombre'].apply(lambda x: busqueda in normalizar_texto(x))]

    if not df_list.empty:
        df_list['Mesa_Int'] = pd.to_numeric(df_list['Mesa'], errors='coerce').fillna(0).astype(int)
        color_map = {"MAYOR": "#ced4da", "ADOLESCENTE": "#90cdf4", "MENOR": "#9ae6b4", "BEBÉ": "#feb2b2"}

        for mesa_num in sorted(df_list['Mesa_Int'].unique()):
            sub_df = df_list[df_list['Mesa_Int'] == mesa_num]
            st.markdown(f"<div class='mesa-header'><span>🪑 MESA {mesa_num}</span></div>", unsafe_allow_html=True)
            for idx, row in sub_df.iterrows():
                c1, c2, c3, c4, c5 = st.columns([0.6, 2.5, 1.5, 1.5, 0.4])
                with c1: st.text_input(f"m_{idx}", row['Mesa'], key=f"mi_{idx}", label_visibility="collapsed", on_change=actualizar_celda, args=(idx, "Mesa", f"mi_{idx}"))
                with c2: st.text_input(f"n_{idx}", row['Nombre'], key=f"ni_{idx}", label_visibility="collapsed", on_change=actualizar_celda, args=(idx, "Nombre", f"ni_{idx}"))
                with c3: st.selectbox(f"cat_{idx}", ["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"], index=["MAYOR", "ADOLESCENTE", "MENOR", "BEBÉ"].index(row['Categoria']), label_visibility="collapsed", key=f"sel_{idx}", on_change=actualizar_celda, args=(idx, "Categoria", f"sel_{idx}"))
                with c4: st.text_input(f"o_{idx}", row['Observaciones'], key=f"oi_{idx}", label_visibility="collapsed", on_change=actualizar_celda, args=(idx, "Observaciones", f"oi_{idx}"))
                with c5:
                    if st.button("🗑️", key=f"di_{idx}"):
                        st.session_state.df = st.session_state.df.drop(idx)
                        guardar_datos(st.session_state.df, nombre_evento)
                        st.rerun()

    # Botón cerrar sesión al final
    st.sidebar.write("---")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.rerun()

    components.html("""<script>
        function setFocus() {
            var inputs = window.parent.document.querySelectorAll('input');
            if (inputs.length > 0) { inputs[0].focus(); inputs[0].select(); }
        }
        setTimeout(setFocus, 350);
    </script>""", height=0)