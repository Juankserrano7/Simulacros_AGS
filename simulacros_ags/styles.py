import streamlit as st

BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css');

    :root {
        /* Identidad Cromática Institucional */
        --color-primary: #21B7D2;
        --color-primary-hover: #1999B0;
        --color-sidebar-bg: linear-gradient(180deg, #0D1B2A 0%, #1B263B 50%, #2A3D54 100%);
        --color-sidebar-card: #1B263B;
        --color-accent-blue: #3B82F6;
        --color-accent-indigo: #6366F1;
        
        /* Superficies y Fondos */
        --color-bg-canvas: #F8FAFC;
        --color-surface-card: #FFFFFF;
        --color-border-subtle: #E2E8F0;

        /* Texto */
        --color-text-primary: #0F172A;
        --color-text-secondary: #64748B;
        --color-text-muted: #94A3B8;

        /* Semántica ICFES */
        --color-excellence: #10B981;
        --color-satisfactory: #0EA5E9;
        --color-warning: #F59E0B;
        --color-critical: #EF4444;

        /* Escala de Espaciado (8px grid) */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 12px;
        --space-lg: 16px;
        --space-xl: 24px;
        --space-2xl: 32px;

        /* Radios de Borde */
        --radius-sm: 4px;
        --radius-md: 8px;
        --radius-lg: 12px;
        --radius-xl: 16px;

        /* Profundidad y Sombras */
        --elevation-0: none;
        --elevation-1: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04);
        --elevation-2: 0 10px 15px -3px rgba(15, 23, 42, 0.1), 0 4px 6px -2px rgba(15, 23, 42, 0.05);
        --elevation-3: 0 20px 25px -5px rgba(15, 23, 42, 0.15), 0 10px 10px -5px rgba(15, 23, 42, 0.04);

        /* Transición Rápida CSS (180ms ease-out) */
        --transition-fast: all 180ms cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-variant-numeric: tabular-nums lining-nums;
    }

    h1, h2, h3, h4, h5, h6, .header-title, .section-header, div[data-testid="stMetricValue"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    
    .stApp {
        background: var(--color-bg-canvas);
    }

    .main {
        background: var(--color-bg-canvas);
    }
    
    /* SIDEBAR STYLING - Institutional Obsidian Navy Design */
    [data-testid="stSidebar"] {
        background: var(--color-sidebar-bg);
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.15);
        min-width: 240px;
        max-width: 800px;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent;
    }
    
    /* Sidebar Header */
    [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.9rem;
        padding: var(--space-sm) 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15);
        margin-bottom: var(--space-md);
    }
    
    /* Radio Buttons Styling */
    [data-testid="stSidebar"] .row-widget.stRadio > div {
        background: transparent;
    }
    
    [data-testid="stSidebar"] .row-widget.stRadio > div > label {
        background: rgba(255, 255, 255, 0.08);
        color: #E2E8F0 !important;
        padding: var(--space-md) var(--space-lg);
        border-radius: var(--radius-md);
        margin-bottom: var(--space-xs);
        transition: var(--transition-fast);
        border: 1px solid rgba(255, 255, 255, 0.08);
        cursor: pointer;
        display: flex;
        align-items: center;
        font-weight: 500;
    }
    
    [data-testid="stSidebar"] .row-widget.stRadio > div > label:hover {
        background: rgba(255, 255, 255, 0.15);
        border-color: rgba(255, 255, 255, 0.25);
        transform: translateX(3px);
    }
    
    [data-testid="stSidebar"] .row-widget.stRadio > div > label[data-baseweb="radio"]:has(input:checked) {
        background: var(--color-primary);
        border-color: var(--color-primary);
        color: #0F172A !important;
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(33, 183, 210, 0.35);
    }
    
    /* Selectbox Styling */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: var(--radius-md);
        color: white;
    }
    
    [data-testid="stSidebar"] .stSelectbox label {
        color: #E2E8F0 !important;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Divider */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.15);
        margin: var(--space-lg) 0;
    }
    
    /* Sidebar Text */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] div {
        color: #E2E8F0;
    }
    
    /* Main Content Buttons */
    .stButton>button {
        background: var(--color-primary);
        color: #0F172A;
        border: none;
        border-radius: var(--radius-md);
        padding: var(--space-sm) var(--space-xl);
        font-weight: 700;
        transition: var(--transition-fast);
        box-shadow: var(--elevation-1);
    }
    
    .stButton>button:hover {
        background: var(--color-primary-hover);
        color: #FFFFFF;
        transform: translateY(-1px);
        box-shadow: var(--elevation-2);
    }
    
    /* Target Metric Cards (Visual Signature Ribbon) */
    .metric-card {
        background: var(--color-surface-card);
        border-radius: var(--radius-lg);
        padding: var(--space-lg);
        box-shadow: var(--elevation-1);
        border: 1px solid var(--color-border-subtle);
        border-left: 4px solid var(--color-primary);
        transition: var(--transition-fast);
        margin-bottom: var(--space-md);
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--elevation-2);
    }
    
    .header-title {
        color: var(--color-text-primary);
        font-size: 2.25rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: var(--space-xs);
        letter-spacing: -0.5px;
    }
    
    .header-subtitle {
        text-align: center;
        color: var(--color-text-secondary);
        font-size: 1.05rem;
        margin-bottom: var(--space-xl);
    }
    
    .section-header {
        background: #1B263B;
        color: #FFFFFF;
        padding: var(--space-md) var(--space-lg);
        border-radius: var(--radius-lg);
        margin: var(--space-lg) 0;
        font-weight: 700;
        border-left: 4px solid var(--color-primary);
    }
    
    .stats-box {
        background: #1B263B;
        color: #FFFFFF;
        padding: var(--space-lg);
        border-radius: var(--radius-lg);
        text-align: center;
        box-shadow: var(--elevation-1);
        border-top: 3px solid var(--color-primary);
    }
    
    .info-badge {
        display: inline-block;
        background: rgba(33, 183, 210, 0.12);
        color: var(--color-primary);
        padding: var(--space-xs) var(--space-md);
        border-radius: var(--radius-sm);
        font-size: 0.85rem;
        font-weight: 600;
        margin: var(--space-xs);
    }
    
    .alert-success {
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.2);
        color: #065F46;
        padding: var(--space-lg);
        border-radius: var(--radius-lg);
        margin: var(--space-md) 0;
    }
    
    .alert-warning {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.2);
        color: #92400E;
        padding: var(--space-lg);
        border-radius: var(--radius-lg);
        margin: var(--space-md) 0;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        color: var(--color-text-primary);
    }
    
    .login-hero {
        text-align: center;
        margin: var(--space-2xl) auto var(--space-xl);
        max-width: 640px;
    }
    
    .login-hero h1 {
        font-size: 2.75rem;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: var(--space-xs);
    }
    
    .login-hero p {
        color: #94A3B8;
        font-size: 1.1rem;
    }
    
    form[data-testid="stForm"] {
        background: var(--color-surface-card);
        border-radius: var(--radius-xl);
        padding: var(--space-2xl);
        box-shadow: var(--elevation-3);
        border: 1px solid var(--color-border-subtle);
    }
    
    form[data-testid="stForm"] label {
        font-weight: 600;
        color: var(--color-text-primary) !important;
    }
    
    form[data-testid="stForm"] input {
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--color-border-subtle) !important;
        background: #F1F5F9;
    }

    .sidebar-user-card {
        background: rgba(255, 255, 255, 0.08);
        border-radius: var(--radius-lg);
        padding: var(--space-md);
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.12);
        margin-bottom: var(--space-md);
    }

    .sidebar-user-name {
        font-size: 0.95rem;
        font-weight: 700;
        color: white;
        margin-bottom: var(--space-xs);
    }

    .sidebar-user-email {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.7);
        margin-bottom: var(--space-sm);
    }
    
    header [data-testid="stToolbar"] a[href*="github"] {
        display: none !important;
    }
    
    header [data-testid="stToolbar"] button[title*="Fork"],
    header [data-testid="stToolbar"] a[title*="Fork"] {
        display: none !important;
    }
    
    /* GLOBAL DROPDOWN / SELECTBOX STYLING */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"],
    div[role="listbox"],
    ul[role="listbox"],
    ul[data-baseweb="menu"] {
        max-height: 280px !important;
        overflow-y: auto !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--elevation-3) !important;
        -webkit-overflow-scrolling: touch !important;
    }

    /* Selectbox Container Focus & Hover */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: var(--radius-md) !important;
    }
</style>
"""


def inject_base_styles():
    """Inyecta el CSS del dashboard."""
    st.markdown(BASE_CSS, unsafe_allow_html=True)


def render_inclusion_badge(text: str = "Inclusión") -> str:
    """Retorna el badge HTML institucional y uniforme para estudiantes o pestañas en condición de inclusión."""
    return f'<span style="display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.25rem 0.6rem; border-radius: var(--radius-sm); background: rgba(99, 102, 241, 0.12); color: var(--color-accent-indigo); font-weight: 600; font-size: 0.85rem;" title="Estudiante en Condición de Inclusión"><i class="bi bi-universal-access-circle" style="font-size: 0.95rem;"></i> {text}</span>'
