"""PostgreSQL data service for inventory management."""

import asyncio
import os
import logging
from typing import List, Dict, Optional
import asyncpg

logger = logging.getLogger("rental-agent")


class PostgresDataService:
    """Handles reading and writing inventory data from PostgreSQL."""

    def __init__(self, database_url: str = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        self._pool = None

    async def _get_pool(self):
        """Get or create connection pool."""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=30
                )
                logger.info("PostgreSQL connection pool created")
            except Exception as e:
                logger.error(f"Failed to create PostgreSQL pool: {e}")
                raise
        return self._pool

    async def init_schema(self):
        """Initialize database schema if it doesn't exist."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    equipment_id VARCHAR(20) PRIMARY KEY,
                    equipment_name VARCHAR(200) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    daily_rate DECIMAL(10, 2) NOT NULL,
                    max_rate DECIMAL(10, 2) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
                    operator_cert_required VARCHAR(200),
                    min_insurance DECIMAL(15, 2) NOT NULL,
                    storage_location VARCHAR(200) NOT NULL,
                    weight_class VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create index on status for fast availability queries
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_inventory_status
                ON inventory(status)
            ''')

            logger.info("Database schema initialized")

    async def get_all_equipment(self) -> List[Dict]:
        """Read all equipment from database."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT
                    equipment_id AS "Equipment ID",
                    equipment_name AS "Equipment Name",
                    category AS "Category",
                    daily_rate AS "Daily Rate",
                    max_rate AS "Max Rate",
                    status AS "Status",
                    operator_cert_required AS "Operator Cert Required",
                    min_insurance AS "Min Insurance",
                    storage_location AS "Storage Location",
                    weight_class AS "Weight Class"
                FROM inventory
                ORDER BY equipment_id
            ''')

            return [dict(row) for row in rows]

    async def get_available_equipment(self) -> List[Dict]:
        """Get only available equipment."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT
                    equipment_id AS "Equipment ID",
                    equipment_name AS "Equipment Name",
                    category AS "Category",
                    daily_rate AS "Daily Rate",
                    max_rate AS "Max Rate",
                    status AS "Status",
                    operator_cert_required AS "Operator Cert Required",
                    min_insurance AS "Min Insurance",
                    storage_location AS "Storage Location",
                    weight_class AS "Weight Class"
                FROM inventory
                WHERE status = 'AVAILABLE'
                ORDER BY equipment_id
            ''')

            return [dict(row) for row in rows]

    async def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict]:
        """Get specific equipment by ID."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT
                    equipment_id AS "Equipment ID",
                    equipment_name AS "Equipment Name",
                    category AS "Category",
                    daily_rate AS "Daily Rate",
                    max_rate AS "Max Rate",
                    status AS "Status",
                    operator_cert_required AS "Operator Cert Required",
                    min_insurance AS "Min Insurance",
                    storage_location AS "Storage Location",
                    weight_class AS "Weight Class"
                FROM inventory
                WHERE equipment_id = $1
            ''', equipment_id)

            return dict(row) if row else None

    async def update_equipment_status(self, equipment_id: str, new_status: str) -> bool:
        """
        Update equipment status with atomic check-and-update.
        Returns True if update successful, False if equipment already rented.
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Use a transaction for atomic check-and-update
            async with conn.transaction():
                # Check current status with row lock (FOR UPDATE)
                current_status = await conn.fetchval('''
                    SELECT status
                    FROM inventory
                    WHERE equipment_id = $1
                    FOR UPDATE
                ''', equipment_id)

                if not current_status:
                    logger.warning(f"Equipment {equipment_id} not found")
                    return False

                if current_status != 'AVAILABLE':
                    logger.warning(f"Equipment {equipment_id} is {current_status}, not available")
                    return False

                # Update status
                result = await conn.execute('''
                    UPDATE inventory
                    SET status = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE equipment_id = $2
                ''', new_status, equipment_id)

                # Check if update was successful
                if result == "UPDATE 1":
                    logger.info(f"Equipment {equipment_id} status updated to {new_status}")
                    return True
                else:
                    logger.error(f"Failed to update equipment {equipment_id}")
                    return False

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("PostgreSQL connection pool closed")
