"""Health check server for container orchestration."""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from threading import Thread

logger = logging.getLogger("rental-agent")

app = FastAPI(title="Rental Agent Health Check")


@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "rental-agent",
            "version": "1.0.0"
        }
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Rental Agent Health Check Server"}


def start_health_server(port: int = 8080):
    """Start health check server in background thread."""
    def run():
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

    thread = Thread(target=run, daemon=True)
    thread.start()
    logger.info(f"Health check server started on port {port}")


if __name__ == "__main__":
    # For standalone testing
    uvicorn.run(app, host="0.0.0.0", port=8080)
