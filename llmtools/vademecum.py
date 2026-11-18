"""Vademecum features: active ingredients and international equivalents.

Vademecum.es is commercial and has no public API (scraping it may breach its terms),
so open sources are combined, using the WHO ATC code as the bridge:
  * CIMA (Spain): composition and ATC of the Spanish medicine.
  * RxNorm / RxClass (NLM, USA): US ingredient and brands for that ATC.
  * openFDA: US label: indications, mechanism, warnings.
"""

from . import cima
from ._http import get_json
from .core import tool

RXNAV = "https://rxnav.nlm.nih.gov/REST"
OPENFDA = "https://api.fda.gov/drug/label.json"


def _spanish_drug(query: str) -> dict | None:
    """Resolve a CN / registration number / name to the CIMA record (first marketed one)."""
    if query.strip().isdigit():
        return cima.get_drug(query)
    res = cima.search(nombre=query, comerc=1) or cima.search(practiv1=query, comerc=1)
    if not res:
        return None
    # The shortest name is usually the "plain" product (not a combination with other APIs).
    best = min(res, key=lambda m: len(m["nombre"]))
    return cima.get_drug(best["nregistro"])


def rxnorm_by_atc(atc5: str) -> list[dict]:
    """RxNorm ingredients whose level-5 ATC is ``atc5`` (via the level-4 class)."""
    data = (
        get_json(f"{RXNAV}/rxclass/classMembers.json", classId=atc5[:5], relaSource="ATC", trans=0)
        or {}
    )
    members = (data.get("drugMemberGroup") or {}).get("drugMember", [])
    out = []
    for m in members:
        attrs = {a["attrName"]: a["attrValue"] for a in m.get("nodeAttr", [])}
        if attrs.get("SourceId") == atc5:
            out.append(m["minConcept"])
    return out


def rxnorm_brands(rxcui: str, limit: int = 15) -> list[str]:
    data = get_json(f"{RXNAV}/rxcui/{rxcui}/related.json", tty="BN") or {}
    groups = (data.get("relatedGroup") or {}).get("conceptGroup", [])
    names = [c["name"] for g in groups for c in g.get("conceptProperties", [])]
    return sorted(set(names))[:limit]


def rxnorm_search(term: str) -> dict | None:
    data = get_json(f"{RXNAV}/approximateTerm.json", term=term, maxEntries=1) or {}
    cands = (data.get("approximateGroup") or {}).get("candidate", [])
    if not cands:
        return None
    rxcui = cands[0]["rxcui"]
    props = (get_json(f"{RXNAV}/rxcui/{rxcui}/properties.json") or {}).get("properties") or {}
    return {"rxcui": rxcui, "name": props.get("name") or cands[0].get("name", term)}


def fda_label(ingredient: str) -> dict | None:
    try:
        data = get_json(OPENFDA, search=f'openfda.generic_name:"{ingredient}"', limit=1)
    except Exception:  # openFDA answers 404 when there are no results
        return None
    res = (data or {}).get("results", [])
    return res[0] if res else None


@tool
def international_equivalents(drug: str) -> str:
    """Find the US equivalent (ingredient and brands) of a Spanish medicine, via its ATC code.

    Args:
        drug: Spanish brand name, active ingredient or national code (CN).
    """
    m = _spanish_drug(drug)
    lines = []
    ingredients: list[dict] = []
    if m:
        atc5 = [a["codigo"] for a in m.get("atcs", []) if len(a["codigo"]) == 7]
        lines.append(f"Spain (CIMA): {m['nombre']} — {m.get('pactivos', '')}")
        lines.append(f"ATC: {', '.join(atc5) or 'no level-5 ATC'}")
        for code in atc5:
            ingredients += rxnorm_by_atc(code)
    if not ingredients:  # no ATC or no mapping: approximate name search
        term = m.get("pactivos", drug) if m else drug
        hit = rxnorm_search(term.split(",")[0])
        if hit:
            ingredients.append(hit)
    if not ingredients:
        return "\n".join(lines + ["No RxNorm equivalent found."])
    for ing in ingredients[:3]:
        brands = rxnorm_brands(ing["rxcui"])
        lines.append(
            f"USA (RxNorm {ing['rxcui']}): {ing['name']}. "
            f"Brands (includes combinations): {', '.join(brands) or '—'}"
        )
    lines.append(
        "Note: same molecule/ATC does not imply same dose, form or indication; "
        "check each country's SmPC/label."
    )
    return "\n".join(lines)


@tool
def active_ingredient_info(active_ingredient: str) -> str:
    """Active ingredient: medicines in Spain (CIMA) and indications/mechanism (FDA label).

    Args:
        active_ingredient: Active ingredient name, e.g. 'paracetamol' or 'atorvastatina'.
    """
    meds = cima.search(practiv1=active_ingredient, comerc=1)
    n = f"{len(meds)}+" if len(meds) >= 200 else str(len(meds))  # CIMA pages by 200
    lines = [f"Spain: {n} marketed medicines containing {active_ingredient}."]
    lines += [f"- {x['nombre']}" for x in meds[:5]]
    hit = rxnorm_search(active_ingredient)
    name_en = hit["name"] if hit else active_ingredient
    label = fda_label(name_en)
    if label:
        for field, title in (
            ("indications_and_usage", "Indications (FDA)"),
            ("mechanism_of_action", "Mechanism (FDA)"),
            ("boxed_warning", "Boxed warning (FDA)"),
        ):
            if label.get(field):
                lines.append(f"\n{title}: {label[field][0][:800]}")
    else:
        lines.append(f"\nNo openFDA label for '{name_en}'.")
    return "\n".join(lines)
