import os
import streamlit as st

st.set_page_config(
    page_title="Tech Job Recommender | AI-Powered Job Matching",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "# Tech Job Recommender\nAI-powered job matching for tech professionals."
    }
)

import plotly.graph_objects as go
from typing import List, Dict, Optional
import requests

if "theme" not in st.session_state:
    st.session_state.theme = "light"

THEMES = {
    "light": {
        "name": "☀️ Light",
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8f9fa",
        "bg_card": "#ffffff",
        "text_primary": "#1a1a1a",
        "text_secondary": "#666666",
        "accent": "#1976d2",
        "accent_gradient": "linear-gradient(135deg, #1976d2 0%, #1565c0 100%)",
        "border": "#e0e0e0",
        "shadow": "rgba(0,0,0,0.08)",
        "success": "#4caf50",
        "warning": "#ff9800",
        "chart_grid": "#e0e0e0",
        "chart_text": "#333333",
    },
    "dark": {
        "name": "🌙 Dark",
        "bg_primary": "#0d1117",
        "bg_secondary": "#161b22",
        "bg_card": "#21262d",
        "text_primary": "#f0f6fc",
        "text_secondary": "#8b949e",
        "accent": "#58a6ff",
        "accent_gradient": "linear-gradient(135deg, #58a6ff 0%, #1f6feb 100%)",
        "border": "#30363d",
        "shadow": "rgba(0,0,0,0.4)",
        "success": "#3fb950",
        "warning": "#d29922",
        "chart_grid": "#30363d",
        "chart_text": "#f0f6fc",
    }
}

def get_theme():
    return THEMES[st.session_state.theme]

