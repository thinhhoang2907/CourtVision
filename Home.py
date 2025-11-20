import streamlit as st

st.set_page_config(page_title="CourtVision", page_icon="🏀", layout="wide")

# Enhanced CSS styling
st.markdown("""
    <style>
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 4rem 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .hero-title {
        font-size: 4rem;
        font-weight: 800;
        color: white;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .hero-subtitle {
        font-size: 1.5rem;
        color: rgba(255,255,255,0.95);
        margin-top: 1rem;
    }
    .feature-card {
        background: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: transform 0.3s ease;
        height: 100%;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        border-color: #1f77b4;
    }
    .feature-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .feature-description {
        color: #666;
        font-size: 1rem;
        line-height: 1.6;
    }
    .stats-highlight {
        background: #1f77b4;
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 2rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stats-number {
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
    }
    .stats-label {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    .navigation-section {
        margin-top: 3rem;
    }
    .nav-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .nav-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        transform: translateY(-3px);
    }
    .nav-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .nav-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
    }
    .footer {
        text-align: center;
        color: #888;
        padding: 2rem;
        margin-top: 4rem;
        border-top: 2px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("""
    <div style='text-align: center; padding: 1rem;'>
        <h2 style='color: #667eea; margin: 0;'>🏀 CourtVision</h2>
        <p style='color: #666; font-size: 0.9rem; margin-top: 0.5rem;'>NBA Analytics Platform</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.divider()

st.sidebar.markdown("""
    <div style='padding: 1rem;'>
        <h3 style='color: #333; font-size: 1.1rem; margin-bottom: 1rem;'>Navigation</h3>
        <p style='color: #666; font-size: 0.95rem; line-height: 1.6;'>
            Use the pages above to explore:
        </p>
        <ul style='color: #666; font-size: 0.9rem; line-height: 1.8;'>
            <li><strong>Player Stats</strong> - Individual performance</li>
            <li><strong>Team Stats</strong> - Team analytics</li>
            <li><strong>Comparisons</strong> - Head-to-head analysis</li>
            <li><strong>Shot Charts</strong> - Visual shot analysis</li>
        </ul>
    </div>
""", unsafe_allow_html=True)

# Hero Section
st.markdown("""
    <div class='hero-section'>
        <h1 class='hero-title'>🏀 CourtVision</h1>
        <p class='hero-subtitle'>Advanced NBA Statistics & Analytics Platform</p>
    </div>
""", unsafe_allow_html=True)

# Welcome message
st.markdown("""
    <div style='text-align: center; margin-bottom: 3rem;'>
        <p style='font-size: 1.2rem; color: #555; line-height: 1.8;'>
            Dive deep into NBA statistics with comprehensive player and team analytics.<br>
            Compare performances, analyze trends, and visualize shot charts with ease.
        </p>
    </div>
""", unsafe_allow_html=True)

# Feature cards
st.markdown("## Key Features")
st.markdown("")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
        <div class='feature-card'>
            <div class='feature-title'>Player Stats</div>
            <p class='feature-description'>
                Search and analyze individual player performance across seasons.
            </p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class='feature-card'>
            <div class='feature-title'>Team Analytics</div>
            <p class='feature-description'>
                Comprehensive team performance analysis including ratings, records, and player contributions.
            </p>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class='feature-card'>
            <div class='feature-title'>Comparisons</div>
            <p class='feature-description'>
                Head-to-head player and team comparisons with advanced metrics and matchup histories.
            </p>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
        <div class='feature-card'>
            <div class='feature-title'>Shot Charts</div>
            <p class='feature-description'>
                Interactive visual analysis of shot locations, efficiency zones, and shooting patterns.
            </p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("")
st.markdown("")

# Stats highlights
st.markdown("## Platform Capabilities")
stats_col1, stats_col2, stats_col3 = st.columns(3)

with stats_col1:
    st.markdown("""
        <div class='stats-highlight'>
            <p class='stats-number'>30+</p>
            <p class='stats-label'>NBA Teams</p>
        </div>
    """, unsafe_allow_html=True)

with stats_col2:
    st.markdown("""
        <div class='stats-highlight'>
            <p class='stats-number'>500+</p>
            <p class='stats-label'>Active Players</p>
        </div>
    """, unsafe_allow_html=True)

with stats_col3:
    st.markdown("""
        <div class='stats-highlight'>
            <p class='stats-number'>10+</p>
            <p class='stats-label'>Seasons Available</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# Getting Started Section
st.markdown("## Getting Started")
st.markdown("")

getting_started_col1, getting_started_col2 = st.columns([2, 1])

with getting_started_col1:
    st.markdown("""
        <div style='background: #f8f9fa; padding: 2rem; border-radius: 12px; border-left: 4px solid #1f77b4;'>
            <h3 style='color: #333; margin-top: 0;'>How to Use CourtVision</h3>
            <ol style='color: #666; font-size: 1rem; line-height: 2;'>
                <li><strong>Select a Page</strong> - Use the sidebar navigation to choose your analysis type</li>
                <li><strong>Choose Your Data</strong> - Select players, teams, or seasons you want to analyze</li>
                <li><strong>Explore Insights</strong> - View detailed statistics, charts, and comparisons</li>
                <li><strong>Refresh Data</strong> - Use the refresh button to get the latest statistics</li>
            </ol>
        </div>
    """, unsafe_allow_html=True)

with getting_started_col2:
    st.markdown("""
        <div style='background: #1f77b4; 
                    padding: 2rem; border-radius: 12px; color: white; height: 100%;
                    display: flex; flex-direction: column; justify-content: center;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
            <h3 style='color: white; margin-top: 0; text-align: center;'>Quick Tip</h3>
            <p style='font-size: 1rem; line-height: 1.6; text-align: center; margin-bottom: 0;'>
                Start with the <strong>Player Stats</strong> page to explore individual performances, 
                or jump to <strong>Comparisons</strong> for side-by-side analysis!
            </p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("")
st.markdown("")

# Navigation cards
st.markdown('<div class="navigation-section">', unsafe_allow_html=True)
st.markdown("## Quick Navigation")
st.markdown("")

nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)

with nav_col1:
    st.markdown("""
        <div class='nav-card'>
            <div class='nav-title'>Player Stats</div>
        </div>
    """, unsafe_allow_html=True)

with nav_col2:
    st.markdown("""
        <div class='nav-card'>
            <div class='nav-title'>Team Stats</div>
        </div>
    """, unsafe_allow_html=True)

with nav_col3:
    st.markdown("""
        <div class='nav-card'>
            <div class='nav-title'>Comparisons</div>
        </div>
    """, unsafe_allow_html=True)

with nav_col4:
    st.markdown("""
        <div class='nav-card'>
            <div class='nav-title'>Shot Charts</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
    <div class='footer'>
        <p style='font-size: 1rem; margin: 0;'><strong>CourtVision</strong> - NBA Analytics Platform</p>
        <p style='font-size: 0.9rem; margin-top: 0.5rem;'>Data sourced from NBA Stats API</p>
        <p style='font-size: 0.85rem; margin-top: 1rem; color: #aaa;'>
            Built with Streamlit • Real-time NBA Statistics • Advanced Analytics
        </p>
    </div>
""", unsafe_allow_html=True)