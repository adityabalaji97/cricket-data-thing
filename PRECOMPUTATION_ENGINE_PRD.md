# Product Requirements Document (PRD): Pre-computation Engine for Cricket Analytics Platform

---

## Overview

This PRD outlines the architecture and functionality of a Pre-computation Engine designed to optimize performance for cricket analytics APIs by pre-calculating expensive aggregations and storing them in indexed database tables. The system is designed for LLM-assisted development and future extensibility.

The system must:

* Transform real-time calculations into fast database lookups
* Support weekly batch processing for data freshness
* Maintain chronological data integrity across all computations
* Enable sub-second API responses for analytics endpoints
* Be modular, extensible, and LLM-readable

---

## System Context & Performance Requirements

### Current Performance Issues
- WPA calculations: 30+ seconds per venue
- Venue analysis: 5-10 seconds per request
- Player impact aggregations: 2-5 seconds per player
- **Target**: <500ms per API request

### Usage Patterns
- **API Load**: ~10 requests per day
- **Query Patterns**: Pre-match analysis, no real-time requirements
- **Data Updates**: Weekly at best (new matches added)
- **User Behavior**: Minimal repeated queries

### Future-Proofing Requirements
- Support for increased API load (10 → 1000+ requests/day)
- Extensible to new cricket formats (Test, ODI)
- Scalable to additional leagues and competitions
- Ready for real-time analysis if requirements change

---

## Core Modules & Pre-computation Tables

### 1. WPA Outcomes Table

**Purpose:** Pre-compute expensive chase outcome aggregations for instant WPA calculations.

**Schema:**
```sql
CREATE TABLE wpa_outcomes (
    id SERIAL PRIMARY KEY,
    venue VARCHAR(255) NOT NULL,
    league VARCHAR(100),
    target_bucket INTEGER NOT NULL,  -- Grouped in 10-run buckets
    over_bucket INTEGER NOT NULL,    -- 0, 5, 10, 15, 19
    wickets_lost INTEGER NOT NULL,
    runs_range_min INTEGER NOT NULL, -- Score bucket start
    runs_range_max INTEGER NOT NULL, -- Score bucket end
    total_outcomes INTEGER NOT NULL,
    successful_chases INTEGER NOT NULL,
    win_probability DECIMAL(5,3) NOT NULL,
    sample_size INTEGER NOT NULL,
    computed_date TIMESTAMP NOT NULL,
    data_through_date DATE NOT NULL  -- Latest match included
);

-- Critical indexes
CREATE INDEX idx_wpa_lookup ON wpa_outcomes(venue, target_bucket, over_bucket, wickets_lost);
CREATE INDEX idx_wpa_league ON wpa_outcomes(league, target_bucket, over_bucket, wickets_lost);
```

**Data Source:** Second innings chase data from deliveries + matches tables
**Update Frequency:** Weekly
**Fallback Hierarchy:** venue → cluster → league → global

### 2. Venue Resource Tables

**Purpose:** Pre-compute DLS-style resource percentages for venue context analysis.

**Schema:**
```sql
CREATE TABLE venue_resources (
    id SERIAL PRIMARY KEY,
    venue VARCHAR(255) NOT NULL,
    league VARCHAR(100),
    innings INTEGER NOT NULL,
    over_num INTEGER NOT NULL,
    wickets_lost INTEGER NOT NULL,
    resource_percentage DECIMAL(5,2) NOT NULL,
    avg_runs_at_state DECIMAL(6,2),
    avg_final_score DECIMAL(6,2),
    sample_size INTEGER NOT NULL,
    computed_date TIMESTAMP NOT NULL,
    data_through_date DATE NOT NULL
);

CREATE INDEX idx_venue_resources ON venue_resources(venue, innings, over_num, wickets_lost);
```

**Data Source:** Historical ball-by-ball match states
**Update Frequency:** Weekly
**Fallback Hierarchy:** venue → cluster → league → global

### 3. Player Performance Baselines

**Purpose:** Pre-compute player performance metrics for RAR and impact calculations.

