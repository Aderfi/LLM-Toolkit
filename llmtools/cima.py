"""CIMA (AEMPS): authorised medicines in Spain, supply problems, registry changes and notes.

Public REST API: https://cima.aemps.es/cima/rest/
(documentation: "CIMA REST API" on the AEMPS website). Query parameters and response
fields are the API's own (Spanish) names.
"""

from datetime import date, datetime, timedelta

from ._http import get_json
from .core import tool

CIMA = "https://cima.aemps.es/cima/rest"
CHANGE_TYPE = {1: "new", 2: "withdrawn", 3: "modified"}


def _date(ms: int | None) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%d/%m/%Y") if ms else "?"


def get_drug(ref: str) -> dict | None:
    """Full record by national code (6-7 digits) or registration number."""
    ref = ref.strip()
    key = "cn" if ref.isdigit() and len(ref) in (6, 7) else "nregistro"
    return get_json(f"{CIMA}/medicamento", **{key: ref})


def search(**params) -> list[dict]:
    data = get_json(f"{CIMA}/medicamentos", **params) or {}
    return data.get("resultados", [])


def supply_problems(cn: str = "") -> list[dict]:
    """All pages of supply problems (or those of one national code)."""
    if cn:
        return (get_json(f"{CIMA}/psuministro/{cn}") or {}).get("resultados", [])
    out, page = [], 1
    while True:
        data = get_json(f"{CIMA}/psuministro", pagina=page) or {}
        res = data.get("resultados", [])
        out.extend(res)
        if not res or len(out) >= data.get("totalFilas", 0) or page >= 20:
            return out
        page += 1


def registry_changes(since: date, max_pages: int = 30) -> list[dict]:
    """Registry changes since ``since`` (new, withdrawn and modified)."""
    out, page = [], 1
    while page <= max_pages:
        data = (
            get_json(f"{CIMA}/registroCambios", fecha=since.strftime("%d/%m/%Y"), pagina=page) or {}
        )
        res = data.get("resultados", [])
        out.extend(res)
        if not res or len(out) >= data.get("totalFilas", 0):
            break
        page += 1
    return out


def _drug_line(m: dict) -> str:
    flags = [
        "marketed" if m.get("comerc") else "not marketed",
        "prescription" if m.get("receta") else "no prescription",
    ]
    if m.get("generico"):
        flags.append("EFG/generic")
    if m.get("psum"):
        flags.append("⚠ supply problem")
    return (
        f"- {m.get('nombre')} (nreg {m.get('nregistro')}, {m.get('labtitular')}; "
        f"{', '.join(flags)})"
    )


@tool
def cima_search_drug(
    name: str = "",
    active_ingredient: str = "",
    atc: str = "",
    marketed_only: bool = True,
    max_results: int = 10,
) -> str:
    """Search medicines authorised in Spain (CIMA) by name, active ingredient or ATC code.

    Args:
        name: Brand name or part of it, e.g. 'ibuprofeno cinfa'.
        active_ingredient: Active ingredient name (Spanish), e.g. 'paracetamol'.
        atc: ATC code, e.g. 'N02BE01'.
        marketed_only: If True, only medicines currently marketed.
        max_results: Maximum number of results.
    """
    if not (name or active_ingredient or atc):
        return "Give name, active_ingredient or atc."
    res = search(
        nombre=name,
        practiv1=active_ingredient,
        atc=atc,
        comerc=1 if marketed_only else None,
    )
    if not res:
        return "No results in CIMA."
    lines = [_drug_line(m) for m in res[:max_results]]
    extra = "\n(more results available; refine the search)" if len(res) > max_results else ""
    return "\n".join(lines) + extra


