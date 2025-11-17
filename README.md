# AuthorizationRentals

AI-powered voice agent for automating inventory rental workflows using LiveKit and OpenAI Realtime API.

## Overview

AuthorizationRentals is a production-ready voice agent system designed to handle inbound inventory rental calls from start to finish. It manages complex multi-step workflows including customer verification, inventory discovery, price negotiation, user certification, and insurance verification - all through natural voice conversations.

### Key Features

- 🎤 **Natural Voice Conversations** - OpenAI Realtime API with voice modality
- 🔄 **State Machine Workflow** - 8-stage rental process with validation gates
- 🧠 **Dynamic Instruction Updates** - Agent instructions adapt to each workflow stage
- 📋 **Function Calling** - Structured LLM tool calls for verifications and data operations
- 💰 **Smart Price Negotiation** - Configurable min/max rates with attempt limits
- ✅ **Multi-Level Verification** - Business license, location safety, user certs, insurance
- 🔒 **Atomic Booking** - Race condition handling for concurrent agents
- 📊 **CSV Inventory Management** - Simple file-based inventory database

## Architecture

### Design Philosophy

The system is built around three core architectural patterns:

1. **State Machine Pattern** - Conversation flow managed through explicit workflow stages
2. **Dynamic Instruction Updates** - LLM context switches based on current stage
3. **Function Tool Architecture** - All business logic encapsulated in callable tools

This design ensures:
- Clear conversation progression
- Context-appropriate LLM responses
- Separation of concerns between state, logic, and presentation
- Testable and maintainable codebase

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LiveKit Room                            │
│                     (Voice I/O Channel)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AgentSession                               │
│                  (Session Management)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RentalAgent                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              ConversationState                           │  │
│  │  • Current workflow stage                                │  │
│  │  • Customer/equipment data                               │  │
│  │  • Verification status                                   │  │
│  │  • Stage validation logic                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┼────────────────────────────────┐ │
│  │  Function Tools (LLM Callable)                            │ │
│  │  • verify_business_license                                │ │
│  │  • search_available_equipment                             │ │
│  │  • select_equipment                                       │ │
│  │  • verify_site_safety                                     │ │
│  │  • propose_price / accept_price                           │ │
│  │  • verify_operator_credentials                            │ │
│  │  • verify_insurance_coverage                              │ │
│  │  • complete_booking                                       │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
    │  DataService│  │ Verification│  │ Prompt       │
    │             │  │  Service    │  │ Generator    │
    │ • CSV CRUD  │  │ • License   │  │ • Stage-based│
    │ • Inventory │  │ • Operator  │  │   prompts    │
    │ • Status    │  │ • Insurance │  │ • Context    │
    │   updates   │  │ • Site      │  │   injection  │
    └─────────────┘  └─────────────┘  └──────────────┘
```

### Project Structure

```
AuthorizationRentals/
├── main.py                          # Entry point & LiveKit integration
├── src/
│   ├── agents/
│   │   └── rental_agent.py          # Main agent orchestration
│   ├── services/
│   │   ├── data_service.py          # Inventory management
│   │   ├── google_sheets_service.py # Google Sheets integration
│   │   └── verification_service.py  # External verification APIs
│   └── utils/
│       ├── conversation_state.py    # State machine implementation
│       ├── prompts.py               # Stage-based prompt templates
│       └── function_tools.py        # Tool formatting utilities
├── data/
│   └── equipment_inventory.csv      # Inventory database
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Container configuration
└── render.yaml                      # Deployment configuration
```

## Workflow System

### State Machine Design

The conversation follows a linear state machine with validation gates:

```
GREETING
    ↓ (always advances)
CUSTOMER_VERIFICATION
    ↓ (requires: customer_verified = True)
EQUIPMENT_DISCOVERY
    ↓ (requires: selected_equipment != None)
REQUIREMENTS_CONFIRMATION
    ↓ (requires: site_verified = True)
PRICING_NEGOTIATION
    ↓ (requires: agreed_daily_rate != None)