**Schema:**
```sql
CREATE TABLE player_baselines (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    venue_type VARCHAR(50) NOT NULL,  -- 'venue_specific', 'cluster', 'league', 'global'
    venue_identifier VARCHAR(255),    -- Venue name or cluster name
    league VARCHAR(100),
    phase VARCHAR(20) NOT NULL,       -- 'powerplay', 'middle', 'death', 'overall'
    role VARCHAR(20) NOT NULL,        -- 'batting', 'bowling'
    
    -- Batting metrics
    avg_runs DECIMAL(5,2),
    avg_strike_rate DECIMAL(5,2),
    avg_balls_faced DECIMAL(5,2),
    boundary_percentage DECIMAL(4,2),
    
    -- Bowling metrics  
    avg_economy DECIMAL(4,2),
    avg_wickets DECIMAL(4,2),
    dot_ball_percentage DECIMAL(4,2),
    avg_overs DECIMAL(3,1),
    
    matches_played INTEGER NOT NULL,
    computed_date TIMESTAMP NOT NULL,
    data_through_date DATE NOT NULL
);

CREATE INDEX idx_player_baselines ON player_baselines(player_name, venue_type, phase, role);
```

**Data Source:** BattingStats and BowlingStats tables
**Update Frequency:** Weekly
**Scope:** Individual players across different venue types and phases

### 4. Team Phase Statistics

**Purpose:** Pre-compute team-level performance for contextual comparisons.

**Schema:**
```sql
CREATE TABLE team_phase_stats (
    id SERIAL PRIMARY KEY,
    team VARCHAR(255) NOT NULL,
    venue_type VARCHAR(50) NOT NULL,
    venue_identifier VARCHAR(255),
    league VARCHAR(100),
    phase VARCHAR(20) NOT NULL,
    innings INTEGER NOT NULL,
    
    avg_runs DECIMAL(6,2) NOT NULL,
    avg_wickets DECIMAL(4,2) NOT NULL,
    avg_run_rate DECIMAL(4,2) NOT NULL,
    avg_balls_faced INTEGER,
    boundary_rate DECIMAL(4,2),
    
    matches_played INTEGER NOT NULL,
    computed_date TIMESTAMP NOT NULL,
    data_through_date DATE NOT NULL
);

CREATE INDEX idx_team_stats ON team_phase_stats(team, venue_type, phase, innings);
```

**Data Source:** Aggregated match and delivery data
**Update Frequency:** Weekly
**Scope:** Team performance across venues, phases, and innings

### 5. Computation Metadata

**Purpose:** Track computation status, dependencies, and data lineage.

**Schema:**
```sql
CREATE TABLE computation_runs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    computation_type VARCHAR(50) NOT NULL, -- 'full_rebuild', 'incremental', 'backfill'
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL,           -- 'running', 'completed', 'failed'
    records_processed INTEGER,
    data_through_date DATE NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_computation_status ON computation_runs(table_name, status, start_time);
```

---

## Batch Processing Architecture

### 1. Core Processing Pipeline

**Execution Order:** (Dependencies must be respected)
```python
class PrecomputationPipeline:
    """
    Weekly batch processing pipeline for pre-computing analytics tables.
    
    Executes in dependency order to ensure data consistency.
    """
    
    def execute_weekly_rebuild(self, through_date: date):
        """
        Full weekly rebuild of all pre-computed tables.
        
        Args:
            through_date: Process all matches up to this date
        """
        pipeline_steps = [
            ("team_phase_stats", self.rebuild_team_stats),
            ("player_baselines", self.rebuild_player_baselines), 
            ("venue_resources", self.rebuild_venue_resources),
            ("wpa_outcomes", self.rebuild_wpa_outcomes)
        ]
        
        for table_name, rebuild_func in pipeline_steps:
            self.execute_with_monitoring(table_name, rebuild_func, through_date)
```

### 2. Incremental Processing Support

