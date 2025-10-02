# Voice-Activated Equipment Rental System

AI-powered voice agent for automating construction equipment rental calls using LiveKit.

## Features

- 🎤 Natural voice conversations with customers
- 📋 7-stage rental workflow automation
- ✅ Real-time verification (license, operator, site, insurance)
- 💰 Intelligent price negotiation
- 📊 CSV-based inventory management
- 🔒 Race condition handling for concurrent bookings
- 📞 Twilio integration for inbound calls

## Setup

### Prerequisites

- Python 3.13+
- LiveKit account
- Twilio phone number (configured with LiveKit SIP)
- API keys: OpenAI, Deepgram, ElevenLabs

### Installation

```bash
# Clone and setup
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Running Locally

```bash
# Start the agent
python main.py dev

# Test conversation flow
python test_conversation.py
```

## Architecture

```
equipment-rental-voice-system/
├── src/
│   ├── agents/
│   │   └── rental_agent.py       # Main voice agent
│   ├── services/
│   │   ├── data_service.py       # CSV inventory management
│   │   └── verification_service.py  # External verifications
│   └── utils/
│       ├── conversation_state.py  # Workflow state machine
│       ├── prompts.py            # Stage-based prompts
│       └── function_tools.py     # LLM function definitions
├── data/
│   └── equipment_inventory.csv   # Equipment database
└── main.py                       # Entry point
```

## Workflow Stages

1. **Greeting** - Initial contact
2. **Customer Verification** - Business license check
3. **Equipment Discovery** - Browse and select equipment
4. **Requirements Confirmation** - Site safety verification
5. **Pricing Negotiation** - Rate negotiation within bounds
6. **Operator Certification** - Verify operator credentials
7. **Insurance Verification** - Check coverage requirements
8. **Booking Completion** - Finalize and update inventory

## Configuration

### Environment Variables

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-secret
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...
```

### Equipment Data

Edit `data/equipment_inventory.csv` to manage inventory:
- Add/remove equipment
- Update rates and availability
- Set operator requirements
- Configure insurance minimums

## Testing

```bash
# Run service tests
python test_services.py

# Simulate full conversation
python test_conversation.py

# Test live with playground
python main.py dev
```

## Deployment

### Local Development
```bash
python main.py dev
```

### Production (Cloud)
```bash
# Deploy to your cloud provider
# Ensure LIVEKIT_URL points to production server
python main.py start
```

## Key Design Decisions

- **Stage-based prompts**: Each workflow stage has focused instructions
- **Late race condition check**: Only validate availability at final booking
- **Function calling**: LLM decides when to call verification APIs
- **Natural language matching**: Let AI match customer needs to equipment
- **Atomic CSV updates**: Single lock for status changes

## Troubleshooting

**Agent not connecting:**
- Check LIVEKIT credentials in .env
- Verify agent name matches Twilio config

**CSV not updating:**
- Check file permissions
- Ensure only one agent instance running locally

**Function calls failing:**
- Check OpenAI API key
- Review logs: `python main.py dev --log-level DEBUG`

## License

MIT