OPERATOR_CERTIFICATION
    ↓ (requires: operator_verified = True)
INSURANCE_VERIFICATION
    ↓ (requires: insurance_verified = True)
BOOKING_COMPLETION
    ↓ (booking confirmed or failed)
CALL_ENDED
```

Each stage has specific:
- **Entry Requirements** - Validated before stage transition
- **Stage Instructions** - Focused prompts for the LLM
- **Available Tools** - Stage-appropriate function calls
- **Exit Conditions** - Success criteria to advance

See `src/utils/conversation_state.py:62-108` for implementation.

### Dynamic Instruction System

The agent's instructions update dynamically as the conversation progresses:

1. **Stage Transition** - When a tool advances the workflow stage
2. **Context Injection** - Stage-specific data added to prompt (equipment details, rates, etc.)
3. **Instruction Update** - `agent.update_instructions()` called with new prompt
4. **LLM Refocus** - Model receives updated context for next response

Example: During PRICING_NEGOTIATION, the LLM receives:
```python
{
    'daily_rate': 450.00,
    'max_rate': 500.00,
    'negotiation_attempts': 1,
    'max_attempts': 3
}
```

This enables contextual responses without bloating the initial prompt.

See `src/agents/rental_agent.py:61-71` for implementation.

## Workflow Stages

### 1. Greeting
**Goal:** Establish contact and identify customer needs

**LLM Behavior:**
- Warm professional greeting
- Ask what equipment they need
- Request business license number

**Tools Available:** None (conversational stage)

---

### 2. Customer Verification
**Goal:** Validate business license with state authorities

**LLM Behavior:**
- Confirm license number by repeating back
- Call verification service
- Acknowledge business name on success

**Tools Available:**
- `verify_business_license(license_number: str)`

**State Updates:**
- `customer_verified = True`
- `business_license` stored
- `business_name` populated

**Exit:** Advances to EQUIPMENT_DISCOVERY or ends call if verification fails

---

### 3. Equipment Discovery
**Goal:** Help customer find suitable equipment

**LLM Behavior:**
- Understand job requirements through conversation
- Search inventory based on natural language queries
- Present 2-3 relevant options with rates
- Answer capability questions
- Confirm selection

**Tools Available:**
- `search_available_equipment(search_query: str)` - Returns formatted equipment list
- `select_equipment(equipment_id: str)` - Locks in choice

**State Updates:**
- `selected_equipment` stored (full equipment object)
- `equipment_id` stored

**Exit:** Advances to REQUIREMENTS_CONFIRMATION when equipment selected

---

### 4. Requirements Confirmation
**Goal:** Collect job details and verify site safety

**LLM Behavior:**
- Request delivery location address
- Explain equipment requirements (certifications, weight class)
- Call site verification
- Confirm safety approval

**Tools Available:**
- `verify_site_safety(job_address: str)`

**Context Provided:**
- Selected equipment name
- Required operator certification
- Equipment weight class

**State Updates:**
- `job_address` stored
- `site_verified = True`

**Exit:** Advances to PRICING_NEGOTIATION or ends call if site unsuitable

---

### 5. Pricing Negotiation
**Goal:** Agree on rental rate within acceptable bounds

**LLM Behavior:**
- Present daily rate
- Listen to customer budget/duration
- Negotiate within min/max bounds
- Track negotiation attempts (max 3)
- Accept final price

**Tools Available:**
- `propose_price(proposed_daily_rate: float, rental_days: int)` - Test price point
- `accept_price(confirmed_daily_rate: float)` - Lock in agreed rate

**Context Provided:**
- `daily_rate` - Starting/minimum rate
- `max_rate` - Maximum acceptable rate
- `negotiation_attempts` - Current attempt count
- `max_attempts` - Limit (3)

**State Updates:**
- `agreed_daily_rate` stored
- `rental_days` stored
- `negotiation_attempts` incremented

**Exit:** Advances to OPERATOR_CERTIFICATION or ends call if negotiation fails

---

### 6. Operator Certification
**Goal:** Verify operator has required certifications

**LLM Behavior:**
- Explain certification requirement
- Collect operator name, license, phone
- Call verification service
- Confirm approval

**Tools Available:**
- `verify_operator_credentials(operator_name: str, operator_license: str, operator_phone: str)`

**Context Provided:**
- Required certification type (e.g., "Basic Safety Certification")

**State Updates:**
- `operator_name` stored
- `operator_license` stored
- `operator_phone` stored
- `operator_verified = True`

**Exit:** Advances to INSURANCE_VERIFICATION or ends call if credentials invalid

---

### 7. Insurance Verification
**Goal:** Ensure adequate insurance coverage

**LLM Behavior:**
- Explain minimum insurance requirement
- Collect policy number
- Call verification service
- Confirm coverage approval

**Tools Available:**
- `verify_insurance_coverage(policy_number: str)`

**Context Provided:**
- Minimum insurance amount (e.g., "$500,000")

**State Updates:**
- `insurance_policy` stored
- `insurance_verified = True`

**Exit:** Advances to BOOKING_COMPLETION or ends call if coverage insufficient

---

### 8. Booking Completion
**Goal:** Finalize rental and update inventory

**LLM Behavior:**
- Confirm all details
- Call booking function
- Provide booking reference number
- Summarize rental details (equipment, dates, rates, location)
- Mention email confirmation
- Offer additional assistance
- Thank customer

**Tools Available:**
- `complete_booking()` - Atomic inventory update
- `end_call(reason: str)` - Graceful termination

**State Updates:**
- `booking_confirmed = True`
- `booking_reference` generated
- Equipment status → "RENTED"

**Exit:** Ends call with confirmation details

## Function Tools API

### Customer Verification

#### `verify_business_license(license_number: str)`
Verifies business license with state authorities.

**Parameters:**
- `license_number` - Business license provided by customer

**Returns:**
- Success: `"Business license verified. Customer: {business_name}"`
- Failure: `"License verification failed. Cannot proceed with rental."`

**Side Effects:**
- Updates `state.business_license`
- Updates `state.business_name`
- Sets `state.customer_verified = True`
- Advances stage on success
- Ends call on failure

---

### Equipment Discovery

#### `search_available_equipment(search_query: str)`
Searches inventory based on natural language query.

**Parameters:**
- `search_query` - Natural language description (e.g., "generator for event", "projector under $400")

**Returns:**
Formatted list of available equipment with:
- Equipment ID
- Name
- Category
- Daily rate
- Operator certification required
- Storage location

**Example:**
```
Found 3 available items:

ITM001 - Professional Generator (8000W capacity)
  Category: Power Equipment | Daily: $450 | Cert: Basic Safety
  Location: Warehouse A

ITM003 - HD Projector (4K, 5000 lumens)
  Category: AV Equipment | Daily: $275 | Cert: None
  Location: Yard B
```

---

#### `select_equipment(equipment_id: str)`
Selects specific equipment by ID.

**Parameters:**
- `equipment_id` - Equipment identifier (e.g., "EQ001")

**Returns:**
- Success: `"Selected: {name} at ${rate}/day. Location: {location}"`
- Not found: `"Equipment {id} not found."`
- Unavailable: `"Equipment {id} is not available (Status: {status})."`

**Side Effects:**
- Stores full equipment object in `state.selected_equipment`
- Updates `state.equipment_id`
- Advances stage

---

### Site Verification

#### `verify_site_safety(job_address: str)`
Verifies delivery location can safely accommodate equipment.

**Parameters:**
- `job_address` - Job site address

**Returns:**
- Success: `"Site verified for {weight_class} equipment at {address}."`
- Failure: `"Site does not meet safety requirements. Cannot proceed."`

**Side Effects:**
- Updates `state.job_address`
- Sets `state.site_verified = True`
- Advances stage on success
- Ends call on failure

---

### Pricing

#### `propose_price(proposed_daily_rate: float, rental_days: int = 1)`
Tests a price point during negotiation.

**Parameters:**
- `proposed_daily_rate` - Proposed rate per day
- `rental_days` - Rental duration (default: 1)

**Returns:**
- Too low: `"Rate ${rate}/day is below our minimum of ${min}/day. Can you work with a higher rate?"`
- Too high: `"Rate ${rate}/day exceeds our maximum of ${max}/day."`
- Acceptable: `"Rate of ${rate}/day for {days} days is acceptable. Total would be ${total}. Please confirm this rate to proceed."`
- Max attempts: `"Cannot negotiate below ${min}/day. Maximum attempts reached. Thank you for your interest."`

**Side Effects:**
- Increments `state.negotiation_attempts`
- Updates `state.rental_days`
- Ends call if max attempts exceeded

---

#### `accept_price(confirmed_daily_rate: float)`
Locks in agreed rental rate.

**Parameters:**
- `confirmed_daily_rate` - Final agreed rate

**Returns:**
`"Price confirmed at ${rate}/day. Total cost: ${total}. Now let's verify your operator credentials."`

**Side Effects:**
- Updates `state.agreed_daily_rate`
- Advances stage

---

### Operator Certification

#### `verify_operator_credentials(operator_name: str, operator_license: str, operator_phone: str)`
Verifies operator has required certifications.

**Parameters:**
- `operator_name` - Operator's full name
- `operator_license` - License/certification number
- `operator_phone` - Contact phone number

**Returns:**
- Success: `"Operator {name} verified for {cert_type}. Phone: {phone}"`
- Failure: `"Operator credentials could not be verified. Cannot proceed with rental."`

**Side Effects:**
- Updates `state.operator_name`
- Updates `state.operator_license`
- Updates `state.operator_phone`
- Sets `state.operator_verified = True`
- Advances stage on success
- Ends call on failure

---

### Insurance

#### `verify_insurance_coverage(policy_number: str)`
Verifies insurance meets minimum requirements.

**Parameters:**
- `policy_number` - Insurance policy number

**Returns:**
- Success: `"Insurance policy {number} verified with ${amount} coverage."`
- Failure: `"Insurance coverage is insufficient. Cannot proceed with rental."`

**Side Effects:**
- Updates `state.insurance_policy`
- Sets `state.insurance_verified = True`
- Advances stage on success
- Ends call on failure

---

### Booking

#### `complete_booking()`
Finalizes rental and updates inventory atomically.

**Parameters:** None

**Returns:**
- Success: Detailed confirmation with booking reference, equipment details, rates, location
- Race condition: `"Sorry, {equipment} was just booked by another customer. Let me show you alternatives."`

**Side Effects:**
- Equipment status → "RENTED" (atomic CSV update)
- Generates `state.booking_reference`
- Sets `state.booking_confirmed = True`

**Race Condition Handling:**
This function performs an atomic check-and-update on the CSV file. If another agent has rented the equipment between selection and booking, the operation fails gracefully and suggests alternatives.

---

#### `end_call(reason: str = "completed")`
Gracefully ends the conversation.

**Parameters:**
- `reason` - End reason code (e.g., "completed", "failed_verification", "no_equipment")

**Returns:**
`"Thank you for contacting Easy Inventory Rentals. Have a great day!"`

**Side Effects:**
- Updates `state.stage = CALL_ENDED`
- Stores end reason in `state.context_data['end_reason']`

## Installation & Setup

### Prerequisites

- Python 3.13+
- LiveKit Cloud account
- OpenAI API key with Realtime API access
- (Optional) Twilio phone number for inbound calls
- (Optional) Google Sheets API credentials

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/AuthorizationRentals.git
cd AuthorizationRentals

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Optional: Google Sheets Integration
GOOGLE_SHEETS_CREDENTIALS_PATH=/path/to/credentials.json
GOOGLE_SHEETS_ID=your-spreadsheet-id
```

