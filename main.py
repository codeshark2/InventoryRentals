import asyncio
import logging
import os
from dotenv import load_dotenv

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
    Agent,
    AgentSession,
)
from livekit.plugins import openai

from src.agents.rental_agent import RentalAgent
from health_server import start_health_server

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rental-agent")


def validate_environment():
    """Validate required environment variables on startup."""
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY"
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        error_msg = f"Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info("Environment validation passed")


async def entrypoint(ctx: JobContext):
    """Entry point for each call session."""
    
    logger.info(f"Starting new rental agent session - Room: {ctx.room.name}")
    
    # Initialize rental agent state
    rental_agent = RentalAgent()
    
    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to room")
    
    # Get initial instructions
    initial_instructions = rental_agent.get_current_instructions()
    
    # Create Agent configuration
    agent = Agent(
        instructions=initial_instructions,
        tools=[
            rental_agent.verify_business_license,
            rental_agent.search_available_equipment,
            rental_agent.select_equipment,
            rental_agent.verify_site_safety,
            rental_agent.propose_price,
            rental_agent.accept_price,
            rental_agent.verify_operator_credentials,
            rental_agent.verify_insurance_coverage,
            rental_agent.complete_booking,
            rental_agent.end_call,
        ],
        llm=openai.realtime.RealtimeModel(
            model="gpt-realtime",
            voice="sage",
            temperature=0.7,
            modalities=["audio", "text"],
        ),
    )
    
    # Store agent reference
    rental_agent.set_agent(agent)
    
    logger.info("Agent configured, creating session...")
    
    # Create and start AgentSession (uses Agent's configuration)
    session = AgentSession()
    
    # Start the session with the agent and room
    await session.start(agent, room=ctx.room)

    logger.info("AgentSession started and running!")

if __name__ == "__main__":
    # Validate environment before starting
    validate_environment()

    # Start health check server
    start_health_server(port=int(os.getenv("HEALTH_PORT", "8080")))

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="rental-agent",
        )
    )