**Future Enhancement for Higher Volume:**
```python
class IncrementalProcessor:
    """
    Incremental processing for when data updates become more frequent.
    
    Currently not needed (weekly updates) but designed for future scaling.
    """
    
    def process_new_matches(self, new_match_ids: List[str]):
        """
        Process only newly added matches and update affected pre-computed data.
        
        Args:
            new_match_ids: List of match IDs added since last computation
        """
        affected_venues = self.get_affected_venues(new_match_ids)
        affected_players = self.get_affected_players(new_match_ids)
        
        # Update only affected rows instead of full rebuild
        self.update_venue_data(affected_venues)
        self.update_player_data(affected_players)
```

### 3. Data Quality Validation

**Automated Quality Checks:**
```python
class DataQualityValidator:
    """
    Validates pre-computed data for statistical and logical consistency.
    """
    
    def validate_wpa_outcomes(self) -> ValidationResult:
        """
        Validate WPA outcome data for logical consistency.
        
        Returns:
            ValidationResult with pass/fail status and detailed findings
        """
        checks = [
            self.check_probability_bounds(),    # Win probabilities in [0,1]
            self.check_sample_size_thresholds(), # Minimum sample sizes met
            self.check_logical_consistency(),   # Higher scores = higher win prob
            self.check_completeness()          # No missing critical combinations
        ]
        
    def validate_venue_resources(self) -> ValidationResult:
        """
        Validate venue resource tables against DLS principles.
        """
        checks = [
            self.check_resource_monotonicity(), # Resources decrease with overs/wickets
            self.check_resource_bounds(),       # Resource % in reasonable range
            self.check_venue_coverage()        # All major venues covered
        ]
```

---

## API Integration Layer

### 1. Fast Lookup Interface

**Optimized for LLM Development:**
```python
class PrecomputedDataService:
    """
    Service layer for accessing pre-computed analytics data.
    
    Provides simple, fast methods for retrieving pre-calculated values
    with automatic fallback hierarchy.
    """
    
    def get_win_probability(self, venue: str, target: int, over: int, 
                          wickets: int, runs: int, league: str = None) -> float:
        """
        Get win probability from pre-computed data with fallback.
        
        Args:
            venue: Venue name (exact match from database)
            target: Target score to chase
            over: Current over (0-19)
            wickets: Wickets lost (0-9)
            runs: Current runs scored
            league: League for filtering (optional)
            
        Returns:
            Win probability between 0.0 and 1.0
            
        Fallback Order:
            1. Venue-specific data
            2. Venue cluster data  
            3. League-wide data
            4. Global data
            5. Heuristic calculation (last resort)
        """
        
    def get_venue_resource_percentage(self, venue: str, innings: int, 
                                    over: int, wickets: int, 
                                    league: str = None) -> float:
        """
        Get resource percentage remaining from pre-computed venue data.
        """
        
    def get_player_baseline_stats(self, player: str, venue_type: str, 
                                phase: str, role: str) -> Dict[str, float]:
        """
        Get player baseline performance metrics for RAR calculations.
        """
```

### 2. Fallback Strategy Implementation

**Hierarchical Data Access:**
```python
class FallbackDataManager:
    """
    Manages fallback hierarchy for pre-computed data access.
    
    Ensures consistent fallback behavior across all analytics components.
    """
    
    def get_with_fallback(self, query_params: Dict, table_name: str) -> Optional[Dict]:
        """
        Execute query with automatic fallback through hierarchy.
        
        Args:
            query_params: Parameters for data lookup
            table_name: Target pre-computed table
            
        Returns:
            Data dictionary or None if no fallback available
            
        Fallback Hierarchy:
            1. Exact venue match
            2. Venue cluster match  
            3. League-wide match
            4. Global match
        """
        
        fallback_strategies = [
            ("venue_specific", self.query_venue_specific),
            ("cluster", self.query_cluster_level),
            ("league", self.query_league_level), 
            ("global", self.query_global_level)
        ]
        
        for strategy_name, query_func in fallback_strategies:
            result = query_func(query_params, table_name)
            if result and self.meets_quality_threshold(result):
                return self.add_metadata(result, strategy_name)
                
        return None
```

