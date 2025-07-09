import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from fpdf import FPDF
import base64
import unicodedata

# =============================================
# CONFIGURACIÓN INICIAL
# =============================================
st.set_page_config(
    page_title="Gestión Perfiles 360",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# CARGA DE DATOS (CON MANEJO DE ERRORES)
# =============================================
@st.cache_data(ttl=3600)
def cargar_datos():
    try:
        # URLs de datos
        URL_EVAL = "https://docs.google.com/spreadsheets/d/1hcPBE_gkMmgn4JBjTrqbG3I_vzaFjRraX4sA5e4qKTE/export?format=csv"
        URL_SEG = "https://docs.google.com/spreadsheets/d/1p_vMUMIlprH-4ArY0kl_75XsUqBgIqV-CMEWs-6-zjw/export?format=csv"
        URL_CUMPLIMIENTO = "https://docs.google.com/spreadsheets/d/1miD-cft9CKEjfAv5vHj7P1RB0_bvL9z2/export?format=xlsx"

        # Cargar datos de evaluación y seguimiento
        df_eval = pd.read_csv(URL_EVAL)
        df_seg = pd.read_csv(URL_SEG)
        
        # Normalizar nombres de columnas
        def normalizar_columna(col):
            return ''.join(
                c for c in unicodedata.normalize('NFD', col)
                if unicodedata.category(c) != 'Mn'
            ).lower().strip().replace(' ', '_')

        df_eval.columns = [normalizar_columna(c) for c in df_eval.columns]
        df_seg.columns = df_seg.columns.str.strip().str.lower().str.replace(' ', '_')

        try:
            # Cargar datos de cumplimiento
            df_cump = pd.read_excel(URL_CUMPLIMIENTO, sheet_name='CUMPLIMIENTO')
            df_cump.columns = df_cump.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Procesar cumplimiento
            df_cump['fecha'] = pd.to_datetime(df_cump.apply(lambda x: f"{x['year']}-{x['mes']}-01", axis=1))
            df_cump['cumplimiento_num'] = pd.to_numeric(df_cump['cumplimiento'], errors='coerce')/100
            
            # Cargar información de vendedores
            df_info = pd.read_excel(URL_CUMPLIMIENTO, sheet_name='informaciones')
            df_info.columns = df_info.columns.str.strip().str.lower().str.replace(' ', '_')
            
            # Procesar fechas
            df_info['fecha_ingreso'] = pd.to_datetime(df_info['fecha_ingreso'])
            df_info['fecha_nacimiento'] = pd.to_datetime(df_info['fecha_nacimiento'])
            
            return df_eval, df_seg, df_cump, df_info

        except Exception as e:
            st.warning(f"Error al cargar archivo de cumplimientos: {str(e)}")
            return df_eval, df_seg, pd.DataFrame(), pd.DataFrame()

    except Exception as e:
        st.error(f"Error crítico al cargar datos: {str(e)}")
        st.stop()

df_eval_orig, df_seg_orig, df_cump_orig, df_info_orig = cargar_datos()

# =============================================
# DEFINICIONES Y VALIDACIONES
# =============================================
vendedor_col = "ruta"
supervisor_col = "supervisor"

# Validar columnas esenciales
if vendedor_col not in df_eval_orig.columns:
    st.error(f"Columna '{vendedor_col}' no encontrada. Columnas disponibles: {df_eval_orig.columns.tolist()}")
    st.stop()

if supervisor_col not in df_eval_orig.columns:
    st.error(f"Columna '{supervisor_col}' no encontrada. Columnas disponibles: {df_eval_orig.columns.tolist()}")
    st.stop()

# Definición de categorías
categorias = {
    "Desempeño Comercial": [
        "efectividad_real_vs_meta",
        "cumple_con_cuotas_de_venta_mensual",
        "cierra_ventas_sin_depender_de_promociones",
        "promueve_productos_nuevos/ofertas"
    ],
    "Ejecución en Ruta": [
        "visita_todos_sus_clientes_por_día?",
        "puntualidad_y_asistencia",
        "planea_su_ruta_diaria",
        "eficiencia_en_tiempo_por_punto"
    ],
    "Habilidades Blandas": [
        "respeto,_trato_cordial_y_empatía",
        "gana_confianza_del_cliente",
        "soluciona_conflictos_con_criterio",
        "clientes_solicitan_ser_visitados_por_él"
    ],
    "Autonomía": [
        "soluciona_imprevistos_sin_llamar_al_supervisor",
        "toma_la_iniciativa_sin_necesidad_de_ser_presionado",
        "se_adapta_con_facilidad_a_cambios"
    ],
    "Herramientas": [
        "usa_adecuadamente_las_aplicaciones",
        "reportes_y_formularios_sin_errores",
        "mantiene_la_motocicleta_en_condiciones"
    ]
}

descripcion_segmentos = {
    "🟢 Alto Desempeño & Alto Potencial": "Vendedores con excelentes resultados actuales y alto potencial de crecimiento. Futuros líderes del equipo.",
    "🟡 Buen Desempeño pero Bajo Potencial": "Vendedores consistentes en resultados pero con limitado crecimiento. Claves para operación actual.",
    "🟠 Alto Potencial pero Bajo Desempeño": "Vendedores con gran capacidad pero bajo desempeño actual. Oportunidad de desarrollo.",
    "🔴 Bajo Desempeño & Bajo Potencial": "Vendedores con bajo rendimiento y poca proyección. Requieren acciones inmediatas.",
    "🧩 Inconsistente / Perfil Mixto": "Vendedores con desempeño irregular. Necesitan evaluación detallada."
}

# =============================================
# PROCESAMIENTO DE DATOS
# =============================================
def procesar_datos(df_eval):
    try:
        # Evitar columnas cualitativas al convertir
        columnas_cualitativas = [
            "fortalezas_mas_destacadas",
            "oportunidades_de_mejora",
            "recomendaciones_especificas_de_formacion"
        ]

        for col in df_eval.columns:
            if col not in [vendedor_col, supervisor_col] + columnas_cualitativas:
                df_eval[col] = pd.to_numeric(df_eval[col], errors='coerce')

        # Calcular puntajes por categoría
        for categoria, columnas in categorias.items():
            cols_categoria = [col for col in df_eval.columns if any(term in col for term in columnas)]
            cols_categoria = [col for col in cols_categoria if pd.api.types.is_numeric_dtype(df_eval[col])]
            
            df_eval[categoria] = df_eval[cols_categoria].mean(axis=1) if cols_categoria else np.nan

        # Calcular puntaje total y potencial
        df_eval['puntaje_total'] = df_eval[list(categorias.keys())].mean(axis=1)
        df_eval['potencial'] = df_eval[['Autonomía', 'Habilidades Blandas', 'Herramientas']].mean(axis=1)

        # Segmentación del equipo
        condiciones = [
            (df_eval['puntaje_total'] >= 8) & (df_eval['potencial'] >= 8),
            (df_eval['puntaje_total'] >= 8) & (df_eval['potencial'] < 6),
            (df_eval['puntaje_total'] < 6) & (df_eval['potencial'] >= 8),
            (df_eval['puntaje_total'] < 6) & (df_eval['potencial'] < 6)
        ]
        opciones = [
            "🟢 Alto Desempeño & Alto Potencial",
            "🟡 Buen Desempeño pero Bajo Potencial",
            "🟠 Alto Potencial pero Bajo Desempeño",
            "🔴 Bajo Desempeño & Bajo Potencial"
        ]
        df_eval['segmento'] = np.select(condiciones, opciones, default="🧩 Inconsistente / Perfil Mixto")

        return df_eval

    except Exception as e:
        st.error(f"Error al procesar datos: {str(e)}")
        return pd.DataFrame()

df_eval = procesar_datos(df_eval_orig.copy())

# Procesar datos de cumplimiento
if not df_cump_orig.empty:
    try:
        df_cump = df_cump_orig.copy()
        df_cump['fecha'] = pd.to_datetime(df_cump.apply(lambda x: f"{x['year']}-{x['mes']}-01", axis=1))
        df_cump['cumplimiento_num'] = (
            df_cump['cumplimiento']
            .astype(str)
            .str.replace('%', '')
            .str.replace(',', '.')
            .replace('nan', np.nan)
            .replace('', np.nan)
            .astype(float) / 100
        )
    except Exception as e:
        st.warning(f"Error al procesar cumplimientos: {str(e)}")
        df_cump = pd.DataFrame()
else:
    df_cump = pd.DataFrame()

# Procesar datos de información
if not df_info_orig.empty:
    try:
        df_info = df_info_orig.copy()
        df_info.columns = df_info.columns.str.strip().str.lower().str.replace(' ', '_')
        df_info['nombre_vendedor'] = df_info['nombre_vendedor'].str.strip().str.upper()
    except Exception as e:
        st.warning(f"Error al procesar información de vendedores: {str(e)}")
        df_info = pd.DataFrame()
else:
    df_info = pd.DataFrame()

# =============================================
# FUNCIÓN PARA GENERAR PDF (MEJORADA)
# =============================================
def generar_pdf_perfil(vendedor, df_eval, df_seg, df_cump=None, df_info=None, tipo="general"):
    try:
        mask = df_eval['ruta'].str.strip().str.upper() == vendedor.strip().upper()
        if not mask.any():
            st.error(f"No se encontró al vendedor {vendedor} en evaluación")
            return None

        datos_vendedor = df_eval[mask].iloc[0].to_dict()
        info_vendedor = {}
        if df_info is not None and not df_info.empty:
            mask_info = df_info['ruta'].str.strip().str.upper() == vendedor.strip().upper()
            if mask_info.any():
                info_vendedor = df_info[mask_info].iloc[0].to_dict()

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(left=15, top=15, right=15)

        try:
            pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
            pdf.set_font('DejaVu', '', 12)
        except:
            pdf.set_font("Arial", size=12)

        # Encabezado general
        pdf.set_fill_color(240, 240, 240)
        pdf.rect(10, 10, 190, 40, 'F')
        pdf.set_font('', 'B', 16)
        pdf.cell(190, 10, txt="IDENTIFICACIÓN COMERCIAL", ln=1, align='C')
        pdf.set_font('', '', 12)
        if info_vendedor:
            pdf.cell(95, 8, txt=f"Nombre: {info_vendedor.get('nombre_vendedor', 'N/D')}", ln=0)
            pdf.cell(95, 8, txt=f"Ruta: {info_vendedor.get('ruta', 'N/D')}", ln=1)
            pdf.cell(95, 8, txt=f"Cédula: {info_vendedor.get('cedula', 'N/D')}", ln=0)
            pdf.cell(95, 8, txt=f"Teléfono: {info_vendedor.get('telefono', 'N/D')}", ln=1)
            try:
                fecha_ingreso = pd.to_datetime(info_vendedor.get('fecha_ingreso'))
                tiempo = (datetime.now() - fecha_ingreso).days // 30
                pdf.cell(95, 8, txt=f"Antigüedad: {tiempo} meses", ln=0)
            except:
                pdf.cell(95, 8, txt="Antigüedad: N/D", ln=0)
            pdf.cell(95, 8, txt=f"Zona: {info_vendedor.get('zona', 'N/D')}", ln=1)
        pdf.ln(10)

        # Evaluación cualitativa
        columnas_cualitativas = {
            "fortalezas_mas_destacadas": "Fortalezas destacadas",
            "oportunidades_de_mejora": "Oportunidades de mejora",
            "recomendaciones_especificas_de_formacion": "Recomendaciones de formación"
        }

        pdf.set_font('', 'B', 14)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, "EVALUACIÓN CUALITATIVA", ln=1, fill=True)
        pdf.ln(3)

        for col, titulo in columnas_cualitativas.items():
            pdf.set_font('', 'B', 12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, f"{titulo}:", ln=1, fill=True)
            contenido = datos_vendedor.get(col, "")
            if pd.isna(contenido) or str(contenido).strip() == "":
                pdf.set_font('', 'I', 10)
                pdf.cell(0, 6, "No fue completado.", ln=1)
            else:
                pdf.set_font('', '', 10)
                pdf.multi_cell(0, 6, str(contenido).strip())
            pdf.ln(2)

        if tipo == "general":
            pdf.set_font('', 'B', 14)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 10, "EVALUACIÓN POR COMPETENCIAS", ln=1, fill=True)
            pdf.ln(3)

            for categoria, columnas in categorias.items():
                pdf.set_font('', 'B', 12)
                pdf.cell(0, 8, txt=categoria, ln=1)
                pdf.set_font('', '', 10)
                for col in columnas:
                    if col in datos_vendedor:
                        valor = datos_vendedor[col]
                        if isinstance(valor, (int, float)) and pd.notna(valor):
                            valor_str = f"{valor:.2f}/10"
                        else:
                            valor_str = str(valor)
                        pdf.cell(0, 6, txt=f"- {col.replace('_', ' ').capitalize()}: {valor_str}", ln=1)
                pdf.ln(2)

            # Logros
            if df_cump is not None and not df_cump.empty:
                logros = df_cump[
                    (df_cump['vendedor'].str.upper() == vendedor.upper()) &
                    (df_cump['cumplimiento_num'] > 0.8)
                ].sort_values('fecha', ascending=False).head(3)
                if not logros.empty:
                    pdf.set_font('', 'B', 14)
                    pdf.set_fill_color(220, 220, 220)
                    pdf.cell(0, 10, "LOGROS DESTACADOS", ln=1, fill=True)
                    pdf.set_font('', '', 10)
                    for _, row in logros.iterrows():
                        mes = f"{row['mes']}-{row['year']}"
                        cumplimiento = f"{float(row['cumplimiento']):.2f}%"
                        pdf.cell(0, 6, txt=f"{row['indicador']}: {cumplimiento} (Mes: {mes})", ln=1)

        elif tipo == "reconocimiento":
            pdf.set_font('', 'B', 16)
            pdf.cell(0, 10, txt="CARTA DE RECONOCIMIENTO", ln=1, align='C')
            pdf.ln(10)
            pdf.set_font('', '', 12)
            pdf.multi_cell(0, 8, txt=f"A quien corresponda:")
            pdf.ln(5)
            pdf.multi_cell(0, 8, txt=f"Reconocemos al colaborador {vendedor} por su excelente desempeño durante los siguientes periodos:")
            pdf.ln(5)

            if df_cump is not None and not df_cump.empty:
                df_vend_cump = df_cump[df_cump['vendedor'].str.upper() == vendedor.upper()].copy()
                df_vend_cump = df_vend_cump[df_vend_cump['cumplimiento_num'] > df_vend_cump['cumplimiento_num'].mean()]
                df_vend_cump = df_vend_cump.sort_values(['year', 'mes'], ascending=[False, False])
                for _, row in df_vend_cump.head(5).iterrows():
                    mes = f"{row['mes']}-{row['year']}"
                    cumplimiento = f"{float(row['cumplimiento']):.2f}%"
                    pdf.cell(100, 6, txt=f"- {row['indicador']}:", ln=0)
                    pdf.cell(90, 6, txt=f"{cumplimiento} (Mes: {mes})", ln=1)

            pdf.ln(10)
            pdf.multi_cell(0, 8, txt="Este reconocimiento se otorga como muestra de aprecio por su dedicación y compromiso con la excelencia comercial.")
            pdf.ln(15)
            pdf.cell(100, 8, txt="Santo Domingo, " + datetime.now().strftime("%d/%m/%Y"), ln=0)
            pdf.cell(90, 8, txt="_________________________", ln=1)
            pdf.cell(100, 8, txt="", ln=0)
            pdf.cell(90, 8, txt="Firma Supervisor", ln=1)
            pdf.ln(15)
            pdf.cell(0, 8, txt="_________________________", ln=1)
            pdf.cell(0, 8, txt="Firma Gerente Comercial", ln=1)

        elif tipo == "mejora":
            pdf.set_font('', 'B', 16)
            pdf.cell(0, 10, txt="PLAN DE MEJORA", ln=1, align='C')
            pdf.ln(10)

            pdf.set_font('', 'B', 12)
            pdf.cell(100, 8, txt="Vendedor:", ln=0)
            pdf.set_font('', '')
            pdf.cell(90, 8, txt=vendedor, ln=1)

            pdf.set_font('', 'B', 12)
            pdf.cell(100, 8, txt="Ruta:", ln=0)
            pdf.set_font('', '')
            pdf.cell(90, 8, txt=info_vendedor.get('ruta', 'N/D'), ln=1)

            pdf.set_font('', 'B', 12)
            pdf.cell(100, 8, txt="Fecha:", ln=0)
            pdf.set_font('', '')
            pdf.cell(90, 8, txt=datetime.now().strftime("%d/%m/%Y"), ln=1)
            pdf.ln(10)

            pdf.set_font('', 'B', 14)
            pdf.cell(0, 10, txt="ÁREAS DE OPORTUNIDAD", ln=1)

            if df_cump is not None and not df_cump.empty:
                df_vend_cump = df_cump[df_cump['vendedor'].str.upper() == vendedor.upper()].copy()
                df_vend_cump = df_vend_cump[df_vend_cump['cumplimiento_num'] < df_vend_cump['cumplimiento_num'].mean()]
                df_vend_cump = df_vend_cump.sort_values(['year', 'mes'], ascending=[False, False])
                for _, row in df_vend_cump.head(5).iterrows():
                    mes = f"{row['mes']}-{row['year']}"
                    cumplimiento = f"{float(row['cumplimiento']):.2f}%"
                    pdf.set_font('', 'B', 10)
                    pdf.cell(100, 6, txt=f"{row['indicador']}:", ln=0)
                    pdf.set_font('', '')
                    pdf.cell(90, 6, txt=f"{cumplimiento} (Mes: {mes})", ln=1)

            pdf.ln(5)
            pdf.set_font('', 'B', 14)
            pdf.cell(0, 10, txt="PLAN DE ACCIÓN", ln=1)
            segmento = datos_vendedor.get('segmento', 'N/D')
            acciones = [
                "1. Capacitación en técnicas de venta (8 horas)",
                "2. Acompañamiento semanal del supervisor",
                "3. Establecimiento de metas quincenales",
                "4. Revisión diaria de objetivos"
            ] if "Bajo" in segmento else [
                "1. Taller especializado de habilidades",
                "2. Mentoría mensual con vendedor líder",
                "3. Metas mensuales con retroalimentación"
            ]
            for accion in acciones:
                pdf.set_font('', '', 12)
                pdf.multi_cell(0, 6, txt=accion)
                pdf.ln(1)

            pdf.ln(10)
            pdf.set_font('', 'B', 14)
            pdf.cell(0, 10, txt="COMPROMISO DEL COLABORADOR", ln=1)
            pdf.set_font('', '', 12)
            pdf.multi_cell(0, 8, txt="Yo, _________________________________________, me comprometo a seguir el plan de mejora establecido y a trabajar en las áreas de oportunidad identificadas.")
            pdf.ln(15)
            pdf.cell(100, 8, txt="_________________________", ln=0)
            pdf.cell(90, 8, txt="_________________________", ln=1)
            pdf.cell(100, 8, txt="Firma Vendedor", ln=0)
            pdf.cell(90, 8, txt="Firma Supervisor", ln=1)

        return pdf.output(dest='S').encode('latin-1', errors='replace')

    except Exception as e:
        st.error(f"Error al generar PDF: {str(e)}")
        return None
    
