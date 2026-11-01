import logging
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()  # .env is git-ignored; see .env.example
from .api.routes import router  # noqa: E402
from .config import MAX_BODY_BYTES, allowed_origins  # noqa: E402
from .errors import ApiError  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
# httpx logs every request URL at INFO, including query strings such as ?api-key=... -> keep it quiet
for _name in ("httpx", "httpcore", "google_genai", "google.genai"):
    logging.getLogger(_name).setLevel(logging.WARNING)
log = logging.getLogger("krishimitra")

app = FastAPI(title="KrishiMitra AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins(),
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


def _err(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.middleware("http")
async def guard(request: Request, call_next):
    if int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES:
        return _err(413, "REQUEST_TOO_LARGE", "Request is too large.")
    rid = uuid.uuid4().hex[:12]
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(ApiError)
async def api_error(_: Request, e: ApiError):
    return _err(e.status, e.code, e.message)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, e: RequestValidationError):
    return _err(422, "VALIDATION_ERROR", "Some inputs are not valid numbers or text. Please check the form.")


@app.exception_handler(Exception)
async def unexpected(_: Request, e: Exception):
    # Genuine bugs are logged with a traceback and reported as such (never disguised as a provider outage)
    log.exception("unhandled error")
    return _err(500, "INTERNAL_ERROR", "Something went wrong on the server. Please try again, and tell the operator if it persists.")


app.include_router(router)
