import logging
import os
import re
import shutil
import sys
import tempfile
import threading
import uuid
from urllib.parse import quote

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from . import render
from .compiler import compile_tex
from .tandoor_client import TandoorClient

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tandoor2xcookybooky")

app = FastAPI(title="Tandoor2xcookybooky-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CFG_PATH = "/app/xcookybooky.cfg"
BABEL_LANG = os.environ.get("LATEX_BABEL_LANG", "nswissgerman")
PDF_AUTHOR = os.environ.get("LATEX_PDF_AUTHOR", "Tandoor")


def _sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "-", name).strip()
    return name or "recipe"


def _content_disposition(filename: str) -> str:
    ascii_fallback = filename.encode("ascii", "ignore").decode("ascii") or "recipe.pdf"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


def _prepare_recipe(client: TandoorClient, recipe_id: int, work_dir: str, pictures_dir: str) -> dict:
    recipe = client.fetch_recipe(recipe_id)
    image = client.download_image(recipe)
    if image:
        image_bytes, extension = image
        image_filename = f"{recipe_id}.{extension}"
        with open(os.path.join(pictures_dir, image_filename), "wb") as f:
            f.write(image_bytes)
        recipe["image_file"] = image_filename
    else:
        recipe["image_file"] = None
    return recipe


MIN_FONT_SIZE_PT = 6


def _find_fitting_font_size(work_dir: str, recipe: dict, recipe_id) -> float | None:
    """xcookybooky can't break a recipe across pages (wrapfigure limitation),
    so a too-long recipe would push its trailing hint box onto an otherwise
    empty extra page. Test-compile the recipe standalone, first at the normal
    size, then - only if that doesn't fit - with the ingredients/preparation
    text shrunk 1pt at a time (via \\changefontsizes) until it fits on one
    page or MIN_FONT_SIZE_PT is reached."""
    recipe_name = recipe.get("name") or f"Recipe {recipe_id}"

    def compiles_on_one_page(font_size_pt):
        tex_parts = [
            render.render_preamble(BABEL_LANG, PDF_AUTHOR, recipe_name),
            render.render_document_start(),
            render.render_recipe_fragment(recipe, font_size_pt),
            render.render_document_end(),
        ]
        tex_filename = f"sizetest_{recipe_id}.tex"
        with open(os.path.join(work_dir, tex_filename), "w", encoding="utf-8") as f:
            f.write("\n".join(tex_parts))
        try:
            _, page_count = compile_tex(work_dir, tex_filename, timeout=60)
        except HTTPException:
            return False  # unlikely to be size-related, but don't let it kill the whole job
        logger.info("Recipe %s: font_size=%s -> %s page(s)", recipe_id, font_size_pt or "default", page_count)
        return page_count == 1

    if compiles_on_one_page(None):
        return None

    font_size_pt = 10
    while font_size_pt >= MIN_FONT_SIZE_PT:
        if compiles_on_one_page(font_size_pt):
            return font_size_pt
        font_size_pt -= 1
    return MIN_FONT_SIZE_PT


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/recipe/{recipe_id}")
def get_recipe_pdf(recipe_id: int, payload: dict = Body(...)):
    host = payload.get("host")
    token = payload.get("token")
    if not host or not token:
        raise HTTPException(status_code=400, detail="host and token are required.")

    logger.info("Recipe %s: fetching from %s", recipe_id, host)
    client = TandoorClient(host, token)
    work_dir = tempfile.mkdtemp(prefix="tandoor_pdf_")
    pictures_dir = os.path.join(work_dir, "Pictures")
    os.makedirs(pictures_dir, exist_ok=True)
    shutil.copy(CFG_PATH, work_dir)

    recipe = _prepare_recipe(client, recipe_id, work_dir, pictures_dir)
    recipe_name = recipe.get("name") or f"Recipe {recipe_id}"

    tex_parts = [
        render.render_preamble(BABEL_LANG, PDF_AUTHOR, recipe_name),
        render.render_document_start(),
        render.render_recipe_fragment(recipe),
        render.render_document_end(),
    ]
    tex_filename = "recipe.tex"
    with open(os.path.join(work_dir, tex_filename), "w", encoding="utf-8") as f:
        f.write("\n".join(tex_parts))

    logger.info("Recipe %s (%s): compiling PDF", recipe_id, recipe_name)
    pdf_path, _ = compile_tex(work_dir, tex_filename)
    logger.info("Recipe %s (%s): done, sending PDF", recipe_id, recipe_name)
    download_name = f"{_sanitize_filename(recipe_name)}.pdf"

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(download_name)},
        background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
    )