def get_theme_css():
    t = get_theme()
    is_dark = st.session_state.theme == "dark"
    
    # Dark mode specific colors
    input_bg = "#21262d" if is_dark else "#ffffff"
    input_text = "#f0f6fc" if is_dark else "#1a1a1a"
    dropdown_bg = "#21262d" if is_dark else "#ffffff"
    dropdown_text = "#f0f6fc" if is_dark else "#1a1a1a"
    dropdown_hover = "#30363d" if is_dark else "#f0f0f0"
    button_bg = "#30363d" if is_dark else "#f0f0f0"
    button_text = "#f0f6fc" if is_dark else "#1a1a1a"
    
    # Dropdown popover (opened menu) - Streamlit forces light bg, so always use dark text
    popover_bg = "#ffffff"
    popover_text = "#1a1a1a"
    popover_hover = "#f0f0f0"
    
    return f"""
<style>
    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* Main app background */
    .stApp {{
        background-color: {t['bg_primary']};
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {t['bg_secondary']};
        border-right: 1px solid {t['border']};
    }}
    
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {{
        color: {t['text_primary']} !important;
    }}
    
    /* ============================================ */
    /* TEXT INPUTS & TEXT AREAS                     */
    /* ============================================ */
    [data-testid="stSidebar"] .stTextArea textarea,
    [data-testid="stSidebar"] .stTextInput input {{
        background-color: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
    }}
    
    [data-testid="stSidebar"] textarea::placeholder,
    [data-testid="stSidebar"] input::placeholder {{
        color: {t['text_secondary']} !important;
        opacity: 0.8 !important;
    }}
    
    /* ============================================ */
    /* NUMBER INPUT WITH +/- BUTTONS                */
    /* ============================================ */
    [data-testid="stSidebar"] .stNumberInput {{
        background-color: transparent !important;
    }}
    
    [data-testid="stSidebar"] .stNumberInput input {{
        background-color: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {t['border']} !important;
    }}
    
    [data-testid="stSidebar"] .stNumberInput button {{
        background-color: {button_bg} !important;
        color: {button_text} !important;
        border: 1px solid {t['border']} !important;
    }}
    
    [data-testid="stSidebar"] .stNumberInput button:hover {{
        background-color: {t['accent']} !important;
        color: white !important;
    }}
    
    [data-testid="stSidebar"] .stNumberInput [data-baseweb="input"] {{
        background-color: {input_bg} !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stNumberInputContainer"] {{
        background-color: {input_bg} !important;
        border-radius: 8px !important;
    }}
    
    [data-testid="stSidebar"] [data-testid="stNumberInputContainer"] button {{
        background-color: {button_bg} !important;
        color: {button_text} !important;
    }}
    
    /* Step buttons (+ and -) */
    [data-testid="stSidebar"] button[kind="secondary"] {{
        background-color: {button_bg} !important;
        color: {button_text} !important;
    }}
    
    /* ============================================ */
    /* SELECT BOXES / DROPDOWNS                     */
    /* ============================================ */
    [data-testid="stSidebar"] .stSelectbox > div > div {{
        background-color: {dropdown_bg} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
    }}
    
    [data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {{
        background-color: {dropdown_bg} !important;
        color: {dropdown_text} !important;
    }}
    
    [data-testid="stSidebar"] .stSelectbox span,
    [data-testid="stSidebar"] .stSelectbox div {{
        color: {dropdown_text} !important;
    }}
    
    /* Dropdown arrow icon */
    [data-testid="stSidebar"] .stSelectbox svg {{
        fill: {dropdown_text} !important;
    }}
    
    /* ============================================ */
    /* DROPDOWN MENU (POPOVER)                      */
    /* ============================================ */
    [data-baseweb="popover"] {{
        background-color: {popover_bg} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 20px {t['shadow']} !important;
    }}
    
    [data-baseweb="popover"] * {{
        color: {popover_text} !important;
    }}
    
    [data-baseweb="menu"] {{
        background-color: {popover_bg} !important;
    }}
    
    [data-baseweb="menu"] ul {{
        background-color: {popover_bg} !important;
    }}
    
    [data-baseweb="menu"] li {{
        background-color: {popover_bg} !important;
        color: {popover_text} !important;
    }}
    
    [data-baseweb="menu"] li * {{
        color: {popover_text} !important;
    }}
    
    [data-baseweb="menu"] li:hover {{
        background-color: {popover_hover} !important;
    }}
    
    [data-baseweb="menu"] li[aria-selected="true"] {{
        background-color: {t['accent']} !important;
        color: white !important;
    }}
    
    [data-baseweb="menu"] li[aria-selected="true"] * {{
        color: white !important;
    }}
    
    /* Option text in dropdown - force dark text on light bg */
    [data-baseweb="menu"] li span,
    [data-baseweb="menu"] li div,
    [data-baseweb="menu"] li p {{
        color: {popover_text} !important;
    }}
    
    [data-baseweb="menu"] li:hover span,
    [data-baseweb="menu"] li:hover div,
    [data-baseweb="menu"] li:hover p {{
        color: {popover_text} !important;
    }}
    
    [data-baseweb="menu"] li[aria-selected="true"] span,
    [data-baseweb="menu"] li[aria-selected="true"] div,
    [data-baseweb="menu"] li[aria-selected="true"] p {{
        color: white !important;
    }}
    
    /* Streamlit selectbox dropdown list items */
    div[data-baseweb="select"] ul li {{
        color: {popover_text} !important;
    }}
    
    /* Force text color in all dropdown options */
    [role="listbox"] [role="option"] {{
        color: {popover_text} !important;
        background-color: {popover_bg} !important;
    }}
    
    [role="listbox"] [role="option"]:hover {{
        background-color: {popover_hover} !important;
    }}
    
    [role="listbox"] [role="option"][aria-selected="true"] {{
        background-color: {t['accent']} !important;
        color: white !important;
    }}
    
    /* ============================================ */
    /* SLIDER                                       */
    /* ============================================ */
    [data-testid="stSidebar"] .stSlider label {{
        color: {t['text_primary']} !important;
    }}
    
    [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {{
        background-color: transparent !important;
    }}
    
    /* ============================================ */
    /* CHECKBOX                                     */
    /* ============================================ */
    [data-testid="stSidebar"] .stCheckbox label {{
        color: {t['text_primary']} !important;
    }}
    
    /* ============================================ */
    /* EXPANDER                                     */
    /* ============================================ */
    [data-testid="stSidebar"] .streamlit-expanderHeader {{
        background-color: {t['bg_card']} !important;
        color: {t['text_primary']} !important;
        border: 1px solid {t['border']} !important;
        border-radius: 8px !important;
    }}
    
    [data-testid="stSidebar"] .streamlit-expanderContent {{
        background-color: {t['bg_card']} !important;
        border: 1px solid {t['border']} !important;
        border-top: none !important;
    }}
    
    /* Main container */
    .main .block-container {{
        padding-top: 1rem;
        max-width: 1200px;
    }}
    
    /* Header */
    .main-header {{
        background: {t['accent_gradient']};
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 20px {t['shadow']};
    }}
    
    .main-header h1 {{
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        color: white;
    }}
    
    .main-header p {{
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
        color: white;
    }}
    
    /* Stat cards */
    .stat-card {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 2px 8px {t['shadow']};
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    
    .stat-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 16px {t['shadow']};
    }}
    
    .stat-value {{
        font-size: 2rem;
        font-weight: 700;
        color: {t['accent']};
    }}
    
    .stat-label {{
        color: {t['text_secondary']};
        font-size: 0.85rem;
        margin-top: 0.25rem;
    }}
    
    /* Job cards */
    .job-card {{
        background: {t['bg_card']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px {t['shadow']};
        transition: all 0.2s ease;
    }}
    
    .job-card:hover {{
        border-color: {t['accent']};
        box-shadow: 0 4px 20px {t['shadow']};
    }}
    
    /* Match badges */
    .match-badge {{
        display: inline-flex;
        align-items: center;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.95rem;
    }}
    
    .match-excellent {{
        background: linear-gradient(135deg, #4caf50 0%, #43a047 100%);
        color: white;
    }}
    
    .match-strong {{
        background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
        color: white;
    }}
    
    .match-good {{
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        color: white;
    }}
    
    .match-partial {{
        background: {t['bg_secondary']};
        color: {t['text_secondary']};
        border: 1px solid {t['border']};
    }}
    
    /* Skill tags */
    .skill-tag {{
        display: inline-block;
        padding: 0.3rem 0.75rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 0.15rem;
        font-weight: 500;
    }}
    
    .skill-matched {{
        background: {'#1a4d2e' if st.session_state.theme == 'dark' else '#e8f5e9'};
        color: {t['success']};
        border: 1px solid {t['success']}40;
    }}
    
    .skill-missing {{
        background: {t['bg_secondary']};
        color: {t['text_secondary']};
        border: 1px solid {t['border']};
    }}
    
    .skill-critical {{
        background: {'#4d3319' if st.session_state.theme == 'dark' else '#fff3e0'};
        color: {t['warning']};
        border: 1px solid {t['warning']}40;
    }}
    
    /* Info tags */
    .info-tag {{
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 0.75rem;
        border-radius: 6px;
        font-size: 0.85rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        background: {t['bg_secondary']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
    }}
    
    /* Section headers */
    .section-header {{
        font-size: 1.25rem;
        font-weight: 600;
        color: {t['text_primary']};
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid {t['accent']};
    }}
    
    /* Buttons */
    .stButton > button {{
        background: {t['accent_gradient']};
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.2s ease;
    }}
    
    .stButton > button:hover {{
        box-shadow: 0 4px 12px {t['accent']}40;
        transform: translateY(-1px);
    }}
    
    /* Empty state */
    .empty-state {{
        text-align: center;
        padding: 3rem;
        color: {t['text_secondary']};
        background: {t['bg_card']};
        border-radius: 16px;
        border: 1px solid {t['border']};
    }}
    
    .empty-state-icon {{
        font-size: 4rem;
        margin-bottom: 1rem;
    }}
    
    /* Text colors */
    h1, h2, h3, h4, h5, h6 {{
        color: {t['text_primary']} !important;
    }}
    
    p, span, div {{
        color: {t['text_primary']};
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        background: {t['bg_secondary']} !important;
        border-radius: 8px;
    }}
    
    /* Metrics */
    [data-testid="stMetricValue"] {{
        color: {t['accent']} !important;
    }}
    
    [data-testid="stMetricLabel"] {{
        color: {t['text_secondary']} !important;
    }}
</style>
"""


