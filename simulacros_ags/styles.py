import streamlit as st

BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css');
    
    * {
        font-family: 'Inter', sans-serif;
        box-sizing: border-box;
    }
    
    /* ===== FONDO PRINCIPAL CON PROFUNDIDAD ===== */
    .main {
        background: #f0f4f8;
        background-image:
            radial-gradient(circle at 20% 20%, rgba(26,115,232,0.06) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(13,158,217,0.05) 0%, transparent 50%);
    }
    
    /* Contenedor principal */
    section[data-testid="stMain"] > div,
    [data-testid="block-container"] {
        background: transparent;
    }
    
    /* Panel de contenido — tarjeta elevada con sombra profunda */
    [data-testid="block-container"] {
        background: #ffffff !important;
        border-radius: 20px !important;
        box-shadow:
            0 1px 2px rgba(0,0,0,0.04),
            0 4px 12px rgba(26,115,232,0.07),
            0 16px 40px rgba(26,115,232,0.06),
            0 32px 64px rgba(0,0,0,0.05) !important;
        padding: 2rem 2.5rem 3rem !important;
        margin: 1rem auto !important;
        border: 1px solid rgba(26,115,232,0.08) !important;
    }
    
    /* SIDEBAR STYLING - Bootstrap 5 Design */
    [data-testid="stSidebar"][aria-expanded="true"] {
        min-width: 288px;
    }
    [data-testid="stSidebar"] {
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
    
    /* ===== BOTONES PRINCIPALES ===== */
    .stButton>button {
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        transition: all 0.25s ease;
        box-shadow:
            0 2px 4px rgba(26,115,232,0.25),
            0 6px 16px rgba(26,115,232,0.30);
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow:
            0 4px 8px rgba(26,115,232,0.30),
            0 12px 28px rgba(26,115,232,0.40);
    }
    
    /* ===== METRIC CARDS CON EFECTO 3D ===== */
    .metric-card {
        background: #ffffff;
        border-radius: 18px;
        padding: 1.5rem 1.8rem;
        /* Sombra multicapa = efecto de elevación 3D */
        box-shadow:
            0 1px 2px rgba(0,0,0,0.04),
            0 4px 10px rgba(26,115,232,0.10),
            0 12px 28px rgba(26,115,232,0.08);
        transition: transform 0.22s ease, box-shadow 0.22s ease;
        margin-bottom: 1rem;
        border: 1px solid rgba(26,115,232,0.10);
        /* Borde superior de acento */
        border-top: 3px solid #1a73e8;
    }
    
    .metric-card:hover {
        transform: translateY(-6px);
        box-shadow:
            0 2px 4px rgba(0,0,0,0.06),
            0 8px 20px rgba(26,115,232,0.18),
            0 24px 48px rgba(26,115,232,0.14);
    }
    
    .header-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.2rem;
        font-weight: 800;
        text-align: center;
        margin: 0.2rem 0 0.5rem;
        letter-spacing: -0.5px;
        color: #1565c0;
    }
    
    .header-subtitle {
        text-align: center;
        color: #6c757d;
        font-size: 1.05rem;
        margin-bottom: 1.8rem;
        margin-top: 0;
    }

    /* ===== JERARQUIA TIPOGRAFICA h3 / h4 ===== */
    /* h3 generados por st.markdown('### ...') */
    [data-testid="block-container"] h3,
    .main h3 {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1e3a5f;
        margin: 1.2rem 0 0.6rem;
        padding: 0;
        letter-spacing: -0.2px;
    }

    /* h4 generados por st.markdown('#### ...') */
    [data-testid="block-container"] h4,
    .main h4 {
        font-size: 1rem;
        font-weight: 600;
        color: #2d4a6e;
        margin: 0.9rem 0 0.4rem;
        padding: 0;
    }
    
    /* ===== SECTION HEADER CON PADDING AMPLIO Y SOMBRA 3D ===== */
    .section-header {
        background: linear-gradient(135deg, #1a73e8 0%, #0d9ed9 100%);
        color: white;
        /* Padding generoso: vertical 1rem / horizontal 1.8rem — sin ajuste al borde */
        padding: 1rem 1.8rem;
        border-radius: 12px;
        margin: 2rem 0 1.2rem;
        font-weight: 700;
        font-size: 1.05rem;
        letter-spacing: 0.2px;
        line-height: 1.5;
        /* Sombra multicapa para sensación 3D */
        box-shadow:
            0 2px 4px rgba(26,115,232,0.20),
            0 6px 16px rgba(26,115,232,0.28),
            0 14px 32px rgba(13,158,217,0.16),
            inset 0 1px 0 rgba(255,255,255,0.18);
        /* Sutil borde inferior para separación visual */
        border-bottom: 2px solid rgba(255,255,255,0.20);
        /* Brillo interior en la parte superior */
        position: relative;
        overflow: hidden;
    }
    
    /* Reflejo brillante en la parte superior del section-header */
    .section-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 40%;
        background: linear-gradient(180deg,
            rgba(255,255,255,0.18) 0%,
            transparent 100%);
        pointer-events: none;
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
    
    /* ===== SEPARADORES HR ===== */
    /* Reduce el espacio excesivo que Streamlit añade alrededor de --- */
    [data-testid="stMarkdown"] hr {
        margin: 1.2rem 0 !important;
        border: none !important;
        border-top: 1px solid rgba(26,115,232,0.12) !important;
    }

    /* ===== ALERT BOXES MEJORADOS ===== */
    .alert-warning {
        background: #fffbf0;
        border-left: 4px solid #f59e0b;
        border-radius: 10px;
        color: #78350f;
        padding: 1.2rem 1.4rem;
        margin: 0.8rem 0;
        line-height: 1.65;
    }

    .alert-warning h4 {
        color: #92400e;
        margin: 0 0 0.6rem;
        font-size: 1rem;
    }

    .alert-warning ul {
        margin: 0.2rem 0 0;
        padding-left: 1.3rem;
    }

    .alert-warning li {
        margin-bottom: 0.35rem;
    }

    .alert-success {
        background: #f0fdf4;
        border-left: 4px solid #22c55e;
        border-radius: 10px;
        color: #14532d;
        padding: 1.2rem 1.4rem;
        margin: 0.8rem 0;
        line-height: 1.65;
    }

    .alert-success h4 {
        color: #166534;
        margin: 0 0 0.6rem;
        font-size: 1rem;
    }

    .alert-success ul {
        margin: 0.2rem 0 0;
        padding-left: 1.3rem;
    }

    .alert-success li {
        margin-bottom: 0.35rem;
    }

    /* ===== TARJETAS DE RECOMENDACIONES ===== */
    .rec-card {
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        color: #ffffff;
        line-height: 1.65;
        box-shadow:
            0 2px 6px rgba(0,0,0,0.10),
            0 8px 20px rgba(0,0,0,0.08);
    }

    .rec-card h4 {
        margin: 0 0 0.8rem;
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
    }

    .rec-card ul {
        margin: 0;
        padding-left: 1.3rem;
    }

    .rec-card li {
        margin-bottom: 0.4rem;
        font-size: 0.93rem;
    }

    .rec-card-short  { background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%); }
    .rec-card-medium { background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%); }
    .rec-card-long   { background: linear-gradient(135deg, #059669 0%, #047857 100%); }

    /* ===== STREAMLIT METRIC WIDGETS ===== */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #1565c0;
    }

    /* Contenedor de cada metric widget con elevación suave */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        box-shadow:
            0 2px 6px rgba(26,115,232,0.08),
            0 8px 20px rgba(26,115,232,0.07);
        border: 1px solid rgba(26,115,232,0.09);
        border-top: 3px solid #1a73e8;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow:
            0 4px 10px rgba(26,115,232,0.14),
            0 14px 32px rgba(26,115,232,0.12);
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #6b7a99;
    }
    
    /* ESTILOS PARA EL RANKING */
    .ranking-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        margin-bottom: 2rem;
    }
    
    .podium-container {
        display: flex;
        justify-content: center;
        align-items: flex-end;
        gap: 1.5rem;
        margin: 2rem 0;
        padding: 2rem;
    }
    
    .podium-place {
        flex: 1;
        max-width: 200px;
        text-align: center;
        transition: transform 0.3s ease;
    }
    
    .podium-place:hover {
        transform: translateY(-10px);
    }
    
    .podium-first {
        order: 2;
    }
    
    .podium-second {
        order: 1;
    }
    
    .podium-third {
        order: 3;
    }
    
    .podium-avatar {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: linear-gradient(135deg, #fff 0%, #f0f0f0 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3rem;
        margin: 0 auto 1rem;
        border: 4px solid;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }
    
    .podium-first .podium-avatar {
        width: 140px;
        height: 140px;
        border-color: #FFD700;
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
    }
    
    .podium-second .podium-avatar {
        width: 120px;
        height: 120px;
        border-color: #C0C0C0;
        background: linear-gradient(135deg, #C0C0C0 0%, #A8A8A8 100%);
    }
    
    .podium-third .podium-avatar {
        width: 110px;
        height: 110px;
        border-color: #CD7F32;
        background: linear-gradient(135deg, #CD7F32 0%, #B8732E 100%);
    }
    
    .podium-base {
        background: rgba(255, 255, 255, 0.95);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
        margin-top: 1rem;
    }
    
    .podium-first .podium-base {
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.2) 0%, rgba(255, 255, 255, 0.95) 100%);
        padding: 2rem 1.5rem;
    }
    
    .podium-second .podium-base {
        background: linear-gradient(135deg, rgba(192, 192, 192, 0.2) 0%, rgba(255, 255, 255, 0.95) 100%);
    }
    
    .podium-third .podium-base {
        background: linear-gradient(135deg, rgba(205, 127, 50, 0.2) 0%, rgba(255, 255, 255, 0.95) 100%);
    }
    
    .podium-name {
        font-weight: 700;
        font-size: 1.1rem;
        color: #333;
        margin-bottom: 0.5rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .podium-score {
        font-size: 2rem;
        font-weight: 800;
        color: #667eea;
        margin: 0.5rem 0;
    }
    
    .podium-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        margin-top: 0.5rem;
    }
    
    .leaderboard-row {
        background: white;
        padding: 1rem 1.5rem;
        margin: 0.5rem 0;
        border-radius: 12px;
        display: flex;
        align-items: center;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .leaderboard-row:hover {
        transform: translateX(10px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    
    .rank-number {
        font-size: 1.5rem;
        font-weight: 800;
        color: #667eea;
        min-width: 50px;
        text-align: center;
    }
    
    .player-info {
        flex: 1;
        margin: 0 1rem;
    }
    
    .player-name {
        font-weight: 700;
        font-size: 1.1rem;
        color: #333;
        margin-bottom: 0.2rem;
    }
    
    .player-score {
        font-size: 1.8rem;
        font-weight: 800;
        color: #667eea;
        min-width: 100px;
        text-align: right;
    }
    
    .trophy-icon {
        font-size: 2.5rem;
        animation: bounce 2s infinite;
    }
    
    .login-hero {
        text-align: center;
        margin: 3rem auto 2rem;
        max-width: 640px;
    }
    
    .login-hero h1 {
        font-size: 3rem;
        font-weight: 800;
        color: #f4f7ff;
        margin-bottom: 0.5rem;
    }
    
    .login-hero p {
        color: #cfd6e8;
        font-size: 1.1rem;
        margin: 0 auto;
    }
    
    .login-logo img {
        width: 320px;
        max-width: 85%;
        margin: 0 auto 1.5rem;
        display: block;
        filter: drop-shadow(0 18px 40px rgba(13, 27, 42, 0.25));
    }
    
    .login-helper {
        text-align: center;
        color: #c0cadc;
        margin-bottom: 1.2rem;
    }
    
    .login-background {
        background: #0b1a2b;
        border-radius: 24px;
        padding: 3rem 2rem 4rem;
        box-shadow: 0 35px 80px rgba(5, 10, 20, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.07);
    }
    
    .login-card {
        background: #ffffff;
        border-radius: 26px;
        padding: 2.8rem 3.2rem;
        border: 1px solid rgba(13, 27, 42, 0.1);
        box-shadow: 0 30px 70px rgba(4, 9, 20, 0.25);
        color: #0d1b2a;
    }
    
    .login-card label {
        color: #ffffff !important;
        font-weight: 600;
    }
    
    .login-card input {
        border-radius: 14px !important;
        border: 1px solid rgba(13, 27, 42, 0.2) !important;
        background: #f5f6fb;
        color: #0d1b2a !important;
    }
    
    .login-card input::placeholder {
        color: rgba(13, 27, 42, 0.55);
    }
    
    .login-card .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #5a60ff 100%);
        border: none;
        color: #ffffff;
        box-shadow: 0 18px 45px rgba(89, 101, 242, 0.35);
    }
    
    form[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 24px;
        padding: 2.2rem;
        box-shadow: 0 25px 60px rgba(15, 23, 42, 0.15);
        border: 1px solid rgba(65, 90, 119, 0.1);
        backdrop-filter: blur(12px);
    }
    
    form[data-testid="stForm"] label {
        font-weight: 600;
        color: #FFFFFF !important;
    }
    
    form[data-testid="stForm"] input {
        border-radius: 12px !important;
        border: 1px solid rgba(13, 27, 42, 0.15) !important;
        background: rgba(160, 32, 240, 0.03);
    }

    .sidebar-user-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1rem;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.15);
        margin-bottom: 1rem;
    }

    .sidebar-user-name {
        font-size: 1rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.2rem;
    }

    .sidebar-user-email {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.75);
        margin-bottom: 0.8rem;
    }
    
    header [data-testid="stToolbar"] a[href*="github"] {
        display: none !important;
    }
    
    header [data-testid="stToolbar"] button[title*="Fork"],
    header [data-testid="stToolbar"] a[title*="Fork"] {
        display: none !important;
    }
    
    /* GLOBAL DROPDOWN / SELECTBOX SCROLLBAR STYLING */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"],
    div[role="listbox"],
    ul[role="listbox"],
    ul[data-baseweb="menu"] {
        max-height: 280px !important;
        overflow-y: auto !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
        -webkit-overflow-scrolling: touch !important;
    }

    [data-baseweb="popover"] ul,
    [data-baseweb="menu"] ul,
    div[role="listbox"] ul {
        max-height: 280px !important;
        overflow-y: auto !important;
    }

    /* Custom Scrollbar for Dropdown Popovers */
    [data-baseweb="popover"]::-webkit-scrollbar,
    [data-baseweb="popover"] *::-webkit-scrollbar,
    [data-baseweb="menu"]::-webkit-scrollbar,
    div[role="listbox"]::-webkit-scrollbar,
    ul[role="listbox"]::-webkit-scrollbar {
        width: 8px !important;
    }

    [data-baseweb="popover"]::-webkit-scrollbar-track,
    [data-baseweb="popover"] *::-webkit-scrollbar-track,
    [data-baseweb="menu"]::-webkit-scrollbar-track,
    div[role="listbox"]::-webkit-scrollbar-track,
    ul[role="listbox"]::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.1) !important;
        border-radius: 10px !important;
    }

    [data-baseweb="popover"]::-webkit-scrollbar-thumb,
    [data-baseweb="popover"] *::-webkit-scrollbar-thumb,
    [data-baseweb="menu"]::-webkit-scrollbar-thumb,
    div[role="listbox"]::-webkit-scrollbar-thumb,
    ul[role="listbox"]::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%) !important;
        border-radius: 10px !important;
    }

    [data-baseweb="popover"] li,
    div[role="listbox"] li,
    ul[role="listbox"] li,
    [data-baseweb="menu"] [role="option"] {
        padding: 0.6rem 1rem !important;
        font-size: 0.95rem !important;
        border-radius: 6px !important;
        transition: background 0.2s ease !important;
    }

    /* Selectbox Container Focus & Hover */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px !important;
    }

    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
</style>


"""


def load_sidebar_css() -> str:
    """Carga el CSS de la barra lateral desde el archivo estatico dedicado."""
    from pathlib import Path
    css_path = Path(__file__).parent / "static" / "sidebar.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def inject_base_styles():
    """Inyecta el CSS del dashboard y la barra lateral con cache-busting."""
    import time
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    sidebar_css = load_sidebar_css()
    if sidebar_css:
        st.markdown(f"<style>/* v={time.time()} */\n{sidebar_css}</style>", unsafe_allow_html=True)


def load_login_css() -> str:
    """Carga el CSS del login desde el archivo estatico dedicado."""
    from pathlib import Path
    css_path = Path(__file__).parent / "static" / "login.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""