# In-memory job tracking for the (potentially long-running) collected PDF
# build, so the extension can poll for progress instead of just waiting on
# one blocking request. Fine for a single-container, personal-use service.
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _set_job(job_id: str, **fields) -> None:
    with JOBS_LOCK:
        JOBS.setdefault(job_id, {}).update(fields)


def _run_all_recipes_job(job_id: str, host: str, token: str) -> None:
    try:
        _set_job(job_id, status="fetching_list", current=0, total=0)
        logger.info("Job %s: fetching recipe list from %s", job_id, host)
        client = TandoorClient(host, token)
        recipe_ids = client.fetch_all_recipe_ids()
        if not recipe_ids:
            _set_job(job_id, status="error", detail="No recipes found on this Tandoor instance.")
            return
        logger.info("Job %s: %d recipes found", job_id, len(recipe_ids))
        _set_job(job_id, status="fetching", total=len(recipe_ids))

        work_dir = tempfile.mkdtemp(prefix="tandoor_book_")
        pictures_dir = os.path.join(work_dir, "Pictures")
        os.makedirs(pictures_dir, exist_ok=True)
        shutil.copy(CFG_PATH, work_dir)

        tex_parts = [
            render.render_preamble(BABEL_LANG, PDF_AUTHOR, "Rezeptsammlung"),
            render.render_document_start(),
            "\\tableofcontents\n\\clearpage",
        ]
        for index, recipe_id in enumerate(recipe_ids, start=1):
            logger.info("Job %s: fetching recipe %d/%d (id=%s)", job_id, index, len(recipe_ids), recipe_id)
            _set_job(job_id, current=index)
            recipe = _prepare_recipe(client, recipe_id, work_dir, pictures_dir)
            font_size_pt = _find_fitting_font_size(work_dir, recipe, recipe_id)
            if font_size_pt:
                logger.info(
                    "Job %s: recipe %s doesn't fit on one page at normal size, "
                    "shrinking ingredients/preparation to %dpt",
                    job_id, recipe_id, font_size_pt,
                )
            tex_parts.append(render.render_recipe_fragment(recipe, font_size_pt))
            tex_parts.append("\\clearpage")
        tex_parts.append(render.render_document_end())

        tex_filename = "cookbook.tex"
        with open(os.path.join(work_dir, tex_filename), "w", encoding="utf-8") as f:
            f.write("\n".join(tex_parts))

        logger.info("Job %s: compiling %d recipes", job_id, len(recipe_ids))
        _set_job(job_id, status="compiling")
        pdf_path, _ = compile_tex(work_dir, tex_filename, timeout=900)
        logger.info("Job %s: done", job_id)
        _set_job(job_id, status="done", pdf_path=pdf_path, work_dir=work_dir)
    except HTTPException as exc:
        logger.error("Job %s failed: %s", job_id, exc.detail)
        _set_job(job_id, status="error", detail=str(exc.detail))
    except Exception as exc:  # noqa: BLE001 - report any failure back to the client
        logger.exception("Job %s failed", job_id)
        _set_job(job_id, status="error", detail=str(exc))


@app.post("/api/recipes/all/start")
def start_all_recipes_job(payload: dict = Body(...)):
    host = payload.get("host")
    token = payload.get("token")
    if not host or not token:
        raise HTTPException(status_code=400, detail="host and token are required.")

    job_id = uuid.uuid4().hex
    _set_job(job_id, status="queued", current=0, total=0)
    thread = threading.Thread(target=_run_all_recipes_job, args=(job_id, host, token), daemon=True)
    thread.start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Unknown job id.")
        return {k: v for k, v in job.items() if k not in ("pdf_path", "work_dir")}


@app.get("/api/jobs/{job_id}/download")
def download_job_pdf(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or job.get("status") != "done":
            raise HTTPException(status_code=409, detail="Job is not finished yet.")
        pdf_path = job["pdf_path"]
        work_dir = job["work_dir"]

    def cleanup():
        shutil.rmtree(work_dir, ignore_errors=True)
        with JOBS_LOCK:
            JOBS.pop(job_id, None)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition("Rezeptsammlung.pdf")},
        background=BackgroundTask(cleanup),
    )
