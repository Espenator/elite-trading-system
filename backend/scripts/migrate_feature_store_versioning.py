"""
Migration script to add versioning columns to existing feature store data.

This script safely adds pipeline_version, schema_version, and feature_count columns
to existing records in the features table, backfilling with default values.

Usage:
    python backend/scripts/migrate_feature_store_versioning.py [--dry-run]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def migrate_feature_store(dry_run: bool = False):
    """Migrate feature store schema to include versioning columns.

    Args:
        dry_run: If True, only report what would be done without making changes
    """
    from app.data.duckdb_storage import duckdb_store

    conn = duckdb_store.get_thread_cursor()

    logger.info("Starting feature store versioning migration...")

    # Check current schema
    try:
        schema_info = conn.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'features'
            ORDER BY ordinal_position
        """).fetchall()

        logger.info("Current features table schema:")
        for col_name, col_type in schema_info:
            logger.info(f"  - {col_name}: {col_type}")

        # Check if versioning columns already exist
        columns = [col[0] for col in schema_info]
        has_pipeline_version = 'pipeline_version' in columns
        has_schema_version = 'schema_version' in columns
        has_feature_count = 'feature_count' in columns

        if has_pipeline_version and has_schema_version and has_feature_count:
            logger.info("✓ All versioning columns already exist. No migration needed.")
            return

        # Count existing records
        result = conn.execute("SELECT COUNT(*) FROM features").fetchone()
        record_count = result[0] if result else 0
        logger.info(f"Found {record_count} existing feature records")

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            if not has_pipeline_version:
                logger.info("Would add: pipeline_version column (default '1.0.0')")
            if not has_schema_version:
                logger.info("Would add: schema_version column (default '1.0')")
            if not has_feature_count:
                logger.info("Would add: feature_count column")
            return

        # Add missing columns
        if not has_pipeline_version:
            logger.info("Adding pipeline_version column...")
            conn.execute("""
                ALTER TABLE features
                ADD COLUMN pipeline_version VARCHAR DEFAULT '1.0.0'
            """)
            logger.info("✓ Added pipeline_version column")

        if not has_schema_version:
            logger.info("Adding schema_version column...")
            conn.execute("""
                ALTER TABLE features
                ADD COLUMN schema_version VARCHAR DEFAULT '1.0'
            """)
            logger.info("✓ Added schema_version column")

        if not has_feature_count:
            logger.info("Adding feature_count column...")
            conn.execute("""
                ALTER TABLE features
                ADD COLUMN feature_count INTEGER DEFAULT 0
            """)
            logger.info("✓ Added feature_count column")

            # Backfill feature_count from feature_json
            logger.info("Backfilling feature_count from feature_json...")
            conn.execute("""
                UPDATE features
                SET feature_count = json_array_length(json_keys(feature_json::JSON))
                WHERE feature_json IS NOT NULL
            """)
            updated = conn.execute("SELECT COUNT(*) FROM features WHERE feature_count > 0").fetchone()[0]
            logger.info(f"✓ Updated feature_count for {updated} records")

        # Add index if needed
        logger.info("Ensuring index on pipeline_version...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_features_pipeline_version
            ON features (pipeline_version)
        """)
        logger.info("✓ Index created")

        logger.info("Migration completed successfully!")

        # Show summary
        summary = conn.execute("""
            SELECT
                pipeline_version,
                schema_version,
                COUNT(*) as count,
                AVG(feature_count) as avg_features
            FROM features
            GROUP BY pipeline_version, schema_version
            ORDER BY pipeline_version DESC
        """).fetchall()

        logger.info("\nFeature store version summary:")
        for pipeline_v, schema_v, count, avg_features in summary:
            logger.info(
                f"  Pipeline {pipeline_v} / Schema {schema_v}: "
                f"{count} records, avg {avg_features:.1f} features"
            )

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Migrate feature store to include versioning columns"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    try:
        migrate_feature_store(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
