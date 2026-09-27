from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Files that must be revalidated on every load so new releases reach users.
NO_CACHE = {"index.html", "sw.js", "manifest.webmanifest"}


def mount_frontend(app: FastAPI, dist: Path) -> None:
    """Serve the built single-page app; register after the API routes so those take priority."""
    dist = dist.resolve()
    index = dist / "index.html"

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist):
            headers = {"Cache-Control": "no-cache"} if candidate.name in NO_CACHE else None
            return FileResponse(candidate, headers=headers)
        # Client-side routes (/diet, /progress, …) all load the app shell.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
