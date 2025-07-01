"""
Entrypoint for launching the FastAPI TradeSphere backend with uvicorn.

This script ensures application can be run directly with:
    python -m api
or
    python src/api/__main__.py

It loads the FastAPI app from main.py and starts a production-ready server.
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
