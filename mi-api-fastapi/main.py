from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


# Endpoint principal    
@app.get("/")
def hello():
    return {
        "status": "ok",
        "message": "Pipeline CI/CD funcionando",
        "env": "dev"
    }


# Smoke test endpoint
@app.get("/health")
def health():
    return JSONResponse(
        content={"status": "healthy"},
        status_code=200
    )