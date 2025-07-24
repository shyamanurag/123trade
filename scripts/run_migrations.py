"""
Database Migration Runner
Automatically runs all pending migrations
"""
import os
import sys
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self):
        self.migrations_dir = Path(__file__).parent.parent / "database" / "migrations"
        self.applied_migrations_table = "schema_migrations"
        
    async def run(self):
        """Run all pending migrations"""
        conn = None
        try:
            # Parse database URL to get connection parameters
            import urllib.parse
            parsed = urllib.parse.urlparse(settings.DATABASE_URL)
            
            # Connect to database
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]  # Remove leading slash
            )
            
            logger.info("Connected to database")
            
            # Create migrations table if not exists
            await self._create_migrations_table(conn)
            
            # Get applied migrations
            applied = await self._get_applied_migrations(conn)
            logger.info(f"Found {len(applied)} applied migrations")
            
            # Get migration files
            migration_files = sorted(self.migrations_dir.glob("*.sql"))
            
            # Run pending migrations
            for migration_file in migration_files:
                migration_name = migration_file.name
                
                if migration_name not in applied:
                    logger.info(f"Running migration: {migration_name}")
                    
                    # Read migration content
                    with open(migration_file, 'r') as f:
                        migration_sql = f.read()
                    
                    # Run migration
                    try:
                        await conn.execute(migration_sql)
                        
                        # Record migration
                        await conn.execute(
                            f"INSERT INTO {self.applied_migrations_table} (version, applied_at) VALUES ($1, $2)",
                            migration_name,
                            datetime.now()
                        )
                        
                        logger.info(f"✅ Migration {migration_name} completed successfully")
                    except Exception as e:
                        logger.error(f"❌ Migration {migration_name} failed: {e}")
                        raise
                else:
                    logger.info(f"⏭️  Skipping already applied migration: {migration_name}")
            
            logger.info("All migrations completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            if conn:
                await conn.close()
    
    async def _create_migrations_table(self, conn):
        """Create migrations tracking table"""
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.applied_migrations_table} (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
    
    async def _get_applied_migrations(self, conn):
        """Get list of applied migrations"""
        rows = await conn.fetch(f"SELECT version FROM {self.applied_migrations_table}")
        return [row['version'] for row in rows]

async def main():
    runner = MigrationRunner()
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main()) 