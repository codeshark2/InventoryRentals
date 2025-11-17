import asyncio
import os
import logging
from typing import List, Dict, Optional
from google.oauth2 import service_account
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("rental-agent")


class GoogleSheetsDataService:
    """Handles reading and writing equipment inventory data from Google Sheets."""
    
    def __init__(
        self,
        credentials_path: str = "credentials.json",
        spreadsheet_id: str = None,
        range_name: str = None,
        timeout: int = 30
    ):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID")  # Match .env variable name
        # Use "Inventory" sheet by default, or from env
        self.range_name = range_name or os.getenv("GOOGLE_SHEETS_RANGE", "Inventory!A:J")
        self.timeout = timeout  # API call timeout in seconds
        self._lock = asyncio.Lock()
        self._service = None
        
    def _get_service(self):
        """Get or create Google Sheets service."""
        if self._service is None:
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            # Try credentials file first, fall back to default credentials
            try:
                if os.path.exists(self.credentials_path):
                    credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_path, scopes=SCOPES
                    )
                else:
                    # Use default Cloud Run credentials
                    from google.auth import default
                    credentials, _ = default(scopes=SCOPES)
            except (FileNotFoundError, DefaultCredentialsError, ValueError) as e:
                logger.error(f"Error loading credentials: {e}")
                raise
                
            self._service = build('sheets', 'v4', credentials=credentials)
        return self._service
    
    async def get_all_equipment(self) -> List[Dict]:
        """Read all equipment from Google Sheets."""
        loop = asyncio.get_running_loop()

        def _read_sheet():
            try:
                service = self._get_service()
                sheet = service.spreadsheets()
                result = sheet.values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=self.range_name
                ).execute()

                values = result.get('values', [])

                if not values:
                    return []

                # First row is headers
                headers = values[0]
                equipment_list = []

                # Convert rows to dictionaries
                for row in values[1:]:
                    # Pad row if it has fewer columns than headers
                    while len(row) < len(headers):
                        row.append('')

                    equipment = dict(zip(headers, row))
                    equipment_list.append(equipment)

                return equipment_list

            except HttpError as error:
                logger.error(f"Google Sheets API error: {error}")
                return []

        # Run in thread pool to avoid blocking with timeout
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _read_sheet),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Google Sheets API call timed out after {self.timeout} seconds")
            return []
    
    async def get_available_equipment(self) -> List[Dict]:
        """Get only available equipment."""
        all_equipment = await self.get_all_equipment()
        return [eq for eq in all_equipment if eq.get('Status') == 'AVAILABLE']
    
    async def get_equipment_by_id(self, equipment_id: str) -> Optional[Dict]:
        """Get specific equipment by ID."""
        all_equipment = await self.get_all_equipment()
        for eq in all_equipment:
            if eq.get('Equipment ID') == equipment_id:
                return eq
        return None
    
    async def update_equipment_status(self, equipment_id: str, new_status: str) -> bool:
        """
        Update equipment status with atomic check-and-update.
        Returns True if update successful, False if equipment already rented.
        """
        async with self._lock:
            loop = asyncio.get_running_loop()

            def _update_sheet():
                try:
                    # Read current data
                    service = self._get_service()
                    sheet = service.spreadsheets()
                    
                    result = sheet.values().get(
                        spreadsheetId=self.spreadsheet_id,
                        range=self.range_name
                    ).execute()
                    
                    values = result.get('values', [])
                    
                    if not values:
                        return False
                    
                    headers = values[0]
                    
                    # Find the equipment and status column
                    equipment_id_col = headers.index('Equipment ID')
                    status_col = headers.index('Status')
                    
                    # Find the row with matching equipment ID
                    equipment_row = None
                    for i, row in enumerate(values[1:], start=2):  # Start at 2 (1-indexed, skip header)
                        if len(row) > equipment_id_col and row[equipment_id_col] == equipment_id:
                            equipment_row = i
                            current_status = row[status_col] if len(row) > status_col else ''
                            
                            # Check if already rented
                            if current_status != 'AVAILABLE':
                                return False
                            
                            break
                    
                    if equipment_row is None:
                        return False
                    
                    # Update the status
                    # Convert column index to letter (A, B, C, etc.)
                    status_col_letter = chr(65 + status_col)  # 65 is 'A'
                    # Extract sheet name from range_name (e.g., "Inventory!A:J" -> "Inventory")
                    sheet_name = self.range_name.split('!')[0] if '!' in self.range_name else 'Inventory'
                    update_range = f"{sheet_name}!{status_col_letter}{equipment_row}"
                    
                    body = {
                        'values': [[new_status]]
                    }
                    
                    sheet.values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=update_range,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    
                    return True

                except HttpError as error:
                    logger.error(f"Google Sheets API error during update: {error}")
                    return False

            # Run in thread pool with timeout
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, _update_sheet),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Google Sheets update timed out after {self.timeout} seconds")
                return False

