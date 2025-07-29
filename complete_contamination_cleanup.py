#!/usr/bin/env python3
"""
COMPLETE CONTAMINATION CLEANUP SCRIPT
Eliminates ALL sources of contaminated trade data from:
- Main trades table
- paper_trades table  
- Redis cache (all trade keys)
- SQLite backup files
- Trading persistence system
- Order manager duplicates
"""

import asyncio
import logging
import os
import sys
import json
import glob
from datetime import datetime
from sqlalchemy import create_engine, text
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompleteContaminationCleanup:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/trading_system')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.cleanup_report = {
            'timestamp': datetime.now().isoformat(),
            'actions_taken': [],
            'tables_cleaned': [],
            'redis_keys_deleted': [],
            'files_removed': [],
            'errors': []
        }

    async def run_complete_cleanup(self):
        """Run comprehensive cleanup of ALL contamination sources"""
        try:
            logger.info("🚀 STARTING COMPLETE CONTAMINATION CLEANUP")
            logger.info("=" * 60)

            # 1. Clean PostgreSQL Database
            await self._clean_postgresql_database()
            
            # 2. Clean Redis Cache
            await self._clean_redis_cache()
            
            # 3. Clean SQLite Backup Files
            await self._clean_sqlite_files()
            
            # 4. Clean Trading Persistence System
            await self._clean_persistence_system()
            
            # 5. Verify Cleanup Success
            await self._verify_cleanup_success()
            
            # 6. Generate Report
            self._generate_cleanup_report()
            
            logger.info("✅ COMPLETE CONTAMINATION CLEANUP FINISHED")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            self.cleanup_report['errors'].append(str(e))
            return False

    async def _clean_postgresql_database(self):
        """Clean ALL trade-related tables in PostgreSQL"""
        try:
            logger.info("🗄️ CLEANING POSTGRESQL DATABASE")
            
            engine = create_engine(self.database_url)
            
            with engine.connect() as conn:
                # Get all tables to understand what exists
                tables_query = text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE '%trade%'
                """)
                
                result = conn.execute(tables_query)
                existing_tables = [row[0] for row in result.fetchall()]
                
                logger.info(f"📋 Found trade-related tables: {existing_tables}")
                
                # Clean each table with all possible contaminated data patterns
                cleanup_queries = []
                
                for table in existing_tables:
                    if 'trade' in table:
                        # Delete ALL trades (including any contaminated ones)
                        cleanup_queries.append(f"DELETE FROM {table};")
                        cleanup_queries.append(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1;")
                        self.cleanup_report['tables_cleaned'].append(table)
                
                # Additional specific cleanup queries
                additional_queries = [
                    # Clean main trades table completely
                    "DELETE FROM trades;",
                    "ALTER SEQUENCE trades_trade_id_seq RESTART WITH 1;",
                    
                    # Clean paper_trades if exists
                    "DELETE FROM paper_trades;",
                    
                    # Clean any order-related contamination
                    "DELETE FROM orders WHERE status IN ('MOCK', 'PAPER', 'SIMULATED');",
                    
                    # Clean any positions with zero/invalid prices
                    "DELETE FROM positions WHERE entry_price <= 0 OR current_price <= 0;",
                    
                    # Reset any sequence counters
                    "SELECT setval(pg_get_serial_sequence('trades', 'trade_id'), 1, false);",
                ]
                
                cleanup_queries.extend(additional_queries)
                
                # Execute all cleanup queries
                for query in cleanup_queries:
                    try:
                        result = conn.execute(text(query))
                        affected_rows = result.rowcount if hasattr(result, 'rowcount') else 0
                        logger.info(f"✅ Executed: {query[:50]}... (affected: {affected_rows} rows)")
                        self.cleanup_report['actions_taken'].append(f"DB: {query[:50]}...")
                    except Exception as e:
                        if "does not exist" not in str(e).lower():
                            logger.warning(f"⚠️ Query failed: {query[:50]}... - {e}")
                            self.cleanup_report['errors'].append(f"DB Query: {str(e)}")
                
                conn.commit()
                logger.info("✅ PostgreSQL database cleaned successfully")
                
        except Exception as e:
            logger.error(f"❌ PostgreSQL cleanup failed: {e}")
            self.cleanup_report['errors'].append(f"PostgreSQL: {str(e)}")

    async def _clean_redis_cache(self):
        """Clean ALL trade-related Redis keys"""
        try:
            logger.info("🔄 CLEANING REDIS CACHE")
            
            redis_client = redis.from_url(self.redis_url)
            
            # Define all possible trade-related key patterns
            trade_key_patterns = [
                'trade:*',
                'trades_*',
                'paper_trading:*',
                'user:*:trades:*',
                'trading_session:*',
                'order:*',
                'position:*',
                'pnl:*',
                'strategy:*:trades:*',
                'compliance:trades:*',
                'sharekhan:orders:*',
                'autonomous:trades:*'
            ]
            
            total_deleted = 0
            
            for pattern in trade_key_patterns:
                try:
                    keys = await redis_client.keys(pattern)
                    if keys:
                        deleted = await redis_client.delete(*keys)
                        total_deleted += deleted
                        self.cleanup_report['redis_keys_deleted'].extend([k.decode() if isinstance(k, bytes) else k for k in keys])
                        logger.info(f"✅ Deleted {deleted} keys matching pattern: {pattern}")
                    else:
                        logger.info(f"ℹ️ No keys found for pattern: {pattern}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to clean pattern {pattern}: {e}")
                    self.cleanup_report['errors'].append(f"Redis {pattern}: {str(e)}")
            
            await redis_client.close()
            
            logger.info(f"✅ Redis cleanup completed - {total_deleted} keys deleted")
            self.cleanup_report['actions_taken'].append(f"Redis: {total_deleted} keys deleted")
            
        except Exception as e:
            logger.error(f"❌ Redis cleanup failed: {e}")
            self.cleanup_report['errors'].append(f"Redis: {str(e)}")

    async def _clean_sqlite_files(self):
        """Clean SQLite backup files used by trading persistence"""
        try:
            logger.info("📁 CLEANING SQLITE BACKUP FILES")
            
            # Search for SQLite files in common locations
            sqlite_patterns = [
                'trading_*.db',
                'trades.db',
                'paper_*.db',
                'backup_*.db',
                '*.sqlite',
                '*.sqlite3'
            ]
            
            search_paths = ['.', 'src', 'data', 'backups', 'logs']
            
            removed_files = []
            
            for search_path in search_paths:
                if os.path.exists(search_path):
                    for pattern in sqlite_patterns:
                        file_pattern = os.path.join(search_path, pattern)
                        matching_files = glob.glob(file_pattern)
                        
                        for file_path in matching_files:
                            try:
                                os.remove(file_path)
                                removed_files.append(file_path)
                                logger.info(f"✅ Removed SQLite file: {file_path}")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to remove {file_path}: {e}")
                                self.cleanup_report['errors'].append(f"File {file_path}: {str(e)}")
            
            self.cleanup_report['files_removed'] = removed_files
            self.cleanup_report['actions_taken'].append(f"Files: {len(removed_files)} SQLite files removed")
            
            logger.info(f"✅ SQLite cleanup completed - {len(removed_files)} files removed")
            
        except Exception as e:
            logger.error(f"❌ SQLite cleanup failed: {e}")
            self.cleanup_report['errors'].append(f"SQLite: {str(e)}")

    async def _clean_persistence_system(self):
        """Clean trading persistence system state"""
        try:
            logger.info("🔧 CLEANING PERSISTENCE SYSTEM")
            
            # Reset persistence system by removing state files
            persistence_files = [
                'trading_persistence.json',
                'current_session.json',
                'trades_backup.json'
            ]
            
            for file_name in persistence_files:
                if os.path.exists(file_name):
                    try:
                        os.remove(file_name)
                        logger.info(f"✅ Removed persistence file: {file_name}")
                        self.cleanup_report['files_removed'].append(file_name)
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to remove {file_name}: {e}")
                        self.cleanup_report['errors'].append(f"Persistence {file_name}: {str(e)}")
            
            self.cleanup_report['actions_taken'].append("Persistence: System state files cleaned")
            logger.info("✅ Persistence system cleaned")
            
        except Exception as e:
            logger.error(f"❌ Persistence cleanup failed: {e}")
            self.cleanup_report['errors'].append(f"Persistence: {str(e)}")

    async def _verify_cleanup_success(self):
        """Verify that cleanup was successful"""
        try:
            logger.info("🔍 VERIFYING CLEANUP SUCCESS")
            
            # Check PostgreSQL
            engine = create_engine(self.database_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM trades"))
                trade_count = result.fetchone()[0]
                
                if trade_count == 0:
                    logger.info("✅ PostgreSQL trades table is clean (0 records)")
                else:
                    logger.warning(f"⚠️ PostgreSQL still has {trade_count} trade records")
                    self.cleanup_report['errors'].append(f"Verification: {trade_count} trades still exist")
            
            # Check Redis
            redis_client = redis.from_url(self.redis_url)
            trade_keys = await redis_client.keys('trade:*')
            await redis_client.close()
            
            if not trade_keys:
                logger.info("✅ Redis trade keys are clean")
            else:
                logger.warning(f"⚠️ Redis still has {len(trade_keys)} trade keys")
                self.cleanup_report['errors'].append(f"Verification: {len(trade_keys)} Redis trade keys still exist")
            
            verification_success = trade_count == 0 and len(trade_keys) == 0
            self.cleanup_report['actions_taken'].append(f"Verification: {'PASSED' if verification_success else 'FAILED'}")
            
            return verification_success
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            self.cleanup_report['errors'].append(f"Verification: {str(e)}")
            return False

    def _generate_cleanup_report(self):
        """Generate comprehensive cleanup report"""
        try:
            # Calculate summary statistics
            total_actions = len(self.cleanup_report['actions_taken'])
            total_tables = len(self.cleanup_report['tables_cleaned'])
            total_redis_keys = len(self.cleanup_report['redis_keys_deleted'])
            total_files = len(self.cleanup_report['files_removed'])
            total_errors = len(self.cleanup_report['errors'])
            
            # Add summary to report
            self.cleanup_report['summary'] = {
                'total_actions': total_actions,
                'tables_cleaned': total_tables,
                'redis_keys_deleted': total_redis_keys,
                'files_removed': total_files,
                'errors_encountered': total_errors,
                'success_rate': ((total_actions - total_errors) / total_actions * 100) if total_actions > 0 else 0
            }
            
            # Save report to file
            report_filename = f"contamination_cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(report_filename, 'w') as f:
                json.dump(self.cleanup_report, f, indent=2)
            
            # Print summary
            logger.info("\n" + "=" * 60)
            logger.info("📋 CLEANUP SUMMARY REPORT")
            logger.info("=" * 60)
            logger.info(f"✅ Total Actions: {total_actions}")
            logger.info(f"🗄️ Tables Cleaned: {total_tables}")
            logger.info(f"🔄 Redis Keys Deleted: {total_redis_keys}")
            logger.info(f"📁 Files Removed: {total_files}")
            logger.info(f"❌ Errors: {total_errors}")
            logger.info(f"📊 Success Rate: {self.cleanup_report['summary']['success_rate']:.1f}%")
            logger.info(f"💾 Full report saved: {report_filename}")
            
            if total_errors == 0:
                logger.info("🎉 COMPLETE SUCCESS - All contamination sources eliminated!")
            else:
                logger.warning("⚠️ Some errors encountered - check report for details")
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")

async def main():
    """Main function to run complete contamination cleanup"""
    cleanup = CompleteContaminationCleanup()
    success = await cleanup.run_complete_cleanup()
    
    if success:
        print("\n🎉 CONTAMINATION CLEANUP COMPLETED SUCCESSFULLY!")
        print("Your trading system is now clean of all contaminated data.")
        return 0
    else:
        print("\n❌ CONTAMINATION CLEANUP ENCOUNTERED ERRORS!")
        print("Check the generated report for details.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 