# AuthorizationRentals - Specific Code Issues and Fixes

## ISSUE #1: Print Statements Instead of Logging

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/services/google_sheets_service.py`

**Line 41**:
```python
except Exception as e:
    print(f"Error loading credentials: {e}")
    raise
```

**Line 81**:
```python
except HttpError as error:
    print(f"An error occurred: {error}")
    return []
```

**Line 167**:
```python
except HttpError as error:
    print(f"An error occurred: {error}")
    return False
```

### Fix
```python
# At top of file, add:
import logging
logger = logging.getLogger(__name__)

# Replace each print() with:
logger.error(f"Error loading credentials", exc_info=True)
logger.error(f"Google Sheets error", exc_info=True)
logger.error(f"Google Sheets update error", exc_info=True)
```

---

## ISSUE #2: Hardcoded Business Name

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/agents/rental_agent.py`

**Line 91**:
```python
self.state.business_name = "Metro Construction LLC"
```

This line is in `verify_business_license()` and returns a hardcoded name regardless of license verification result.

### Context
```python
async def verify_business_license(self, license_number: str):
    logger.info(f"Verifying business license: {license_number}")
    
    success, message = await self.verification_service.verify_business_license(license_number)
    
    if success:
        self.state.business_license = license_number
        self.state.customer_verified = True
        self.state.business_name = "Metro Construction LLC"  # HARDCODED!
        self.state.advance_stage()
        await self._update_instructions()
        return f"Business license verified. Customer: {self.state.business_name}"
```

### Fix
Extract business name from actual verification service or require it as parameter:

```python
async def verify_business_license(self, license_number: str, business_name: str = None):
    logger.info(f"Verifying business license: {license_number}")
    
    success, message, verified_business_name = await self.verification_service.verify_business_license(license_number)
    
    if success:
        self.state.business_license = license_number
        self.state.customer_verified = True
        self.state.business_name = verified_business_name or business_name or "Unknown"
        self.state.advance_stage()
        await self._update_instructions()
        return f"Business license verified. Customer: {self.state.business_name}"
```

And update verification_service to return business name:
```python
@staticmethod
async def verify_business_license(license_number: str) -> Tuple[bool, str, Optional[str]]:
    """
    Returns: (success, message, business_name)
    """
    # In production, would call real API
    return True, f"Verified", "Customer Business Name"
```

---

## ISSUE #3: No Environment Variable Validation

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/services/google_sheets_service.py`

**Lines 19-21**:
```python
def __init__(
    self,
    credentials_path: str = "credentials.json",
    spreadsheet_id: str = None,
    range_name: str = None
):
    self.credentials_path = credentials_path
    self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID")
    self.range_name = range_name or os.getenv("GOOGLE_SHEETS_RANGE", "Inventory!A:J")
    self._lock = asyncio.Lock()
    self._service = None
```

### Fix
```python
def __init__(
    self,
    credentials_path: str = "credentials.json",
    spreadsheet_id: str = None,
    range_name: str = None
):
    self.credentials_path = credentials_path
    
    # Validate environment variables
    self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID")
    if not self.spreadsheet_id:
        raise ValueError(
            "GOOGLE_SHEET_ID environment variable must be set or passed as parameter"
        )
    
    self.range_name = range_name or os.getenv("GOOGLE_SHEETS_RANGE", "Inventory!A:J")
    
    self._lock = asyncio.Lock()
    self._service = None
    
    logger.info(f"GoogleSheetsDataService initialized with sheet: {self.spreadsheet_id}")
```

### Add to main.py
```python
import os

