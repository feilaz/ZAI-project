from http import HTTPStatus

import psycopg
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def problem(status, detail, headers=None, errors=None):
    body = {"type": "about:blank", "title": HTTPStatus(status).phrase, "status": status, "detail": detail}
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json", headers=headers)


async def http_error(request: Request, error: HTTPException):
    return problem(error.status_code, error.detail, error.headers)


async def validation_error(request: Request, error: RequestValidationError):
    errors = error.errors()
    status = 422
    if any(item["loc"][0] == "query" or item["type"] == "json_invalid" for item in errors):
        status = 400
    elif any(item["loc"][0] == "path" for item in errors):
        status = 404
    return problem(status, "Invalid request", errors=[
        {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
        for item in errors
    ])


async def database_error(request: Request, error: psycopg.OperationalError):
    return problem(503, "Database unavailable")


async def check_media_types(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        accepted = {}
        for entry in request.headers.get("accept", "*/*").split(","):
            media_type, *parameters = entry.strip().lower().split(";")
            quality = 1.0
            for parameter in parameters:
                if parameter.strip().startswith("q="):
                    try:
                        quality = float(parameter.strip()[2:])
                    except ValueError:
                        quality = 0
            accepted[media_type.strip()] = quality
        response_type = "application/json"
        if request.method == "GET" and request.url.path == "/api/measurements/stream":
            response_type = "text/event-stream"
        category = response_type.split("/")[0] + "/*"
        quality = accepted.get(response_type, accepted.get(category, accepted.get("*/*", 0)))
        if not 0 < quality <= 1:
            return problem(406, f"Only {response_type} responses are available")
        if request.method in {"POST", "PUT", "PATCH"} and await request.body():
            content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type != "application/json":
                return problem(415, "Request body must use application/json")
    return await call_next(request)


def install_error_handlers(app):
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(psycopg.OperationalError, database_error)
    app.middleware("http")(check_media_types)