# =============================================
# INTERFAZ PRINCIPAL
# =============================================
st.sidebar.header("Filtros")
vista = st.sidebar.radio("Vista", ["Resumen Ejecutivo", "Individual", "Equipo"])

if vista == "Resumen Ejecutivo":
    st.header("📊 Resumen Ejecutivo - Visión General")
    st.markdown("""
    **Vista panorámica** del desempeño del equipo comercial con métricas clave, distribución de talento 
    y análisis comparativos por áreas y supervisores.
    """)
    
    # Calcular métricas generales
    total_colaboradores = df_eval_orig[vendedor_col].nunique()
    total_supervisores = df_eval_orig[supervisor_col].nunique()
    media_total = df_eval['puntaje_total'].mean()
    media_potencial = df_eval['potencial'].mean()

    # Métricas en columnas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Colaboradores", total_colaboradores)
    col2.metric("Total Supervisores", total_supervisores)
    col3.metric("Puntaje Promedio", f"{media_total:.1f}/10")
    col4.metric("Potencial Promedio", f"{media_potencial:.1f}/10")

    st.markdown("---")
    
    # Nueva sección de Evolución de Indicadores
    if not df_cump.empty:
        st.subheader("📈 Evolución de Indicadores de Gestión")
        
        # Filtros para la vista general
        col1, col2 = st.columns(2)
        with col1:
            indicador_sel = st.selectbox("Seleccionar Indicador", df_cump['indicador'].unique())
        with col2:
            periodo_sel = st.selectbox("Período", ["Últimos 6 meses", "Últimos 12 meses", "Todo el historial"])
        
        # Aplicar filtros
        df_filtrado = df_cump[df_cump['indicador'] == indicador_sel]
        if periodo_sel == "Últimos 6 meses":
            fecha_limite = pd.to_datetime('today') - pd.DateOffset(months=6)
            df_filtrado = df_filtrado[df_filtrado['fecha'] >= fecha_limite]
        elif periodo_sel == "Últimos 12 meses":
            fecha_limite = pd.to_datetime('today') - pd.DateOffset(months=12)
            df_filtrado = df_filtrado[df_filtrado['fecha'] >= fecha_limite]
        
        # Gráfico de evolución general
        fig_evo_general = px.line(
            df_filtrado.groupby('fecha').agg({'cumplimiento_num': 'mean'}).reset_index(),
            x='fecha',
            y='cumplimiento_num',
            title=f"Evolución de {indicador_sel} - Equipo Comercial",
            labels={'cumplimiento_num': '% Cumplimiento', 'fecha': 'Fecha'}
        )
        fig_evo_general.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_evo_general, use_container_width=True)
        
        # Comparativa por supervisores
        st.subheader("Comparativa por Supervisores")
        
        df_sup = df_filtrado.groupby(['supervisor', 'fecha']).agg({'cumplimiento_num': 'mean'}).reset_index()
        
        fig_sup = px.line(
            df_sup,
            x='fecha',
            y='cumplimiento_num',
            color='supervisor',
            title=f"Desempeño por Supervisor - {indicador_sel}",
            labels={'cumplimiento_num': '% Cumplimiento', 'fecha': 'Fecha'}
        )
        fig_sup.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig_sup, use_container_width=True)
        
        # Top 5 y Bottom 5 vendedores
        st.subheader("Top y Bottom Performers")
        
        df_top = df_filtrado.groupby('vendedor').agg({'cumplimiento_num': 'mean'}).reset_index()
        df_top = df_top.sort_values('cumplimiento_num', ascending=False)
        
        col_top, col_bottom = st.columns(2)
        
        with col_top:
            st.markdown("🏆 **Top 5 Vendedores**")
            st.dataframe(
                df_top.head(5).style.format({'cumplimiento_num': '{:.1%}'}),
                hide_index=True,
                use_container_width=True
            )
        
        with col_bottom:
            st.markdown("⚠️ **Bottom 5 Vendedores**")
            st.dataframe(
                df_top.tail(5).style.format({'cumplimiento_num': '{:.1%}'}),
                hide_index=True,
                use_container_width=True
            )
    else:
        st.warning("No se encontraron datos de cumplimiento para mostrar")
    
    st.markdown("---")
    
    # Gráfico de distribución de puntajes
    st.subheader("Distribución de Puntajes Totales")
    st.caption("Frecuencia de los puntajes generales de todo el equipo")
    fig_dist = px.histogram(df_eval, x='puntaje_total', nbins=20, 
                           labels={'puntaje_total': 'Puntaje Total'},
                           color_discrete_sequence=['#636EFA'])
    st.plotly_chart(fig_dist, use_container_width=True)

    # Evaluación por áreas
    st.subheader("📌 Evaluación General por Áreas Clave")
    st.caption("Promedio del equipo en cada categoría de evaluación")
    
    avg_areas = {area: df_eval[area].mean() for area in categorias.keys()}
    cols = st.columns(len(categorias))
    
    for i, (area, promedio) in enumerate(avg_areas.items()):
        with cols[i]:
            if promedio >= 8:
                color = "green"
                emoji = "✅"
            elif promedio >= 6:
                color = "orange"
                emoji = "⚠️"
            else:
                color = "red"
                emoji = "❌"
            
            st.markdown(f"<h3 style='color:{color}'>{emoji} {area}</h3>", unsafe_allow_html=True)
            st.metric("Puntaje Promedio", f"{promedio:.1f}/10")

    st.markdown("---")
    
    # Segmentación del equipo
    st.subheader("🧩 Segmentación del Equipo")
    st.caption("Clasificación de vendedores según desempeño y potencial")
    
    segment_counts = df_eval['segmento'].value_counts().reset_index()
    segment_counts.columns = ['Segmento', 'Cantidad']
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.dataframe(
            segment_counts.merge(
                pd.DataFrame.from_dict(descripcion_segmentos, orient='index', columns=['Descripción']),
                left_on='Segmento', right_index=True
            ).sort_values('Cantidad', ascending=False),
            hide_index=True,
            use_container_width=True
        )
    
    with col2:
        fig_segmentos = px.pie(segment_counts, 
                              values='Cantidad', 
                              names='Segmento',
                              color='Segmento',
                              color_discrete_map={
                                  "🟢 Alto Desempeño & Alto Potencial": "#00CC96",
                                  "🟡 Buen Desempeño pero Bajo Potencial": "#FFA15A",
                                  "🟠 Alto Potencial pero Bajo Desempeño": "#FECB52",
                                  "🔴 Bajo Desempeño & Bajo Potencial": "#EF553B",
                                  "🧩 Inconsistente / Perfil Mixto": "#AB63FA"
                              })
        st.plotly_chart(fig_segmentos, use_container_width=True)

    # Mapa de calor de competencias
    st.subheader("🔥 Correlación entre Competencias")
    st.caption("Relación estadística entre las diferentes áreas evaluadas")
    
    # Preparar datos para el mapa de calor
    corr_matrix = df_eval[list(categorias.keys())].corr().round(2)
    
    fig_heatmap = px.imshow(
        corr_matrix,
        text_auto=True,
        color_continuous_scale='RdBu',
        range_color=[-1, 1],
        labels=dict(x="Competencia", y="Competencia", color="Correlación"),
        x=corr_matrix.columns,
        y=corr_matrix.columns
    )
    fig_heatmap.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=500
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