def validate_environment():
    """Validate all required environment variables at startup."""
    required_vars = {
        "LIVEKIT_URL": "LiveKit server URL",
        "LIVEKIT_API_KEY": "LiveKit API key",
        "LIVEKIT_API_SECRET": "LiveKit API secret",
        "GOOGLE_SHEET_ID": "Google Sheets ID for inventory",
        "OPENAI_API_KEY": "OpenAI API key",
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")
    
    if missing:
        raise ValueError(
            f"Missing required environment variables:\n" +
            "\n".join(f"  - {var}" for var in missing)
        )
    
    logger.info("All required environment variables configured")

# In main.py, before creating any services:
if __name__ == "__main__":
    try:
        validate_environment()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    cli.run_app(...)
```

---

## ISSUE #4: CSV Writing Without Escaping

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/services/data_service.py`

**Lines 64-74**:
```python
async with aiofiles.open(self.csv_path, mode='w', encoding='utf-8', newline='') as f:
    if all_equipment:
        fieldnames = all_equipment[0].keys()
        content = ','.join(fieldnames) + '\n'
        
        for eq in all_equipment:
            row = ','.join(str(eq[field]) for field in fieldnames)
            content += row + '\n'
        
        await f.write(content)

return True
```

### Problem
If any field contains:
- Commas: `"Acme, Inc."` → breaks CSV parsing
- Quotes: `"John ""The Boss"" Smith"` → escaping broken
- Newlines: Multi-line values break row parsing

### Fix (Using CSV Module)
```python
import csv
import io

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
        
        # Write back to CSV PROPERLY
        try:
            async with aiofiles.open(self.csv_path, mode='w', encoding='utf-8', newline='') as f:
                if all_equipment:
                    fieldnames = all_equipment[0].keys()
                    
                    # Use StringIO for CSV writing
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_equipment)
                    
                    await f.write(output.getvalue())
            
            return True
        except IOError as e:
            logger.error(f"Failed to write CSV: {e}", exc_info=True)
            return False
```

---

## ISSUE #5: Generic Exception Handling

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/services/google_sheets_service.py`

**Lines 31-42**:
```python
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
        except Exception as e:  # TOO GENERIC!
            print(f"Error loading credentials: {e}")
            raise
            
        self._service = build('sheets', 'v4', credentials=credentials)
    return self._service
```

### Fix
```python
import logging
from google.auth.exceptions import DefaultCredentialsError

logger = logging.getLogger(__name__)

def _get_service(self):
    """Get or create Google Sheets service."""
    if self._service is None:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        
        try:
            if os.path.exists(self.credentials_path):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        self.credentials_path, scopes=SCOPES
                    )
                    logger.info(f"Loaded credentials from {self.credentials_path}")
                except FileNotFoundError:
                    logger.error(f"Credentials file not found: {self.credentials_path}")
                    raise ValueError(f"Service account credentials file missing at {self.credentials_path}")
                except ValueError as e:
                    logger.error(f"Invalid credentials file format: {e}")
                    raise ValueError(f"Invalid service account credentials: {e}")
            else:
                # Use default Cloud Run credentials
                try:
                    from google.auth import default
                    credentials, _ = default(scopes=SCOPES)
                    logger.info("Using default Google Cloud credentials")
                except DefaultCredentialsError as e:
                    logger.error("Could not find default Google credentials")
                    raise ValueError(
                        "No Google credentials found. Either provide credentials.json or set up Application Default Credentials"
                    )
                
            self._service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets API service initialized successfully")
            
        except ValueError:
            # Re-raise as-is with clear message
            raise
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error initializing Google Sheets: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize Google Sheets API: {e}") from e
    
    return self._service
```

---

## ISSUE #6: No Timeout Configuration

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/services/google_sheets_service.py`

**Lines 52-58**:
```python
def _read_sheet():
    try:
        service = self._get_service()
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=self.spreadsheet_id,
            range=self.range_name
        ).execute()  # NO TIMEOUT!
```

