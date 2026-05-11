from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import auth, babies, care_logs, health, milestones, reminders

app = FastAPI(
    title=settings.APP_NAME,
    description="BebeRehber ebeveyn rehberi uygulamasının backend API'si",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(babies.router)
app.include_router(care_logs.router)
app.include_router(milestones.router)
app.include_router(reminders.router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "slogan": "Ebeveynliğin dijital rehberi, her an yanınızda.",
        "version": "0.1.0",
    }