### Running Locally

```bash
# Start agent in development mode
python main.py dev

# View logs with debug level
python main.py dev --log-level DEBUG
```

The agent will connect to LiveKit and wait for incoming calls.

### Testing

```bash
# Test individual services
python test_services.py

# Simulate full conversation flow
python test_conversation.py

# Test with LiveKit Playground
# 1. Run: python main.py dev
# 2. Open LiveKit Console → Agents → Playground
# 3. Select your agent and start conversation
```

## Configuration

### Equipment Inventory

Edit `data/equipment_inventory.csv` to manage inventory:

```csv
Equipment ID,Equipment Name,Category,Daily Rate,Max Rate,Status,Operator Cert Required,Min Insurance,Storage Location,Weight Class
ITM001,Professional Generator,Power Equipment,450.00,500.00,AVAILABLE,Basic Safety,500000,Warehouse A,Medium
ITM002,HD Projector,AV Equipment,275.00,325.00,AVAILABLE,None,250000,Yard B,Light
```

**Fields:**
- `Equipment ID` - Unique identifier
- `Equipment Name` - Display name
- `Category` - Equipment category (for search matching)
- `Daily Rate` - Minimum acceptable daily rate
- `Max Rate` - Maximum negotiable rate
- `Status` - AVAILABLE | RENTED | MAINTENANCE
- `Operator Cert Required` - Required certification (or "None")
- `Min Insurance` - Minimum insurance coverage required
- `Storage Location` - Pickup location
- `Weight Class` - Light | Medium | Heavy

