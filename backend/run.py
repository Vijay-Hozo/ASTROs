#!/usr/bin/env python
"""
Simple server runner for FastAPI backend.
"""
import asyncio
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting FastAPI backend server...")
    try:
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8001,
            reload=False,
            workers=1,
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise
