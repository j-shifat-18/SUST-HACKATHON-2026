import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, agent

app = FastAPI(
    title="SUST Hackathon 2026 - AI Agent Backend",
    description="FastAPI Backend integrating Supabase Auth/DB and OpenAI Agent SDK",
    version="1.0.0"
)

# Configure CORS Middleware
# In production, specify actual origins instead of ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(agent.router, prefix="/api/agent", tags=["AI Agent"])

@app.get("/", tags=["Health Check"])
async def root():
    return {
        "status": "healthy",
        "service": "SUST Hackathon 2026 AI Agent Backend",
        "message": "FastAPI is running and ready to accept requests."
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