---

## System Constraints & Design Principles

### 1. Chronological Data Integrity

**Strict Temporal Constraints:**
- All pre-computed tables include `data_through_date` column
- API calls specify `before_date` parameter for historical analysis
- No future data contamination in any calculation
- Batch processing respects chronological boundaries

### 2. Modular Architecture

**Component Isolation:**
- Each pre-computed table has independent rebuild logic
- Clear interfaces between computation modules
- Dependency injection for testing and extensibility
- Consistent error handling and logging

### 3. LLM-Friendly Design

**Development Optimization:**
- Clear, descriptive function and variable names
- Comprehensive docstrings with type hints
- JSON-serializable data structures
- Consistent patterns across modules
- Example usage in every major function

### 4. Future Extensibility

**Designed for Growth:**
- Table schemas support additional columns without migration pain
- Venue clustering system is configuration-driven
- New leagues/competitions require minimal code changes
- Real-time processing hooks pre-built but unused
- Caching layer interfaces defined but not implemented

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Core Infrastructure**
- Database schema creation with indexes
- Base batch processing framework
- Data quality validation framework
- Basic API integration layer

**Deliverables:**
- `precomputed_tables.sql` - Schema definitions
- `batch_processor.py` - Core processing engine
- `data_validator.py` - Quality checking framework
- `precomputed_service.py` - API integration layer

### Phase 2: WPA Implementation (Week 2)
**WPA-Specific Components**
- WPA outcomes table computation logic
- Integration with existing WPA curve trainer
- Performance testing and optimization
- API endpoint updates

**Deliverables:**
- `wpa_precomputer.py` - WPA outcomes computation
- `test_wpa_precomputation.py` - Comprehensive testing
- Updated WPA engine to use pre-computed data

### Phase 3: Venue & Player Analytics (Week 3)
**Complete Analytics Suite**
- Venue resource table computation
- Player baseline statistics computation
- Team phase statistics computation
- Full API integration

**Deliverables:**
- `venue_precomputer.py` - Venue analytics computation
- `player_precomputer.py` - Player baseline computation
- `team_precomputer.py` - Team statistics computation
- Updated analytics endpoints

### Phase 4: Production & Monitoring (Week 4)
**Production Readiness**
- Automated weekly batch processing
- Monitoring and alerting
- Performance optimization
- Documentation and deployment

**Deliverables:**
- `weekly_batch_job.py` - Production batch processing
- `monitoring_dashboard.py` - System health monitoring
- Production deployment configuration
- Complete system documentation

---

## Success Metrics

### Performance Improvements
- **API Response Time**: Current 30+ seconds → Target <500ms
- **Database Load**: 90%+ reduction in complex aggregation queries
- **Batch Processing Time**: <4 hours for full weekly rebuild
- **Data Freshness**: <7 days lag from match to analytics availability

### Quality Metrics
- **Data Coverage**: >95% of venue/league combinations covered
- **Accuracy**: Pre-computed values match real-time calculations
- **Reliability**: <1% failed batch processing runs
- **Consistency**: Identical results for identical inputs

### Future-Proofing Metrics
- **Scalability**: Support 100x current API load without architecture changes
- **Extensibility**: Add new league/format in <1 day development time
- **Maintainability**: New developers productive in <2 days

---

## Risk Mitigation

### Data Consistency Risks
- **Mitigation**: Comprehensive validation suite with automated alerts
- **Rollback**: Keep previous week's data for instant fallback
- **Monitoring**: Real-time data quality dashboards

### Performance Risks  
- **Mitigation**: Incremental processing capability (future-ready)
- **Scaling**: Database partitioning by league/season
- **Caching**: Redis integration hooks (implemented but unused)

### Development Risks
- **Mitigation**: LLM-optimized code patterns and documentation
- **Testing**: Comprehensive test suites with real data validation
- **Deployment**: Blue-green deployment capability for zero-downtime updates

---

**End of PRD**