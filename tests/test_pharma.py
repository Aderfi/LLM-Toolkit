"""Pharmacy tools with the HTTP layer faked (no network)."""

from llmtools import aemps, cima, vademecum


def test_cima_search_drug(monkeypatch):
    res = {
        "resultados": [
            {
                "nombre": "IBUPROFENO CINFA 600 mg",
                "nregistro": "123",
                "labtitular": "Cinfa",
                "comerc": True,
                "receta": True,
                "generico": True,
                "psum": True,
            }
        ]
    }
    seen = {}
    monkeypatch.setattr(cima, "get_json", lambda url, **p: seen.update(p) or res)
    out = cima.cima_search_drug(active_ingredient="ibuprofeno")
    assert seen == {"nombre": "", "practiv1": "ibuprofeno", "atc": "", "comerc": 1}
    assert "IBUPROFENO CINFA" in out and "EFG/generic" in out and "supply problem" in out
    assert "Give name" in cima.cima_search_drug()


def test_cima_drug_info_not_found(monkeypatch):
    monkeypatch.setattr(cima, "get_json", lambda url, **p: None)
    assert "Not found in CIMA" in cima.cima_drug_info("654321")


def test_cima_supply_problems_filters_inactive(monkeypatch):
    rows = [
        {"nombre": "ATORVASTATINA X", "cn": "1", "fini": 1700000000000, "activo": True},
        {"nombre": "ATORVASTATINA Y", "cn": "2", "fini": 1700000000000, "activo": False},
    ]
    monkeypatch.setattr(cima, "supply_problems", lambda cn="": rows)
    out = cima.cima_supply_problems(text="atorva")
    assert "1 active problems" in out and "X" in out and "Y (CN" not in out


def test_aemps_alerts_filter(monkeypatch):
    items = [
        {"title": "Retirada de lote", "link": "u1", "date": "Mon, 01 Jan 2026", "summary": ""},
        {"title": "Nota informativa", "link": "u2", "date": "Tue, 02 Jan 2026", "summary": ""},
    ]
    monkeypatch.setattr(aemps, "rss_entries", lambda url=None: items)
    out = aemps.aemps_alerts("retirada")
    assert "u1" in out and "u2" not in out
    assert aemps.aemps_alerts("nothing") == "No matching publications."


def test_international_equivalents_without_matches(monkeypatch):
    monkeypatch.setattr(vademecum, "_spanish_drug", lambda q: None)
    monkeypatch.setattr(vademecum, "rxnorm_search", lambda term: None)
    assert "No RxNorm equivalent" in vademecum.international_equivalents("xyz")
