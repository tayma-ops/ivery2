"""Only explicitly public frontend files may be served; source and DBs stay private."""

from pathlib import Path
from django.conf import settings
from django.http import Http404
from django.views.static import serve

FRONTEND = settings.BASE_DIR / "."
PUBLIC = {
    "index.html",
    "help.html",
    "contact.html",
    "header.html",
    "footer.html",
    "store-config.js",
    "backend.js",
    "app.js",
    "style.css",
    "styles.css",
}


def frontend(request, path="index.html"):
    pieces = Path(path).parts
    if not pieces or any(p.startswith(".") for p in pieces):
        raise Http404
    if path not in PUBLIC and (
        pieces[0] not in {"assets", "media"}
        or Path(path).suffix.lower()
        not in {
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".mp4",
            ".webm",
            ".ttf",
            ".woff",
            ".woff2",
            ".webp",
            ".css",
            ".js",
        }
    ):
        raise Http404
    return serve(request, path, document_root=FRONTEND)
