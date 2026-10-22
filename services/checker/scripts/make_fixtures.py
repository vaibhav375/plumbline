"""Build the parser test fixtures in tests/fixtures. Re-run after changing the worked example."""

import io
import shutil
from pathlib import Path

from docx import Document
from docx.shared import Inches
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
BANNER = ROOT.parents[1] / "supabase" / "seed" / "aurelle" / "banner_v1.png"
TEXT = (
    "Meet the NEW Aurelle Vitamin-C serum!!! 100% natural, eco-friendly and clinically proven "
    "to fade dark spots by 60% in just 2 weeks."
)


def text_pdf(lines: list[str]) -> bytes:
    """Smallest valid PDF with a real text layer (Helvetica), offsets computed for the xref."""
    stream = (
        "BT /F1 14 Tf 72 720 Td 18 TL "
        + " ".join(
            "(" + ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") '"
            for ln in lines
        )
        + " ET"
    )
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        " /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, body in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1"))
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    out.writelines(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out.write(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out.getvalue()


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / "empty.txt").write_bytes(b"")
    shutil.copy(BANNER, FIX / "banner_v1.png")

    # DOCX: heading, the claim paragraph, the banner (no alt text) and a logo with alt text.
    doc = Document()
    doc.add_heading("Vitamin C launch post", level=1)
    doc.add_paragraph(TEXT)
    doc.add_picture(str(BANNER), width=Inches(3))
    logo = io.BytesIO()
    Image.new("RGB", (200, 60), "#2D2A27").save(logo, "PNG")
    doc.add_picture(logo, width=Inches(1))
    doc.inline_shapes[1]._inline.docPr.set("descr", "Aurelle logo")
    doc.add_paragraph("Shop the Vitamin C Brightening Serum.")
    doc.save(FIX / "post.docx")

    pdf = text_pdf([TEXT[:70], TEXT[70:]])
    (FIX / "post.pdf").write_bytes(pdf)

    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    writer.encrypt(user_password="secret", owner_password="owner", algorithm="AES-128")
    with (FIX / "encrypted.pdf").open("wb") as f:
        writer.write(f)

    # Scanned PDF: the same words, but only as pixels (no text layer).
    scan = Image.new("RGB", (1240, 400), "white")
    ImageDraw.Draw(scan).text(
        (60, 150), "clinically proven", font=ImageFont.load_default(size=64), fill="black"
    )
    scan.save(FIX / "scanned.pdf", "PDF", resolution=150)

    print("\n".join(sorted(p.name for p in FIX.iterdir())))


if __name__ == "__main__":
    main()
