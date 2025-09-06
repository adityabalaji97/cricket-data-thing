#!/usr/bin/env python3
"""
Data Validator

Validates data completeness and generates quality reports for the cricket data pipeline.
This component serves as the final quality assurance step to ensure all data processing
phases completed successfully.

Part of the Unified Cricket Data Pipeline - Phase 1, Step 3
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from database import get_database_connection
from models import Player, Match, Delivery, BattingStats, BowlingStats

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Structured result for individual validation checks"""
    component: str
    status: str  # 'PASS', 'WARN', 'FAIL'
    message: str
    details: Optional[Dict] = None
    count_total: Optional[int] = None
    count_populated: Optional[int] = None
    percentage: Optional[float] = None

@dataclass
class ValidationReport:
    """Complete validation report for a category"""
    category: str
    overall_status: str
    results: List[ValidationResult] = field(default_factory=list)
    summary: Optional[str] = None

class DataValidator:
    """
    Validates data completeness and generates quality reports.
    
    This class performs comprehensive validation of:
    - Delivery enhancement columns
    - Player data completeness  
    - Statistics coverage
    - Data integrity checks
    """
    
    def __init__(self):
        """Initialize validator with database connection"""
        self.engine, SessionLocal = get_database_connection()
        self.session = SessionLocal()
        self.validation_threshold = 95.0  # Minimum acceptable completeness percentage
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    def validate_delivery_columns(self) -> ValidationReport:
        """
        Validate delivery enhancement columns completeness.
        
        Checks all enhancement columns added by the pipeline:
        - striker_batter_type, non_striker_batter_type
        - bowler_type, crease_combo
        - ball_direction and other derived columns
        
        Returns:
            ValidationReport with detailed results for each column
        """
        logger.info("Starting delivery columns validation...")
        
        results = []
        
        # Get total delivery count
        total_deliveries = self.session.query(func.count(Delivery.id)).scalar()
        
        # Define columns to validate
        columns_to_check = [
            'striker_batter_type',
            'non_striker_batter_type', 
            'bowler_type',
            'crease_combo',
            'ball_direction'
        ]
        
        for column in columns_to_check:
            result = self._validate_delivery_column(column, total_deliveries)
            results.append(result)
        
        # Determine overall status
        failed_checks = [r for r in results if r.status == 'FAIL']
        warning_checks = [r for r in results if r.status == 'WARN']
        
        if failed_checks:
            overall_status = 'FAIL'
            summary = f"{len(failed_checks)} columns failed validation"
        elif warning_checks:
            overall_status = 'WARN'
            summary = f"{len(warning_checks)} columns have warnings"
        else:
            overall_status = 'PASS'
            summary = "All delivery columns properly populated"
        
        return ValidationReport(
            category="Delivery Columns",
            overall_status=overall_status,
            results=results,
            summary=summary
        )
    
    def _validate_delivery_column(self, column_name: str, total_count: int) -> ValidationResult:
        """
        Validate a specific delivery column.
        
        Args:
            column_name: Name of the column to validate
            total_count: Total number of deliveries
            
        Returns:
            ValidationResult for this column
        """
        try:
            # Query for populated count (not null and not 'unknown')
            query = text(f"""
                SELECT 
                    COUNT(*) as populated,
                    COUNT(CASE WHEN {column_name} = 'unknown' THEN 1 END) as unknown_count
                FROM deliveries 
                WHERE {column_name} IS NOT NULL
            """)
            
            result = self.session.execute(query).fetchone()
            populated_count = result.populated
            unknown_count = result.unknown_count
            
            # Calculate percentage
            percentage = (populated_count / total_count * 100) if total_count > 0 else 0
            
            # Determine status
            if percentage >= self.validation_threshold:
                status = 'PASS'
                message = f"{column_name}: {percentage:.1f}% populated"
            elif percentage >= 80:
                status = 'WARN'
                message = f"{column_name}: {percentage:.1f}% populated (below threshold)"
            else:
                status = 'FAIL'
                message = f"{column_name}: {percentage:.1f}% populated (critically low)"
            
            return ValidationResult(
                component=column_name,
                status=status,
                message=message,
                count_total=total_count,
                count_populated=populated_count,
                percentage=percentage,
                details={
                    'unknown_count': unknown_count,
                    'null_count': total_count - populated_count,
                    'threshold': self.validation_threshold
                }
            )
            
        except Exception as e:
            logger.error(f"Error validating column {column_name}: {str(e)}")
            return ValidationResult(
                component=column_name,
                status='FAIL',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)}
            )
    
    def validate_player_completeness(self) -> ValidationReport:
        """
        Validate player data completeness.
        
        Checks:
        - All players referenced in deliveries exist in players table
        - Player nationality/team information completeness
        - Player type information (batter_type, bowler_type)
        
        Returns:
            ValidationReport with player completeness details
        """
        logger.info("Starting player completeness validation...")
        
        results = []
        
        # Check for missing players referenced in deliveries
        missing_players_result = self._check_missing_players()
        results.append(missing_players_result)
        
        # Check player information completeness
        nationality_result = self._check_player_nationality_completeness()
        results.append(nationality_result)
        
        # Check player type information
        player_types_result = self._check_player_types_completeness()
        results.append(player_types_result)
        
        # Determine overall status
        failed_checks = [r for r in results if r.status == 'FAIL']
        warning_checks = [r for r in results if r.status == 'WARN']
        
        if failed_checks:
            overall_status = 'FAIL'
            summary = f"Player data issues: {len(failed_checks)} critical problems"
        elif warning_checks:
            overall_status = 'WARN'
            summary = f"Player data warnings: {len(warning_checks)} areas need attention"
        else:
            overall_status = 'PASS'
            summary = "All player data complete and consistent"
        
        return ValidationReport(
            category="Player Completeness",
            overall_status=overall_status,
            results=results,
            summary=summary
        )
    
    def _check_missing_players(self) -> ValidationResult:
        """Check for players referenced in deliveries but missing from players table"""
        try:
            query = text("""
                SELECT COUNT(DISTINCT player_name) as missing_count
                FROM (
                    SELECT DISTINCT batter as player_name FROM deliveries
                    UNION
                    SELECT DISTINCT non_striker as player_name FROM deliveries  
                    UNION
                    SELECT DISTINCT bowler as player_name FROM deliveries
                ) all_players
                WHERE player_name NOT IN (SELECT name FROM players)
            """)
            
            result = self.session.execute(query).fetchone()
            missing_count = result.missing_count
            
            if missing_count == 0:
                return ValidationResult(
                    component="Missing Players",
                    status="PASS",
                    message="All referenced players exist in players table",
                    count_total=missing_count
                )
            else:
                return ValidationResult(
                    component="Missing Players",
                    status="FAIL",
                    message=f"{missing_count} players referenced in deliveries but missing from players table",
                    count_total=missing_count
                )
                
        except Exception as e:
            return ValidationResult(
                component="Missing Players",
                status="FAIL",
                message=f"Error checking missing players: {str(e)}",
                details={'error': str(e)}
            )
    
    def _check_player_nationality_completeness(self) -> ValidationResult:
        """Check player nationality information completeness"""
        try:
            query = text("""
                SELECT 
                    COUNT(*) as total_players,
                    COUNT(nationality) as with_nationality,
                    COUNT(CASE WHEN nationality = 'unknown' THEN 1 END) as unknown_nationality
                FROM players
            """)
            
            result = self.session.execute(query).fetchone()
            total = result.total_players
            with_nationality = result.with_nationality
            unknown = result.unknown_nationality
            
            percentage = (with_nationality / total * 100) if total > 0 else 0
            
            if percentage >= 90:
                status = "PASS"
                message = f"Player nationality: {percentage:.1f}% complete"
            elif percentage >= 70:
                status = "WARN"
                message = f"Player nationality: {percentage:.1f}% complete (needs improvement)"
            else:
                status = "FAIL"
                message = f"Player nationality: {percentage:.1f}% complete (critically low)"
            
            return ValidationResult(
                component="Player Nationality",
                status=status,
                message=message,
                count_total=total,
                count_populated=with_nationality,
                percentage=percentage,
                details={'unknown_count': unknown}
            )
            
        except Exception as e:
            return ValidationResult(
                component="Player Nationality",
                status="FAIL",
                message=f"Error checking nationality: {str(e)}",
                details={'error': str(e)}
            )
    
    def _check_player_types_completeness(self) -> ValidationResult:
        """Check player type information (batter_type, bowler_type) completeness"""
        try:
            query = text("""
                SELECT 
                    COUNT(*) as total_players,
                    COUNT(batter_type) as with_batter_type,
                    COUNT(bowler_type) as with_bowler_type,
                    COUNT(CASE WHEN batter_type = 'unknown' THEN 1 END) as unknown_batter,
                    COUNT(CASE WHEN bowler_type = 'unknown' THEN 1 END) as unknown_bowler
                FROM players
            """)
            
            result = self.session.execute(query).fetchone()
            total = result.total_players
            with_batter = result.with_batter_type
            with_bowler = result.with_bowler_type
            unknown_batter = result.unknown_batter
            unknown_bowler = result.unknown_bowler
            
            batter_percentage = (with_batter / total * 100) if total > 0 else 0
            bowler_percentage = (with_bowler / total * 100) if total > 0 else 0
            avg_percentage = (batter_percentage + bowler_percentage) / 2
            
            if avg_percentage >= 85:
                status = "PASS"
                message = f"Player types: {avg_percentage:.1f}% complete (B:{batter_percentage:.1f}%, Bow:{bowler_percentage:.1f}%)"
            elif avg_percentage >= 70:
                status = "WARN"
                message = f"Player types: {avg_percentage:.1f}% complete (needs improvement)"
            else:
                status = "FAIL"
                message = f"Player types: {avg_percentage:.1f}% complete (critically low)"
            
            return ValidationResult(
                component="Player Types",
                status=status,
                message=message,
                count_total=total,
                percentage=avg_percentage,
                details={
                    'batter_type_count': with_batter,
                    'bowler_type_count': with_bowler,
                    'unknown_batter': unknown_batter,
                    'unknown_bowler': unknown_bowler,
                    'batter_percentage': batter_percentage,
                    'bowler_percentage': bowler_percentage
                }
            )
            
        except Exception as e:
            return ValidationResult(
                component="Player Types",
                status="FAIL",
                message=f"Error checking player types: {str(e)}",
                details={'error': str(e)}
            )
    
    def validate_statistics_coverage(self) -> ValidationReport:
        """
        Validate statistics coverage.
        
        Checks:
        - Batting statistics exist for all relevant players
        - Bowling statistics exist for all relevant players
        - Statistics are up-to-date with delivery data
        
        Returns:
            ValidationReport with statistics coverage details
        """
        logger.info("Starting statistics coverage validation...")
        
        results = []
        
        # Check batting statistics coverage
        batting_stats_result = self._check_batting_statistics_coverage()
        results.append(batting_stats_result)
        
        # Check bowling statistics coverage
        bowling_stats_result = self._check_bowling_statistics_coverage()
        results.append(bowling_stats_result)
        
        # Determine overall status
        failed_checks = [r for r in results if r.status == 'FAIL']
        warning_checks = [r for r in results if r.status == 'WARN']
        
        if failed_checks:
            overall_status = 'FAIL'
            summary = f"Statistics issues: {len(failed_checks)} critical problems"
        elif warning_checks:
            overall_status = 'WARN'
            summary = f"Statistics warnings: {len(warning_checks)} areas need attention"
        else:
            overall_status = 'PASS'
            summary = "All statistics properly generated and up-to-date"
        
        return ValidationReport(
            category="Statistics Coverage",
            overall_status=overall_status,
            results=results,
            summary=summary
        )
    
    def _check_batting_statistics_coverage(self) -> ValidationResult:
        """Check batting statistics coverage"""
        try:
            query = text("""
                SELECT 
                    COUNT(DISTINCT batter) as total_batters_in_deliveries,
                    COUNT(DISTINCT bs.player_name) as batters_with_stats
                FROM deliveries d
                LEFT JOIN batting_stats bs ON d.batter = bs.player_name
            """)
            
            result = self.session.execute(query).fetchone()
            total_batters = result.total_batters_in_deliveries
            with_stats = result.batters_with_stats
            
            percentage = (with_stats / total_batters * 100) if total_batters > 0 else 0
            
            if percentage >= 95:
                status = "PASS"
                message = f"Batting statistics: {percentage:.1f}% coverage"
            elif percentage >= 85:
                status = "WARN"
                message = f"Batting statistics: {percentage:.1f}% coverage (some missing)"
            else:
                status = "FAIL"
                message = f"Batting statistics: {percentage:.1f}% coverage (many missing)"
            
            return ValidationResult(
                component="Batting Statistics",
                status=status,
                message=message,
                count_total=total_batters,
                count_populated=with_stats,
                percentage=percentage
            )
            
        except Exception as e:
            return ValidationResult(
                component="Batting Statistics",
                status="FAIL",
                message=f"Error checking batting statistics: {str(e)}",
                details={'error': str(e)}
            )
    
    def _check_bowling_statistics_coverage(self) -> ValidationResult:
        """Check bowling statistics coverage"""
        try:
            query = text("""
                SELECT 
                    COUNT(DISTINCT bowler) as total_bowlers_in_deliveries,
                    COUNT(DISTINCT bs.player_name) as bowlers_with_stats
                FROM deliveries d
                LEFT JOIN bowling_stats bs ON d.bowler = bs.player_name
            """)
            
            result = self.session.execute(query).fetchone()
            total_bowlers = result.total_bowlers_in_deliveries
            with_stats = result.bowlers_with_stats
            
            percentage = (with_stats / total_bowlers * 100) if total_bowlers > 0 else 0
            
            if percentage >= 95:
                status = "PASS"
                message = f"Bowling statistics: {percentage:.1f}% coverage"
            elif percentage >= 85:
                status = "WARN"
                message = f"Bowling statistics: {percentage:.1f}% coverage (some missing)"
            else:
                status = "FAIL"
                message = f"Bowling statistics: {percentage:.1f}% coverage (many missing)"
            
            return ValidationResult(
                component="Bowling Statistics",
                status=status,
                message=message,
                count_total=total_bowlers,
                count_populated=with_stats,
                percentage=percentage
            )
            
        except Exception as e:
            return ValidationResult(
                component="Bowling Statistics",
                status="FAIL",
                message=f"Error checking bowling statistics: {str(e)}",
                details={'error': str(e)}
            )
    
    def generate_data_quality_report(self) -> str:
        """
        Generate comprehensive data quality report.
        
        Runs all validation checks and creates a formatted report
        suitable for logging, email, or display.
        
        Returns:
            Formatted string report with all validation results
        """
        logger.info("Generating comprehensive data quality report...")
        
        # Run all validations
        delivery_report = self.validate_delivery_columns()
        player_report = self.validate_player_completeness()
        stats_report = self.validate_statistics_coverage()
        
        # Generate report
        report_lines = []
        report_lines.append("" + "=" * 60)
        report_lines.append("       CRICKET DATA QUALITY VALIDATION REPORT")
        report_lines.append(f"       Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("" + "=" * 60)
        
        # Overall status
        all_reports = [delivery_report, player_report, stats_report]
        failed_reports = [r for r in all_reports if r.overall_status == 'FAIL']
        warning_reports = [r for r in all_reports if r.overall_status == 'WARN']
        
        if failed_reports:
            overall_status = "❌ CRITICAL ISSUES FOUND"
        elif warning_reports:
            overall_status = "⚠️  WARNINGS PRESENT"
        else:
            overall_status = "✅ ALL CHECKS PASSED"
        
        report_lines.append(f"\n📊 OVERALL STATUS: {overall_status}")
        report_lines.append("")
        
        # Add each category
        for report in all_reports:
            report_lines.extend(self._format_validation_report(report))
            report_lines.append("")
        
        # Summary
        report_lines.append("" + "-" * 60)
        report_lines.append("📋 SUMMARY:")
        for report in all_reports:
            status_icon = self._get_status_icon(report.overall_status)
            report_lines.append(f"  {status_icon} {report.category}: {report.summary}")
        
        report_lines.append("" + "=" * 60)
        
        return "\n".join(report_lines)
    
    def _format_validation_report(self, report: ValidationReport) -> List[str]:
        """Format a validation report for display"""
        lines = []
        status_icon = self._get_status_icon(report.overall_status)
        
        lines.append(f"📂 {report.category.upper()} {status_icon}")
        lines.append(f"   {report.summary}")
        lines.append("")
        
        for result in report.results:
            result_icon = self._get_status_icon(result.status)
            lines.append(f"   {result_icon} {result.message}")
            
            # Add details if available
            if result.details and result.status != 'PASS':
                for key, value in result.details.items():
                    if key != 'error':
                        lines.append(f"      • {key}: {value}")
        
        return lines
    
    def _get_status_icon(self, status: str) -> str:
        """Get emoji icon for status"""
        icons = {
            'PASS': '✅',
            'WARN': '⚠️',
            'FAIL': '❌'
        }
        return icons.get(status, '❓')
    
    def run_full_validation(self) -> Dict[str, ValidationReport]:
        """
        Run all validation checks and return structured results.
        
        Returns:
            Dictionary with validation reports for each category
        """
        logger.info("Running full validation suite...")
        
        results = {
            'delivery_columns': self.validate_delivery_columns(),
            'player_completeness': self.validate_player_completeness(),
            'statistics_coverage': self.validate_statistics_coverage()
        }
        
        return results


def main():
    """
    Command-line interface for data validation.
    
    Usage:
        python data_validator.py [--report-file output.txt] [--verbose]
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate cricket data quality')
    parser.add_argument('--report-file', '-f', help='Save report to file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        with DataValidator() as validator:
            if args.json:
                # JSON output for programmatic use
                import json
                results = validator.run_full_validation()
                output = {}
                for category, report in results.items():
                    output[category] = {
                        'status': report.overall_status,
                        'summary': report.summary,
                        'results': [
                            {
                                'component': r.component,
                                'status': r.status,
                                'message': r.message,
                                'percentage': r.percentage
                            } for r in report.results
                        ]
                    }
                
                json_output = json.dumps(output, indent=2)
                print(json_output)
                
                if args.report_file:
                    with open(args.report_file, 'w') as f:
                        f.write(json_output)
            else:
                # Human-readable report
                report = validator.generate_data_quality_report()
                print(report)
                
                if args.report_file:
                    with open(args.report_file, 'w') as f:
                        f.write(report)
    
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
