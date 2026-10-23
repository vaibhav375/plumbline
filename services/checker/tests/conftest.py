import json
from pathlib import Path

import pytest
from PIL import Image

from plumbline import ops
from plumbline.models import Document, OrgContext
from plumbline.parsers import DocBuilder
from plumbline.rules.load import load_seed_dir

SEED = Path(__file__).resolve().parents[3] / "supabase" / "seed" / "aurelle"


@pytest.fixture(autouse=True)
def _fresh_cache():
    ops.clear_cache()


@pytest.fixture(scope="session")
def aurelle() -> OrgContext:
    ctx, errors = load_seed_dir(SEED)
    assert errors == []
    return ctx


@pytest.fixture(scope="session")
def samples() -> dict[str, dict]:
    return {c["key"]: c for c in json.loads((SEED / "contents.json").read_text(encoding="utf-8"))}


def sample_doc(sample: dict) -> Document:
    b = DocBuilder()
    for para in sample["text"].split("\n\n"):
        b.add(para)
    if sample.get("banner"):
        img = Image.open(SEED / sample["banner"])
        b.add_image(img, img.width, img.height, alt_text=None)
    return b.build("text")


@pytest.fixture(scope="session")
def worked_example(samples) -> Document:
    """§4.4: the post text plus its banner (no alt text)."""
    return sample_doc(samples["worked-example"])