### Fix
```python
import socket

def _read_sheet():
    """Read from Google Sheets with timeout protection."""
    try:
        service = self._get_service()
        sheet = service.spreadsheets()
        
        # Set timeout on socket level
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(30)  # 30 second timeout
        
        try:
            result = sheet.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=self.range_name,
                timeout=30  # Also set request timeout
            ).execute()
        finally:
            socket.setdefaulttimeout(old_timeout)
        
        values = result.get('values', [])
        
        if not values:
            logger.warning("Google Sheets returned empty result")
            return []
        
        # Convert rows to dictionaries
        headers = values[0]
        equipment_list = []
        
        for row in values[1:]:
            # Pad row if it has fewer columns than headers
            while len(row) < len(headers):
                row.append('')
            
            equipment = dict(zip(headers, row))
            equipment_list.append(equipment)
        
        logger.info(f"Read {len(equipment_list)} equipment items from Google Sheets")
        return equipment_list
        
    except socket.timeout:
        logger.error("Google Sheets API request timed out after 30 seconds")
        return []
    except HttpError as error:
        logger.error(f"Google Sheets API error: {error}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading Google Sheets: {e}", exc_info=True)
        return []
```

---

## ISSUE #7: Deprecated asyncio Pattern

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/services/google_sheets_service.py`

**Lines 49, 106**:
```python
async def get_all_equipment(self) -> List[Dict]:
    """Read all equipment from Google Sheets."""
    loop = asyncio.get_event_loop()  # DEPRECATED
    
    def _read_sheet():
        # ... sync code ...
        return equipment_list
    
    return await loop.run_in_executor(None, _read_sheet)
```

### Fix (Python 3.9+)
```python
async def get_all_equipment(self) -> List[Dict]:
    """Read all equipment from Google Sheets."""
    
    def _read_sheet():
        # ... sync code ...
        return equipment_list
    
    # Modern way: use asyncio.to_thread (Python 3.9+)
    return await asyncio.to_thread(_read_sheet)
```

### Fallback (Python 3.8)
```python
async def get_all_equipment(self) -> List[Dict]:
    """Read all equipment from Google Sheets."""
    
    def _read_sheet():
        # ... sync code ...
        return equipment_list
    
    # Get running loop instead of event loop
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _read_sheet)
```

---

## ISSUE #8: Missing Input Validation

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/agents/rental_agent.py`

**Multiple functions lack validation**:
- Line 76: `verify_business_license(license_number: str)` 
- Line 179: `propose_price(proposed_daily_rate: float, rental_days: int = 1)`
- Line 235: `verify_operator_credentials(operator_name, operator_license, operator_phone)`

### Example Fix
```python
from typing import Optional

def _validate_license_number(license_number: str) -> Optional[str]:
    """Validate business license format."""
    if not license_number:
        return "License number cannot be empty"
    
    if len(license_number.strip()) < 3:
        return "License number too short (minimum 3 characters)"
    
    # Remove common separators for length check
    clean_license = license_number.replace('-', '').replace('_', '')
    if not clean_license.isalnum():
        return "License number contains invalid characters"
    
    return None  # Valid

@llm.function_tool()
async def verify_business_license(self, license_number: str):
    """Verify customer's business license with state authorities."""
    
    # Validate input
    error = self._validate_license_number(license_number)
    if error:
        return f"Invalid license format: {error}"
    
    logger.info(f"Verifying business license: {license_number}")
    
    # ... rest of function

def _validate_price(price: float, min_price: float, max_price: float) -> Optional[str]:
    """Validate proposed price."""
    if price <= 0:
        return "Price must be greater than zero"
    
    if price < min_price:
        return f"Price below minimum (${min_price})"
    
    if price > max_price:
        return f"Price exceeds maximum (${max_price})"
    
    return None

@llm.function_tool()
async def propose_price(self, proposed_daily_rate: float, rental_days: int = 1):
    """Propose a negotiated price for the equipment rental."""
    
    if not self.state.selected_equipment:
        return "No equipment selected."
    
    equipment = self.state.selected_equipment
    min_rate = float(equipment['Daily Rate'])
    max_rate = float(equipment['Max Rate'])
    
    # Validate input FIRST
    error = self._validate_price(proposed_daily_rate, min_rate, max_rate)
    if error:
        return error
    
    if rental_days < 1 or rental_days > 365:
        return "Rental duration must be between 1 and 365 days"
    
    # ... rest of function
```

