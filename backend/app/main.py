import os
import re
import shutil
import tempfile
from urllib.parse import quote

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from . import render
from .compiler import compile_tex
from .tandoor_client import TandoorClient

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


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/api/recipe/{recipe_id}")
def get_recipe_pdf(recipe_id: int, payload: dict = Body(...)):
    host = payload.get("host")
    token = payload.get("token")
    if not host or not token:
        raise HTTPException(status_code=400, detail="host and token are required.")

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

    pdf_path = compile_tex(work_dir, tex_filename)
    download_name = f"{_sanitize_filename(recipe_name)}.pdf"

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(download_name)},
        background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
    )


@app.post("/api/recipes/all")
def get_all_recipes_pdf(payload: dict = Body(...)):
    host = payload.get("host")
    token = payload.get("token")
    if not host or not token:
        raise HTTPException(status_code=400, detail="host and token are required.")

    client = TandoorClient(host, token)
    recipe_ids = client.fetch_all_recipe_ids()
    if not recipe_ids:
        raise HTTPException(status_code=404, detail="No recipes found on this Tandoor instance.")

    work_dir = tempfile.mkdtemp(prefix="tandoor_book_")
    pictures_dir = os.path.join(work_dir, "Pictures")
    os.makedirs(pictures_dir, exist_ok=True)
    shutil.copy(CFG_PATH, work_dir)

    tex_parts = [
        render.render_preamble(BABEL_LANG, PDF_AUTHOR, "Rezeptsammlung"),
        render.render_document_start(),
        "\\tableofcontents\n\\clearpage",
    ]
    for recipe_id in recipe_ids:
        recipe = _prepare_recipe(client, recipe_id, work_dir, pictures_dir)
        tex_parts.append(render.render_recipe_fragment(recipe))
        tex_parts.append("\\clearpage")
    tex_parts.append(render.render_document_end())

    tex_filename = "cookbook.tex"
    with open(os.path.join(work_dir, tex_filename), "w", encoding="utf-8") as f:
        f.write("\n".join(tex_parts))

    pdf_path = compile_tex(work_dir, tex_filename)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition("Rezeptsammlung.pdf")},
        background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
    )
