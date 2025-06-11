# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
import os
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import fastapi.exceptions
from pydantic import BaseModel
from datetime import datetime, timedelta

# Define the FastAPI app
app = FastAPI()

# Add CORS middleware for frontend API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model cache to avoid frequent API calls
model_cache = {
    "data": None,
    "last_updated": None,
    "cache_duration": timedelta(hours=1)  # Cache for 1 hour
}

class ModelInfo(BaseModel):
    """Model information from OpenRouter API"""
    id: str
    name: str
    description: Optional[str] = None
    context_length: Optional[int] = None
    pricing: Optional[Dict[str, Any]] = None
    architecture: Optional[Dict[str, Any]] = None

async def fetch_openrouter_models() -> List[ModelInfo]:
    """Fetch available models from OpenRouter API with caching"""
    global model_cache

    # Check if cache is still valid
    if (model_cache["data"] is not None and
        model_cache["last_updated"] is not None and
        datetime.now() - model_cache["last_updated"] < model_cache["cache_duration"]):
        print("Returning cached models")
        return model_cache["data"]

    print("Fetching models from OpenRouter API...")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://openrouter.ai/api/v1/models")
            response.raise_for_status()

            data = response.json()
            models = []

            # Process and filter models
            for model_data in data.get("data", []):
                # Filter out models that might not be suitable or available
                if model_data.get("id") and model_data.get("name"):
                    model_info = ModelInfo(
                        id=model_data["id"],
                        name=model_data["name"],
                        description=model_data.get("description", ""),
                        context_length=model_data.get("context_length"),
                        pricing=model_data.get("pricing"),
                        architecture=model_data.get("architecture")
                    )
                    models.append(model_info)

            # Update cache
            model_cache["data"] = models
            model_cache["last_updated"] = datetime.now()

            print(f"Successfully fetched {len(models)} models from OpenRouter")
            return models

    except Exception as e:
        print(f"Error fetching models from OpenRouter: {e}")
        # Return cached data if available, otherwise return default models
        if model_cache["data"] is not None:
            print("Returning cached models due to API error")
            return model_cache["data"]
        else:
            # Return some default models as fallback
            print("Returning default models as fallback")
            return [
                ModelInfo(
                    id="deepseek/deepseek-r1-0528:free",
                    name="DeepSeek R1 (Free)",
                    description="DeepSeek R1 model with free tier access",
                    context_length=128000
                ),
                ModelInfo(
                    id="openai/gpt-4o-mini",
                    name="GPT-4o Mini",
                    description="OpenAI's efficient GPT-4o mini model",
                    context_length=128000
                ),
                ModelInfo(
                    id="anthropic/claude-3.5-sonnet",
                    name="Claude 3.5 Sonnet",
                    description="Anthropic's Claude 3.5 Sonnet model",
                    context_length=200000
                )
            ]

@app.get("/api/models", response_model=List[ModelInfo])
async def get_available_models():
    """Get list of available models from OpenRouter"""
    try:
        models = await fetch_openrouter_models()
        return models
    except Exception as e:
        print(f"Error in get_available_models endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available models")


def create_frontend_router(build_dir="../frontend/dist"):
    """Creates a router to serve the React frontend.

    Args:
        build_dir: Path to the React build directory relative to this file.

    Returns:
        A Starlette application serving the frontend.
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir
    static_files_path = build_path / "assets"  # Vite uses 'assets' subdir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: Frontend build directory not found or incomplete at {build_path}. Serving frontend will likely fail."
        )
        # Return a dummy router if build isn't ready
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "Frontend not built. Run 'npm run build' in the frontend directory.",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    build_dir = pathlib.Path(build_dir)

    react = FastAPI(openapi_url="")
    react.mount(
        "/assets", StaticFiles(directory=static_files_path), name="static_assets"
    )

    @react.get("/{path:path}")
    async def handle_catch_all(request: Request, path: str):
        fp = build_path / path
        if not fp.exists() or not fp.is_file():
            fp = build_path / "index.html"
        return fastapi.responses.FileResponse(fp)

    return react


# Mount the frontend under /app to not conflict with the LangGraph API routes
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