def get_api_base_url() -> str:
    url = os.environ.get("API_BASE_URL")
    if url:
        return url
    try:
        if hasattr(st, 'secrets') and "API_BASE_URL" in st.secrets:
            return st.secrets["API_BASE_URL"]
    except Exception:
        pass
    return "http://localhost:8000"

API_BASE_URL = get_api_base_url()

PRESETS = {
    "balanced": {
        "name": "⚖️ Balanced",
        "description": "Equal consideration of all factors",
        "weights": {"skill": 0.30, "experience": 0.25, "seniority": 0.15, "location": 0.15, "salary": 0.15}
    },
    "skill_focused": {
        "name": "🎯 Skill-Focused",
        "description": "Prioritizes skill match (50% weight)",
        "weights": {"skill": 0.50, "experience": 0.20, "seniority": 0.15, "location": 0.10, "salary": 0.05}
    },
    "career_growth": {
        "name": "📈 Career Growth",
        "description": "Emphasizes experience alignment (35% weight)",
        "weights": {"skill": 0.30, "experience": 0.35, "seniority": 0.20, "location": 0.10, "salary": 0.05}
    },
    "compensation_first": {
        "name": "💰 Compensation First",
        "description": "Focuses on salary fit (35% weight)",
        "weights": {"skill": 0.25, "experience": 0.20, "seniority": 0.10, "location": 0.10, "salary": 0.35}
    },
    "remote_priority": {
        "name": "🌍 Remote Priority",
        "description": "Prioritizes remote/location match (30% weight)",
        "weights": {"skill": 0.30, "experience": 0.20, "seniority": 0.10, "location": 0.30, "salary": 0.10}
    },
}

