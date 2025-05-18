# Cricket Data Thing 🏏

A comprehensive cricket analytics platform for visualizing and analyzing T20 cricket data, with a focus on venue analysis, player performance metrics, and team matchups.

<img width="1680" alt="Dashboard" src="https://github.com/user-attachments/assets/c91c40d6-9095-428b-9059-a993f31c640c" />

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Technical Architecture](#technical-architecture)
- [Data Processing Pipeline](#data-processing-pipeline)
- [Key Visualizations](#key-visualizations)
- [Installation and Setup](#installation-and-setup)
- [Development Process](#development-process)
- [Technical Challenges and Solutions](#technical-challenges-and-solutions)
- [Performance Optimizations](#performance-optimizations)
- [Future Enhancements](#future-enhancements)
- [Acknowledgements](#acknowledgements)

## Overview

Cricket Data Thing is a full-stack web application for analyzing T20 cricket data across various competitions including international matches and major T20 leagues (IPL, BBL, PSL, CPL, etc.). The application provides comprehensive statistical analysis including venue statistics, batting and bowling performance metrics, phase-wise analysis, fantasy points projections, and head-to-head matchups between teams and players.

### Problem Solved

- Professional cricket teams and fantasy cricket enthusiasts need data-driven insights to make strategic decisions
- Traditional cricket statistics don't offer detailed phase-wise (powerplay, middle overs, death overs) analysis
- Limited tools exist for analyzing venue-specific performance patterns
- Fantasy cricket players need specialized metrics for player selection

Cricket Data Thing addresses these needs by providing an intuitive interface with advanced visualizations and metrics that enable deep cricket analysis for strategic decision-making.

## Features

### Venue Analysis
- Detailed venue statistics with win percentages (batting first vs. chasing)
- Phase-wise scoring patterns across different venues
- Average scoring metrics (first innings, second innings, winning scores)
- Highest/lowest totals and successful chases
- Batting and bowling leaderboards specific to each venue

### Player Profiling
- Comprehensive batting statistics with phase breakdown
- Performance against different bowling types (pace vs. spin)
- Career progression analysis
- Comparison with average player performance
- Fantasy points calculation and projection

### Team Matchups
- Head-to-head team statistics
- Recent form analysis
- Player-vs-player matchup matrices
- Bowler type analysis (effectiveness of different bowling styles)
- Batting/bowling strengths and weaknesses

### Fantasy Cricket Support
- Fantasy points leaderboards
- Points breakdown by batting, bowling, and fielding
- Historical fantasy performance at specific venues
- Player-vs-opponent fantasy scoring patterns

### Advanced Filtering Options
- Date range selection
- Competition filtering (leagues, international matches)
- Team selection for customized analysis
- Minimum innings/matches thresholds

## Technical Architecture

Cricket Data Thing follows a modern web application architecture with clear separation of concerns:

<img width="1178" alt="Screenshot 2025-05-18 at 18 19 22" src="https://github.com/user-attachments/assets/b98fca61-bf6f-4b35-beb3-55005f548569" />
<img width="1178" alt="Screenshot 2025-05-18 at 18 19 33" src="https://github.com/user-attachments/assets/3b73fa7e-b38e-49f2-b771-ccd4bc8a8995" />


### Frontend (React.js)
- **Framework**: React.js with React Router for navigation
- **UI Components**: Material-UI for responsive design (as seen in the package.json with @mui dependencies)
- **Data Visualization**: Recharts for charts and data visualization
- **HTTP Client**: Axios for API requests
- **Responsive Design**: Mobile-first approach with adaptive layouts using Material UI's responsive components

### Backend (FastAPI)
- **Framework**: FastAPI for high-performance API endpoints
- **Database Access**: SQLAlchemy ORM for database operations
- **Data Processing**: Direct SQL queries with SQLAlchemy for data manipulation and aggregation
- **Error Handling**: Middleware for database connection error handling
- **CORS Support**: Built-in CORS middleware configured for secure cross-origin requests

### Database (PostgreSQL)
- **Primary Data Store**: PostgreSQL for relational data (as seen in database.py connection strings)
- **Schema Design**: Optimized for cricket analytics queries
- **Main Tables**:
  - `matches` - Match details and results
  - `deliveries` - Ball-by-ball data for each match
  - `players` - Player information and attributes
  - `batting_stats` - Aggregated batting statistics
  - `bowling_stats` - Aggregated bowling statistics

### Deployment
- **Frontend Hosting**: Vercel (as indicated by vercel.json and VERCEL-related files)
- **Backend Hosting**: Heroku (indicated by Procfile in the api directory)
- **Environment Management**: Environment variables via .env files
- **Database**: PostgreSQL database (referenced in database.py)

## Data Processing Pipeline

The application's data pipeline transforms raw cricket data into actionable insights:

1. **Data Collection**:
   - Ball-by-ball data from Cricsheet.org in JSON format (as indicated by json directories in project structure)
   - Player information from various sources (compiled in player database tables)

2. **Data Transformation**:
   - Standardization of team and player names (using mappings in models.py)
   - Calculation of derived statistics (strike rates, economy rates, etc.)
   - Phase-wise aggregation (powerplay, middle overs, death overs)
   - Fantasy points calculation based on performance metrics (as seen in fantasy_points.py)

3. **Data Loading**:
   - Population of the PostgreSQL database with processed data (via scripts like load_all_matches.py)
   - Creation of aggregated statistics tables for performance (batting_stats and bowling_stats)
   - Data cleaning and standardization processes (standardize_teams.py)

4. **Data Serving**:
   - API endpoints for various analytical views (main.py)
   - Query optimization with SQL query templates and parameters
   - Handling of complex filtering requirements (leagues, dates, teams)

## Key Visualizations

### Venue Analysis Dashboard
The venue analysis dashboard provides comprehensive statistics for each cricket venue, including win percentages, scoring patterns, and phase-wise strategies.

<img width="1680" alt="Venue Analysis" src="https://github.com/user-attachments/assets/2c54ce1f-05f7-4913-b91c-ac04516b3601" />

### Batting Performance Scatter Plot
The batting scatter plot visualizes player performance based on average and strike rate, helping identify player roles (anchors, finishers, etc.).

<img width="1504" alt="Batter Scatter" src="https://github.com/user-attachments/assets/aee00bf1-7be1-45cc-86e4-4e02e6e2b572" />

### Matchup Matrix
The matchup matrix displays head-to-head statistics between batters and bowlers, highlighting strengths and weaknesses.

<img width="1680" alt="Matchup Matrix" src="https://github.com/user-attachments/assets/1555080c-6679-4099-adc8-1af34ca77c57" />

### Fantasy Points Analysis
The fantasy points visualization breaks down fantasy performance by batting, bowling, and fielding contributions.

<img width="1680" alt="Fantasy Points Analysis" src="https://github.com/user-attachments/assets/0716006f-f2b9-4cd8-83dc-80e19c679b6c" />

### Phase-wise Performance Analysis
The phase analysis charts show how teams and players perform during different phases of a T20 innings.

<img width="1497" alt="Phase-wise Strategy" src="https://github.com/user-attachments/assets/1841130b-9a4f-4505-a28b-0f17b3254680" />

## Installation and Setup

### Prerequisites
- Node.js (v14+)
- Python (v3.8+)
- PostgreSQL (v12+)

### Frontend Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/cricket-data-thing.git
cd cricket-data-thing/cricket-viz

# Install dependencies
npm install

# Start development server
npm start
```

### Backend Setup
```bash
# Navigate to API directory
cd api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials

# Start the API server
uvicorn main:app --reload
```

### Database Setup
```bash
# Create PostgreSQL database
createdb cricket_db

# Run database migration
python reset_db.py

# Load sample data
python load_all_matches.py
```

## Development Process

The Cricket Data Thing project was developed using an iterative approach, focusing on delivering value incrementally:

1. **Initial Planning and Research**
   - Research on available cricket data sources
   - Definition of key metrics and visualizations
   - Architecture design and technology selection

2. **Backend Development**
   - Database schema design
   - Data ingestion and processing pipeline
   - API endpoints development
   - Query optimization

3. **Frontend Development**
   - UI component design
   - Chart and visualization implementation
   - Filter and search functionality
   - Mobile responsiveness

4. **Integration and Testing**
   - API integration with frontend
   - End-to-end testing
   - Performance optimization
   - Bug fixing

5. **Deployment and Monitoring**
   - Production deployment
   - Monitoring and logging setup
   - Documentation

6. **Continuous Improvement**
   - User feedback collection
   - New feature development
   - Data quality improvement
   - Performance optimization

## Technical Challenges and Solutions

### Challenge 1: Handling Large Datasets
**Problem**: Processing ball-by-ball data for thousands of matches was computationally intensive and slow.

**Solution**: Implemented a pre-aggregation strategy where derived statistics are calculated and stored during data ingestion, reducing query complexity at runtime. Created dedicated batting_stats and bowling_stats tables for quick access to aggregated metrics.

### Challenge 2: Complex Statistical Calculations
**Problem**: Cricket statistics often require complex calculations (e.g., phase-wise strike rates, fantasy points) that were difficult to express in SQL queries.

**Solution**: Developed specialized SQL queries with calculated fields and window functions. Used parameterized queries to handle complex filtering scenarios. Implemented dedicated statistical functions like get_phase_stats for standardized calculation of metrics.

### Challenge 3: Real-time Filtering Performance
**Problem**: Applying multiple filters (date ranges, competitions, teams) to large datasets resulted in slow query performance.

**Solution**: Implemented strategic database indexing on frequently filtered columns. Added query parameterization using SQLAlchemy's query building capabilities. Optimized complex queries by breaking them into smaller, more manageable CTEs (Common Table Expressions).

### Challenge 4: Responsive Visualization Design
**Problem**: Cricket visualizations needed to be informative on both desktop and mobile devices, with varying screen sizes.

**Solution**: Developed responsive components with conditional rendering based on device size (using Material-UI's useMediaQuery hook). Implemented simplified visualization variants for mobile devices. Used flex layouts and grid systems to adapt to different screen sizes.

## Performance Optimizations

The application incorporates several performance optimizations:

1. **Database Query Optimization**
   - Use of Common Table Expressions (CTEs) for complex queries
   - Parameterized queries to avoid SQL injection and improve caching
   - Strategic use of SQL window functions for efficient aggregations

2. **Backend Performance**
   - Connection pooling for database access
   - Error handling middleware to gracefully manage database connection issues
   - Query result caching for repetitive requests

3. **Frontend Performance**
   - Conditional rendering based on data availability
   - Responsive design with simplified views for mobile
   - Loading states and error handling for API requests

4. **Network Optimization**
   - Efficient API response structure
   - Error handling with appropriate HTTP status codes
   - CORS configuration for secure cross-origin requests

## Future Enhancements

The Cricket Data Thing platform has several planned enhancements:

1. **Predictive Analytics**
   - Machine learning models for match outcome prediction
   - Player performance forecasting
   - Fantasy points projection

2. **Advanced Visualization**
   - Interactive wagon wheel (batting shot distribution)
   - Bowling heatmaps showing pitch maps
   - Player tracking visualization

3. **Personalization**
   - User accounts for saving favorite players and teams
   - Customizable dashboards
   - Alerts for significant statistical milestones

4. **Data Expansion**
   - Integration with live match data
   - Historical ODI and Test match data
   - Player social media sentiment analysis

5. **API Platform**
   - Public API for developers
   - Embeddable widgets for cricket blogs and websites
   - Subscription-based premium features

## Acknowledgements

Cricket Data Thing would not have been possible without the contributions and inspirations from the cricket analytics community:

- [Cricsheet.org](https://cricsheet.org/) for the comprehensive ball-by-ball dataset
- Cricket statisticians and analysts whose work inspired many of the metrics and visualizations
- The open-source community for the tools and libraries that power the application

### Data Credits
- Ball-by-ball data from [Cricsheet.org](https://cricsheet.org/)
- Player information from various public cricket APIs
- Team and competition metadata from public sources

### Technology Stack Credits
- React.js and Material-UI for the frontend interface
- FastAPI and SQLAlchemy for the backend API
- Recharts for data visualization
- PostgreSQL for data storage
- Vercel and Heroku for hosting

### Inspiration from Cricket Analysts
- @prasannalara, @cricketingview, @randomcricstat, @cricviz and other cricket analysis Twitter accounts
- ESPNCricinfo and Cricbuzz for statistical reference
- Cricket analytics blogs and publications

---

Developed with ❤️ for cricket and data
