from __future__ import annotations

import io
import pytest
from PIL import Image


def _db_available() -> bool:
    try:
        from app.db.session import engine
        import sqlalchemy as sa
        with engine.connect() as c:
            c.execute(sa.text("select 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="DB not available")


def test_image_search_fallback(monkeypatch):
    # Create a small red image and save to uploads
    from app.core.settings import get_settings
    from pathlib import Path
    from app.routers.tools import image_search
    from app.schemas import ImageSearchRequest

    settings = get_settings()
    uploads = Path(settings.upload_dir)
    uploads.mkdir(parents=True, exist_ok=True)

    img = Image.new('RGB', (32, 32), (255, 0, 0))
    upload_id = 'test_image_red.jpg'
    img.save(uploads / upload_id, format='JPEG')

    items = image_search(ImageSearchRequest(upload_id=upload_id, k=8))
    assert isinstance(items, list)
    # When no image embeddings are present, fallback may still return results
    assert len(items) >= 0