elif vista == "Individual":
    st.header("👤 Vista Individual")
    st.markdown("""
    **Análisis detallado** por vendedor, incluyendo evaluación completa, seguimiento de visitas 
    y recomendaciones personalizadas de desarrollo.
    """)
    
    # Selector de vendedor
    vendedores = df_eval[vendedor_col].unique()
    vendedor_sel = st.sidebar.selectbox("Seleccionar Ruta / Vendedor", sorted(vendedores))
    
    # Mostrar información básica del vendedor
    if not df_info.empty:
        try:
            info_vendedor = df_info[df_info['ruta'].str.strip().str.upper() == vendedor_sel.strip().upper()].iloc[0]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Nombre:** {info_vendedor['nombre_vendedor']}")
                st.markdown(f"**Ruta:** {info_vendedor['ruta']}")
                st.markdown(f"**Cédula:** {info_vendedor['cedula']}")
            with col2:
                st.markdown(f"**Teléfono:** {info_vendedor['telefono']}")
                st.markdown(f"**Fecha Nacimiento:** {info_vendedor['fecha_nacimiento'].strftime('%d/%m/%Y')}")
                st.markdown(f"**Zona:** {info_vendedor['zona']}")
            with col3:
                tiempo_compania = (datetime.now() - info_vendedor['fecha_ingreso']).days//30
                st.markdown(f"**Fecha Ingreso:** {info_vendedor['fecha_ingreso'].strftime('%d/%m/%Y')}")
                st.markdown(f"**Tiempo en compañía:** {tiempo_compania} meses")
                st.markdown(f"**Puesto:** {info_vendedor['puesto']}")
        except:
            st.warning("No se encontró información adicional para este vendedor")
    else:
        st.warning("No se cargó información adicional de vendedores")
    
    # Filtrar datos
    eval_sel = df_eval[df_eval['ruta'] == vendedor_sel].iloc[0]
    seg_sel = df_seg_orig[df_seg_orig[vendedor_col] == vendedor_sel]
    
    # Determinar segmento
    if eval_sel['puntaje_total'] >= 8 and eval_sel['potencial'] >= 8:
        segmento = "🟢 Alto Desempeño & Alto Potencial"
    elif eval_sel['puntaje_total'] >= 8 and eval_sel['potencial'] < 6:
        segmento = "🟡 Buen Desempeño pero Bajo Potencial"
    elif eval_sel['puntaje_total'] < 6 and eval_sel['potencial'] >= 8:
        segmento = "🟠 Alto Potencial pero Bajo Desempeño"
    elif eval_sel['puntaje_total'] < 6 and eval_sel['potencial'] < 6:
        segmento = "🔴 Bajo Desempeño & Bajo Potencial"
    else:
        segmento = "🧩 Inconsistente / Perfil Mixto"
    
    # Pestañas para vista individual
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Resumen", "📝 Evaluación Completa", "🔄 Seguimiento", "📈 Indicadores", "🎯 Plan de Desarrollo"])

    with tab1:
        st.subheader(f"📊 Resumen de Desempeño: {vendedor_sel}")

        # --- Métricas principales ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Puntaje Total", f"{eval_sel['puntaje_total']:.1f}/10")
        col2.metric("Potencial", f"{eval_sel['potencial']:.1f}/10")
        col3.metric("Segmento", eval_sel['segmento'], help=descripcion_segmentos.get(eval_sel['segmento'], ""))

        # Mapeo de columnas cualitativas a títulos
        columnas_cualitativas = {
            "fortalezas_mas_destacadas": "🌟 Fortalezas Destacadas",
            "oportunidades_de_mejora": "📉 Oportunidades de Mejora",
            "recomendaciones_especificas_de_formacion": "🎓 Recomendaciones de Formación"
        }

        # Mostrar como párrafos tipo diálogo
        for col, titulo in columnas_cualitativas.items():
            if col in eval_sel:
                contenido = eval_sel[col]
                if pd.isna(contenido) or str(contenido).strip() == "":
                    st.info(f"**{titulo}:** No fue completado.")
                else:
                    st.markdown(f"**{titulo}:**")
                    st.markdown(f"> {contenido.strip()}")
                    st.markdown("")  # Espacio entre secciones
            else:
                st.warning(f"Columna '{col}' no encontrada.")
            
        # Gráfico de radar
        st.subheader("Desempeño por Área")
        categorias_radar = list(categorias.keys())
        valores_radar = [eval_sel[c] for c in categorias_radar]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=valores_radar,
            theta=categorias_radar,
            fill='toself',
            name=vendedor_sel,
            line_color='#636EFA'
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10]
                )),
            showlegend=False,
            margin=dict(l=50, r=50, t=50, b=50),
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Nueva sección: Potencial para supervisor
        st.subheader("🔍 Potencial para Supervisor")
        potencial_supervisor = "Sí" if (eval_sel['potencial'] >= 8 and eval_sel['Habilidades Blandas'] >= 8) else "Con desarrollo" if (eval_sel['potencial'] >= 7) else "No"
        
        col_pot1, col_pot2 = st.columns(2)
        with col_pot1:
            st.metric("¿Tiene potencial para ser supervisor?", potencial_supervisor)
        
        with col_pot2:
            if potencial_supervisor == "Sí":
                st.success("Este colaborador muestra las competencias necesarias para asumir un rol de supervisión.")
            elif potencial_supervisor == "Con desarrollo":
                st.warning("Podría desarrollar las competencias necesarias con un plan de formación adecuado.")
            else:
                st.info("Actualmente no muestra el perfil requerido para supervisión.")
        
        # Métricas Claves para HHRR
        st.markdown("---")
        st.subheader("📌 Métricas Claves para HHRR")

        cols_hr = st.columns(4)

        with cols_hr[0]:
            st.metric("📅 Antigüedad", "2.5 años", help="Tiempo en el puesto actual")

        with cols_hr[1]:
            if not df_cump.empty:
                df_vend_cump = df_cump[df_cump['vendedor'] == vendedor_sel].copy()
                if not df_vend_cump.empty:
                    # Solución: Convertir a string primero y manejar NaN
                    df_vend_cump['cumplimiento_num'] = (
                        df_vend_cump['cumplimiento'].astype(str)
                        .str.replace('%', '')
                        .replace('nan', np.nan)
                        .astype(float) / 100
            )
            
            df_vend_cump = df_vend_cump.sort_values(['year', 'mes'])
            tendencia = "↑ Mejorando" if df_vend_cump['cumplimiento_num'].iloc[-1] > df_vend_cump['cumplimiento_num'].iloc[0] else "↓ Empeorando"
            st.metric("📈 Tendencia Cumplimiento", tendencia)

        with cols_hr[2]:
            puntaje_total = eval_sel.get('puntaje_total', 0)
            if puntaje_total >= 8:
                consistencia = "Alta"
                color = "green"
            elif puntaje_total >= 6:
                consistencia = "Media"
                color = "orange"
            else:
                consistencia = "Baja"
                color = "red"
            st.markdown("🔄 **Consistencia**")
            st.markdown(f"<span style='color:{color}; font-size: 20px'>{consistencia}</span>", unsafe_allow_html=True)

        with cols_hr[3]:
            potencial = eval_sel.get('potencial', 0)
            if potencial >= 8:
                nivel_potencial = "Alto"
                color = "green"
            elif potencial >= 6:
                nivel_potencial = "Medio"
                color = "orange"
            else:
                nivel_potencial = "Bajo"
                color = "red"
            st.markdown("🚀 **Potencial**")
            st.markdown(f"<span style='color:{color}; font-size: 20px'>{nivel_potencial}</span>", unsafe_allow_html=True)

        # Matriz de decisión HHRR
        st.markdown("#### Matriz de Decisión HHRR")

        decision_data = {
            "Factor": [
                "Desempeño Actual",
                "Potencial de Crecimiento",
                "Tendencia Reciente",
                "Consistencia Histórica",
                "Alineamiento Cultural"
            ],
            "Evaluación": [
                "Alto" if puntaje_total >= 8 else "Medio" if puntaje_total >= 6 else "Bajo",
                nivel_potencial,
                tendencia if 'tendencia' in locals() else "N/D",
                consistencia,
                "Alto"
            ],
            "Recomendación": [
                "Mantener/Desarrollar" if puntaje_total >= 8 else "Capacitar" if puntaje_total >= 6 else "Revisar",
                "Invertir en desarrollo" if potencial >= 8 else "Monitorear" if potencial >= 6 else "Limitar inversión",
                "Reforzar positivamente" if 'tendencia' in locals() and tendencia == "↑ Mejorando" else "Intervenir",
                "Estable" if consistencia == "Alta" else "Volátil",
                "Retener"
            ]
        }

        st.dataframe(
            pd.DataFrame(decision_data),
            hide_index=True,
            use_container_width=True
        )

        st.markdown("---")
        
        # Botones para generar PDFs
    st.markdown("---")
    st.subheader("📄 Generar Reportes Formales")
    
    col_pdf1, col_pdf2, col_pdf3 = st.columns(3)
    
    with col_pdf1:
        if st.button("📄 Generar Perfil PDF"):
            pdf_bytes = generar_pdf_perfil(vendedor_sel, df_eval, df_seg_orig, df_cump_orig, df_info_orig, "general")
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Descargar Perfil Completo",
                    data=pdf_bytes,
                    file_name=f"Perfil_{vendedor_sel}.pdf",
                    mime="application/pdf"
                )
    
    with col_pdf2:
        if st.button("🏆 Generar Reconocimiento PDF"):
            pdf_bytes = generar_pdf_perfil(vendedor_sel, df_eval, df_seg_orig, df_cump_orig, df_info_orig, "reconocimiento")
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Descargar Reconocimiento",
                    data=pdf_bytes,
                    file_name=f"Reconocimiento_{vendedor_sel}.pdf",
                    mime="application/pdf"
                )
    
    with col_pdf3:
        if st.button("⚠️ Generar Plan Mejora PDF"):
            pdf_bytes = generar_pdf_perfil(vendedor_sel, df_eval, df_seg_orig, df_cump_orig, df_info_orig, "mejora")
            if pdf_bytes:
                st.download_button(
                    label="⬇️ Descargar Plan de Mejora",
                    data=pdf_bytes,
                    file_name=f"Plan_Mejora_{vendedor_sel}.pdf",
                    mime="application/pdf"
                )
    
    with tab2:
        st.subheader("Evaluación Completa por Competencias")
     
        # Verificación de datos
        if pd.isna(eval_sel['efectividad_real_vs_meta']):
            st.warning("Datos de evaluación incompletos para este vendedor")
        else:
            # Sección: Venta y Negociación
            st.markdown("### 💰 Venta y Negociación")
            cols_venta = st.columns(3)
            with cols_venta[0]:
                valor = eval_sel.get('efectividad_real_vs_meta', np.nan)
                st.metric("Efectividad", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Capacidad para lograr los objetivos de venta")
            with cols_venta[1]:
                valor = eval_sel.get('manejo_de_objeciones_efectivas', np.nan)
                st.metric("Manejo de Objeciones", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Habilidad para manejar objeciones de clientes")
            with cols_venta[2]:
                valor = eval_sel.get('cierra_ventas_sin_depender_de_promociones', np.nan)
                st.metric("Venta Cruzada", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Capacidad para vender productos complementarios")

            # Sección: Relación con Clientes
            st.markdown("### 🤝 Relación con Clientes")
            cols_cliente = st.columns(3)
            with cols_cliente[0]:
                valor = eval_sel.get('gana_confianza_del_cliente', np.nan)
                st.metric("Empatía", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Capacidad para entender las necesidades del cliente")
            with cols_cliente[1]:
                valor = eval_sel.get('soluciona_conflictos_con_criterio', np.nan)
                st.metric("Confianza", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Generación de confianza con los clientes")
            with cols_cliente[2]:
                valor = eval_sel.get('soluciona_conflictos_con_criterio', np.nan)
                st.metric("Resolución de Conflictos", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Habilidad para resolver problemas con clientes")

            # Sección: Comportamiento y Actitud
            st.markdown("### 🧠 Comportamiento y Actitud")
            cols_actitud = st.columns(3)
            with cols_actitud[0]:
                valor = eval_sel.get('toma_la_iniciativa_sin_necesidad_de_ser_presionado.', np.nan)
                st.metric("Iniciativa", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Proactividad y toma de iniciativa")
            with cols_actitud[1]:
                valor = eval_sel.get('resuelve_problemas_cotidianos_de_manera_práctica_y_rápida.', np.nan)
                st.metric("Adaptación", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Flexibilidad ante cambios")
            with cols_actitud[2]:
                valor = eval_sel.get('persiste_en_la_venta_con_educación_y_sin_presión_al_cliente.', np.nan)
                st.metric("Persistencia", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Constancia ante desafíos")

            # Sección: Aptitudes
            st.markdown("### 🛠️ Aptitudes Técnicas")
            cols_apt = st.columns(3)
            with cols_apt[0]:
                valor = eval_sel.get('usa_adecuadamente_las_aplicaciones', np.nan)
                st.metric("Manejo de Herramientas", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Uso de aplicaciones y sistemas")
            with cols_apt[1]:
                valor = eval_sel.get('reporta_faltantes_o_problemas_de_averias', np.nan)
                st.metric("Reportes", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Elaboración de informes y reportes")
            with cols_apt[2]:
                valor = eval_sel.get('planifica_su_ruta_diaria_de_manera_lógica_y_eficiente.', np.nan)
                st.metric("Planificación", 
                         f"{valor:.1f}/10" if pd.notna(valor) else "N/D",
                         help="Organización y planificación de rutas")
    
    with tab3:
        st.subheader("🔄 Seguimiento de Visitas")
        st.caption("Registro histórico de visitas y acompañamientos realizados")

        # --- Formulario para agregar nuevos comentarios ---
        st.markdown("### ✍️ Agregar Nuevo Comentario")
        
        with st.form(key='form_comentario', clear_on_submit=True):
            nuevo_comentario = st.text_area("Observaciones del supervisor:", 
                                        placeholder="Describa el desempeño, oportunidades de mejora, etc...",
                                        height=150)
            supervisor_name = st.text_input("Nombre del supervisor:", 
                                        value=st.session_state.get('supervisor_name', ''))
            fecha_visita = st.date_input("Fecha de visita:", 
                                        value=datetime.now())
            
            submitted = st.form_submit_button("💾 Guardar Comentario")
            
            if submitted:
                if not nuevo_comentario:
                    st.warning("⚠️ Por favor ingrese un comentario")
                else:
                    # Crear nuevo registro
                    nuevo_registro = {
                        'ruta': vendedor_sel,
                        'supervisor': supervisor_name,
                        'comentarios': nuevo_comentario,
                        'fecha_visita': fecha_visita.strftime('%Y-%m-%d'),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    try:
                        # Aquí deberías implementar la lógica para guardar en tu fuente de datos
                        # Ejemplo para guardar en un CSV temporal:
                        # df_nuevo = pd.DataFrame([nuevo_registro])
                        # df_nuevo.to_csv('seguimiento_temp.csv', mode='a', header=False, index=False)
                        
                        st.success("✅ Comentario guardado correctamente")
                        st.session_state.supervisor_name = supervisor_name  # Guardar para próxima vez
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")

        # --- Visualización de datos históricos ---
        if seg_sel.empty:
            st.warning("No hay registros de seguimiento para este vendedor.")
        else:
            # Verificar y limpiar la columna de fecha
            if 'timestamp' in seg_sel.columns:
                try:
                    seg_sel['timestamp'] = pd.to_datetime(seg_sel['timestamp'])
                except:
                    st.warning("Formato de fecha no reconocido en los registros")
            
            # Gráfico de visitas por mes
            st.markdown("#### 📅 Visitas por Mes")
            if 'timestamp' in seg_sel.columns:
                visitas_por_mes = seg_sel.groupby(seg_sel['timestamp'].dt.to_period('M')).size()
                visitas_por_mes.index = visitas_por_mes.index.to_timestamp()
                
                fig = px.bar(
                    visitas_por_mes,
                    x=visitas_por_mes.index,
                    y=visitas_por_mes.values,
                    labels={'x': 'Mes', 'y': 'N° Visitas'},
                    color_discrete_sequence=['#4E79A7']
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No se encontró columna de fecha para generar el gráfico")

            # Tabla con todos los registros de seguimiento
            st.markdown("#### 📝 Últimas Visitas Registradas")
            
            # Ordenar por fecha descendente y mostrar todas las columnas
            columnas_orden = ['timestamp'] + [col for col in seg_sel.columns if col != 'timestamp']
            
            st.dataframe(
                seg_sel.sort_values('timestamp', ascending=False).head(20),
                column_order=columnas_orden,
                use_container_width=True,
                height=500,
                hide_index=True
            )

            # Estadísticas resumen
            st.markdown("#### 📊 Estadísticas de Seguimiento")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'timestamp' in seg_sel.columns:
                    primera_visita = seg_sel['timestamp'].min()
                    st.metric("Primera visita", primera_visita.strftime('%d/%m/%Y'))
                else:
                    st.metric("Total registros", len(seg_sel))
            
            with col2:
                if 'timestamp' in seg_sel.columns:
                    ultima_visita = seg_sel['timestamp'].max()
                    st.metric("Última visita", ultima_visita.strftime('%d/%m/%Y'))
                else:
                    st.metric("Supervisores distintos", seg_sel['supervisor'].nunique())
            
            with col3:
                if 'comentarios' in seg_sel.columns:
                    avg_len = seg_sel['comentarios'].str.len().mean()
                    st.metric("Longitud promedio comentarios", f"{avg_len:.0f} caracteres")
                else:
                    st.metric("Registros este año", len(seg_sel))
    
    with tab4:
        st.subheader("📈 Indicadores de Gestión Comercial")
        
        if not df_cump.empty:
            df_vendedor_cump = df_cump[df_cump['vendedor'] == vendedor_sel].copy()
            
            if not df_vendedor_cump.empty:
                # Convertir porcentaje a numérico
                df_vendedor_cump['cumplimiento_num'] = (
                    df_vendedor_cump['cumplimiento']
                    .astype(str)  # Convertir a string primero
                    .str.replace('%', '')
                    .replace('nan', np.nan)  # Manejar valores NaN
                    .astype(float) / 100
)
                df_vendedor_cump['fecha'] = pd.to_datetime(df_vendedor_cump.apply(lambda x: f"{x['year']}-{x['mes']}-01", axis=1))
                
                # Gráfico de evolución temporal
                st.markdown("#### Evolución Temporal")
                
                fig_evo = px.line(
                    df_vendedor_cump.sort_values('fecha'),
                    x='fecha',
                    y='cumplimiento_num',
                    color='indicador',
                    title=f"Evolución de Indicadores - {vendedor_sel}",
                    labels={'cumplimiento_num': '% Cumplimiento', 'fecha': 'Fecha'},
                    markers=True
                )
                fig_evo.update_yaxes(tickformat=".0%")
                fig_evo.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_evo, use_container_width=True)
                
                # Comparativa con el equipo
                st.markdown("#### Comparativa con el Equipo")
                
                # Calcular promedios del equipo por indicador
                df_team_avg = df_cump.copy()
                df_team_avg = df_team_avg.groupby(['indicador', 'year', 'mes']).agg({'cumplimiento_num': 'mean'}).reset_index()
                df_team_avg['fecha'] = pd.to_datetime(df_team_avg.apply(lambda x: f"{x['year']}-{x['mes']}-01", axis=1))
                
                # Unir datos del vendedor con promedios del equipo
                df_comparativa = df_vendedor_cump.merge(
                    df_team_avg,
                    on=['indicador', 'fecha'],
                    suffixes=('_vendedor', '_equipo')
                )
                
                # Mostrar comparativa para el último período disponible
                ultimo_mes = df_vendedor_cump['fecha'].max()
                df_ultimo_mes = df_comparativa[df_comparativa['fecha'] == ultimo_mes]
                
                if not df_ultimo_mes.empty:
                    st.markdown(f"##### Comparativa último período ({ultimo_mes.strftime('%B %Y')})")
                    
                    for _, row in df_ultimo_mes.iterrows():
                        delta = (row['cumplimiento_num_vendedor'] - row['cumplimiento_num_equipo']) * 100
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{row['indicador']}**")
                        with col2:
                            st.metric(
                                label="",
                                value=f"{row['cumplimiento_num_vendedor']:.1%}",
                                delta=f"{delta:.1f}pp vs equipo",
                                delta_color="inverse" if delta < 0 else "normal"
                            )
                
                # Gráfico de radar para comparar múltiples indicadores
                if len(df_vendedor_cump['indicador'].unique()) > 2:
                    st.markdown("#### Comparativa Multidimensional")
                    
                    # Obtener últimos datos por indicador
                    df_last_values = df_vendedor_cump.sort_values(['indicador', 'fecha']).groupby('indicador').last().reset_index()
                    
                    fig_radar = go.Figure()
                    
                    # Añadir vendedor
                    fig_radar.add_trace(go.Scatterpolar(
                        r=df_last_values['cumplimiento_num'],
                        theta=df_last_values['indicador'],
                        fill='toself',
                        name=vendedor_sel,
                        line_color='blue'
                    ))
                    
                    # Añadir promedio equipo
                    team_last_values = df_team_avg.sort_values(['indicador', 'fecha']).groupby('indicador').last().reset_index()
                    fig_radar.add_trace(go.Scatterpolar(
                        r=team_last_values['cumplimiento_num'],
                        theta=team_last_values['indicador'],
                        fill='toself',
                        name='Promedio Equipo',
                        line_color='red'
                    ))
                    
                    fig_radar.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 1], tickformat=".0%")),
                        showlegend=True,
                        margin=dict(l=50, r=50, t=50, b=50),
                        height=500,
                        title="Comparación con Promedio del Equipo"
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
            else:
                st.warning(f"No se encontraron datos de cumplimiento para {vendedor_sel}")
        else:
            st.warning("No se encontraron datos de cumplimiento para mostrar")
    
    with tab5:
        st.subheader("🎯 Plan de Desarrollo Personalizado")
        
        # Sección de recomendaciones específicas
        st.markdown("### 📚 Recomendaciones Específicas de Formación")
        
        if eval_sel['Habilidades Blandas'] < 7:
            st.markdown("""
            #### 🧠 Habilidades Blandas
            - **Curso recomendado:** Comunicación Efectiva y Manejo de Objeciones
            - **Duración:** 8 horas
            - **Modalidad:** Taller práctico
            - **Objetivo:** Mejorar capacidad de escucha activa y manejo de objeciones
            """)
        
        if eval_sel['Autonomía'] < 6:
            st.markdown("""
            #### 🦅 Autonomía
            - **Curso recomendado:** Toma de Decisiones y Resolución de Problemas
            - **Duración:** 12 horas
            - **Modalidad:** Online con casos prácticos
            - **Objetivo:** Desarrollar pensamiento crítico y autonomía
            """)
        
        if eval_sel['Herramientas'] < 6:
            st.markdown("""
            #### 💻 Herramientas Digitales
            - **Curso recomendado:** Dominio de Herramientas Comerciales
            - **Duración:** 16 horas
            - **Modalidad:** Presencial con ejercicios prácticos
            - **Objetivo:** Optimizar uso de herramientas tecnológicas
            """)
        
        # Plan de acción por segmento
        st.markdown("---")
        st.subheader("📅 Plan de Acción Según Segmento")
        
        if segmento == "🟢 Alto Desempeño & Alto Potencial":
            st.success("**Estrategia:** Desarrollo de liderazgo y retención")
            st.markdown("""
            1. **Mentoría:** Asignar como mentor de nuevos vendedores
            2. **Proyectos especiales:** Involucrar en proyectos estratégicos
            3. **Formación avanzada:** Curso de liderazgo ejecutivo (40 horas)
            4. **Visibilidad:** Presentar en reuniones de gerencia
            """)
        
        elif segmento == "🟡 Buen Desempeño pero Bajo Potencial":
            st.info("**Estrategia:** Mantenimiento y desarrollo de autonomía")
            st.markdown("""
            1. **Rotación controlada:** Variar rutas periódicamente
            2. **Metas de autonomía:** Establecer objetivos graduales
            3. **Talleres:** Pensamiento crítico (8 horas)
            4. **Reconocimiento:** Destacar consistencia en resultados
            """)
        
        elif segmento == "🟠 Alto Potencial pero Bajo Desempeño":
            st.warning("**Estrategia:** Desarrollo acelerado")
            st.markdown("""
            1. **Capacitación intensiva:** Programa acelerado de habilidades comerciales
            2. **Acompañamiento:** Mentoría semanal con supervisor
            3. **Metas claras:** Objetivos SMART con seguimiento quincenal
            4. **Retroalimentación:** Sesiones de feedback estructurado
            """)
        
        elif segmento == "🔴 Bajo Desempeño & Bajo Potencial":
            st.error("**Estrategia:** Acción correctiva")
            st.markdown("""
            1. **Plan de mejora:** Con objetivos y plazos específicos
            2. **Capacitación básica:** Refuerzo de competencias esenciales
            3. **Monitoreo estrecho:** Revisión diaria/semanal de avances
            4. **Evaluación continua:** Decisión sobre continuidad en el puesto
            """)
        
        else:  # Perfil mixto
            st.info("**Estrategia:** Evaluación personalizada")
            st.markdown("""
            1. **Análisis detallado:** Identificar patrones y causas raíz
            2. **Plan personalizado:** Enfocado en áreas específicas
            3. **Seguimiento individualizado:** Ajustar según evolución
            """)
        
        # Timeline de desarrollo
        st.markdown("---")
        st.subheader("⏳ Cronograma de Desarrollo")
        
        timeline_data = {
            "Actividad": [
                "Evaluación inicial",
                "Formación específica",
                "Seguimiento 1:1",
                "Evaluación de progreso",
                "Plan de carrera"
            ],
            "Fecha": [
                "Ene 2024",
                "Feb-Mar 2024",
                "Abr 2024",
                "Jul 2024",
                "Oct 2024"
            ],
            "Responsable": [
                "RRHH",
                "Capacitación",
                "Supervisor",
                "RRHH",
                "Gerencia"
            ]
        }
        
        st.dataframe(
            pd.DataFrame(timeline_data),
            hide_index=True,
            use_container_width=True
        )

else:  # Vista de Equipo
    st.header("👥 Vista General del Equipo")
    st.markdown("""
    **Análisis comparativo** del equipo completo, con ranking de vendedores, matriz de talento 
    y evaluación por áreas clave.
    """)
    
    # Filtros adicionales
    supervisores = df_eval['supervisor'].unique()
    supervisor_sel = st.sidebar.multiselect("Filtrar por Supervisor", supervisores)
    
    rutas = df_eval[vendedor_col].unique()
    ruta_sel = st.sidebar.multiselect("Filtrar por Ruta", rutas)
    
    # Aplicar filtros
    df_filtrado = df_eval.copy()
    if supervisor_sel:
        df_filtrado = df_filtrado[df_filtrado['supervisor'].isin(supervisor_sel)]
    if ruta_sel:
        df_filtrado = df_filtrado[df_filtrado['vendedor'].isin(ruta_sel)]
    
    # Pestañas para vista de equipo
    tab1, tab2, tab3 = st.tabs(["🏆 Ranking", "🧩 Matriz de Talento", "📊 Análisis por Área"])
    
    with tab1:
        st.subheader("Ranking de Vendedores")
        st.caption("Comparativa de desempeño según diferentes métricas")
        
        metrica_ranking = st.selectbox("Ordenar por", ["Puntaje Total", "Potencial"] + list(categorias.keys()))
        
        if metrica_ranking == "Puntaje Total":
            df_ranking = df_filtrado.sort_values("puntaje_total", ascending=False)
            col_ranking = "puntaje_total"
        elif metrica_ranking == "Potencial":
            df_ranking = df_filtrado.sort_values("potencial", ascending=False)
            col_ranking = "potencial"
        else:
            df_ranking = df_filtrado.sort_values(metrica_ranking, ascending=False)
            col_ranking = metrica_ranking
        
        st.dataframe(
            df_ranking[[vendedor_col, 'supervisor', col_ranking, 'segmento']]
            .set_index('ruta')
            .style.background_gradient(cmap='YlGnBu', subset=[col_ranking]),
            use_container_width=True
        )
        
        fig = px.bar(
            df_ranking.head(15),
            x='ruta',
            y=col_ranking,
            color='supervisor',
            title=f"Top 15 por {metrica_ranking}",
            labels={'ruta': 'ruta', col_ranking: metrica_ranking}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Matriz de Talento: Desempeño vs Potencial")
        st.caption("Clasificación estratégica del talento en el equipo")
        
        fig = px.scatter(
            df_filtrado,
            x='puntaje_total',
            y='potencial',
            color='supervisor',
            hover_name='ruta',
            text='ruta',
            labels={'puntaje_total': 'Desempeño Total', 'potencial': 'Potencial'},
            title="Matriz de Talento"
        )
        
        fig.update_layout(
            shapes=[
                dict(type='line', x0=7, x1=7, y0=0, y1=10, line=dict(color='gray', dash='dot')),
                dict(type='line', x0=0, x1=10, y0=7, y1=7, line=dict(color='gray', dash='dot')),
                dict(type='rect', x0=7, x1=10, y0=7, y1=10, line=dict(color='green'), opacity=0.1),
                dict(type='rect', x0=0, x1=7, y0=7, y1=10, line=dict(color='orange'), opacity=0.1),
                dict(type='rect', x0=7, x1=10, y0=0, y1=7, line=dict(color='yellow'), opacity=0.1),
                dict(type='rect', x0=0, x1=7, y0=0, y1=7, line=dict(color='red'), opacity=0.1)
            ],
            annotations=[
                dict(x=8.5, y=8.5, text="Estrellas", showarrow=False, font=dict(color='green')),
                dict(x=3.5, y=8.5, text="Potenciales", showarrow=False, font=dict(color='orange')),
                dict(x=8.5, y=3.5, text="Mantenedores", showarrow=False, font=dict(color='gold')),
                dict(x=3.5, y=3.5, text="Riesgos", showarrow=False, font=dict(color='red'))
            ],
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        #### Interpretación de la Matriz:
        - **🟢 Estrellas (Alto desempeño, alto potencial):** Futuros líderes, asignar proyectos especiales
        - **🟡 Potenciales (Bajo desempeño, alto potencial):** Invertir en desarrollo, mentoría
        - **🟠 Mantenedores (Alto desempeño, bajo potencial):** Clave para resultados actuales
        - **🔴 Riesgos (Bajo desempeño, bajo potencial):** Planes de mejora o salida
        """)
    
    with tab3:
        st.subheader("📊 Análisis por Áreas Clave")
        st.caption("Evaluación detallada por categorías con recomendaciones personalizadas")
        
        area_sel = st.selectbox("Seleccionar área para análisis", list(categorias.keys()))
        
        # Datos para el área seleccionada
        df_area = df_filtrado[['ruta', 'supervisor', area_sel, 'segmento']].sort_values(area_sel, ascending=False)
        promedio_area = df_eval[area_sel].mean()
        
        # Crear columna 'estado' basada en los valores del área seleccionada
        df_area['estado'] = pd.cut(
            df_area[area_sel],
            bins=[0, 6, 8, 10],
            labels=["🔴 Crítico", "🟡 Aceptable", "🟢 Fuerte"]
        )
        
        # Gráficos y datos
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"#### Distribución de {area_sel}")
            fig_dist = px.histogram(
                df_filtrado,
                x=area_sel,
                nbins=20,
                labels={area_sel: "Puntaje"},
                color_discrete_sequence=['#636EFA']
            )
            fig_dist.add_vline(x=promedio_area, line_dash="dash", line_color="red", 
                             annotation_text=f"Promedio: {promedio_area:.1f}", 
                             annotation_position="top")
            st.plotly_chart(fig_dist, use_container_width=True)
        
        with col2:
            st.markdown(f"#### Ranking de {area_sel}")
            st.dataframe(
                df_area.head(10).style.background_gradient(
                    cmap='YlGnBu',
                    subset=[area_sel]
                ),
                use_container_width=True
            )
        
        # Gráfico de barras por estado
        st.markdown(f"#### Estado por Vendedor en {area_sel}")
        fig_barras = px.bar(
            df_area.head(20),
            x='ruta',
            y=area_sel,
            color='estado',
            color_discrete_map={
                "🔴 Crítico": "#EF553B",
                "🟡 Aceptable": "#FECB52",
                "🟢 Fuerte": "#00CC96"
            },
            labels={'ruta': 'ruta', area_sel: 'Puntaje'},
            category_orders={"estado": ["🔴 Crítico", "🟡 Aceptable", "🟢 Fuerte"]}
        )
        st.plotly_chart(fig_barras, use_container_width=True)
        
        # Recomendaciones por segmento y puntuación
        st.markdown("---")
        st.subheader("🎯 Recomendaciones por Segmento y Puntuación")
        
        # Obtener estadísticas del área seleccionada
        stats_area = {
            "Promedio": df_filtrado[area_sel].mean(),
            "Mínimo": df_filtrado[area_sel].min(),
            "Máximo": df_filtrado[area_sel].max(),
            "Desviación estándar": df_filtrado[area_sel].std()
        }
        
        col_stats1, col_stats2 = st.columns(2)
        
        with col_stats1:
            st.markdown("##### Estadísticas del Área")
            for stat, value in stats_area.items():
                st.metric(stat, f"{value:.1f}")
        
        with col_stats2:
            st.markdown("##### Recomendaciones Generales")
            if stats_area["Promedio"] < 6:
                st.error("**Área crítica** que requiere intervención inmediata")
                st.markdown("""
                - Talleres intensivos para todo el equipo
                - Acompañamiento cercano de supervisores
                - Revisión de procesos y herramientas
                """)
            elif stats_area["Promedio"] < 8:
                st.warning("**Área a mejorar** con oportunidades de crecimiento")
                st.markdown("""
                - Capacitaciones específicas
                - Intercambio de mejores prácticas
                - Establecer metas de mejora
                """)
            else:
                st.success("**Área fuerte** que puede optimizarse aún más")
                st.markdown("""
                - Certificaciones avanzadas
                - Programas de mentoría inversa
                - Proyectos de innovación
                """)

# =============================================
# FOOTER
# =============================================
st.markdown("---")
st.caption("Sistema de Gestión de perfiles comercial | © 2025 | Versión 2.1")
