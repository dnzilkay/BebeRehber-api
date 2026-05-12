from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import (
    admin,
    albums,
    auth,
    babies,
    baby_members,
    care_logs,
    community,
    export,
    health,
    journal_entries,
    media,
    milestones,
    reminders,
    social,
    timeline,
)

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
app.include_router(albums.router)
app.include_router(journal_entries.router)
app.include_router(media.router)
app.include_router(timeline.router)
app.include_router(export.router)
app.include_router(baby_members.baby_router)
app.include_router(baby_members.invites_router)
app.include_router(community.router)
app.include_router(admin.router)
app.include_router(social.router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "slogan": "Ebeveynliğin dijital rehberi, her an yanınızda.",
        "version": "0.1.0",
    }