@tool
def cima_drug_info(code: str) -> str:
    """CIMA record of a medicine: composition, ATC, company, SmPC and package leaflet.

    Args:
        code: National code (CN, 6-7 digits) or registration number.
    """
    m = get_drug(code)
    if not m:
        return f"Not found in CIMA: {code}"
    ingredients = ", ".join(
        f"{p['nombre']} {p.get('cantidad', '')} {p.get('unidad', '')}".strip()
        for p in m.get("principiosActivos", [])
    ) or m.get("pactivos", "")
    atcs = ", ".join(f"{a['codigo']} ({a['nombre']})" for a in m.get("atcs", []))
    docs = {1: "SmPC", 2: "Package leaflet"}
    doc_lines = [
        f"{docs[d['tipo']]}: {d.get('urlHtml') or d['url']}"
        for d in m.get("docs", [])
        if d["tipo"] in docs
    ]
    packs = "; ".join(f"{p['cn']} {p['nombre']}" for p in m.get("presentaciones", [])[:5])

    def yn(v: object) -> str:
        return "yes" if v else "no"

    return "\n".join(
        [
            m["nombre"],
            f"Registration no.: {m['nregistro']} | Holder: {m.get('labtitular')}",
            f"Active ingredients: {ingredients}",
            f"ATC: {atcs}",
            f"Form: {(m.get('formaFarmaceutica') or {}).get('nombre', '?')} | "
            f"Routes: {', '.join(v['nombre'] for v in m.get('viasAdministracion', []))}",
            f"Prescription: {m.get('cpresc')} | Marketed: {yn(m.get('comerc'))}"
            f" | Supply problem: {yn(m.get('psum'))}"
            f" | Safety notes: {yn(m.get('notas'))}",
            f"Packs: {packs}",
            *doc_lines,
        ]
    )


@tool
def cima_supply_problems(cn: str = "", text: str = "", max_results: int = 20) -> str:
    """Active supply problems (shortages) registered by the AEMPS.

    Args:
        cn: Specific national code (empty = all).
        text: Filter by text in the name, e.g. 'atorvastatina'.
        max_results: Maximum number of results.
    """
    res = [r for r in supply_problems(cn) if r.get("activo", True)]
    if text:
        res = [r for r in res if text.lower() in r.get("nombre", "").lower()]
    res.sort(key=lambda r: r.get("fini") or 0, reverse=True)
    if not res:
        return "No matching active supply problems."
    lines = [
        f"- {r['nombre']} (CN {r['cn']}) from {_date(r.get('fini'))}"
        f" to {_date(r.get('ffin'))}. {r.get('observ', '')}".strip()
        for r in res[:max_results]
    ]
    return f"{len(res)} active problems. Most recent:\n" + "\n".join(lines)


@tool
def cima_registry_changes(
    days: int = 7, include_modifications: bool = False, max_results: int = 30
) -> str:
    """Medicines newly authorised or withdrawn in CIMA over the last days.

    Args:
        days: How many days back to check (max 30).
        include_modifications: Also include modifications (there are many).
        max_results: Maximum number of results.
    """
    since = date.today() - timedelta(days=max(1, min(days, 30)))
    types = {1, 2, 3} if include_modifications else {1, 2}
    res = [r for r in registry_changes(since) if r.get("tipoCambio") in types]
    res.sort(key=lambda r: r.get("fecha") or 0, reverse=True)
    if not res:
        return f"No new or withdrawn medicines since {since:%d/%m/%Y}."
    lines = [
        f"- [{CHANGE_TYPE.get(r['tipoCambio'], '?')}] {_date(r.get('fecha'))} {r['nombre']}"
        f" (nreg {r['nregistro']}, {r.get('labtitular', '')})"
        for r in res[:max_results]
    ]
    return "\n".join(lines)


@tool
def cima_safety_notes(code: str) -> str:
    """AEMPS safety information notes linked to a medicine.

    Args:
        code: National code (CN) or registration number.
    """
    m = get_drug(code)
    if not m:
        return f"Not found in CIMA: {code}"
    notes = get_json(f"{CIMA}/notas", nregistro=m["nregistro"]) or []
    if not notes:
        return f"{m['nombre']}: no safety notes."
    return f"{m['nombre']}:\n" + "\n".join(
        f"- {_date(n.get('fecha'))} {n.get('referencia', '')}: {n.get('asunto')} ({n.get('url')})"
        for n in notes
    )
