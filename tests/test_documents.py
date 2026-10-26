"""Integration: Document Service (ТЗ 3.2.7) — Excel, PDF, CSV для Гранд-Смета."""
from __future__ import annotations

import zipfile

from neuro_smetchik.documents import generate
from neuro_smetchik.repository import load_estimate


def test_xlsx_is_valid_and_contains_positions(client, sample_estimate, estimator_headers):
    est = load_estimate(sample_estimate["id"])
    info = generate(est, "xlsx", estimator_headers)
    with zipfile.ZipFile(info["path"]) as z:
        assert "xl/worksheets/sheet1.xml" in z.namelist()
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        assert est["positions"][0]["catalog_id"] in sheet
    r = client.get(f"/api/v1/estimates/{est['id']}/documents/xlsx")
    assert r.status_code == 200 and r.content[:2] == b"PK"


def test_pdf_is_generated_with_cyrillic_font(client, sample_estimate, estimator_headers):
    est = load_estimate(sample_estimate["id"])
    info = generate(est, "pdf", estimator_headers)
    content = open(info["path"], "rb").read()
    assert content.startswith(b"%PDF") and b"DejaVu" in content
    r = client.get(f"/api/v1/estimates/{est['id']}/documents/pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_grand_smeta_csv_export(client, sample_estimate, estimator_headers):
    est = load_estimate(sample_estimate["id"])
    info = generate(est, "grand_smeta_csv", estimator_headers)
    text = open(info["path"], "r", encoding="utf-8-sig").read()
    assert ";" in text and "Обоснование" in text and "ИТОГО" in text
    assert est["positions"][0]["catalog_id"] in text
    r = client.get(f"/api/v1/estimates/{est['id']}/documents/csv")
    assert r.status_code == 200
