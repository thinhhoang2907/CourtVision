# CourtVision

**Advanced NBA Statistics & Analytics Platform**

CourtVision is a comprehensive Python and Streamlit-based web application that makes basketball statistics accessible and engaging for fans of all levels. The platform provides interactive visualizations, detailed player and team analytics, and powerful comparison tools to help users understand basketball performance data.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.39.0-red)

---

## Table of Contents

- [Features](#-features)
- [Demo](#-demo)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Technologies Used](#-technologies-used)
- [Key Components](#-key-components)
- [Data Sources](#-data-sources)
- [Future Enhancements](#-future-enhancements)
- [Acknowledgments](#-acknowledgments)

---

##  Features

###  Player Statistics
- **Comprehensive Player Search**: Search for any NBA player by name or filter by team
- **Season-by-Season Analysis**: View detailed statistics for any season in a player's career
- **Per-Game Metrics**: PPG, RPG, APG, SPG, BPG with visual metric cards
- **Career Trends**: Interactive charts showing scoring and shooting efficiency over time
- **Advanced Statistics**: View detailed breakdowns including field goal percentages, minutes played, and more

###  Team Analytics
- **Team Performance Dashboard**: Season records, offensive/defensive ratings, and net ratings
- **Player Statistics by Team**: Complete roster analysis with per-game averages
- **Team Leaders**: Highlighted top performers in points, rebounds, and assists
- **Advanced Metrics**: Offensive rating, defensive rating, and efficiency metrics
- **Beautiful Data Tables**: Sortable, searchable player statistics with column configurations

###  Head-to-Head Comparisons
- **Player vs Player**: Side-by-side statistical comparisons with advanced metrics
- **Team vs Team**: Compare team performance with head-to-head matchup histories
- **Advanced Metrics Included**: 
  - Player Efficiency Rating (PER) using the full Hollinger/BBR formula
  - True Shooting Percentage (TS%)
  - Usage Rate (USG%)
- **Season Flexibility**: Automatically adjusts to available seasons for each player
- **Visual Comparison Tables**: Clean, organized data presentation

###  Shot Charts & Efficiency
- **Interactive Shot Charts**: Scatter plots showing every shot attempt on a regulation half-court
- **Efficiency Heatmaps**: Visualize shooting hot zones with gradient color mapping
- **Multi-Player Comparison**: Compare shot profiles for up to two players side-by-side
- **Customizable Views**: 
  - Color by player, make/miss status, or shot zone
  - Toggle between FG% and shot volume heatmaps
- **Accurate Court Rendering**: Properly scaled NBA half-court with all regulation markings
- **Hover Details**: Interactive tooltips showing shot distance, result, and location

---

##  Demo

**Live Application**: [CourtVision on Streamlit Cloud](#) *(https://courtvision2526.streamlit.app/)*

**Local Demo**:
```bash
streamlit run Home.py
```

---

##  Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Internet connection (for NBA API access)

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/thinhhoang2907/CourtVision.git
   cd CourtVision
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate Virtual Environment**
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```
   - **Windows**:
     ```bash
     .venv\Scripts\activate
     ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Application**
   ```bash
   streamlit run Home.py
   ```

6. **Access the Application**
   - Open your browser and navigate to `http://localhost:8501`

---

##  Usage

### Navigation
The application features a sidebar navigation system with four main sections:

1. **Player Stats**: Search and analyze individual player performance
2. **Team Stats**: Explore team-level statistics and roster analysis
3. **Comparisons**: Head-to-head player and team comparisons
4. **Shot Charts**: Visual analysis of shooting patterns and efficiency

### Quick Start Guide

**Analyzing a Player:**
1. Navigate to "Player Stats" from the sidebar
2. Either select a team to browse the roster or search by player name
3. Choose the player from the dropdown
4. Select a season to view detailed statistics
5. Explore career trends in the charts below

**Comparing Players:**
1. Navigate to "Comparisons" from the sidebar
2. Select "Players" mode
3. Choose a season for comparison
4. Search for and select two players (Player A and Player B)
5. View side-by-side statistics including advanced metrics

**Viewing Shot Charts:**
1. Navigate to "Shot Charts" from the sidebar
2. Select season and season type (Regular Season or Playoffs)
3. Search for up to two players to compare
4. Toggle between shot scatter plots and efficiency heatmaps
5. Customize color schemes and metrics

---

##  Project Structure

```
courtvision/
│
├── Home.py                          # Main landing page
├── pages/
│   ├── 1_Player_Stats.py           # Player statistics page
│   ├── 2_Team_Stats.py             # Team statistics page
│   ├── 3_Comparisons.py            # Comparison page
│   └── 4_Shot_Charts.py            # Shot charts page
│
├── courtvision/
│   └── data/
│       └── nba_client.py           # NBA API client and data processing
│
├── data/
│   └── cache/                      # Local data cache (generated)
│
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── .gitignore                      # Git ignore rules
```

---

##  Technologies Used

### Core Technologies
- **Python 3.13.7**: Primary programming language
- **Streamlit 1.50.0**: Web application framework
- **Pandas 2.2.3**: Data manipulation and analysis
- **NumPy**: Numerical computing for shot chart calculations

### Visualization Libraries
- **Matplotlib 3.9.2**: Static chart generation
- **Plotly 5.24.1**: Interactive visualizations and charts

### Data Source
- **nba_api 1.11.3**: Official NBA statistics API wrapper

### Development Tools
- **Visual Studio Code**: Code editor
- **Git & GitHub**: Version control
- **Streamlit Cloud**: Deployment platform

---

##  Key Components

### Data Processing (`nba_client.py`)
- **API Integration**: Robust connection to NBA Stats API with error handling
- **Caching System**: Local CSV-based cache to reduce API calls and improve performance
- **Data Normalization**: Consistent data formatting across different API endpoints
- **Advanced Calculations**:
  - Player Efficiency Rating (PER) using full Hollinger formula
  - True Shooting Percentage (TS%)
  - Usage Rate (USG%)
  - Team offensive/defensive ratings

### Court Visualization
- **Accurate Rendering**: NBA regulation half-court with proper dimensions
- **Court Elements**:
  - Three-point arc and corner lines
  - Free throw circle and lane (paint)
  - Restricted area arc
  - Backboard and hoop
- **Aspect Ratio Control**: Maintains 1:1 scaling to prevent distortion

### User Interface
- **Responsive Design**: Optimized for desktop and laptop viewing
- **Custom CSS Styling**: Professional appearance with gradient effects
- **Interactive Components**:
  - Searchable dropdowns
  - Toggle switches and radio buttons
  - Hover tooltips on charts
  - Sortable data tables

---

##  Data Sources

CourtVision uses the NBA Stats API through the `nba_api` Python library:

- **Player Statistics**: Basic and advanced metrics dating back several decades
- **Team Statistics**: Current and historical team performance data
- **Shot Chart Data**: Detailed shot location coordinates and outcomes
- **Game Logs**: Team and player game-by-game performance

**Data Update Frequency**: Real-time during NBA season (data typically updates within 24 hours of games)

**Caching Strategy**:
- Popular players/teams: Cached for 24 hours
- Historical data: Cached for 1 week
- Shot chart data: Cached per request session

---

##  Future Enhancements

### Planned Features
- **Multi-League Support**: Expand to include EuroLeague and NCAA basketball
- **Predictive Analytics**: Machine learning models for performance forecasting
- **Advanced Visualizations**: 
  - Player movement heatmaps
  - Play-by-play analysis
  - Defensive positioning charts
- **Mobile Application**: iOS and Android native apps
- **Social Features**:
  - User accounts and saved favorites
  - Share statistical insights
  - Custom analytical reports
- **Real-Time Updates**: Live game tracking and statistics
- **API Development**: Public API endpoints for third-party integration

### Potential Improvements
- Enhanced data visualization with D3.js
- Historical play-by-play database
- Advanced filtering and search capabilities
- Export functionality (PDF, CSV)
- Dark mode theme option

---


##  Acknowledgments

- **NBA Stats API**: For providing comprehensive basketball statistics data
- **Streamlit**: For the excellent web application framework
- **DePauw University CS Department**: For guidance and support throughout development
- **Basketball-Reference**: For PER calculation methodology
- **The NBA Community**: For inspiration and feedback

---

##  Contact

**Thinh Hoang** - DePauw University Computer Science

- GitHub: [@thinhhoang2907](https://github.com/thinhhoang2907)
- Email: thinhhoang_2026@depauw.edu
- Project Link: [https://github.com/thinhhoang2907/CourtVision](https://github.com/thinhhoang2907/CourtVision)

---


**Built by Thinh Hoang**

*Making NBA statistics accessible to fans everywhere*