SENIORITY_LEVELS = ["entry", "mid", "senior", "lead", "executive"]
SENIORITY_DISPLAY = {
    "entry": "🌱 Entry Level",
    "mid": "💼 Mid Level", 
    "senior": "⭐ Senior",
    "lead": "👑 Lead",
    "executive": "🏆 Executive"
}

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
    
    def _handle_response(self, response: requests.Response) -> Dict:
        if response.status_code >= 400:
            try:
                error_msg = response.json().get("detail", "Unknown error")
            except:
                error_msg = response.text or f"HTTP {response.status_code}"
            raise Exception(f"API Error: {error_msg}")
        return response.json()
    
    def create_candidate(self, skills, experience_years, seniority, location_preference, remote_preferred, salary_expected):
        payload = {
            "skills": skills, "experience_years": experience_years, "seniority": seniority,
            "location_preference": location_preference, "remote_preferred": remote_preferred,
            "salary_expected": salary_expected,
        }
        return self._handle_response(requests.post(f"{self.base_url}/api/candidates", json=payload))
    
    def get_recommendations(self, candidate_id: str, preset: str = "balanced", limit: int = 10):
        return self._handle_response(requests.get(
            f"{self.base_url}/api/recommendations/{candidate_id}", params={"preset": preset, "limit": limit}))
    
    def get_jobs(self, limit: int = 20, offset: int = 0):
        return self._handle_response(requests.get(f"{self.base_url}/api/jobs", params={"limit": limit, "offset": offset}))
    
    def submit_feedback(self, candidate_id, job_id, feedback_type, preset_used=None):
        payload = {"candidate_id": candidate_id, "job_id": job_id, "feedback_type": feedback_type, "preset_used": preset_used}
        return self._handle_response(requests.post(f"{self.base_url}/api/feedback", json=payload))
    
    def health_check(self):
        try:
            return self._handle_response(requests.get(f"{self.base_url}/health", timeout=5))
        except:
            return {"status": "unhealthy"}

api_client = APIClient(API_BASE_URL)


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

