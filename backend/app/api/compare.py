"""Property comparison API endpoint."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.api.properties import get_properties
from app.schemas import CompareRequest, CompareResponse, PropertyItem

router = APIRouter(prefix="/api/compare", tags=["Compare"])


@router.post("", response_model=CompareResponse)
def compare_properties(req: CompareRequest):
    all_props = {p["id"]: p for p in get_properties()}
    selected = []

    for pid in req.property_ids:
        if pid in all_props:
            selected.append(all_props[pid])
        else:
            raise HTTPException(status_code=404, detail=f"Property ID '{pid}' not found")

    # Generate a structured comparison summary
    lines = ["### Side-by-Side Property Comparison\n"]
    for p in selected:
        lines.append(
            f"- **{p.get('name') or p.get('title')}** ({p.get('platform').upper()}):\n"
            f"  - **Location**: {p.get('city')}, {p.get('country')} ({p.get('district', 'N/A')})\n"
            f"  - **Type & Purpose**: {p.get('property_type')} for {p.get('purpose', 'sale').title()}\n"
            f"  - **Price**: {p.get('price_display')}\n"
            f"  - **Developer / Brand**: {p.get('developer', 'N/A')} "
            + (f"| Partner: {p.get('brand_partner')}" if p.get('brand_partner') else "") + "\n"
            f"  - **Bedrooms / Area**: {p.get('bedrooms', 'N/A')} beds | {p.get('area_sqm', 'N/A')} SQM\n"
        )

    summary = "\n".join(lines)
    return CompareResponse(
        properties=selected,
        comparison_summary=summary
    )
