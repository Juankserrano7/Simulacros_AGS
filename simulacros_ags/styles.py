import streamlit as st

BASE_CSS = """
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
        min-width: 240px;
        max-width: 800px;
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
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
</style>
"""


def inject_base_styles():
    """Inyecta el CSS del dashboard."""
    st.markdown(BASE_CSS, unsafe_allow_html=True)