def render_radar_chart(scores: Dict) -> go.Figure:
    t = get_theme()
    categories = ['Skills', 'Experience', 'Seniority', 'Location', 'Salary']
    values = [scores.get("skill_score", 0), scores.get("experience_score", 0),
              scores.get("seniority_score", 0), scores.get("location_score", 0), scores.get("salary_score", 0)]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]], theta=categories + [categories[0]],
        fill='toself', fillcolor=hex_to_rgba(t['accent'], 0.3),
        line=dict(color=t['accent'], width=2), name='Match Score'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickvals=[0.25, 0.5, 0.75, 1.0],
                           ticktext=['25%', '50%', '75%', '100%'], gridcolor=t['chart_grid'],
                           tickfont=dict(color=t['chart_text'])),
            angularaxis=dict(gridcolor=t['chart_grid'], tickfont=dict(color=t['chart_text'])),
            bgcolor='rgba(0,0,0,0)',
        ),
        showlegend=False, height=280, margin=dict(l=50, r=50, t=30, b=30),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def render_comparison_chart(recommendations: List[Dict]) -> go.Figure:
    if not recommendations:
        return None
    t = get_theme()
    top_jobs = recommendations[:5]
    job_titles = [f"{r['job']['title'][:28]}..." if len(r['job']['title']) > 28 else r['job']['title'] for r in top_jobs]
    scores = [r['scores']['composite_score'] * 100 for r in top_jobs]
    colors = ['#4caf50' if s >= 75 else '#2196f3' if s >= 60 else '#ff9800' if s >= 45 else '#9e9e9e' for s in scores]
    
    fig = go.Figure(data=go.Bar(
        x=scores, y=job_titles, orientation='h', marker_color=colors,
        text=[f"{s:.0f}%" for s in scores], textposition='outside',
        textfont=dict(size=11, color=t['chart_text']),
    ))
    
    fig.update_layout(
        xaxis_title="", yaxis_title="", height=200, margin=dict(l=10, r=40, t=10, b=30),
        xaxis=dict(range=[0, 110], gridcolor=t['chart_grid'], tickfont=dict(color=t['chart_text'])),
        yaxis=dict(autorange="reversed", tickfont=dict(color=t['chart_text'])),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def render_job_card(rec: Dict, candidate_id: str, preset_used: str, idx: int):
    t = get_theme()
    job = rec["job"]
    scores = rec["scores"]
    skill_analysis = rec.get("skill_analysis", {})
    explanation = rec.get("explanation", "")
    match_pct = int(scores["composite_score"] * 100)
    
    if match_pct >= 80:
        badge_class, badge_text = "match-excellent", f"🎯 {match_pct}% Excellent"
    elif match_pct >= 65:
        badge_class, badge_text = "match-strong", f"✨ {match_pct}% Strong"
    elif match_pct >= 50:
        badge_class, badge_text = "match-good", f"👍 {match_pct}% Good"
    else:
        badge_class, badge_text = "match-partial", f"📊 {match_pct}%"
    
    with st.container():
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"### {job['title']}")
            company_line = f"**{job['company']}**"
            if job['requirements'].get('location'):
                company_line += f" · 📍 {job['requirements']['location']}"
            st.markdown(company_line)
        with col2:
            st.markdown(f"<div class='match-badge {badge_class}'>{badge_text}</div>", unsafe_allow_html=True)
        
        # Tags
        req = job['requirements']
        tags_html = "<div style='margin: 0.75rem 0;'>"
        if req.get('seniority'):
            tags_html += f"<span class='info-tag'>🎖️ {req['seniority'].title()}</span>"
        if req.get('remote'):
            tags_html += "<span class='info-tag'>🌍 Remote</span>"
        if req.get('salary_min') and req.get('salary_max'):
            tags_html += f"<span class='info-tag'>💰 ${req['salary_min']:,}-${req['salary_max']:,}</span>"
        tags_html += "</div>"
        st.markdown(tags_html, unsafe_allow_html=True)
        
        # Skills
        if req.get('skills'):
            matched = set(s.lower() for s in skill_analysis.get('matched_skills', []))
            critical = set(s.lower() for s in skill_analysis.get('critical_missing_skills', []))
            skills_html = "<div style='margin: 0.5rem 0;'>"
            for skill in req['skills'][:10]:
                if skill.lower() in matched:
                    skills_html += f"<span class='skill-tag skill-matched'>✓ {skill}</span>"
                elif skill.lower() in critical:
                    skills_html += f"<span class='skill-tag skill-critical'>⚡ {skill}</span>"
                else:
                    skills_html += f"<span class='skill-tag skill-missing'>{skill}</span>"
            skills_html += "</div>"
            st.markdown(skills_html, unsafe_allow_html=True)
        
        with st.expander("📊 Match Details"):
            st.markdown(explanation)
            cols = st.columns(5)
            for col, (label, key) in zip(cols, [("Skills", "skill_score"), ("Exp", "experience_score"),
                ("Seniority", "seniority_score"), ("Location", "location_score"), ("Salary", "salary_score")]):
                col.metric(label, f"{scores.get(key, 0)*100:.0f}%")
        
        col1, col2, _ = st.columns([1, 1, 6])
        with col1:
            if st.button("👍 Like", key=f"like_{job['id']}_{idx}", use_container_width=True):
                try:
                    api_client.submit_feedback(candidate_id, job['id'], "like", preset_used)
                    st.success("✓")
                except Exception as e:
                    st.error(str(e))
        with col2:
            if st.button("👎 Pass", key=f"pass_{job['id']}_{idx}", use_container_width=True):
                try:
                    api_client.submit_feedback(candidate_id, job['id'], "dislike", preset_used)
                    st.info("✓")
                except Exception as e:
                    st.error(str(e))
        st.markdown("---")


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total == 0:
        return {"skill": 0.2, "experience": 0.2, "seniority": 0.2, "location": 0.2, "salary": 0.2}
    return {k: v / total for k, v in weights.items()}

