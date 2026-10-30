import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import (
    admin,
    auth,
    cases,
    contacts,
    conversations,
    copilot,
    inbox,
    metrics,
    ops,
    patients,
    webhooks,
)
from app.services.conversations import ConversationError

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(
    title="Atención al Paciente — Centro Médico San Bernardino",
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url=None,
)


@app.exception_handler(ConversationError)
def conversation_error_handler(_: Request, exc: ConversationError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


for router in (
    ops.router,
    auth.router,
    inbox.router,
    conversations.router,
    copilot.router,
    contacts.router,
    patients.router,
    cases.router,
    metrics.router,
    admin.router,
    admin.catalog_router,
    webhooks.router,
):
    app.include_router(router, prefix="/api")
