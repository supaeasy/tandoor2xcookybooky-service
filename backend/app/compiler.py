import re
import subprocess

from fastapi import HTTPException

_PAGE_COUNT_RE = re.compile(r"Output written on \S+\.pdf \((\d+) pages?")


def compile_tex(work_dir: str, tex_filename: str, timeout: int = 180) -> tuple[str, int | None]:
    """Compiles a .tex file with latexmk inside work_dir.

    Returns (path to the resulting PDF, page count if it could be parsed from
    the log, else None).
    """
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

    # latexmk reruns pdflatex multiple times when hyperref/references need it
    # (e.g. "Rerun to get outlines right"), and each run prints its own
    # "Output written on ..." line - take the LAST one, which reflects the
    # final, settled page count, not an earlier intermediate pass.
    matches = _PAGE_COUNT_RE.findall(result.stdout)
    page_count = int(matches[-1]) if matches else None
    return f"{work_dir}/{pdf_name}", page_count
