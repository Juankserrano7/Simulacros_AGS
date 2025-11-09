import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Dashboard Simulacros ICFES",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado con Bootstrap 5 inspirado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* SIDEBAR STYLING - Bootstrap 5 Design */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b263b 50%, #415a77 100%);
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.1);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
    }
    
    /* Sidebar Header */
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 1.1rem;
        padding: 1rem 0;
        border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        margin-bottom: 1rem;
    }
    
    /* Radio Buttons Styling */
    [data-testid="stSidebar"] .row-widget.stRadio > div {
        background: transparent;
    }
    
    [data-testid="stSidebar"] .row-widget.stRadio > div > label {
        background: rgba(255, 255, 255, 0.1);
        color: #e0e1dd !important;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.1);
        cursor: pointer;
        display: flex;
        align-items: center;
        font-weight: 500;
    }
    
    [data-testid="stSidebar"] .row-widget.stRadio > div > label:hover {
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.3);
        transform: translateX(5px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    [data-testid="stSidebar"] .row-widget.stRadio > div > label[data-baseweb="radio"] > div:first-child {
        background-color: rgba(255, 255, 255, 0.3);
        border-color: rgba(255, 255, 255, 0.5);
    }
    
    [data-testid="stSidebar"] .row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: #667eea;
        color: white !important;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* Selectbox Styling */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 8px;
        color: white;
    }
    
    [data-testid="stSidebar"] .stSelectbox label {
        color: #e0e1dd !important;
        font-weight: 600;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.3);
        color: white;
    }
    
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"]:hover > div {
        border-color: rgba(255, 255, 255, 0.5);
        background: rgba(255, 255, 255, 0.2);
    }
    
    /* Divider */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2);
        margin: 1.5rem 0;
    }
    
    /* Sidebar Text */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] div {
        color: #e0e1dd;
    }
    
    /* Footer in Sidebar */
    [data-testid="stSidebar"] .sidebar-footer {
        background: rgba(0, 0, 0, 0.2);
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin-top: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Main Content Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .metric-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
    }
    
    .header-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .header-subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1.5rem 0;
        font-weight: 600;
    }
    
    .stats-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3);
    }
    
    .info-badge {
        display: inline-block;
        background: #17a2b8;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0.3rem;
    }
    
    .alert-success {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .alert-warning {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# Función para cargar datos
@st.cache_data
def cargar_datos():
    try:
        hp1 = pd.read_csv('HELMER_PARDO1.csv', skiprows=1)
        hp2 = pd.read_csv('HELMER_PARDO2.csv', skiprows=1)
        prep = pd.read_csv('Avancemos.csv', skiprows=1)
        
        # Limpiar nombres de columnas
        for df in [hp1, hp2, prep]:
            df.columns = df.columns.str.strip()
            df['ESTUDIANTE'] = df['ESTUDIANTE'].str.strip()
            
            # Eliminar filas con estudiantes vacíos o nulos
            df = df[df['ESTUDIANTE'].notna()]
            df = df[df['ESTUDIANTE'] != '']
            
            # Eliminar la fila de "PROMEDIO" o cualquier fila que no sea un estudiante real
            df = df[~df['ESTUDIANTE'].str.upper().str.contains('PROMEDIO', na=False)]
            df = df[~df['ESTUDIANTE'].str.upper().str.contains('TOTAL', na=False)]
            df = df[~df['ESTUDIANTE'].str.upper().str.contains('MEDIA', na=False)]
            
            # Eliminar filas duplicadas basándose en el nombre del estudiante
            df = df.drop_duplicates(subset=['ESTUDIANTE'], keep='first')
            
            # Resetear índices
            df = df.reset_index(drop=True)
        
        return hp1, hp2, prep
    except Exception as e:
        st.error(f"Error al cargar los archivos: {e}")
        st.info("Asegúrate de que los archivos CSV estén en el mismo directorio que el script.")
        return None, None, None

# Cargar datos
hp1, hp2, prep = cargar_datos()

# Verificar si los datos se cargaron correctamente
if hp1 is None or hp2 is None or prep is None:
    st.stop()

materias = ['LECTURA CRITICA', 'MATEMATICAS', 'SOCIALES Y CIUDADANAS', 
            'CIENCIAS NATURALES', 'INGLES']

# Sidebar con diseño Bootstrap 5
with st.sidebar:
    # Header del Sidebar
    st.markdown("""
    <div style='text-align: center; padding: 1.5rem 0; margin-bottom: 1rem;'>
        <h2 style='color: white; font-weight: 800; font-size: 1.8rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
            📊 ICFES Dashboard
        </h2>
        <p style='color: rgba(255,255,255,0.8); font-size: 0.85rem; margin-top: 0.5rem; letter-spacing: 1px;'>
            SISTEMA DE ANÁLISIS
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    
    # Navegación Principal
    st.markdown("### 🧭 NAVEGACIÓN")
    pagina = st.radio(
        "Navegación",
        ["🏠 Inicio", "📊 Reporte General", "🔄 Comparación Simulacros", 
         "👤 Análisis Individual", "📈 Progresión", "📉 Estadísticas Detalladas"],
        label_visibility="collapsed"
    )
    
    st.markdown("<hr style='margin: 1.5rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    
    # Filtros
    st.markdown("### 🎯 FILTROS")
    simulacro_seleccionado = st.selectbox(
        "📋 Simulacro Activo",
        ["Helmer Pardo 1", "Helmer Pardo 2", "Prepárate"]
    )
    
    st.markdown("<hr style='margin: 1.5rem 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    
    # Información del Sistema
    st.markdown("""
    <div class='sidebar-footer'>
        <div style='margin-bottom: 1rem;'>
            <span style='font-size: 2rem;'>🎓</span>
        </div>
        <h4 style='color: white; font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem;'>
            GRADO 11
        </h4>
        <p style='color: rgba(255,255,255,0.7); font-size: 0.85rem; margin: 0;'>
            Período 2024/2025
        </p>
        <div style='margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.1);'>
            <p style='color: rgba(255,255,255,0.6); font-size: 0.75rem; margin: 0;'>
                Sistema de Evaluación<br>y Seguimiento Académico
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Badge de versión
    st.markdown("""
    <div style='text-align: center; margin-top: 1rem;'>
        <span style='background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.7); 
                     padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.7rem; 
                     font-weight: 600; letter-spacing: 0.5px;'>
            v1.0.0
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Información de diagnóstico (expansible)
    with st.expander("🔍 Diagnóstico de Datos"):
        st.write(f"**HP1:** {len(hp1)} estudiantes")
        st.write(f"**HP2:** {len(hp2)} estudiantes")
        st.write(f"**Prepárate:** {len(prep)} estudiantes")

# Mapeo de simulacros
simulacros_map = {
    "Helmer Pardo 1": hp1,
    "Helmer Pardo 2": hp2,
    "Prepárate": prep
}

datos_actual = simulacros_map[simulacro_seleccionado]

# ==================== PÁGINA INICIO ====================
if pagina == "🏠 Inicio":
    st.markdown("<h1 class='header-title'>📊 Dashboard de Análisis de Simulacros ICFES</h1>", unsafe_allow_html=True)
    st.markdown("<p class='header-subtitle'>Sistema Integral de Evaluación y Seguimiento - Grado 11</p>", unsafe_allow_html=True)
    
    # Métricas principales con más información
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>📝 Simulacros</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>3</h2>
            <p style='color: #6c757d;'>HP1, HP2, Prepárate</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_estudiantes = len(hp1)
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>👥 Estudiantes</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>{total_estudiantes}</h2>
            <p style='color: #6c757d;'>Evaluados</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>📚 Áreas</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>5</h2>
            <p style='color: #6c757d;'>Materias ICFES</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_datos = len(hp1) + len(hp2) + len(prep)
        st.markdown(f"""
        <div class='metric-card'>
            <h3 style='color: #667eea;'>📋 Registros</h3>
            <h2 style='font-size: 3rem; color: #764ba2;'>{total_datos}</h2>
            <p style='color: #6c757d;'>Datos totales</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Análisis de Promedios Generales con más detalle
    st.markdown("<h2 class='section-header'>📊 Análisis Comparativo de Simulacros</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    promedios_generales = [
        hp1['PROMEDIO PONDERADO'].mean(),
        hp2['PROMEDIO PONDERADO'].mean(),
        prep['PROMEDIO PONDERADO'].mean()
    ]
    
    with col1:
        st.markdown("### 📈 Evolución de Promedios")
        
        promedios_data = pd.DataFrame({
            'Simulacro': ['Helmer Pardo 1', 'Helmer Pardo 2', 'Prepárate'],
            'Promedio': promedios_generales,
            'Desv. Est.': [hp1['PROMEDIO PONDERADO'].std(), 
                          hp2['PROMEDIO PONDERADO'].std(), 
                          prep['PROMEDIO PONDERADO'].std()]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=promedios_data['Simulacro'],
            y=promedios_data['Promedio'],
            marker_color=['#27ae60', '#f39c12', '#e74c3c'],
            text=[f'{p:.1f}' for p in promedios_data['Promedio']],
            textposition='outside',
            name='Promedio'
        ))
        fig.update_layout(
            height=400,
            showlegend=False,
            yaxis_title="Puntaje Promedio",
            template="plotly_white"
        )
        st.plotly_chart(fig, width="stretch")
        
        # Tabla de cambios
        cambio_1_2 = promedios_generales[1] - promedios_generales[0]
        cambio_2_3 = promedios_generales[2] - promedios_generales[1]
        cambio_total = promedios_generales[2] - promedios_generales[0]
        
        st.markdown("#### 📉 Variaciones Detectadas")
        cambios_df = pd.DataFrame({
            'Transición': ['HP1 → HP2', 'HP2 → Prep', 'HP1 → Prep'],
            'Cambio': [cambio_1_2, cambio_2_3, cambio_total],
            'Porcentaje': [
                (cambio_1_2/promedios_generales[0]*100),
                (cambio_2_3/promedios_generales[1]*100),
                (cambio_total/promedios_generales[0]*100)
            ]
        })
        cambios_df['Cambio'] = cambios_df['Cambio'].round(2)
        cambios_df['Porcentaje'] = cambios_df['Porcentaje'].round(2).astype(str) + '%'
        st.dataframe(cambios_df, width="stretch", hide_index=True)
    
    with col2:
        st.markdown("### 📊 Distribución de Rendimiento por Simulacro")
        
        # Calcular distribuciones para cada simulacro
        def calcular_distribucion(df):
            alto = len(df[df['PROMEDIO PONDERADO'] >= 300])
            medio = len(df[(df['PROMEDIO PONDERADO'] >= 250) & (df['PROMEDIO PONDERADO'] < 300)])
            bajo = len(df[df['PROMEDIO PONDERADO'] < 250])
            return [alto, medio, bajo]
        
        dist_hp1 = calcular_distribucion(hp1)
        dist_hp2 = calcular_distribucion(hp2)
        dist_prep = calcular_distribucion(prep)
        
        fig = go.Figure()
        categorias = ['Alto (≥300)', 'Medio (250-299)', 'Bajo (<250)']
        
        fig.add_trace(go.Bar(name='HP1', x=categorias, y=dist_hp1, marker_color='#27ae60'))
        fig.add_trace(go.Bar(name='HP2', x=categorias, y=dist_hp2, marker_color='#f39c12'))
        fig.add_trace(go.Bar(name='Prep', x=categorias, y=dist_prep, marker_color='#e74c3c'))
        
        fig.update_layout(
            barmode='group',
            height=400,
            yaxis_title="Número de Estudiantes",
            template="plotly_white"
        )
        st.plotly_chart(fig, width="stretch")
        
        # Tabla resumen de distribución
        st.markdown("#### 📋 Resumen de Distribución")
        dist_df = pd.DataFrame({
            'Nivel': categorias,
            'HP1': dist_hp1,
            'HP2': dist_hp2,
            'Prepárate': dist_prep
        })
        st.dataframe(dist_df, width="stretch", hide_index=True)
    
    st.markdown("---")
    
    # Análisis por Materia
    st.markdown("<h2 class='section-header'>📚 Análisis Detallado por Materia</h2>", unsafe_allow_html=True)
    
    # Comparación de materias entre simulacros
    promedios_hp1 = [hp1[mat].mean() for mat in materias]
    promedios_hp2 = [hp2[mat].mean() for mat in materias]
    promedios_prep = [prep[mat].mean() for mat in materias]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=promedios_hp1,
        theta=materias,
        fill='toself',
        name='HP1',
        line_color='#27ae60'
    ))
    fig.add_trace(go.Scatterpolar(
        r=promedios_hp2,
        theta=materias,
        fill='toself',
        name='HP2',
        line_color='#f39c12',
        opacity=0.7
    ))
    fig.add_trace(go.Scatterpolar(
        r=promedios_prep,
        theta=materias,
        fill='toself',
        name='Prepárate',
        line_color='#e74c3c',
        opacity=0.7
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500,
        title="Comparación de Rendimiento por Materia"
    )
    st.plotly_chart(fig, width="stretch")
    
    # Tabla comparativa detallada
    st.markdown("#### 📊 Tabla Comparativa de Materias")
    comp_materias_df = pd.DataFrame({
        'Materia': materias,
        'HP1': promedios_hp1,
        'HP2': promedios_hp2,
        'Prepárate': promedios_prep,
        'Mejor': [max(hp1, hp2, prep) for hp1, hp2, prep in zip(promedios_hp1, promedios_hp2, promedios_prep)],
        'Peor': [min(hp1, hp2, prep) for hp1, hp2, prep in zip(promedios_hp1, promedios_hp2, promedios_prep)],
        'Rango': [max(hp1, hp2, prep) - min(hp1, hp2, prep) for hp1, hp2, prep in zip(promedios_hp1, promedios_hp2, promedios_prep)]
    })
    comp_materias_df = comp_materias_df.round(2)
    st.dataframe(
        comp_materias_df.style.background_gradient(subset=['HP1', 'HP2', 'Prepárate'], cmap='RdYlGn', vmin=40, vmax=90),
        width="stretch",
        hide_index=True
    )
    
    st.markdown("---")
    
    # Hallazgos y Recomendaciones
    st.markdown("<h2 class='section-header'>🔍 Hallazgos Principales y Recomendaciones</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    cambio_hp1_hp2 = hp2['PROMEDIO PONDERADO'].mean() - hp1['PROMEDIO PONDERADO'].mean()
    mejor_materia = max(materias, key=lambda m: hp1[m].mean())
    peor_materia = min(materias, key=lambda m: hp1[m].mean())
    
    # Calcular materia con mayor variabilidad
    variabilidades = {mat: hp1[mat].std() for mat in materias}
    mat_variable = max(variabilidades, key=variabilidades.get)
    
    # Calcular materia con mayor caída
    cambios_materias = {mat: hp2[mat].mean() - hp1[mat].mean() for mat in materias}
    mat_mayor_caida = min(cambios_materias, key=cambios_materias.get)
    mat_mayor_mejora = max(cambios_materias, key=cambios_materias.get)
    
    with col1:
        st.markdown(f"""
        <div class='alert-warning'>
            <h4>⚠️ Áreas de Atención Prioritaria</h4>
            <ul>
                <li><strong>Caída General:</strong> {abs(cambio_hp1_hp2):.1f} puntos entre HP1 y HP2 ({abs(cambio_hp1_hp2/promedios_generales[0]*100):.1f}%)</li>
                <li><strong>Materia con Mayor Caída:</strong> {mat_mayor_caida} ({cambios_materias[mat_mayor_caida]:.1f} puntos)</li>
                <li><strong>Materia más Variable:</strong> {mat_variable} (σ = {variabilidades[mat_variable]:.1f})</li>
                <li><strong>Puntaje Promedio más Bajo:</strong> {peor_materia} ({min(promedios_hp1):.1f} puntos)</li>
                <li><strong>Estudiantes en Riesgo:</strong> {len(hp1[hp1['PROMEDIO PONDERADO'] < 250])} ({len(hp1[hp1['PROMEDIO PONDERADO'] < 250])/len(hp1)*100:.1f}%)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='alert-success'>
            <h4>✅ Fortalezas y Oportunidades</h4>
            <ul>
                <li><strong>Mejor Materia:</strong> {mejor_materia} ({max(promedios_hp1):.1f} puntos promedio)</li>
                <li><strong>Materia con Mayor Mejora:</strong> {mat_mayor_mejora} (+{cambios_materias[mat_mayor_mejora]:.1f} puntos)</li>
                <li><strong>Estudiantes Destacados:</strong> {len(hp1[hp1['PROMEDIO PONDERADO'] >= 350])} con puntaje ≥350</li>
                <li><strong>Consistencia:</strong> {materias[np.argmin([hp1[m].std() for m in materias])]} es la más consistente</li>
                <li><strong>Potencial de Mejora:</strong> Identificados {len(hp1[(hp1['PROMEDIO PONDERADO'] >= 250) & (hp1['PROMEDIO PONDERADO'] < 300)])} estudiantes en rango medio</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Recomendaciones estratégicas
    st.markdown("<h2 class='section-header'>💡 Recomendaciones Estratégicas</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white;'>
            <h4>🎯 Corto Plazo</h4>
            <ul style='font-size: 0.9rem;'>
                <li>Refuerzo intensivo en materia con mayor caída</li>
                <li>Talleres de nivelación para estudiantes en riesgo</li>
                <li>Simulacros adicionales focalizados</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 1.5rem; border-radius: 10px; color: white;'>
            <h4>📅 Mediano Plazo</h4>
            <ul style='font-size: 0.9rem;'>
                <li>Grupos de estudio por niveles</li>
                <li>Seguimiento personalizado semanal</li>
                <li>Banco de ejercicios por materia</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                    padding: 1.5rem; border-radius: 10px; color: #333;'>
            <h4>🎓 Largo Plazo</h4>
            <ul style='font-size: 0.9rem;'>
                <li>Programa de tutorías entre pares</li>
                <li>Preparación psicológica pre-examen</li>
                <li>Sistema de recompensas por mejora</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== REPORTE GENERAL ====================
elif pagina == "📊 Reporte General":
    st.markdown(f"<h1 class='header-title'>📊 Reporte General - {simulacro_seleccionado}</h1>", unsafe_allow_html=True)
    
    # Métricas principales expandidas
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📚 Estudiantes", len(datos_actual))
    
    with col2:
        promedio = datos_actual['PROMEDIO PONDERADO'].mean()
        st.metric("📊 Promedio", f"{promedio:.1f}")
    
    with col3:
        mejor = datos_actual['PROMEDIO PONDERADO'].max()
        st.metric("🏆 Máximo", f"{mejor:.1f}")
    
    with col4:
        peor = datos_actual['PROMEDIO PONDERADO'].min()
        st.metric("📉 Mínimo", f"{peor:.1f}")
    
    with col5:
        desv = datos_actual['PROMEDIO PONDERADO'].std()
        st.metric("📈 Desv. Est.", f"{desv:.1f}")
    
    st.markdown("---")
    
    # Análisis estadístico detallado
    st.markdown("<h2 class='section-header'>📊 Análisis Estadístico Completo</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Medidas de Tendencia Central")
        medidas_df = pd.DataFrame({
            'Estadístico': ['Media', 'Mediana', 'Moda', 'Rango', 'Rango Intercuartílico'],
            'Valor': [
                datos_actual['PROMEDIO PONDERADO'].mean(),
                datos_actual['PROMEDIO PONDERADO'].median(),
                datos_actual['PROMEDIO PONDERADO'].mode().values[0] if len(datos_actual['PROMEDIO PONDERADO'].mode()) > 0 else 'N/A',
                datos_actual['PROMEDIO PONDERADO'].max() - datos_actual['PROMEDIO PONDERADO'].min(),
                datos_actual['PROMEDIO PONDERADO'].quantile(0.75) - datos_actual['PROMEDIO PONDERADO'].quantile(0.25)
            ]
        })
        medidas_df['Valor'] = medidas_df['Valor'].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
        st.dataframe(medidas_df, width="stretch", hide_index=True)
        
        st.markdown("### 📊 Percentiles")
        percentiles_df = pd.DataFrame({
            'Percentil': ['P10', 'P25', 'P50 (Mediana)', 'P75', 'P90'],
            'Puntaje': [
                datos_actual['PROMEDIO PONDERADO'].quantile(0.10),
                datos_actual['PROMEDIO PONDERADO'].quantile(0.25),
                datos_actual['PROMEDIO PONDERADO'].quantile(0.50),
                datos_actual['PROMEDIO PONDERADO'].quantile(0.75),
                datos_actual['PROMEDIO PONDERADO'].quantile(0.90)
            ]
        })
        percentiles_df['Puntaje'] = percentiles_df['Puntaje'].round(2)
        st.dataframe(percentiles_df, width="stretch", hide_index=True)
    
    with col2:
        st.markdown("### 🎯 Distribución por Rangos de Puntaje")
        rangos = {
            'Excelente (≥350)': len(datos_actual[datos_actual['PROMEDIO PONDERADO'] >= 350]),
            'Sobresaliente (300-349)': len(datos_actual[(datos_actual['PROMEDIO PONDERADO'] >= 300) & (datos_actual['PROMEDIO PONDERADO'] < 350)]),
            'Satisfactorio (250-299)': len(datos_actual[(datos_actual['PROMEDIO PONDERADO'] >= 250) & (datos_actual['PROMEDIO PONDERADO'] < 300)]),
            'Básico (200-249)': len(datos_actual[(datos_actual['PROMEDIO PONDERADO'] >= 200) & (datos_actual['PROMEDIO PONDERADO'] < 250)]),
            'Bajo (<200)': len(datos_actual[datos_actual['PROMEDIO PONDERADO'] < 200])
        }
        
        fig = go.Figure(data=[go.Pie(
            labels=list(rangos.keys()),
            values=list(rangos.values()),
            hole=0.4,
            marker_colors=['#27ae60', '#3498db', '#f39c12', '#e67e22', '#e74c3c']
        )])
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=400, title="Distribución del Rendimiento")
        st.plotly_chart(fig, width="stretch")
        
        # Tabla de distribución
        rangos_df = pd.DataFrame({
            'Categoría': list(rangos.keys()),
            'Cantidad': list(rangos.values()),
            'Porcentaje': [f"{(v/len(datos_actual)*100):.1f}%" for v in rangos.values()]
        })
        st.dataframe(rangos_df, width="stretch", hide_index=True)
    
    st.markdown("---")
    
    # Gráfica de promedios por materia con más detalle
    st.markdown("<h2 class='section-header'>📚 Análisis Detallado por Materia</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Promedios y Comparación")
        promedios_materias = [datos_actual[mat].mean() for mat in materias]
        
        fig = go.Figure(data=[
            go.Bar(
                x=materias,
                y=promedios_materias,
                marker_color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6'],
                text=[f'{p:.1f}' for p in promedios_materias],
                textposition='outside'
            )
        ])
        fig.add_hline(y=np.mean(promedios_materias), line_dash="dash", 
                      line_color="red", annotation_text="Promedio General")
        fig.update_layout(
            title=f"Rendimiento por Área - {simulacro_seleccionado}",
            xaxis_title="Materia",
            yaxis_title="Puntaje Promedio",
            height=450,
            template="plotly_white"
        )
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.markdown("### 🎯 Desempeño Relativo")
        # Calcular desempeño relativo (comparado con el promedio de todas las materias)
        promedio_general_materias = np.mean(promedios_materias)
        desempeno_relativo = [(p - promedio_general_materias) for p in promedios_materias]
        
        fig = go.Figure(data=[
            go.Bar(
                x=materias,
                y=desempeno_relativo,
                marker_color=['#27ae60' if d > 0 else '#e74c3c' for d in desempeno_relativo],
                text=[f'{d:+.1f}' for d in desempeno_relativo],
                textposition='outside'
            )
        ])
        fig.add_hline(y=0, line_color="black")
        fig.update_layout(
            title="Diferencia vs Promedio General",
            xaxis_title="Materia",
            yaxis_title="Puntos sobre/bajo el promedio",
            height=450,
            template="plotly_white"
        )
        st.plotly_chart(fig, width="stretch")
    
    st.markdown("---")
    
    # Distribuciones y Análisis Avanzado
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Distribución del Promedio Ponderado")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=datos_actual['PROMEDIO PONDERADO'],
            nbinsx=20,
            marker_color='#667eea',
            name='Frecuencia',
            opacity=0.7
        ))
        fig.add_vline(
            x=datos_actual['PROMEDIO PONDERADO'].mean(),
            line_dash="dash",
            line_color="red",
            annotation_text=f"Media: {datos_actual['PROMEDIO PONDERADO'].mean():.1f}"
        )
        fig.add_vline(
            x=datos_actual['PROMEDIO PONDERADO'].median(),
            line_dash="dot",
            line_color="green",
            annotation_text=f"Mediana: {datos_actual['PROMEDIO PONDERADO'].median():.1f}"
        )
        fig.update_layout(height=400, showlegend=False, 
                         xaxis_title="Puntaje", yaxis_title="Frecuencia")
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.markdown("### 📈 Boxplot Comparativo")
        fig = go.Figure()
        for i, mat in enumerate(materias):
            fig.add_trace(go.Box(
                y=datos_actual[mat],
                name=mat.split()[0],
                marker_color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6'][i],
                boxmean='sd'
            ))
        fig.update_layout(height=400, showlegend=True, yaxis_title="Puntaje")
        st.plotly_chart(fig, width="stretch")
    
    st.markdown("---")
    
    # Tabla de estadísticas descriptivas completa
    st.markdown("<h2 class='section-header'>📋 Estadísticas Descriptivas Completas</h2>", unsafe_allow_html=True)
    
    stats_df = pd.DataFrame({
        'Materia': materias,
        'Media': [datos_actual[m].mean() for m in materias],
        'Mediana': [datos_actual[m].median() for m in materias],
        'Desv. Est.': [datos_actual[m].std() for m in materias],
        'Mínimo': [datos_actual[m].min() for m in materias],
        'Q1': [datos_actual[m].quantile(0.25) for m in materias],
        'Q3': [datos_actual[m].quantile(0.75) for m in materias],
        'Máximo': [datos_actual[m].max() for m in materias],
        'Rango': [datos_actual[m].max() - datos_actual[m].min() for m in materias],
        'CV (%)': [(datos_actual[m].std() / datos_actual[m].mean() * 100) for m in materias]
    })
    stats_df = stats_df.round(2)
    st.dataframe(
        stats_df.style.background_gradient(subset=['Media', 'Mediana'], cmap='RdYlGn', vmin=40, vmax=90),
        width="stretch",
        hide_index=True
    )
    
    st.markdown("---")
    
    # Análisis de correlación dentro del simulacro
    st.markdown("<h2 class='section-header'>🔗 Matriz de Correlación entre Materias</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        correlacion = datos_actual[materias].corr()
        
        fig = px.imshow(
            correlacion,
            text_auto='.2f',
            color_continuous_scale='RdBu_r',
            aspect='auto',
            zmin=-1,
            zmax=1,
            labels=dict(color="Correlación")
        )
        fig.update_layout(height=500, title="Correlación entre Materias")
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.markdown("### 🔍 Interpretación")
        st.info("""
        **Correlación Alta (>0.7)**  
        Fuerte relación entre materias
        
        **Correlación Media (0.4-0.7)**  
        Relación moderada
        
        **Correlación Baja (<0.4)**  
        Independencia relativa
        """)
        
        # Encontrar la correlación más alta (excluyendo diagonal)
        corr_values = correlacion.values
        np.fill_diagonal(corr_values, -1)
        max_corr_idx = np.unravel_index(corr_values.argmax(), corr_values.shape)
        max_corr = corr_values[max_corr_idx]
        
        st.success(f"""
        **Mayor Correlación:**  
        {materias[max_corr_idx[0]].split()[0]} ↔️ {materias[max_corr_idx[1]].split()[0]}  
        Coeficiente: {max_corr:.2f}
        """)

# ==================== COMPARACIÓN SIMULACROS ====================
elif pagina == "🔄 Comparación Simulacros":
    st.markdown("<h1 class='header-title'>🔄 Comparación entre Simulacros</h1>", unsafe_allow_html=True)
    
    # Comparación de promedios
    st.markdown("<h2 class='section-header'>📊 Comparación de Promedios por Materia</h2>", unsafe_allow_html=True)
    
    promedios_hp1 = [hp1[mat].mean() for mat in materias]
    promedios_hp2 = [hp2[mat].mean() for mat in materias]
    promedios_prep = [prep[mat].mean() for mat in materias]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Helmer Pardo 1', x=materias, y=promedios_hp1, marker_color='#3498db'))
    fig.add_trace(go.Bar(name='Helmer Pardo 2', x=materias, y=promedios_hp2, marker_color='#2ecc71'))
    fig.add_trace(go.Bar(name='Prepárate', x=materias, y=promedios_prep, marker_color='#e74c3c'))
    
    fig.update_layout(
        barmode='group',
        height=500,
        title="Comparación de Promedios por Materia",
        xaxis_title="Materia",
        yaxis_title="Puntaje Promedio",
        template="plotly_white"
    )
    st.plotly_chart(fig, width="stretch")
    
    st.markdown("---")
    
    # Tabla comparativa
    st.markdown("<h2 class='section-header'>📋 Tabla Comparativa</h2>", unsafe_allow_html=True)
    
    comp_df = pd.DataFrame({
        'Materia': materias,
        'HP1': promedios_hp1,
        'HP2': promedios_hp2,
        'Prepárate': promedios_prep,
        'Cambio HP1→HP2': [hp2-hp1 for hp1, hp2 in zip(promedios_hp1, promedios_hp2)],
        'Cambio HP2→Prep': [prep-hp2 for hp2, prep in zip(promedios_hp2, promedios_prep)]
    })
    comp_df = comp_df.round(2)
    
    # Estilo condicional
    st.dataframe(
        comp_df.style.background_gradient(subset=['Cambio HP1→HP2', 'Cambio HP2→Prep'], cmap='RdYlGn', vmin=-20, vmax=20),
        width="stretch"
    )
    
    st.markdown("---")
    
    # Evolución del promedio general
    st.markdown("<h2 class='section-header'>📈 Evolución del Promedio General</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    promedios_generales = [
        hp1['PROMEDIO PONDERADO'].mean(),
        hp2['PROMEDIO PONDERADO'].mean(),
        prep['PROMEDIO PONDERADO'].mean()
    ]
    
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=['Helmer Pardo 1', 'Helmer Pardo 2', 'Prepárate'],
            y=promedios_generales,
            mode='lines+markers+text',
            text=[f'{p:.2f}' for p in promedios_generales],
            textposition='top center',
            line=dict(color='#667eea', width=4),
            marker=dict(size=15, color=['#27ae60', '#f39c12', '#e74c3c'])
        ))
        fig.update_layout(
            title="Tendencia del Promedio Ponderado",
            yaxis_title="Promedio Ponderado",
            height=400,
            template="plotly_white"
        )
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        cambio_1_2 = promedios_generales[1] - promedios_generales[0]
        cambio_2_3 = promedios_generales[2] - promedios_generales[1]
        
        st.markdown("### 📉 Cambios Registrados")
        st.markdown(f"""
        <div class='stats-box'>
            <h4>HP1 → HP2</h4>
            <h2>{cambio_1_2:.2f}</h2>
            <p>puntos</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='stats-box' style='background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);'>
            <h4>HP2 → Prep</h4>
            <h2>{cambio_2_3:.2f}</h2>
            <p>puntos</p>
        </div>
        """, unsafe_allow_html=True)

# ==================== ANÁLISIS INDIVIDUAL ====================
elif pagina == "👤 Análisis Individual":
    st.markdown("<h1 class='header-title'>👤 Análisis Individual de Estudiantes</h1>", unsafe_allow_html=True)
    
    estudiante_seleccionado = st.selectbox(
        "Seleccionar Estudiante",
        sorted(datos_actual['ESTUDIANTE'].unique())
    )
    
    datos_estudiante = datos_actual[datos_actual['ESTUDIANTE'] == estudiante_seleccionado].iloc[0]
    
    st.markdown(f"### 📊 Resultados de: **{estudiante_seleccionado}**")
    if 'GRADO' in datos_estudiante:
        st.markdown(f"**Grado:** {datos_estudiante['GRADO']}")
    
    st.markdown("---")
    
    # Métricas del estudiante
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🎯 Promedio Ponderado", f"{datos_estudiante['PROMEDIO PONDERADO']:.1f}")
    
    with col2:
        percentil = (datos_actual['PROMEDIO PONDERADO'] < datos_estudiante['PROMEDIO PONDERADO']).sum() / len(datos_actual) * 100
        st.metric("📊 Percentil", f"{percentil:.1f}%")
    
    with col3:
        ranking = datos_actual.sort_values('PROMEDIO PONDERADO', ascending=False).reset_index(drop=True)
        posicion = ranking[ranking['ESTUDIANTE'] == estudiante_seleccionado].index[0] + 1
        st.metric("🏆 Posición", f"{posicion} / {len(datos_actual)}")
    
    with col4:
        mejor_materia = max(materias, key=lambda m: datos_estudiante[m])
        st.metric("⭐ Mejor Materia", mejor_materia.split()[0])
    
    st.markdown("---")
    
    # Gráfica radar
    st.markdown("<h2 class='section-header'>📊 Perfil de Competencias</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        valores_estudiante = [datos_estudiante[mat] for mat in materias]
        promedios_grupo = [datos_actual[mat].mean() for mat in materias]
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=valores_estudiante,
            theta=materias,
            fill='toself',
            name='Estudiante',
            line_color='#667eea'
        ))
        fig.add_trace(go.Scatterpolar(
            r=promedios_grupo,
            theta=materias,
            fill='toself',
            name='Promedio Grupo',
            line_color='#e74c3c',
            opacity=0.6
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=450,
            title="Comparación con el Promedio del Grupo"
        )
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        fig = go.Figure()
        colores = ['#27ae60' if v >= p else '#e74c3c' for v, p in zip(valores_estudiante, promedios_grupo)]
        fig.add_trace(go.Bar(
            x=materias,
            y=valores_estudiante,
            marker_color=colores,
            text=[f'{v:.1f}' for v in valores_estudiante],
            textposition='outside',
            name='Puntajes'
        ))
        fig.add_trace(go.Scatter(
            x=materias,
            y=promedios_grupo,
            mode='markers+lines',
            name='Promedio Grupo',
            line=dict(color='red', dash='dash'),
            marker=dict(size=10)
        ))
        fig.update_layout(
            title="Puntajes por Materia",
            yaxis_title="Puntaje",
            height=450,
            template="plotly_white"
        )
        st.plotly_chart(fig, width="stretch")
    
    # Tabla de puntajes
    st.markdown("<h2 class='section-header'>📋 Detalle de Puntajes</h2>", unsafe_allow_html=True)
    
    detalle_df = pd.DataFrame({
        'Materia': materias,
        'Puntaje': valores_estudiante,
        'Promedio Grupo': promedios_grupo,
        'Diferencia': [e - g for e, g in zip(valores_estudiante, promedios_grupo)]
    })
    detalle_df = detalle_df.round(2)
    
    st.dataframe(
        detalle_df.style.background_gradient(subset=['Diferencia'], cmap='RdYlGn', vmin=-20, vmax=20),
        width="stretch"
    )

# ==================== PROGRESIÓN ====================
elif pagina == "📈 Progresión":
    st.markdown("<h1 class='header-title'>📈 Análisis de Progresión</h1>", unsafe_allow_html=True)
    
    # Preparar datos de progresión
    hp1_temp = hp1.copy()
    hp2_temp = hp2.copy()
    prep_temp = prep.copy()
    
    hp1_temp['ESTUDIANTE'] = hp1_temp['ESTUDIANTE'].str.strip().str.upper()
    hp2_temp['ESTUDIANTE'] = hp2_temp['ESTUDIANTE'].str.strip().str.upper()
    prep_temp['ESTUDIANTE'] = prep_temp['ESTUDIANTE'].str.strip().str.upper()
    
    progresion = pd.merge(
        hp1_temp[['ESTUDIANTE', 'PROMEDIO PONDERADO']],
        hp2_temp[['ESTUDIANTE', 'PROMEDIO PONDERADO']],
        on='ESTUDIANTE',
        suffixes=('_HP1', '_HP2')
    )
    
    progresion = pd.merge(
        progresion,
        prep_temp[['ESTUDIANTE', 'PROMEDIO PONDERADO']],
        on='ESTUDIANTE'
    )
    
    progresion.columns = ['ESTUDIANTE', 'HP1', 'HP2', 'Avancemos']
    progresion['CAMBIO_HP1_HP2'] = progresion['HP2'] - progresion['HP1']
    progresion['CAMBIO_HP2_PREP'] = progresion['Avancemos'] - progresion['HP2']
    progresion['CAMBIO_TOTAL'] = progresion['Avancemos'] - progresion['HP1']
    
    st.markdown(f"**Estudiantes encontrados en los 3 simulacros:** {len(progresion)}")
    
    # Métricas de progresión
    col1, col2, col3 = st.columns(3)
    
    with col1:
        mejoraron_hp2 = (progresion['CAMBIO_HP1_HP2'] > 0).sum()
        st.metric("📈 Mejoraron HP1→HP2", f"{mejoraron_hp2} ({mejoraron_hp2/len(progresion)*100:.1f}%)")
    
    with col2:
        empeoraron_hp2 = (progresion['CAMBIO_HP1_HP2'] < 0).sum()
        st.metric("📉 Empeoraron HP1→HP2", f"{empeoraron_hp2} ({empeoraron_hp2/len(progresion)*100:.1f}%)")
    
    with col3:
        cambio_promedio = progresion['CAMBIO_HP1_HP2'].mean()
        st.metric("📊 Cambio Promedio HP1→HP2", f"{cambio_promedio:.2f}")
    
    st.markdown("---")
    
    # Gráfica de progresión individual
    st.markdown("<h2 class='section-header'>📊 Progresión Individual</h2>", unsafe_allow_html=True)
    
    progresion_sorted = progresion.sort_values('CAMBIO_TOTAL')
    
    fig = go.Figure()
    
    colores = ['#27ae60' if c > 0 else '#e74c3c' for c in progresion_sorted['CAMBIO_TOTAL']]
    
    fig.add_trace(go.Bar(
        y=progresion_sorted['ESTUDIANTE'].str.split().str[0],
        x=progresion_sorted['CAMBIO_TOTAL'],
        orientation='h',
        marker_color=colores,
        text=[f'{c:.1f}' for c in progresion_sorted['CAMBIO_TOTAL']],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Cambio Total (HP1 → Prepárate)",
        xaxis_title="Cambio en Promedio Ponderado",
        yaxis_title="Estudiante",
        height=800,
        template="plotly_white"
    )
    fig.add_vline(x=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig, width="stretch")
    
    st.markdown("---")
    
    # Evolución por estudiante
    st.markdown("<h2 class='section-header'>📈 Evolución de los 3 Simulacros</h2>", unsafe_allow_html=True)
    
    estudiantes_mostrar = st.multiselect(
        "Seleccionar estudiantes para comparar",
        progresion['ESTUDIANTE'].tolist(),
        default=progresion.nlargest(5, 'Avancemos')['ESTUDIANTE'].tolist()[:5]
    )
    
    if estudiantes_mostrar:
        fig = go.Figure()
        
        for estudiante in estudiantes_mostrar:
            datos_est = progresion[progresion['ESTUDIANTE'] == estudiante].iloc[0]
            fig.add_trace(go.Scatter(
                x=['HP1', 'HP2', 'Prepárate'],
                y=[datos_est['HP1'], datos_est['HP2'], datos_est['Avancemos']],
                mode='lines+markers',
                name=estudiante.split()[0],
                line=dict(width=3),
                marker=dict(size=10)
            ))
        
        fig.update_layout(
            title="Evolución Individual en los 3 Simulacros",
            xaxis_title="Simulacro",
            yaxis_title="Promedio Ponderado",
            height=500,
            template="plotly_white",
            hovermode='x unified'
        )
        st.plotly_chart(fig, width="stretch")
    
    st.markdown("---")
    
    # Tabla de progresión
    st.markdown("<h2 class='section-header'>📋 Tabla de Progresión Completa</h2>", unsafe_allow_html=True)
    
    tabla_progresion = progresion[['ESTUDIANTE', 'HP1', 'HP2', 'Avancemos', 
                                     'CAMBIO_HP1_HP2', 'CAMBIO_HP2_PREP', 'CAMBIO_TOTAL']]
    tabla_progresion = tabla_progresion.sort_values('CAMBIO_TOTAL', ascending=False)
    tabla_progresion = tabla_progresion.round(2)
    
    st.dataframe(
        tabla_progresion.style.background_gradient(
            subset=['CAMBIO_HP1_HP2', 'CAMBIO_HP2_PREP', 'CAMBIO_TOTAL'], 
            cmap='RdYlGn', 
            vmin=-50, 
            vmax=50
        ),
        width="stretch",
        height=600
    )

# ==================== ESTADÍSTICAS DETALLADAS ====================
elif pagina == "📉 Estadísticas Detalladas":
    st.markdown("<h1 class='header-title'>📉 Estadísticas Detalladas</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Correlaciones", "📈 Análisis por Grado", "🎯 Top Performers"])
    
    with tab1:
        st.markdown("### 🔗 Matriz de Correlación entre Materias")
        
        col1, col2, col3 = st.columns(3)
        
        for idx, (nombre, datos) in enumerate([("HP1", hp1), ("HP2", hp2), ("Prep", prep)]):
            with [col1, col2, col3][idx]:
                st.markdown(f"#### {nombre}")
                correlacion = datos[materias].corr()
                
                fig = px.imshow(
                    correlacion,
                    text_auto='.2f',
                    color_continuous_scale='RdBu_r',
                    aspect='auto',
                    zmin=-1,
                    zmax=1
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, width="stretch")
        
        st.markdown("---")
        st.markdown("### 📊 Interpretación de Correlaciones")
        
        st.info("""
        **Correlación alta (>0.7):** Las materias están fuertemente relacionadas. 
        Un buen desempeño en una suele indicar buen desempeño en la otra.
        
        **Correlación media (0.4-0.7):** Relación moderada entre las materias.
        
        **Correlación baja (<0.4):** Las materias son relativamente independientes.
        """)
    
    with tab2:
        st.markdown("### 📚 Análisis Comparativo por Grado")
        
        simulacro_analisis = st.selectbox(
            "Seleccionar simulacro para análisis por grado",
            ["Helmer Pardo 1", "Helmer Pardo 2", "Prepárate"],
            key="grado_select"
        )
        
        datos_grado = simulacros_map[simulacro_analisis]
        
        if 'GRADO' in datos_grado.columns:
            grados_disponibles = datos_grado['GRADO'].dropna().unique()
            
            # Convertir todos los grados a string para evitar problemas de tipo
            grados_disponibles = [str(g) for g in grados_disponibles]
            
            # Comparación de promedios por grado
            fig = go.Figure()
            
            for grado in sorted(grados_disponibles):
                datos_g = datos_grado[datos_grado['GRADO'].astype(str) == grado]
                promedios_g = [datos_g[mat].mean() for mat in materias]
                
                fig.add_trace(go.Bar(
                    name=f'Grado {grado}',
                    x=materias,
                    y=promedios_g,
                    text=[f'{p:.1f}' for p in promedios_g],
                    textposition='outside'
                ))
            
            fig.update_layout(
                title=f"Comparación de Promedios por Grado - {simulacro_analisis}",
                xaxis_title="Materia",
                yaxis_title="Puntaje Promedio",
                barmode='group',
                height=500,
                template="plotly_white"
            )
            st.plotly_chart(fig, width="stretch")
            
            st.markdown("---")
            
            # Tabla comparativa
            tabla_grados = []
            for grado in sorted(grados_disponibles):
                datos_g = datos_grado[datos_grado['GRADO'].astype(str) == grado]
                fila = {'Grado': grado}
                for mat in materias:
                    fila[mat] = datos_g[mat].mean()
                fila['Promedio General'] = datos_g['PROMEDIO PONDERADO'].mean()
                tabla_grados.append(fila)
            
            df_grados = pd.DataFrame(tabla_grados)
            df_grados = df_grados.round(2)
            
            st.markdown("#### 📊 Tabla de Promedios por Grado")
            st.dataframe(
                df_grados.style.background_gradient(cmap='YlGnBu', subset=materias + ['Promedio General']),
                width="stretch"
            )
        else:
            st.warning("No hay información de grado disponible en este simulacro.")
    
    with tab3:
        st.markdown("### 🏆 Top Performers por Materia")
        
        simulacro_top = st.selectbox(
            "Seleccionar simulacro",
            ["Helmer Pardo 1", "Helmer Pardo 2", "Prepárate"],
            key="top_select"
        )
        
        datos_top = simulacros_map[simulacro_top]
        
        n_top = st.slider("Número de estudiantes a mostrar", 5, 20, 10)
        
        cols = st.columns(2)
        
        for idx, materia in enumerate(materias):
            with cols[idx % 2]:
                st.markdown(f"#### {materia}")
                
                top_materia = datos_top.nlargest(n_top, materia)[['ESTUDIANTE', materia]]
                top_materia = top_materia.reset_index(drop=True)
                top_materia.index = top_materia.index + 1
                
                fig = px.bar(
                    top_materia,
                    x=materia,
                    y='ESTUDIANTE',
                    orientation='h',
                    color=materia,
                    color_continuous_scale='Viridis',
                    text=materia
                )
                fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                fig.update_layout(
                    height=400,
                    showlegend=False,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, width="stretch")
        
        st.markdown("---")
        
        # Ranking general
        st.markdown("### 🏆 Ranking General - Top 20")
        
        ranking_general = datos_top.nlargest(20, 'PROMEDIO PONDERADO')[
            ['ESTUDIANTE'] + materias + ['PROMEDIO PONDERADO']
        ].reset_index(drop=True)
        ranking_general.index = ranking_general.index + 1
        ranking_general = ranking_general.round(2)
        
        st.dataframe(
            ranking_general.style.background_gradient(
                cmap='RdYlGn',
                subset=materias + ['PROMEDIO PONDERADO'],
                vmin=40,
                vmax=100
            ),
            width="stretch",
            height=600
        )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6c757d; padding: 2rem;'>
    <p style='font-size: 0.9rem;'>
        <strong>📊 Dashboard de Análisis de Simulacros ICFES</strong><br>
        Sistema de Evaluación y Seguimiento Académico - Grado 11<br>
        Desarrollado con ❤️ usando Streamlit y Plotly
    </p>
</div>
""", unsafe_allow_html=True)