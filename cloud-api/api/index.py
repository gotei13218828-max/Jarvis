from fastapi import FastAPI

app = FastAPI(
    title="Jarvis Cloud API",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "name": "Jarvis Cloud API",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "jarvis-cloud-api",
    }
