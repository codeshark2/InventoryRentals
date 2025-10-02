import csv
import asyncio
import aiofiles
from typing import List, Dict, Optional
from pathlib import Path


class EquipmentDataService:
    """Handles reading and writing equipment inventory data."""
    
    def __init__(self, csv_path: str = "data/equipment_inventory.csv"):
        self.csv_path = Path(csv_path)
        self._lock = asyncio.Lock()
    
    async def get_all_equipment(self) -> List[Dict]:
        """Read all equipment from CSV."""
        async with aiofiles.open(self.csv_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
        
        lines = content.strip().split('\n')
        reader = csv.DictReader(lines)
        return list(reader)
    
    async def get_available_equipment(self) -> List[Dict]:
        """Get only available equipment."""
        all_equipment = await self.get_all_equipment()
        return [eq for eq in all_equipment if eq['Status'] == 'AVAILABLE']
    
    async def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict]:
        """Get specific equipment by ID."""
        all_equipment = await self.get_all_equipment()
        for eq in all_equipment:
            if eq['Equipment ID'] == equipment_id:
                return eq
        return None
    
    async def update_equipment_status(self, equipment_id: str, new_status: str) -> bool:
        """
        Update equipment status with atomic check-and-update.
        Returns True if update successful, False if equipment already rented.
        """
        async with self._lock:
            # Read current data
            all_equipment = await self.get_all_equipment()
            
            # Find and check equipment
            equipment_found = False
            already_rented = False
            
            for eq in all_equipment:
                if eq['Equipment ID'] == equipment_id:
                    equipment_found = True
                    if eq['Status'] != 'AVAILABLE':
                        already_rented = True
                        break
                    # Update status
                    eq['Status'] = new_status
                    break
            
            if not equipment_found or already_rented:
                return False
            
            # Write back to CSV
            async with aiofiles.open(self.csv_path, mode='w', encoding='utf-8', newline='') as f:
                if all_equipment:
                    fieldnames = all_equipment[0].keys()
                    content = ','.join(fieldnames) + '\n'
                    
                    for eq in all_equipment:
                        row = ','.join(str(eq[field]) for field in fieldnames)
                        content += row + '\n'
                    
                    await f.write(content)
            
            return True