def parse_skills(skills_input: str) -> List[str]:
    if not skills_input:
        return []
    return [s.strip() for s in skills_input.split(",") if s.strip()]

def main():
    t = get_theme()
    
    # Apply theme CSS
    st.markdown(get_theme_css(), unsafe_allow_html=True)
    
    # Initialize session state
    if "candidate_id" not in st.session_state:
        st.session_state.candidate_id = None
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = None
    if "current_preset" not in st.session_state:
        st.session_state.current_preset = "balanced"
    if "custom_weights" not in st.session_state:
        st.session_state.custom_weights = PRESETS["balanced"]["weights"].copy()
    
    with st.sidebar:
        # Theme toggle at top of sidebar
        st.markdown("### 🎨 Theme")
        theme_col1, theme_col2 = st.columns(2)
        with theme_col1:
            if st.button("☀️ Light", use_container_width=True, 
                        type="primary" if st.session_state.theme == "light" else "secondary"):
                st.session_state.theme = "light"
                st.rerun()
        with theme_col2:
            if st.button("🌙 Dark", use_container_width=True,
                        type="primary" if st.session_state.theme == "dark" else "secondary"):
                st.session_state.theme = "dark"
                st.rerun()
        
        st.markdown("---")
        st.markdown("## 👤 Your Profile")
        
        skills_input = st.text_area("🛠️ Skills", placeholder="Python, ML, SQL, FastAPI, Docker, AWS",
                                    help="Enter skills separated by commas", height=100)
        
        experience = st.slider("📅 Years of Experience", 0, 30, 5)
        
        seniority = st.selectbox("🎖️ Seniority Level", SENIORITY_LEVELS, index=2,
                                 format_func=lambda x: SENIORITY_DISPLAY.get(x, x.title()))
        
        st.markdown("---")
        st.markdown("## 📍 Preferences")
        
        location = st.text_input("Location", placeholder="San Francisco, CA")
        remote_preferred = st.checkbox("🌍 Remote Preferred", value=True)
        salary = st.number_input("💰 Expected Salary ($)", 0, 10000000, 120000, 10000, format="%d")
        
        st.markdown("---")
        st.markdown("## ⚖️ Ranking Strategy")
        
        selected_preset = st.selectbox("Weight Preset", list(PRESETS.keys()),
                                       format_func=lambda x: PRESETS[x]["name"],
                                       index=list(PRESETS.keys()).index(st.session_state.current_preset))
        
        if selected_preset != st.session_state.current_preset:
            st.session_state.current_preset = selected_preset
            st.session_state.custom_weights = PRESETS[selected_preset]["weights"].copy()
        
        st.caption(PRESETS[selected_preset]["description"])
        
        with st.expander("🎛️ Fine-tune Weights"):
            w = st.session_state.custom_weights
            skill_w = st.slider("Skill Match", 0.0, 1.0, w["skill"], 0.05)
            exp_w = st.slider("Experience", 0.0, 1.0, w["experience"], 0.05)
            sen_w = st.slider("Seniority", 0.0, 1.0, w["seniority"], 0.05)
            loc_w = st.slider("Location", 0.0, 1.0, w["location"], 0.05)
            sal_w = st.slider("Salary", 0.0, 1.0, w["salary"], 0.05)
            
            # Calculate raw total and normalized weights
            raw_weights = {"skill": skill_w, "experience": exp_w, "seniority": sen_w, "location": loc_w, "salary": sal_w}
            raw_total = sum(raw_weights.values())
            normalized = normalize_weights(raw_weights)
            st.session_state.custom_weights = normalized
            
            # Show weight distribution
            st.markdown("---")
            st.markdown("**📊 Normalized Distribution:**")
            weight_cols = st.columns(5)
            labels = ["Skill", "Exp", "Sen", "Loc", "Sal"]
            keys = ["skill", "experience", "seniority", "location", "salary"]
            for col, label, key in zip(weight_cols, labels, keys):
                pct = int(normalized[key] * 100)
                col.metric(label, f"{pct}%")
            
            if abs(raw_total - 1.0) > 0.01:
                st.info(f"ℹ️ Weights auto-normalized (raw total: {raw_total:.2f})")
        
        st.markdown("---")
        search_clicked = st.button("🔍 Find Matching Jobs", type="primary", use_container_width=True)

    
    # Header
    st.markdown(f"""
    <div class="main-header">
        <h1>🎯 Tech Job Recommender</h1>
        <p>AI-powered job matching for Software Engineering, Data Science & DevOps</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API health
    health = api_client.health_check()
    
    if health.get("status") != "healthy":
        st.error("⚠️ Backend API is not available")
        st.info(f"Start the API: `uvicorn src.api.main:app --reload`")
        st.code(f"API URL: {API_BASE_URL}")
        return
    
    # Stats row
    stats = health.get("stats", {})
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-value">{stats.get('jobs_count', 0):,}</div>
            <div class="stat-label">Tech Jobs Available</div>
        </div>""", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""<div class="stat-card">
            <div class="stat-value">{stats.get('vectors_count', 0):,}</div>
            <div class="stat-label">Indexed for Search</div>
        </div>""", unsafe_allow_html=True)
    
    with col3:
        st.markdown("""<div class="stat-card">
            <div class="stat-value">✅</div>
            <div class="stat-label">API Online</div>
        </div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Handle search
    if search_clicked:
        skills = parse_skills(skills_input)
        if not skills:
            st.warning("⚠️ Please enter at least one skill.")
            return
        
        with st.spinner("🔍 Finding your perfect matches..."):
            try:
                candidate = api_client.create_candidate(
                    skills=skills, experience_years=experience, seniority=seniority,
                    location_preference=location if location else None,
                    remote_preferred=remote_preferred, salary_expected=salary if salary > 0 else None)
                st.session_state.candidate_id = candidate["id"]
                
                recs = api_client.get_recommendations(candidate["id"], st.session_state.current_preset, 15)
                st.session_state.recommendations = recs
            except Exception as e:
                st.error(f"❌ Error: {e}")
                return
    
    # Display recommendations
    if st.session_state.recommendations:
        recs = st.session_state.recommendations
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f'<div class="section-header">📋 Recommended Jobs ({len(recs["recommendations"])} matches)</div>',
                       unsafe_allow_html=True)
            for idx, rec in enumerate(recs["recommendations"]):
                render_job_card(rec, st.session_state.candidate_id, recs["preset_used"], idx)
        
        with col2:
            st.markdown('<div class="section-header">📊 Analysis</div>', unsafe_allow_html=True)
            if recs["recommendations"]:
                st.markdown("**Top Match Breakdown**")
                st.plotly_chart(render_radar_chart(recs["recommendations"][0]["scores"]), use_container_width=True)
                
                st.markdown("**Top 5 Comparison**")
                bar = render_comparison_chart(recs["recommendations"])
                if bar:
                    st.plotly_chart(bar, use_container_width=True)
                
                st.markdown("**Skill Coverage**")
                all_matched, all_missing = set(), set()
                for r in recs["recommendations"][:5]:
                    sa = r.get("skill_analysis", {})
                    all_matched.update(sa.get("matched_skills", []))
                    all_missing.update(sa.get("missing_skills", []))
                all_missing -= all_matched
                
                if all_matched:
                    st.success(f"✅ **Strengths:** {', '.join(sorted(all_matched)[:6])}")
                if all_missing:
                    st.info(f"📚 **To Learn:** {', '.join(sorted(all_missing)[:6])}")
    else:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">🎯</div>
            <h3 style="color: {t['text_primary']}">Ready to find your perfect tech job?</h3>
            <p>Enter your skills in the sidebar and click <strong>Find Matching Jobs</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📌 Featured Jobs")
        try:
            jobs = api_client.get_jobs(limit=5).get("jobs", [])
            for job in jobs:
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{job['title']}**")
                        st.caption(f"🏢 {job['company']}")
                    with col2:
                        if job['requirements'].get('remote'):
                            st.caption("🌍 Remote")
                    if job['requirements'].get('skills'):
                        skills_preview = ', '.join(job['requirements']['skills'][:5])
                        st.caption(f"🛠️ {skills_preview}")
                    st.markdown("---")
        except:
            pass


if __name__ == "__main__":
    main()