### Voice Configuration

Modify agent voice settings in `main.py:56-61`:

```python
llm=openai.realtime.RealtimeModel(
    model="gpt-realtime",
    voice="sage",              # Options: alloy, echo, fable, onyx, nova, shimmer, sage
    temperature=0.7,           # 0.0-1.0 (higher = more creative)
    modalities=["audio", "text"],
)
```

### Negotiation Settings

Adjust negotiation limits in `src/utils/conversation_state.py:42-43`:

```python
negotiation_attempts: int = 0
max_negotiation_attempts: int = 3  # Increase to allow more attempts
```

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t authorizationrentals .

# Run container
docker run -d \
  --env-file .env \
  --name rental-agent \
  authorizationrentals
```

### Cloud Deployment (Render)

The project includes `render.yaml` for one-click deployment:

1. Push to GitHub
2. Connect repository to Render
3. Add environment variables in Render dashboard
4. Deploy

Render will automatically:
- Build Docker image
- Set up health checks
- Scale workers based on load
- Handle restarts on failure

### Production Checklist

- [ ] Replace placeholder verification services with real API integrations
- [ ] Migrate from CSV to production database (PostgreSQL, MongoDB, etc.)
- [ ] Add structured logging with log aggregation (e.g., Datadog, CloudWatch)
- [ ] Implement retry logic with exponential backoff for external API calls
- [ ] Add health check endpoint for container orchestration
- [ ] Configure environment variable validation on startup
- [ ] Set up monitoring and alerting (uptime, error rates, booking conversion)
- [ ] Add rate limiting for external API calls
- [ ] Implement graceful shutdown handling
- [ ] Add input validation for all function tool parameters
- [ ] Set up backup strategy for inventory data
- [ ] Configure secrets management (AWS Secrets Manager, Vault, etc.)

## Development

### Adding New Workflow Stages

1. **Add stage to enum** (`src/utils/conversation_state.py:6-16`):
```python
class WorkflowStage(Enum):
    # ... existing stages ...
    NEW_STAGE = "new_stage"
```

2. **Add validation logic** (`src/utils/conversation_state.py:62-85`):
```python
elif self.stage == WorkflowStage.NEW_STAGE:
    return self.new_requirement_met
