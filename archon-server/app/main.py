from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import chat, auth, models
from .database.db import engine
from .database.models import Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Archon AI Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(models.router, prefix="/models", tags=["models"])


@app.get("/")
async def root():
    return {"message": "Welcome to Archon AI Server"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
