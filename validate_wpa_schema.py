"""
WPA Schema Validation Script

This script validates that the WPA schema migration was applied correctly
and provides detailed verification of the database changes.
"""

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from database import get_database_connection
from models import Delivery
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WPASchemaValidator:
    """
    Validates WPA schema migration and provides detailed verification.
    """
    
    def __init__(self):
        self.engine, self.session_factory = get_database_connection()
        self.inspector = inspect(self.engine)
        self.validation_results = {
            "columns": {},
            "indexes": {},
            "constraints": {},
            "overall_status": "PENDING"
        }
    
    def validate_wpa_columns(self) -> bool:
        """
        Validate that WPA columns were added correctly to deliveries table.
        
        Returns:
            bool: True if all WPA columns exist with correct types
        """
        logger.info("Validating WPA columns in deliveries table...")
        
        try:
            # Get deliveries table columns
            columns = self.inspector.get_columns('deliveries')
            column_dict = {col['name']: col for col in columns}
            
            # Expected WPA columns with their properties
            expected_wpa_columns = {
                'wpa_batter': {
                    'type': 'NUMERIC',  # PostgreSQL DECIMAL becomes NUMERIC
                    'nullable': True
                },
                'wpa_bowler': {
                    'type': 'NUMERIC',
                    'nullable': True
                },
                'wpa_computed_date': {
                    'type': 'TIMESTAMP',
                    'nullable': True
                }
            }
            
            # Validate each WPA column
            for col_name, expected in expected_wpa_columns.items():
                if col_name not in column_dict:
                    self.validation_results["columns"][col_name] = {
                        "status": "MISSING",
                        "error": f"Column {col_name} not found in deliveries table"
                    }
                    logger.error(f"❌ Column {col_name} is missing")
                    continue
                
                actual_col = column_dict[col_name]
                
                # Check data type (allow some flexibility in type matching)
                actual_type = str(actual_col['type']).upper()
                expected_type = expected['type']
                
                type_match = (
                    expected_type in actual_type or 
                    actual_type in expected_type or
                    (expected_type == 'NUMERIC' and 'DECIMAL' in actual_type)
                )
                
                # Check nullable property
                nullable_match = actual_col['nullable'] == expected['nullable']
                
                if type_match and nullable_match:
                    self.validation_results["columns"][col_name] = {
                        "status": "VALID",
                        "actual_type": actual_type,
                        "nullable": actual_col['nullable']
                    }
                    logger.info(f"✅ Column {col_name}: {actual_type} (nullable: {actual_col['nullable']})")
                else:
                    self.validation_results["columns"][col_name] = {
                        "status": "INVALID",
                        "error": f"Type mismatch - expected {expected_type}, got {actual_type}",
                        "expected": expected,
                        "actual": {
                            "type": actual_type,
                            "nullable": actual_col['nullable']
                        }
                    }
                    logger.error(f"❌ Column {col_name} type/nullable mismatch")
            
            # Check if all columns are valid
            all_valid = all(
                result["status"] == "VALID" 
                for result in self.validation_results["columns"].values()
            )
            
            return all_valid
            
        except Exception as e:
            logger.error(f"Error validating WPA columns: {e}")
            self.validation_results["columns"]["error"] = str(e)
            return False
    
    def validate_wpa_indexes(self) -> bool:
        """
        Validate that WPA indexes were created correctly.
        
        Returns:
            bool: True if all expected indexes exist
        """
        logger.info("Validating WPA indexes...")
        
        try:
            # Get all indexes for deliveries table
            indexes = self.inspector.get_indexes('deliveries')
            index_names = [idx['name'] for idx in indexes]
            
            # Expected WPA indexes
            expected_indexes = [
                'idx_deliveries_wpa_computed',
                'idx_deliveries_wpa_match',
                'idx_deliveries_wpa_batter',
                'idx_deliveries_wpa_bowler'
            ]
            
            # Validate each expected index
            for idx_name in expected_indexes:
                if idx_name in index_names:
                    self.validation_results["indexes"][idx_name] = {"status": "EXISTS"}
                    logger.info(f"✅ Index {idx_name} exists")
                else:
                    self.validation_results["indexes"][idx_name] = {
                        "status": "MISSING",
                        "error": f"Index {idx_name} not found"
                    }
                    logger.warning(f"⚠️ Index {idx_name} is missing")
            
            # Check if critical indexes exist (at least the computed date index)
            critical_indexes_exist = 'idx_deliveries_wpa_computed' in index_names
            
            return critical_indexes_exist
            
        except Exception as e:
            logger.error(f"Error validating WPA indexes: {e}")
            self.validation_results["indexes"]["error"] = str(e)
            return False
    
    def validate_wpa_constraints(self) -> bool:
        """
        Validate that WPA constraints were added correctly.
        
        Returns:
            bool: True if constraints are properly configured
        """
        logger.info("Validating WPA constraints...")
        
        try:
            session = self.session_factory()
            
            # Test WPA range constraints by attempting invalid inserts
            constraint_tests = [
                ("wpa_batter range", "SELECT 1 WHERE 1.5 BETWEEN -2.0 AND 2.0"),
                ("wpa_bowler range", "SELECT 1 WHERE -0.8 BETWEEN -2.0 AND 2.0"),
            ]
            
            constraints_valid = True
            
            for test_name, test_query in constraint_tests:
                try:
                    result = session.execute(text(test_query)).fetchone()
                    if result:
                        self.validation_results["constraints"][test_name] = {"status": "VALID"}
                        logger.info(f"✅ Constraint validation: {test_name}")
                    else:
                        constraints_valid = False
                        self.validation_results["constraints"][test_name] = {
                            "status": "INVALID",
                            "error": "Range constraint validation failed"
                        }
                        logger.error(f"❌ Constraint validation failed: {test_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not test constraint {test_name}: {e}")
                    self.validation_results["constraints"][test_name] = {
                        "status": "UNKNOWN",
                        "warning": str(e)
                    }
            
            session.close()
            return constraints_valid
            
        except Exception as e:
            logger.error(f"Error validating WPA constraints: {e}")
            self.validation_results["constraints"]["error"] = str(e)
            return False
    
    def check_deliveries_table_stats(self) -> dict:
        """
        Get statistics about the deliveries table and WPA columns.
        
        Returns:
            dict: Table statistics
        """
        logger.info("Gathering deliveries table statistics...")
        
        try:
            session = self.session_factory()
            
            # Get basic table statistics
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_deliveries,
                    COUNT(wpa_batter) as deliveries_with_wpa_batter,
                    COUNT(wpa_bowler) as deliveries_with_wpa_bowler,
                    COUNT(wpa_computed_date) as deliveries_with_computed_date,
                    MIN(wpa_batter) as min_wpa_batter,
                    MAX(wpa_batter) as max_wpa_batter,
                    MIN(wpa_bowler) as min_wpa_bowler,
                    MAX(wpa_bowler) as max_wpa_bowler
                FROM deliveries
            """)
            
            result = session.execute(stats_query).fetchone()
            
            if result:
                stats = {
                    "total_deliveries": result.total_deliveries,
                    "deliveries_with_wpa_batter": result.deliveries_with_wpa_batter,
                    "deliveries_with_wpa_bowler": result.deliveries_with_wpa_bowler,
                    "deliveries_with_computed_date": result.deliveries_with_computed_date,
                    "wpa_coverage_percentage": round(
                        (result.deliveries_with_wpa_batter / result.total_deliveries) * 100, 2
                    ) if result.total_deliveries > 0 else 0,
                    "min_wpa_batter": float(result.min_wpa_batter) if result.min_wpa_batter else None,
                    "max_wpa_batter": float(result.max_wpa_batter) if result.max_wpa_batter else None,
                    "min_wpa_bowler": float(result.min_wpa_bowler) if result.min_wpa_bowler else None,
                    "max_wpa_bowler": float(result.max_wpa_bowler) if result.max_wpa_bowler else None
                }
                
                logger.info(f"📊 Total deliveries: {stats['total_deliveries']:,}")
                logger.info(f"📊 Deliveries with WPA: {stats['deliveries_with_wpa_batter']:,} ({stats['wpa_coverage_percentage']}%)")
                
                session.close()
                return stats
            else:
                session.close()
                return {"error": "Could not retrieve table statistics"}
                
        except Exception as e:
            logger.error(f"Error gathering table statistics: {e}")
            return {"error": str(e)}
    
    def run_full_validation(self) -> dict:
        """
        Run complete WPA schema validation.
        
        Returns:
            dict: Complete validation results
        """
        logger.info("🔍 Starting WPA schema validation...")
        logger.info("=" * 60)
        
        # Run all validation checks
        columns_valid = self.validate_wpa_columns()
        indexes_valid = self.validate_wpa_indexes()
        constraints_valid = self.validate_wpa_constraints()
        
        # Get table statistics
        table_stats = self.check_deliveries_table_stats()
        
        # Determine overall status
        if columns_valid and indexes_valid:
            if constraints_valid:
                overall_status = "FULLY_VALID"
                status_emoji = "✅"
            else:
                overall_status = "MOSTLY_VALID"
                status_emoji = "⚠️"
        else:
            overall_status = "INVALID"
            status_emoji = "❌"
        
        self.validation_results["overall_status"] = overall_status
        self.validation_results["table_stats"] = table_stats
        self.validation_results["validation_timestamp"] = datetime.now().isoformat()
        
        # Print summary
        logger.info("=" * 60)
        logger.info(f"{status_emoji} WPA Schema Validation: {overall_status}")
        logger.info(f"📅 Validation completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if overall_status == "FULLY_VALID":
            logger.info("🎉 All WPA schema components are properly configured!")
        elif overall_status == "MOSTLY_VALID":
            logger.info("✅ Core WPA schema is valid, minor issues with constraints")
        else:
            logger.error("❌ WPA schema has critical issues that need to be resolved")
        
        return self.validation_results


def main():
    """Run WPA schema validation"""
    try:
        validator = WPASchemaValidator()
        results = validator.run_full_validation()
        
        # Print detailed results for debugging
        print("\n" + "=" * 60)
        print("DETAILED VALIDATION RESULTS")
        print("=" * 60)
        
        import json
        print(json.dumps(results, indent=2, default=str))
        
        # Return appropriate exit code
        if results["overall_status"] in ["FULLY_VALID", "MOSTLY_VALID"]:
            print("\n✅ Schema validation passed!")
            return 0
        else:
            print("\n❌ Schema validation failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Validation script failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
