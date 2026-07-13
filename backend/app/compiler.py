import subprocess

from fastapi import HTTPException


def compile_tex(work_dir: str, tex_filename: str, timeout: int = 180) -> str:
    """Compiles a .tex file with latexmk inside work_dir. Returns path to the resulting PDF."""
    try:
        result = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                tex_filename,
            ],
            cwd=work_dir,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=500, detail="LaTeX compilation timed out.") from exc

    pdf_name = tex_filename.rsplit(".", 1)[0] + ".pdf"
    if result.returncode != 0:
        log_tail = "\n".join(result.stdout.splitlines()[-60:])
        raise HTTPException(
            status_code=500,
            detail=f"LaTeX compilation failed. Last log lines:\n{log_tail}",
        )
    return f"{work_dir}/{pdf_name}"