```

3. **Add to stage order** (`src/utils/conversation_state.py:92-101`):
```python
stage_order = [
    # ... existing stages ...
    WorkflowStage.NEW_STAGE,
    # ... remaining stages ...
]
```

4. **Create stage prompt** (`src/utils/prompts.py:23-138`):
```python
WorkflowStage.NEW_STAGE: """
CURRENT STAGE: New Stage Name

Your goals:
1. Goal one
2. Goal two
"""
```

5. **Add function tools** to `RentalAgent` with `@llm.function_tool()` decorator

### Adding New Function Tools

```python
@llm.function_tool()
async def your_new_tool(self, param: str):
    """
    Tool description for the LLM.

    Args:
        param: Parameter description
    """
    logger.info(f"Calling new tool: {param}")

    # Business logic here
    result = await self.some_service.do_something(param)

    if result:
        self.state.some_field = param
        self.state.advance_stage()
        await self._update_instructions()
        return "Success message for LLM to speak"
    else:
        self.state.end_call("failure_reason")
        return "Failure message for LLM to speak"
```

Register tool in `main.py:44-54`:
```python
tools=[
    # ... existing tools ...
    rental_agent.your_new_tool,
]
```

### Code Style

- Follow PEP 8 style guide
- Use type hints for function parameters and returns
- Document all functions with docstrings
- Log important state changes and API calls
- Keep functions focused and single-purpose

### Testing Best Practices

- Test each workflow stage independently
- Mock external API calls in unit tests
- Test race conditions for booking flow
- Verify state transitions follow validation rules
- Test error handling for failed verifications

## Troubleshooting

### Agent Not Connecting to LiveKit

**Symptoms:** Agent starts but doesn't appear in LiveKit Console

**Solutions:**
- Verify `LIVEKIT_URL` format: `wss://your-project.livekit.cloud`
- Check `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` are correct
- Ensure no firewall blocking WebSocket connections
- Check logs for authentication errors

---

### Function Tools Not Being Called

**Symptoms:** LLM talks about using tools but doesn't actually call them

**Solutions:**
- Verify tools are registered in `main.py:44-54`
- Check function docstrings are clear and descriptive
- Increase temperature for more decisive behavior
- Review logs for OpenAI API errors

---

### CSV File Locking / Corruption

**Symptoms:** Equipment status not updating, concurrent booking errors

**Solutions:**
- Ensure only one agent instance running locally (CSV doesn't support concurrent writes)
- Check file permissions on `data/equipment_inventory.csv`
- For production: Migrate to proper database (PostgreSQL, MongoDB)
- Verify no external processes have file open

---

### Agent Repeating or Looping

**Symptoms:** Agent asks same question multiple times or doesn't progress

**Solutions:**
- Check stage validation logic in `conversation_state.py:62-85`
- Verify `advance_stage()` is called after successful tool execution
- Review stage prompts for conflicting instructions
- Check if tool return messages clearly indicate success/failure

---

### Stage Transitions Not Working

**Symptoms:** Agent stuck on same stage despite meeting requirements

**Solutions:**
- Verify `await self._update_instructions()` is called after stage advancement
- Check `can_proceed_to_next_stage()` logic for current stage
- Ensure state fields are being updated correctly (e.g., `customer_verified = True`)
- Review logs for stage transition attempts

---

### Environment Variables Not Loading

**Symptoms:** Agent crashes on startup with KeyError or None values

**Solutions:**
- Verify `.env` file exists in project root
- Check `load_dotenv()` is called before accessing environment variables
- Use `os.getenv("VAR", "default")` instead of `os.environ["VAR"]`
- For Docker: Ensure environment variables passed with `--env-file` or `-e`

---

### Debug Mode

Enable verbose logging to diagnose issues:

```bash
python main.py dev --log-level DEBUG
```

Check logs for:
- Stage transitions
- Function tool calls
- API responses
- State updates

## Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Follow code style** guidelines (PEP 8)
3. **Add tests** for new features
4. **Update documentation** for API changes
5. **Submit pull request** with clear description

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test
python test_services.py
python test_conversation.py

# Commit with clear messages
git commit -m "Add: Brief description of changes"

# Push and create PR
git push origin feature/your-feature-name
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with:
- [LiveKit](https://livekit.io/) - Real-time voice infrastructure
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime) - Voice-native LLM
- [Python AsyncIO](https://docs.python.org/3/library/asyncio.html) - Async runtime

## Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting guide above

---

**Built for production voice agent workflows.**
