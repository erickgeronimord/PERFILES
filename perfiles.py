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
    page_title="Gestión Comercial 360",
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
categorias_detalladas = {
    "EFICACIA EN RUTA": [
        "visita_todos_sus_clientes_por_dia?",
        "efectividad_real_vs_meta",
        "eficiencia_en_tiempo_por_punto",
        "sabe_priorizar_colmados_de_alto_volumen"
    ],
    "VENTA Y NEGOCIACIÓN": [
        "cumple_con_cuotas_de_venta_mensual",
        "promueve_productos_nuevos/ofertas",
        "cierra_ventas_sin_depender_de_promociones",
        "manejo_de_objeciones_efectivas"
    ],
    "RELACIÓN CON CLIENTES": [
        "respeto,_trato_cordial_y_empatia",
        "gana_confianza_del_cliente",
        "soluciona_conflictos_con_criterio",
        "clientes_solicitan_ser_visitados_por_el"
    ],
    "ORDEN Y EJECUCIÓN EN EL PUNTO DE VENTA": [
        "reporta_faltantes_o_problemas_de_averias",
        "toma_pedidos_bien_detallados",
        "rectifica_pedido_al_cliente"
    ],
    "COMPORTAMIENTO Y ACTITUD": [
        "puntualidad_y_asistencia",
        "uso_correcto_del_uniforme",
        "respeto_por_normas_y_procesos",
        "compromiso_con_la_marca"
    ],
    "CAPACIDAD DE AUTOGESTIÓN": [
        "planea_su_ruta_diaria",
        "soluciona_imprevistos_sin_llamar_al_supervisor",
        "usa_adecuadamente_las_aplicaciones",
        "reportes_y_formularios_sin_errores"
    ],
    "SEGURIDAD Y CONDUCCIÓN": [
        "uso_de_casco_y_chaleco",
        "conduce_de_forma_segura",
        "mantiene_la_motocicleta_en_condiciones",
        "respeta_las_normas_de_transito"
    ],
    "POTENCIAL DE DESARROLLO": [
        "aprende_rapido",
        "recibe_bien_el_feedback",
        "tiene_liderazgo_informal_con_companeros",
        "puede_escalar_a_rutas_de_alto_desempeno"
    ],
    "HABILIDADES": [
        "se_comunica_con_claridad_al_presentar_productos_y_promociones.",
        "sabe_negociar_condiciones_sin_depender_solo_de_descuentos.",
        "recomienda_productos_adecuados_segun_el_perfil_del_cliente.",
        "toma_pedidos_de_forma_precisa_y_sin_errores_frecuentes.",
        "planifica_su_ruta_diaria_de_manera_logica_y_eficiente.",
        "usa_correctamente_las_aplicaciones_moviles_o_herramientas_digitales_asignadas.",
        "maneja_adecuadamente_su_tiempo_durante_las_visitas.",
        "soluciona_situaciones_imprevistas_sin_necesidad_de_escalar_todo_al_supervisor.",
        "detecta_oportunidades_de_venta_cruzada_u_otros_negocios.",
        "mantiene_una_presentacion_personal_adecuada_(uniforme,_aseo,_porte)."
    ],
    "ACTITUDES": [
        "muestra_compromiso_con_la_empresa,_aun_en_situaciones_dificiles.",
        "mantiene_una_actitud_positiva_frente_a_los_rechazos_o_dificultades.",
        "toma_la_iniciativa_sin_necesidad_de_ser_presionado.",
        "colabora_con_sus_companeros_de_equipo_cuando_es_necesario.",
        "acepta_el_feedback_y_busca_aplicarlo_para_mejorar.",
        "trata_a_las_personas_clientas_con_respeto_y_profesionalismo_en_todo_momento.",
        "se_mantiene_etico_en_sus_acciones_(no_manipula_pedidos,_respeta_normas).",
        "persiste_en_la_venta_con_educacion_y_sin_presion_a_la_clientela.",
        "mantiene_el_control_emocional_incluso_bajo_presion.",
        "muestra_interes_por_aprender_y_desarrollarse_constantemente."
    ],
    "APTITUDES": [
        "resuelve_problemas_cotidianos_de_manera_practica_y_rapida.",
        "tiene_influencia_positiva_sobre_sus_companeros_sin_necesidad_de_autoridad_formal.",
        "se_adapta_con_facilidad_a_cambios_en_la_ruta,_herramientas_o_productos.",
        "recuerda_informacion_clave_sobre_personas_clientas,_precios_o_promociones_pasadas.",
        "interpreta_y_comenta_sus_propios_resultados_de_venta_con_criterio.",
        "hace_preguntas_sobre_nuevos_productos,_herramientas_o_estrategias.",
        "mantiene_su_trabajo_ordenado_y_cumple_con_documentacion_sin_errores.",
        "maneja_sus_emociones_con_madurez_en_contextos_dificiles_o_retadores.",
        "busca_mejorar_por_cuenta_propia,_sin_que_se_le_exija.",
        "tiene_el_potencial_para_crecer_a_roles_de_mayor_responsabilidad_en_el_futuro."
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
# FUNCIÓN PARA PROCESAR DATOS CON NUEVAS CATEGORÍAS
# =============================================
def procesar_datos_detallados(df_eval):
    # Normalizar nombres de columnas para coincidir con nuestras categorías
    df_eval.columns = df_eval.columns.str.lower().str.replace(' ', '_').str.replace('?', '')
    
    # Calcular promedios por categoría
    for categoria, columnas in categorias_detalladas.items():
        # Filtrar columnas que existen en el DataFrame
        columnas_existentes = [col for col in columnas if col in df_eval.columns]
        
        if columnas_existentes:
            # Calcular promedio solo si hay columnas existentes
            df_eval[categoria] = df_eval[columnas_existentes].mean(axis=1)
        else:
            df_eval[categoria] = np.nan
    
    # Calcular puntaje total (promedio de todas las categorías principales)
    categorias_principales = list(categorias_detalladas.keys())
    df_eval['puntaje_total'] = df_eval[categorias_principales].mean(axis=1)
    
    # Calcular potencial (promedio de categorías específicas)
    categorias_potencial = [
        "POTENCIAL DE DESARROLLO", 
        "HABILIDADES", 
        "ACTITUDES", 
        "APTITUDES"
    ]
    df_eval['potencial'] = df_eval[categorias_potencial].mean(axis=1)
    
    # Segmentación del equipo (como en tu código original)
    condiciones = [
        (df_eval['puntaje_total'] >= 4.5) & (df_eval['potencial'] >= 4.5),
        (df_eval['puntaje_total'] >= 4.5) & (df_eval['potencial'] < 4.5),
        (df_eval['puntaje_total'] < 4.5) & (df_eval['potencial'] >= 4.5),
        (df_eval['puntaje_total'] < 4.5) & (df_eval['potencial'] < 4.5)
    ]
    opciones = [
        "🟢 Alto Desempeño & Alto Potencial",
        "🟡 Buen Desempeño pero Bajo Potencial",
        "🟠 Alto Potencial pero Bajo Desempeño",
        "🔴 Bajo Desempeño & Bajo Potencial"
    ]
    df_eval['segmento'] = np.select(condiciones, opciones, default="🧩 Inconsistente / Perfil Mixto")
    
    return df_eval

# =============================================
# NUEVA VISTA DE RESUMEN DE DESEMPEÑO
# =============================================
def mostrar_resumen_desempeno(vendedor_sel, df_eval):
    # Obtener datos del vendedor
    datos_vendedor = df_eval[df_eval['ruta'] == vendedor_sel].iloc[0].to_dict()
    
    # Mapeo de colores según puntaje
    def obtener_color(puntaje):
        if puntaje >= 4.5:
            return "#2ecc71"  # Verde
        elif puntaje >= 3.5:
            return "#f39c12"  # Naranja
        else:
            return "#e74c3c"  # Rojo
    
    # --- Contenedor principal con estilo profesional ---
    with st.container():
        # Encabezado con estilo
        st.markdown(f"""
        <div style='background-color:#3498db; padding:15px; border-radius:10px; margin-bottom:20px;'>
            <h2 style='color:white; margin:0;'>📊 Resumen de Desempeño Detallado</h2>
            <h3 style='color:white; margin:0;'>{vendedor_sel}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # --- Sección de métricas clave ---
        with st.container():
            st.markdown("### 📈 Métricas Clave")
            
            # Crear 3 columnas para métricas principales
            col1, col2, col3 = st.columns(3)
            
            # Puntaje General
            with col1:
                puntaje_total = datos_vendedor.get('puntaje_total', 'N/D')
                st.markdown(f"""
                <div style='border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center; background-color:#f8f9fa;'>
                    <h4 style='margin-top:0;'>Puntaje General</h4>
                    <h2 style='color:{obtener_color(puntaje_total) if isinstance(puntaje_total, (int, float)) else "#333"};'>
                        {puntaje_total if isinstance(puntaje_total, str) else f"{puntaje_total:.1f}"}/5
                    </h2>
                </div>
                """, unsafe_allow_html=True)
            
            # Potencial
            with col2:
                potencial = datos_vendedor.get('potencial', 'N/D')
                st.markdown(f"""
                <div style='border:1px solid #ddd; padding:15px; border-radius:10px; text-align:center; background-color:#f8f9fa;'>
                    <h4 style='margin-top:0;'>Potencial</h4>
                    <h2 style='color:{obtener_color(potencial) if isinstance(potencial, (int, float)) else "#333"};'>
                        {potencial if isinstance(potencial, str) else f"{potencial:.1f}"}/5
                    </h2>
                </div>
                """, unsafe_allow_html=True)
            
            # Segmento
            with col3:
                segmento = datos_vendedor.get('segmento', 'N/D')
                desc_segmento = descripcion_segmentos.get(segmento, "Sin descripción disponible")
                st.markdown(f"""
                <div style='border:1px solid #ddd; padding:15px; border-radius:10px; background-color:#f8f9fa;'>
                    <h4 style='margin-top:0; text-align:center;'>Segmento</h4>
                    <div style='text-align:center; font-size:1.2em; margin-bottom:5px;'>{segmento}</div>
                    <div style='font-size:0.9em; color:#666; text-align:center;'>{desc_segmento[:80]}...</div>
                </div>
                """, unsafe_allow_html=True)

                # Mapeo de columnas cualitativas a títulos
        columnas_cualitativas = {
            "fortalezas_mas_destacadas": ("🌟 Fortalezas Destacadas", "#2ecc71"),  # Verde
            "oportunidades_de_mejora": ("📉 Oportunidades de Mejora", "#e74c3c"),  # Rojo
            "recomendaciones_especificas_de_formacion": ("🎓 Recomendaciones", "#3498db")  # Azul
        }

        # Crear columnas
        cols = st.columns(len(columnas_cualitativas))

        for (col_name, (title, color)), col in zip(columnas_cualitativas.items(), cols):
            with col:
                # Crear un contenedor con borde
                with st.container(border=True):
                    # Header con color
                    st.markdown(f"<h4 style='color:{color}'>{title}</h4>", unsafe_allow_html=True)
                    
                    # Contenido
                    if col_name in eval_sel:
                        contenido = eval_sel[col_name]
                        if pd.isna(contenido) or str(contenido).strip() == "":
                            st.warning("Información no disponible")
                        else:
                            st.markdown(f"<div style='padding:10px;'>{contenido.strip()}</div>", 
                                    unsafe_allow_html=True)
                    else:
                        st.error("Dato no encontrado en evaluación")
        
        # Separador visual
        st.markdown("---")
        
        # --- Sección de evaluación por categorías ---
        st.markdown("### 📋 Evaluación por Competencias")
        
        # Dividir categorías en 2 columnas para mejor distribución
        col_cat1, col_cat2 = st.columns(2)
        
        for i, (categoria, columnas) in enumerate(categorias_detalladas.items()):
            # Alternar entre columnas
            target_col = col_cat1 if i % 2 == 0 else col_cat2
            
            with target_col:
                # Obtener puntaje de la categoría
                puntaje_categoria = datos_vendedor.get(categoria, 0)
                color_categoria = obtener_color(puntaje_categoria)
                
                # Tarjeta de categoría
                with st.container():
                    st.markdown(f"""
                    <div style='border:1px solid #ddd; padding:12px; border-radius:8px; margin-bottom:15px; 
                                border-left:5px solid {color_categoria}; background-color:#f8f9fa;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <h4 style='margin:0;'>{categoria}</h4>
                            <span style='font-weight:bold; color:{color_categoria};'>{puntaje_categoria:.1f}/5</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Subcategorías (mostrar como lista)
                    st.markdown("<div style='margin-left:20px; margin-top:5px;'>", unsafe_allow_html=True)
                    for col in columnas:
                        if col in datos_vendedor:
                            valor = datos_vendedor[col]
                            if isinstance(valor, (int, float)):
                                color = obtener_color(valor)
                                valor_str = f"{valor:.1f}/5"
                            else:
                                color = "#95a5a6"  # Gris
                                valor_str = str(valor)
                            
                            st.markdown(
                                f"<div style='padding: 5px; margin-bottom: 5px;'>"
                                f"<span style='color:{color}; font-weight:bold;'>•</span> "
                                f"{col.replace('_', ' ').title()}: <span style='font-weight:bold;'>{valor_str}</span>"
                                "</div>",
                                unsafe_allow_html=True
                            )
                    st.markdown("</div>", unsafe_allow_html=True)
        
        # Separador visual
        st.markdown("---")
        
        # --- Gráfico de radar ---
        st.markdown("### 📊 Visualización por Áreas")
        
        # Preparar datos para el radar
        categorias_radar = list(categorias_detalladas.keys())
        valores_radar = [datos_vendedor.get(c, 0) for c in categorias_radar]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=valores_radar,
            theta=categorias_radar,
            fill='toself',
            name=vendedor_sel,
            line_color='#3498db',
            fillcolor='rgba(52, 152, 219, 0.2)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5]
                )),
            showlegend=False,
            margin=dict(l=50, r=50, t=30, b=50),
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # --- Sección de recomendaciones ---
        st.markdown("---")
        st.markdown("### 🎯 Recomendaciones Clave")
        
        # Generar recomendaciones basadas en el segmento
        segmento = datos_vendedor.get('segmento', 'N/D')
        
        if segmento == "🟢 Alto Desempeño & Alto Potencial":
            st.success("""
            **Estrategia recomendada:** Desarrollo de liderazgo
            - Asignar proyectos estratégicos o mentorías
            - Considerar para programas de alto potencial
            - Proporcionar desafíos adicionales para mantener el compromiso
            """)
        elif segmento == "🟡 Buen Desempeño pero Bajo Potencial":
            st.info("""
            **Estrategia recomendada:** Mantenimiento y especialización
            - Reconocer y recompensar consistencia
            - Desarrollar en áreas técnicas específicas
            - Considerar roles especializados
            """)
        elif segmento == "🟠 Alto Potencial pero Bajo Desempeño":
            st.warning("""
            **Estrategia recomendada:** Desarrollo acelerado
            - Implementar plan de mejora con mentoría
            - Capacitación focalizada en brechas de desempeño
            - Establecer metas claras con seguimiento frecuente
            """)
        elif segmento == "🔴 Bajo Desempeño & Bajo Potencial":
            st.error("""
            **Estrategia recomendada:** Acción correctiva
            - Plan de mejora con objetivos y plazos definidos
            - Revisión de adecuación al puesto
            - Considerar rotación o reemplazo si no hay mejora
            """)
        else:
            st.warning("""
            **Estrategia recomendada:** Evaluación detallada
            - Análisis individualizado de fortalezas y debilidades
            - Plan de desarrollo personalizado
            - Seguimiento cercano para identificar patrones
            """)

# =============================================
# MOSTRAR LEYENDAS DE MATRICES
# =============================================
def mostrar_matrices_talento():
    st.markdown("""
    <style>
    .segment-card {
        border-left: 5px solid;
        padding: 12px;
        margin-bottom: 15px;
        border-radius: 5px;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .matrix-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin: 15px 0;
    }
    .matrix-cell {
        padding: 12px;
        border-radius: 5px;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .matrix-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    .matrix-table th, .matrix-table td {
        padding: 10px;
        text-align: center;
        border: 1px solid #ddd;
    }
    .matrix-table th {
        background-color: #3498db;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Matriz 4-Box ---
    st.markdown("### 📌 Matriz de Talento (4-Box) - Explicación de Segmentos")
    
    # Estrellas
    st.markdown("""
    <div class='segment-card' style='border-color: #2ecc71;'>
        <h4 style='margin:0; color: #2ecc71;'>🟢 Estrellas - Alto Desempeño & Alto Potencial</h4>
        <p style='margin:5px 0;'><b>Descripción:</b> Colaboradores con excelentes resultados actuales y gran potencial de crecimiento.</p>
        <p style='margin:5px 0;'><b>Acciones:</b> Desarrollo de liderazgo, proyectos estratégicos, planes de sucesión.</p>
        <p style='margin:5px 0;'><b>Riesgo:</b> Pérdida por falta de desafíos o reconocimiento.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mantenedores
    st.markdown("""
    <div class='segment-card' style='border-color: #f39c12;'>
        <h4 style='margin:0; color: #f39c12;'>🟡 Mantenedores - Buen Desempeño / Bajo Potencial</h4>
        <p style='margin:5px 0;'><b>Descripción:</b> Consistentes en su rol actual pero con limitado crecimiento.</p>
        <p style='margin:5px 0;'><b>Acciones:</b> Reconocimiento, especialización, roles estables.</p>
        <p style='margin:5px 0;'><b>Riesgo:</b> Estancamiento si no se les valora adecuadamente.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Potenciales
    st.markdown("""
    <div class='segment-card' style='border-color: #e67e22;'>
        <h4 style='margin:0; color: #e67e22;'>🟠 Potenciales - Alto Potencial / Bajo Desempeño</h4>
        <p style='margin:5px 0;'><b>Descripción:</b> Tienen capacidades pero no están rindiendo al máximo.</p>
        <p style='margin:5px 0;'><b>Acciones:</b> Mentoría, capacitación focalizada, claridad de expectativas.</p>
        <p style='margin:5px 0;'><b>Riesgo:</b> Frustración si no se les da oportunidades.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Riesgos
    st.markdown("""
    <div class='segment-card' style='border-color: #e74c3c;'>
        <h4 style='margin:0; color: #e74c3c;'>🔴 Riesgos - Bajo Desempeño & Bajo Potencial</h4>
        <p style='margin:5px 0;'><b>Descripción:</b> Bajo rendimiento y poca proyección de mejora.</p>
        <p style='margin:5px 0;'><b>Acciones:</b> Planes de mejora, reubicación o salida.</p>
        <p style='margin:5px 0;'><b>Riesgo:</b> Impacto negativo en el equipo si no se actúa.</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Matriz 9-Box ---
    st.markdown("### 🧩 Matriz 9-Box - Explicación Detallada")
    
    # Tabla resumen
    st.markdown("""
    <table class='matrix-table'>
        <tr>
            <th>Desempeño\Potencial</th>
            <th>Bajo</th>
            <th>Medio</th>
            <th>Alto</th>
        </tr>
        <tr>
            <td style='font-weight: bold; background-color: #f2f2f2;'>Alto</td>
            <td style='background-color: #fef9e7;'>6. Expertos Técnicos</td>
            <td style='background-color: #e8f8f5;'>8. Futuros Líderes</td>
            <td style='background-color: #d5f5e3;'>9. Estrellas</td>
        </tr>
        <tr>
            <td style='font-weight: bold; background-color: #f2f2f2;'>Medio</td>
            <td style='background-color: #fdebd0;'>5. Colaboradores Clave</td>
            <td style='background-color: #d4e6f1;'>7. Profesionales en Desarrollo</td>
            <td style='background-color: #aed6f1;'>2. Talentos Emergentes</td>
        </tr>
        <tr>
            <td style='font-weight: bold; background-color: #f2f2f2;'>Bajo</td>
            <td style='background-color: #fadbd8;'>1. Bajo Rendimiento</td>
            <td style='background-color: #e8daef;'>4. En Desarrollo</td>
            <td style='background-color: #d2b4de;'>3. Diamantes en Bruto</td>
        </tr>
    </table>
    """, unsafe_allow_html=True)
    
    # Explicación detallada
    st.markdown("""
    <div class='matrix-grid'>
        <div class='matrix-cell' style='background-color: #fadbd8;'>
            <b>1. Bajo Rendimiento</b>
            <p style='margin:5px 0; font-size:13px;'>Necesitan mejora inmediata o salida</p>
        </div>
        <div class='matrix-cell' style='background-color: #aed6f1;'>
            <b>2. Talentos Emergentes</b>
            <p style='margin:5px 0; font-size:13px;'>Buen potencial pero desempeño irregular</p>
        </div>
        <div class='matrix-cell' style='background-color: #d2b4de;'>
            <b>3. Diamantes en Bruto</b>
            <p style='margin:5px 0; font-size:13px;'>Alto potencial oculto por bajo desempeño</p>
        </div>
        <div class='matrix-cell' style='background-color: #e8daef;'>
            <b>4. En Desarrollo</b>
            <p style='margin:5px 0; font-size:13px;'>Requieren más tiempo y apoyo</p>
        </div>
        <div class='matrix-cell' style='background-color: #fdebd0;'>
            <b>5. Colaboradores Clave</b>
            <p style='margin:5px 0; font-size:13px;'>Valiosos para operación actual</p>
        </div>
        <div class='matrix-cell' style='background-color: #fef9e7;'>
            <b>6. Expertos Técnicos</b>
            <p style='margin:5px 0; font-size:13px;'>Especialistas sin interés en crecimiento</p>
        </div>
        <div class='matrix-cell' style='background-color: #d4e6f1;'>
            <b>7. Profesionales en Desarrollo</b>
            <p style='margin:5px 0; font-size:13px;'>En camino a mayores responsabilidades</p>
        </div>
        <div class='matrix-cell' style='background-color: #e8f8f5;'>
            <b>8. Futuros Líderes</b>
            <p style='margin:5px 0; font-size:13px;'>Próximos a convertirse en estrellas</p>
        </div>
        <div class='matrix-cell' style='background-color: #d5f5e3;'>
            <b>9. Estrellas</b>
            <p style='margin:5px 0; font-size:13px;'>Máximo desempeño y potencial</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================
# PROCESAMIENTO DE DATOS
# =============================================
def procesar_datos(df_eval):
    try:
        # Normalizar nombres de columnas
        df_eval.columns = df_eval.columns.str.lower().str.replace(' ', '_').str.replace('?', '')
        
        # Calcular promedios por categoría detallada
        for categoria, columnas in categorias_detalladas.items():
            columnas_existentes = [col for col in columnas if col in df_eval.columns]
            df_eval[categoria] = df_eval[columnas_existentes].mean(axis=1) if columnas_existentes else np.nan
        
        # Calcular puntaje total (promedio de todas las categorías principales)
        categorias_principales = [
            "EFICACIA EN RUTA",
            "VENTA Y NEGOCIACIÓN", 
            "RELACIÓN CON CLIENTES",
            "ORDEN Y EJECUCIÓN EN EL PUNTO DE VENTA",
            "COMPORTAMIENTO Y ACTITUD",
            "CAPACIDAD DE AUTOGESTIÓN",
            "SEGURIDAD Y CONDUCCIÓN"
        ]
        df_eval['puntaje_total'] = df_eval[categorias_principales].mean(axis=1)
        
        # Calcular potencial (basado en categorías de desarrollo)
        categorias_potencial = [
            "POTENCIAL DE DESARROLLO",
            "HABILIDADES",
            "ACTITUDES",
            "APTITUDES"
        ]
        df_eval['potencial'] = df_eval[categorias_potencial].mean(axis=1)
        
        # Segmentación del equipo
        condiciones = [
            (df_eval['puntaje_total'] >= 4.5) & (df_eval['potencial'] >= 4.5),
            (df_eval['puntaje_total'] >= 4.5) & (df_eval['potencial'] < 4.5),
            (df_eval['puntaje_total'] < 4.5) & (df_eval['potencial'] >= 4.5),
            (df_eval['puntaje_total'] < 4.5) & (df_eval['potencial'] < 4.5)
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
    
def generar_alertas(df_eval, df_cump):
    alertas = []
    
    # 1. Alertas por bajo desempeño prolongado
    if not df_cump.empty:
        df_bajo_cump = df_cump.copy()
        
        # Convertir cumplimiento a numérico de manera robusta
        if not pd.api.types.is_numeric_dtype(df_bajo_cump['cumplimiento']):
            # Si no es numérico, intentar convertir de string con %
            df_bajo_cump['cumplimiento_num'] = (
                df_bajo_cump['cumplimiento']
                .astype(str)  # Convertir a string primero
                .str.replace('%', '')
                .str.replace(',', '.')
                .replace('nan', np.nan)
                .replace('', np.nan)
                .astype(float) / 100
            )
        else:
            # Si ya es numérico, asegurar que esté en escala 0-1
            df_bajo_cump['cumplimiento_num'] = df_bajo_cump['cumplimiento'] / 100
        
        # Identificar vendedores con 3+ meses bajo el 70%
        df_bajo_cump['bajo_rendimiento'] = df_bajo_cump['cumplimiento_num'] < 0.7
        bajo_3_meses = df_bajo_cump.groupby('vendedor')['bajo_rendimiento'].sum() >= 3
        
        for vendedor in bajo_3_meses[bajo_3_meses].index:
            alertas.append({
                "tipo": "🔴 Bajo rendimiento prolongado",
                "mensaje": f"{vendedor} lleva 3+ meses con cumplimiento bajo 70%",
                "prioridad": "Alta",
                "accion": "Revisar plan de mejora y considerar acciones"
            })
    
    # 2. Alertas por alto potencial sin plan
    if 'potencial' in df_eval.columns:
        df_alto_potencial = df_eval[df_eval['potencial'] >= 4.5]
        for _, row in df_alto_potencial.iterrows():
            if pd.isna(row.get('plan_desarrollo', None)) or str(row.get('plan_desarrollo', '')).strip() == '':
                alertas.append({
                    "tipo": "🟡 Alto potencial sin plan",
                    "mensaje": f"{row['ruta']} tiene alto potencial pero no tiene plan de desarrollo asignado",
                    "prioridad": "Media",
                    "accion": "Asignar mentor y plan de desarrollo"
                })
    
    # 3. Alertas por equipos en riesgo
    if 'supervisor' in df_eval.columns and 'segmento' in df_eval.columns:
        df_equipos = df_eval.groupby('supervisor').agg({
            'ruta': 'count',
            'segmento': lambda x: (x == "🔴 Bajo Desempeño & Bajo Potencial").sum()
        })
        df_equipos['porcentaje_riesgo'] = df_equipos['segmento'] / df_equipos['ruta']
        
        for supervisor in df_equipos[df_equipos['porcentaje_riesgo'] > 0.3].index:
            alertas.append({
                "tipo": "🔴 Equipo en riesgo",
                "mensaje": f"El equipo de {supervisor} tiene {df_equipos.loc[supervisor, 'segmento']} vendedores en alto riesgo (>30%)",
                "prioridad": "Alta",
                "accion": "Revisar estrategia de supervisión y apoyo al líder"
            })
    
    return pd.DataFrame(alertas) if alertas else pd.DataFrame()

df_eval = procesar_datos(df_eval_orig.copy())

if 'puntaje_total' not in df_eval.columns:
    st.error(f"Columnas faltantes. Disponibles: {df_eval.columns.tolist()}")
    st.stop()

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
# FUNCIÓN PARA GENERAR RECOMENDACIONES
# =============================================

def generar_recomendaciones(vendedor, df_eval, categorias):
    """Genera recomendaciones de formación personalizadas"""
    datos = df_eval[df_eval['ruta'] == vendedor].iloc[0]
    recomendaciones = []
    
    # Umbrales para determinar necesidades
    UMBRAL_CRITICO = 2
    UMBRAL_MEJORA = 4
    
    for categoria, columnas in categorias.items():
        puntaje = datos[categoria]
        
        if puntaje < UMBRAL_CRITICO:
            severidad = "🔴 Crítico"
            cursos = {
                "Desempeño Comercial": ["Curso intensivo de técnicas de venta", "Taller de manejo de objeciones"],
                "Ejecución en Ruta": ["Capacitación en planificación de rutas", "Workshop de gestión del tiempo"],
                "Habilidades Blandas": ["Taller de comunicación efectiva", "Curso de inteligencia emocional"],
                "Autonomía": ["Programa de toma de decisiones", "Workshop de resolución de problemas"],
                "Herramientas": ["Entrenamiento en herramientas digitales", "Sesiones prácticas de reportes"]
            }.get(categoria, ["Curso genérico de desarrollo profesional"])
            
            recomendaciones.append({
                "Área": categoria,
                "Puntaje": puntaje,
                "Severidad": severidad,
                "Cursos Recomendados": cursos,
                "Prioridad": "Alta"
            })
            
        elif puntaje < UMBRAL_MEJORA:
            severidad = "🟡 Necesita mejora"
            cursos = {
                "Desempeño Comercial": ["Taller avanzado de ventas", "Sesión de mejores prácticas comerciales"],
                "Ejecución en Ruta": ["Optimización de rutas", "Webinar de productividad"],
                "Habilidades Blandas": ["Comunicación asertiva", "Taller de escucha activa"],
                "Autonomía": ["Autogestión efectiva", "Webinar de proactividad"],
                "Herramientas": ["Funciones avanzadas de herramientas", "Automatización de reportes"]
            }.get(categoria, ["Curso de desarrollo profesional intermedio"])
            
            recomendaciones.append({
                "Área": categoria,
                "Puntaje": puntaje,
                "Severidad": severidad,
                "Cursos Recomendados": cursos,
                "Prioridad": "Media"
            })
    
    return pd.DataFrame(recomendaciones)

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

            for categoria, columnas in categorias_detalladas.items():
                pdf.set_font('', 'B', 12)
                pdf.cell(0, 8, txt=categoria, ln=1)
                pdf.set_font('', '', 10)
                for col in columnas:
                    if col in datos_vendedor:
                        valor = datos_vendedor[col]
                        if isinstance(valor, (int, float)) and pd.notna(valor):
                            valor_str = f"{valor:.2f}/5"
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

        return pdf.output(dest='S')  # Ya devuelve bytes directamente

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
    try:
        media_total = df_eval['puntaje_total'].mean()
        media_potencial = df_eval['potencial'].mean()
    except KeyError as e:
        st.error(f"Error al calcular métricas: {str(e)}. Columnas disponibles: {df_eval.columns.tolist()}")
        media_total, media_potencial = 0, 0  # Valores por defecto

    # Métricas en columnas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Colaboradores", total_colaboradores)
    col2.metric("Total Supervisores", total_supervisores)
    col3.metric("Puntaje Promedio", f"{media_total:.1f}/5")
    col4.metric("Potencial Promedio", f"{media_potencial:.1f}/5")

    st.markdown("---")

        # Evaluación por áreas
    st.subheader("📌 Evaluación General por Áreas Clave")
    st.caption("Promedio del equipo en cada categoría de evaluación")

    avg_areas = {area: df_eval[area].mean() for area in categorias_detalladas.keys()}

    # Dividir las categorías en 2 grupos para mostrarlas en 2 filas
    categorias_lista = list(categorias_detalladas.keys())
    mitad = len(categorias_lista) // 2 + 1  # Ajuste para dividir mejor las categorías

    # Primera fila de métricas
    cols_fila1 = st.columns(mitad)
    for i, area in enumerate(categorias_lista[:mitad]):
        with cols_fila1[i]:
            promedio = avg_areas[area]
            if promedio >= 4.5:
                color = "green"
                emoji = "✅"
            elif promedio >= 3.5:
                color = "orange"
                emoji = "⚠️"
            else:
                color = "red"
                emoji = "❌"
            
            # Nombre abreviado para categorías largas
            nombre_abreviado = {
                "EFICACIA EN RUTA": "EFICACIA RUTA",
                "VENTA Y NEGOCIACIÓN": "VENTA/NEGOCIACIÓN",
                "RELACIÓN CON CLIENTES": "RELACIÓN CLIENTES",
                "ORDEN Y EJECUCIÓN EN EL PUNTO DE VENTA": "EJECUCIÓN PUNTO VENTA",
                "COMPORTAMIENTO Y ACTITUD": "COMPORTAMIENTO",
                "CAPACIDAD DE AUTOGESTIÓN": "AUTOGESTIÓN",
                "SEGURIDAD Y CONDUCCIÓN": "SEGURIDAD"
            }.get(area, area)
            
            st.markdown(f"<h3 style='color:{color}; font-size: 16px;'>{emoji} {nombre_abreviado}</h3>", unsafe_allow_html=True)
            st.metric("", f"{promedio:.1f}/5")

    # Segunda fila de métricas
    cols_fila2 = st.columns(len(categorias_lista[mitad:]))
    for i, area in enumerate(categorias_lista[mitad:]):
        with cols_fila2[i]:
            promedio = avg_areas[area]
            if promedio >= 4.5:
                color = "green"
                emoji = "✅"
            elif promedio >= 3.5:
                color = "orange"
                emoji = "⚠️"
            else:
                color = "red"
                emoji = "❌"
            
            nombre_abreviado = {
                "POTENCIAL DE DESARROLLO": "POTENCIAL",
                "HABILIDADES": "HABILIDADES",
                "ACTITUDES": "ACTITUDES",
                "APTITUDES": "APTITUDES"
            }.get(area, area)
            
            st.markdown(f"<h3 style='color:{color}; font-size: 16px;'>{emoji} {nombre_abreviado}</h3>", unsafe_allow_html=True)
            st.metric("", f"{promedio:.1f}/5")

        # Selector de supervisor basado en datos reales
    supervisores = df_eval['supervisor'].unique()
    supervisor_sel = st.selectbox("Seleccionar Supervisor", supervisores)
    
    st.markdown("---")
    
    # Sección 1: Resumen General
    st.subheader(f"📌 Resumen General - Equipo de {supervisor_sel}")
    
    # Filtrar datos por supervisor
    df_equipo = df_eval[df_eval['supervisor'] == supervisor_sel]
    
    # Calcular métricas
    total_vendedores = len(df_equipo)
    desempeno_promedio = df_equipo['puntaje_total'].mean()
    
    # Obtener rotación (simulado - necesitarías datos históricos)
    rotacion = "10%"  # Esto debería venir de tus datos históricos
    
    # Calcular cumplimiento promedio si hay datos
    if not df_cump.empty:
        cumplimiento_equipo = df_cump[df_cump['supervisor'] == supervisor_sel]
        if not cumplimiento_equipo.empty:
            cumplimiento_promedio = cumplimiento_equipo['cumplimiento_num'].mean() * 100
        else:
            cumplimiento_promedio = "N/D"
    else:
        cumplimiento_promedio = "N/D"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Vendedores", total_vendedores)
    
    with col2:
        st.metric("Desempeño Promedio", f"{desempeno_promedio:.1f}/5")
    
    with col3:
        st.metric("Rotación 6M", rotacion)
    
    with col4:
        st.metric("Cumplimiento", 
                 f"{cumplimiento_promedio:.1f}%" if isinstance(cumplimiento_promedio, (int, float)) else cumplimiento_promedio)
    
    # Sección 2: Top y Bottom Performers
    st.markdown("---")
    st.subheader("🏆 Top 5 y Bottom 5 Performers")
    
    # Ordenar vendedores por puntaje
    df_equipo_sorted = df_equipo.sort_values('puntaje_total', ascending=False)
    
    # Top 5
    top_vendedores = df_equipo_sorted.head(5)[['ruta', 'puntaje_total', 'segmento']]
    top_vendedores = top_vendedores.rename(columns={
        'ruta': 'Ruta',
        'puntaje_total': 'Puntaje',
        'segmento': 'Segmento'
    })
    
    # Bottom 5
    bottom_vendedores = df_equipo_sorted.tail(5)[['ruta', 'puntaje_total', 'segmento']]
    bottom_vendedores = bottom_vendedores.rename(columns={
        'ruta': 'Ruta',
        'puntaje_total': 'Puntaje',
        'segmento': 'Segmento'
    })
    
    col_top, col_bottom = st.columns(2)
    
    with col_top:
        st.markdown("##### 🏅 Top 5 Performers")
        st.dataframe(
            top_vendedores,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Puntaje": st.column_config.ProgressColumn(
                    "Puntaje",
                    format="%.1f",
                    min_value=0,
                    max_value=5
                )
            }
        )
    
    with col_bottom:
        st.markdown("##### ⚠️ Bottom 5 Performers")
        st.dataframe(
            bottom_vendedores,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Puntaje": st.column_config.ProgressColumn(
                    "Puntaje",
                    format="%.1f",
                    min_value=0,
                    max_value=5
                )
            }
        )
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

    # Mapa de calor de competencias
    st.subheader("🔥 Correlación entre Competencias")
    st.caption("Relación estadística entre las diferentes áreas evaluadas")
    
    # Preparar datos para el mapa de calor
    corr_matrix = df_eval[list(categorias_detalladas.keys())].corr().round(2)
    
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

    st.markdown("---")
    st.subheader("🔔 Alertas Automatizadas")
    
    df_alertas = generar_alertas(df_eval, df_cump)

    if not df_alertas.empty:
        # Filtrar por prioridad
        prioridad = st.selectbox("Filtrar por prioridad:", ["Todas", "Alta", "Media", "Baja"])
        if prioridad != "Todas":
            df_alertas = df_alertas[df_alertas['prioridad'] == prioridad]
        
        # Mostrar alertas
        for _, alerta in df_alertas.iterrows():
            if alerta['prioridad'] == "Alta":
                st.error(f"**{alerta['tipo']}** - {alerta['mensaje']}")
                st.caption(f"Acción recomendada: {alerta['accion']}")
            elif alerta['prioridad'] == "Media":
                st.warning(f"**{alerta['tipo']}** - {alerta['mensaje']}")
                st.caption(f"Acción recomendada: {alerta['accion']}")
            else:
                st.info(f"**{alerta['tipo']}** - {alerta['mensaje']}")
                st.caption(f"Acción recomendada: {alerta['accion']}")
    else:
        st.success("✅ No hay alertas críticas para mostrar")    

            # Sección 5: Recomendaciones Iniciales
    st.markdown("---")
    st.subheader("🎯 Recomendaciones Iniciales")
    
    # Recomendaciones basadas en segmentación
    num_alto_riesgo = len(df_equipo[df_equipo['segmento'] == "🔴 Bajo Desempeño & Bajo Potencial"])
    num_alto_potencial = len(df_equipo[df_equipo['segmento'].isin(["🟢 Alto Desempeño & Alto Potencial", "🟠 Alto Potencial pero Bajo Desempeño"])])
    
    st.markdown(f"""
    Basado en el análisis del equipo de **{supervisor_sel}** ({total_vendedores} vendedores):
    
    1. **Enfoque inmediato:**
       - {num_alto_riesgo} vendedores en alto riesgo requieren planes de mejora
       - {num_alto_potencial} vendedores con alto potencial para desarrollar
    
    2. **Acciones recomendadas:**
       - Revisión 1:1 con bottom performers
       - Asignar mentorías cruzadas (top → alto potencial)
       - Taller de habilidades clave para el segmento predominante
    
    3. **Seguimiento sugerido:**
       - Revisión semanal de métricas clave
       - Evaluación mensual de progreso
       - Ajuste de rutas y asignaciones
    """)
    

elif vista == "Individual":
    st.header("👤 Vista Individual")
    st.markdown("""
    **Análisis detallado** por vendedor, incluyendo evaluación por Competencias, seguimiento de visitas 
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
    segmento = eval_sel['segmento']
    
    # Pestañas para vista individual
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Resumen", "🔄 Seguimiento", "📈 Indicadores", "🎯 Plan de Desarrollo", "🎓 Recomendaciones"])

    with tab1:

    # Mostrar resumen de desempeño detallado
        mostrar_resumen_desempeno(vendedor_sel, df_eval)
        
        # Nueva sección: Potencial para supervisor
        st.subheader("🔍 Potencial para Supervisor")
        potencial_supervisor = "Sí" if (eval_sel['potencial'] >= 4.5 and eval_sel['HABILIDADES'] >= 4.5) else "Con desarrollo" if (eval_sel['potencial'] >= 3.5) else "No"
        
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
            st.metric("📅 Antigüedad", tiempo_compania, "Meses", help="Tiempo en el puesto actual")

        with cols_hr[1]:
            if not df_cump.empty:
                df_vend_cump = df_cump[df_cump['vendedor'] == vendedor_sel].copy()
                if not df_vend_cump.empty:
                    # Convertir cumplimiento a numérico
                    df_vend_cump['cumplimiento_num'] = (
                        df_vend_cump['cumplimiento']
                        .astype(str)
                        .str.replace('%', '')
                        .replace('nan', np.nan)
                        .astype(float) / 100
                    )
                    
                    df_vend_cump = df_vend_cump.sort_values(['year', 'mes'])
                    tendencia = "↑ Mejorando" if df_vend_cump['cumplimiento_num'].iloc[-1] > df_vend_cump['cumplimiento_num'].iloc[0] else "↓ Empeorando"
                    st.metric("📈 Tendencia Cumplimiento", tendencia)

        with cols_hr[2]:
            puntaje_total = eval_sel.get('puntaje_total', 0)
            if puntaje_total >= 4.5:
                consistencia = "Alta"
                color = "green"
            elif puntaje_total >= 3.5:
                consistencia = "Media"
                color = "orange"
            else:
                consistencia = "Baja"
                color = "red"
            st.markdown("🔄 **Consistencia**")
            st.markdown(f"<span style='color:{color}; font-size: 20px'>{consistencia}</span>", unsafe_allow_html=True)

        with cols_hr[3]:
            potencial = eval_sel.get('potencial', 0)
            if potencial >= 4.5:
                nivel_potencial = "Alto"
                color = "green"
            elif potencial >= 3.5:
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
                "Alto" if puntaje_total >= 4.5 else "Medio" if puntaje_total >= 3.5 else "Bajo",
                nivel_potencial,
                tendencia if 'tendencia' in locals() else "N/D",
                consistencia,
                "Alto"
            ],
            "Recomendación": [
                "Mantener/Desarrollar" if puntaje_total >= 4.5 else "Capacitar" if puntaje_total >= 3.5 else "Revisar",
                "Invertir en desarrollo" if potencial >= 4.5 else "Monitorear" if potencial >= 3.5 else "Limitar inversión",
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
        st.subheader("📄 Generar Reportes Formales")
        
        col_pdf1, col_pdf2, col_pdf3 = st.columns(3)
        
        with col_pdf1:
            if st.button("📄 Generar Perfil PDF"):
                pdf_bytes = generar_pdf_perfil(vendedor_sel, df_eval, df_seg_orig, df_cump_orig, df_info_orig, "general")
                if pdf_bytes:
                    st.download_button(
                        label="⬇️ Descargar Perfil Completo",
                        data=pdf_bytes,  # Ya son bytes, no necesitas encode
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
    
    with tab3:
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
    
    with tab4:
        st.subheader("🎯 Plan de Desarrollo Personalizado")
        
        # Sección de recomendaciones específicas
        st.markdown("### 📚 Recomendaciones Específicas de Formación")
        
        if eval_sel['HABILIDADES'] < 2.9:
            st.markdown("""
            #### 🧠 Habilidades Blandas
            - **Curso recomendado:** Comunicación Efectiva y Manejo de Objeciones
            - **Duración:** 8 horas
            - **Modalidad:** Taller práctico
            - **Objetivo:** Mejorar capacidad de escucha activa y manejo de objeciones
            """)
        
        if eval_sel['CAPACIDAD DE AUTOGESTIÓN'] < 2.9:
            st.markdown("""
            #### 🦅 Autonomía
            - **Curso recomendado:** Toma de Decisiones y Resolución de Problemas
            - **Duración:** 12 horas
            - **Modalidad:** Online con casos prácticos
            - **Objetivo:** Desarrollar pensamiento crítico y autonomía
            """)
        
        if eval_sel['HABILIDADES'] < 2.9:
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

    with tab5:
        st.subheader("🎓 Recomendaciones de Formación")
        
        df_recomendaciones = generar_recomendaciones(vendedor_sel, df_eval, categorias_detalladas)
        
        if not df_recomendaciones.empty:
            st.dataframe(
                df_recomendaciones.sort_values('Prioridad', ascending=False),
                column_config={
                    "Cursos Recomendados": st.column_config.ListColumn(
                        "Cursos Recomendados",
                        help="Lista de cursos sugeridos para mejorar en esta área"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Generar resumen ejecutivo
            st.markdown("#### 📋 Resumen de Necesidades")
            
            criticos = df_recomendaciones[df_recomendaciones['Severidad'] == "🔴 Crítico"]
            if not criticos.empty:
                st.error(f"**Áreas críticas ({len(criticos)}):** {', '.join(criticos['Área'])}")
            
            mejoras = df_recomendaciones[df_recomendaciones['Severidad'] == "🟡 Necesita mejora"]
            if not mejoras.empty:
                st.warning(f"**Áreas a mejorar ({len(mejoras)}):** {', '.join(mejoras['Área'])}")
                
            # Botón para generar plan de formación
            if st.button("📄 Generar Plan de Formación PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                pdf.cell(0, 10, f"Plan de Formación para {vendedor_sel}", ln=1, align='C')
                pdf.ln(10)
                
                for _, row in df_recomendaciones.iterrows():
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, f"Área: {row['Área']} ({row['Puntaje']}/5) - {row['Severidad']}", ln=1)
                    pdf.set_font("Arial", '', 10)
                    
                    for curso in row['Cursos Recomendados']:
                        pdf.cell(10)  # Indentación
                        pdf.cell(0, 8, f"- {curso}", ln=1)
                    
                    pdf.ln(5)
                
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button(
                    label="⬇️ Descargar Plan de Formación",
                    data=pdf_bytes,
                    file_name=f"Plan_Formacion_{vendedor_sel}.pdf",
                    mime="application/pdf"
                )
        else:
            st.success("✅ Todas las áreas tienen un buen desempeño. No se requieren acciones de formación inmediatas.")

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
        df_filtrado = df_filtrado[df_filtrado['ruta'].isin(ruta_sel)]
    
    # Pestañas para vista de equipo
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Ranking", "🧩 Matriz de Talento", "📊 Análisis por Área", "🧩 Matriz 9-Box de Talento"])
    
    with tab1:
        st.subheader("Ranking de Vendedores")
        st.caption("Comparativa de desempeño según diferentes métricas")
        
        metrica_ranking = st.selectbox("Ordenar por", ["Puntaje Total", "Potencial"] + list(categorias_detalladas.keys()))
        
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
                dict(type='line', x0=4.5, x1=4.5, y0=0, y1=5, line=dict(color='gray', dash='dot')),
                dict(type='line', x0=0, x1=5, y0=4.5, y1=4.5, line=dict(color='gray', dash='dot')),
                dict(type='rect', x0=4.5, x1=5, y0=4.5, y1=5, line=dict(color='green'), opacity=0.1),
                dict(type='rect', x0=0, x1=4.5, y0=4.5, y1=5, line=dict(color='orange'), opacity=0.1),
                dict(type='rect', x0=4.5, x1=5, y0=0, y1=4.5, line=dict(color='yellow'), opacity=0.1),
                dict(type='rect', x0=0, x1=4.5, y0=0, y1=4.5, line=dict(color='red'), opacity=0.1)
            ],
            annotations=[
                dict(x=4.75, y=4.75, text="Estrellas", showarrow=False, font=dict(color='green')),
                dict(x=2.25, y=4.75, text="Potenciales", showarrow=False, font=dict(color='orange')),
                dict(x=4.75, y=2.25, text="Mantenedores", showarrow=False, font=dict(color='gold')),
                dict(x=2.25, y=2.25, text="Riesgos", showarrow=False, font=dict(color='red'))
            ],
            height=600,
            margin=dict(l=20, r=20, t=40, b=20)  # Margenes ajustados
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
        
        area_sel = st.selectbox("Seleccionar área para análisis", list(categorias_detalladas.keys()))
        
        # Datos para el área seleccionada
        df_area = df_filtrado[['ruta', 'supervisor', area_sel, 'segmento']].sort_values(area_sel, ascending=False)
        promedio_area = df_eval[area_sel].mean()
        
        # Crear columna 'estado' basada en los valores del área seleccionada
        df_area['estado'] = pd.cut(
            df_area[area_sel],
            bins=[0, 3.5, 4.5, 5],
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
            if stats_area["Promedio"] < 3.5:
                st.error("**Área crítica** que requiere intervención inmediata")
                st.markdown("""
                - Talleres intensivos para todo el equipo
                - Acompañamiento cercano de supervisores
                - Revisión de procesos y herramientas
                """)
            elif stats_area["Promedio"] < 4.5:
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

    with tab4:
        st.subheader("🧩 Matriz 9-Box de Talento")
        
        # Definir los límites para la matriz 9-box
        desempeno_limites = [0, 3.5, 4.5, 5]
        potencial_limites = [0, 3.5, 4.5, 5]
        
        # Crear la figura
        fig = px.scatter(
            df_filtrado,
            x='puntaje_total',
            y='potencial',
            color='supervisor',
            hover_name='ruta',
            text='ruta',
            labels={'puntaje_total': 'Desempeño', 'potencial': 'Potencial'},
            title="Matriz 9-Box de Talento",
            range_x=[0,5],
            range_y=[0,5]
        )
        
        # Añadir líneas y zonas
        fig.update_layout(
            shapes=[
                # Líneas verticales
                dict(type='line', x0=desempeno_limites[1], x1=desempeno_limites[1], y0=0, y1=5, line=dict(color='gray', dash='dot')),
                dict(type='line', x0=desempeno_limites[2], x1=desempeno_limites[2], y0=0, y1=5, line=dict(color='gray', dash='dot')),
                # Líneas horizontales
                dict(type='line', x0=0, x1=5, y0=potencial_limites[1], y1=potencial_limites[1], line=dict(color='gray', dash='dot')),
                dict(type='line', x0=0, x1=5, y0=potencial_limites[2], y1=potencial_limites[2], line=dict(color='gray', dash='dot')),
                # Zonas coloreadas (semi-transparentes)
                dict(type='rect', x0=desempeno_limites[2], x1=5, y0=potencial_limites[2], y1=5, line=dict(color='green'), opacity=0.1, fillcolor='green'),
                dict(type='rect', x0=desempeno_limites[1], x1=desempeno_limites[2], y0=potencial_limites[2], y1=5, line=dict(color='limegreen'), opacity=0.1, fillcolor='limegreen'),
                dict(type='rect', x0=desempeno_limites[2], x1=5, y0=potencial_limites[1], y1=potencial_limites[2], line=dict(color='limegreen'), opacity=0.1, fillcolor='limegreen'),
                dict(type='rect', x0=0, x1=desempeno_limites[1], y0=potencial_limites[2], y1=5, line=dict(color='orange'), opacity=0.1, fillcolor='orange'),
                dict(type='rect', x0=desempeno_limites[1], x1=desempeno_limites[2], y0=potencial_limites[1], y1=potencial_limites[2], line=dict(color='yellow'), opacity=0.1, fillcolor='yellow'),
                dict(type='rect', x0=desempeno_limites[2], x1=5, y0=0, y1=potencial_limites[1], line=dict(color='yellow'), opacity=0.1, fillcolor='yellow'),
                dict(type='rect', x0=0, x1=desempeno_limites[1], y0=potencial_limites[1], y1=potencial_limites[2], line=dict(color='yellow'), opacity=0.1, fillcolor='yellow'),
                dict(type='rect', x0=desempeno_limites[1], x1=desempeno_limites[2], y0=0, y1=potencial_limites[1], line=dict(color='orangered'), opacity=0.1, fillcolor='orangered'),
                dict(type='rect', x0=0, x1=desempeno_limites[1], y0=0, y1=potencial_limites[1], line=dict(color='red'), opacity=0.1, fillcolor='red')
            ],
            annotations=[
                dict(x=4.75, y=4.75, text="Estrellas", showarrow=False, font=dict(size=14, color='green')),
                dict(x=4, y=4.75, text="Potencial Alto", showarrow=False, font=dict(size=12, color='limegreen')),
                dict(x=4.75, y=4, text="Desempeño Alto", showarrow=False, font=dict(size=12, color='limegreen')),
                dict(x=1.75, y=4.75, text="Futuro Incierto", showarrow=False, font=dict(size=12, color='orange')),
                dict(x=4, y=4, text="Core", showarrow=False, font=dict(size=14, color='gold')),
                dict(x=4.75, y=1.75, text="Mantenedores", showarrow=False, font=dict(size=12, color='gold')),
                dict(x=1.75, y=4, text="Riesgo Alto", showarrow=False, font=dict(size=12, color='orangered')),
                dict(x=4, y=1.75, text="Riesgo Medio", showarrow=False, font=dict(size=12, color='orangered')),
                dict(x=1.75, y=1.75, text="Riesgo Crítico", showarrow=False, font=dict(size=14, color='red'))
            ],
            height=700,
            margin=dict(l=20, r=20, t=40, b=20)  # Margenes ajustados
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Resumen por cuadrante
        st.subheader("📊 Distribución por Cuadrante")
        
        # Función para asignar cuadrantes
        def asignar_cuadrante(row):
            if row['puntaje_total'] >= desempeno_limites[2] and row['potencial'] >= potencial_limites[2]:
                return "Estrellas"
            elif row['puntaje_total'] >= desempeno_limites[2] and row['potencial'] >= potencial_limites[1]:
                return "Desempeño Alto"
            elif row['puntaje_total'] >= desempeno_limites[1] and row['potencial'] >= potencial_limites[2]:
                return "Potencial Alto"
            elif row['puntaje_total'] >= desempeno_limites[1] and row['potencial'] >= potencial_limites[1]:
                return "Core"
            elif row['puntaje_total'] >= desempeno_limites[2]:
                return "Mantenedores"
            elif row['potencial'] >= potencial_limites[2]:
                return "Futuro Incierto"
            elif row['potencial'] >= potencial_limites[1]:
                return "Riesgo Alto"
            elif row['puntaje_total'] >= desempeno_limites[1]:
                return "Riesgo Medio"
            else:
                return "Riesgo Crítico"
        
        df_filtrado['cuadrante'] = df_filtrado.apply(asignar_cuadrante, axis=1)
        
        # Mostrar distribución
        distribucion = df_filtrado['cuadrante'].value_counts().reset_index()
        distribucion.columns = ['Cuadrante', 'Cantidad']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.dataframe(distribucion, hide_index=True)
        
        with col2:
            fig_pie = px.pie(distribucion, values='Cantidad', names='Cuadrante',
                            color='Cuadrante',
                            color_discrete_map={
                                "Estrellas": "green",
                                "Potencial Alto": "limegreen",
                                "Desempeño Alto": "limegreen",
                                "Core": "gold",
                                "Mantenedores": "gold",
                                "Futuro Incierto": "orange",
                                "Riesgo Alto": "orangered",
                                "Riesgo Medio": "orangered",
                                "Riesgo Crítico": "red"
                            })
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Recomendaciones por cuadrante
        st.subheader("🎯 Acciones Recomendadas por Cuadrante")
        
        recomendaciones_cuadrantes = {
            "Estrellas": [
                "Desarrollar para roles de liderazgo",
                "Asignar proyectos estratégicos",
                "Mentoría inversa (que enseñen a otros)",
                "Plan de sucesión"
            ],
            "Potencial Alto": [
                "Invertir en desarrollo acelerado",
                "Mentoría con líderes senior",
                "Rotación controlada para ganar experiencia",
                "Metas desafiantes pero alcanzables"
            ],
            "Desempeño Alto": [
                "Reconocimiento y retención",
                "Especialización en su área",
                "Participación en proyectos cross",
                "Mentoría a colegas junior"
            ],
            "Core": [
                "Desarrollo de habilidades específicas",
                "Metas claras y alcanzables",
                "Feedback frecuente",
                "Programas de motivación"
            ],
            "Mantenedores": [
                "Reconocer contribución actual",
                "Entrenamiento para mejorar potencial",
                "Rotación limitada para evitar estancamiento",
                "Metas basadas en experiencia"
            ],
            "Futuro Incierto": [
                "Análisis individualizado",
                "Plan de mejora con plazos",
                "Capacitación intensiva",
                "Monitoreo cercano"
            ],
            "Riesgo Alto": [
                "Planes de mejora con hitos",
                "Capacitación básica",
                "Acompañamiento diario/semanal",
                "Evaluación periódica"
            ],
            "Riesgo Medio": [
                "Entrenamiento específico",
                "Metas a corto plazo",
                "Feedback constante",
                "Definir expectativas claras"
            ],
            "Riesgo Crítico": [
                "Acción correctiva inmediata",
                "Plazo definido para mejora",
                "Evaluar continuidad en el puesto",
                "Plan de contingencia"
            ]
        }
        
        cuadrante_seleccionado = st.selectbox("Ver acciones para:", distribucion['Cuadrante'])
        
        st.markdown(f"#### Acciones para {cuadrante_seleccionado}")
        for accion in recomendaciones_cuadrantes.get(cuadrante_seleccionado, ["No se definieron acciones específicas"]):
            st.markdown(f"- {accion}")

    # Llamar a la función en tu sección de equipo
    mostrar_matrices_talento()

# =============================================
# FOOTER
# =============================================
st.markdown("---")
st.caption("Sistema de Gestión Comercial 360 | © 2025 | Versión 2.1")