---

## ISSUE #9: Placeholder Verification Service

### Current Location
**File**: `/home/user/AuthorizationRentals/src/services/verification_service.py`

All functions return `True`:
```python
@staticmethod
async def verify_business_license(license_number: str) -> Tuple[bool, str]:
    # Placeholder: Always returns True for demo
    # In production, this would call state licensing API
    return True, f"Business license {license_number} verified successfully"
```

### Minimal Real Implementation (Example)
```python
import logging
import httpx
from typing import Tuple

logger = logging.getLogger(__name__)

class VerificationService:
    """Handles external verification calls."""
    
    # In production, use actual API endpoints
    LICENSE_API_ENDPOINT = "https://api.state.gov/verify-license"
    CERT_API_ENDPOINT = "https://api.cert-board.gov/check-operator"
    
    @staticmethod
    async def verify_business_license(license_number: str) -> Tuple[bool, str]:
        """Verify business license with state authorities."""
        
        if not license_number:
            return False, "License number cannot be empty"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{VerificationService.LICENSE_API_ENDPOINT}",
                    params={"license": license_number}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("valid"):
                        logger.info(f"License {license_number} verified")
                        return True, f"License verified: {data.get('business_name')}"
                    else:
                        logger.warning(f"License {license_number} invalid")
                        return False, "License not found or invalid"
                else:
                    logger.error(f"License verification API returned {response.status_code}")
                    return False, "Unable to verify license at this time"
                    
        except httpx.TimeoutException:
            logger.error("License verification API timeout")
            return False, "License verification service timeout. Please try again."
        except Exception as e:
            logger.error(f"License verification error: {e}", exc_info=True)
            return False, "Error verifying license. Please try again."
```

---

## ISSUE #10: Race Condition in Service Initialization

### Problem Location
**File**: `/home/user/AuthorizationRentals/src/services/google_sheets_service.py`

**Lines 25-45**:
```python
def _get_service(self):
    """Get or create Google Sheets service."""
    if self._service is None:  # NOT THREAD SAFE
        # ... create service ...
        self._service = build('sheets', 'v4', credentials=credentials)
    return self._service
```

### Fix (Using Lock)
```python
import asyncio
import threading

class GoogleSheetsDataService:
    def __init__(self, ...):
        # ... other init ...
        self._service = None
        self._service_lock = threading.Lock()  # Use thread lock for sync code
    
    def _get_service(self):
        """Get or create Google Sheets service (thread-safe)."""
        if self._service is None:
            with self._service_lock:
                # Double-checked locking
                if self._service is None:
                    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
                    
                    # ... credential loading ...
                    
                    self._service = build('sheets', 'v4', credentials=credentials)
                    logger.info("Google Sheets service initialized")
        
        return self._service
```

---

## Summary of Quick Fixes (Priority Order)

1. **Replace print() with logger** (15 min)
   - Files: google_sheets_service.py lines 41, 81, 167

2. **Add environment validation** (30 min)
   - Add to main.py startup
   - Add checks to GoogleSheetsDataService.__init__

3. **Fix CSV writing** (45 min)
   - Use csv.DictWriter in data_service.py

4. **Add input validation** (1 hour)
   - Validation functions in rental_agent.py
   - Check before processing

5. **Fix asyncio patterns** (30 min)
   - Replace get_event_loop with get_running_loop
   - Use asyncio.to_thread if Python 3.9+

6. **Add timeout to API calls** (1 hour)
   - Socket timeout in google_sheets_service.py
   - Request timeout parameters

7. **Fix hardcoded business name** (30 min)
   - Modify verify_business_license to use data from service
   - Update verification_service return type

