from fastapi import APIRouter, Depends, HTTPException, Response
import sqlite3
from app.api.dependencies import get_db, require_permission
from app.core.permissions import Permission
from app.services.report_service import generate_case_report

router = APIRouter()

@router.get("/investigations/{investigation_id}")
def get_investigation_report_json(
    investigation_id: str,
    current_user: dict = Depends(require_permission(Permission.EXPORT_REPORT)),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        return generate_case_report(db, investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/investigations/{investigation_id}/pdf")
def get_investigation_report_html_pdf(
    investigation_id: str,
    current_user: dict = Depends(require_permission(Permission.EXPORT_REPORT)),
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        data = generate_case_report(db, investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
        
    # Generate clean, printable executive forensic PDF/HTML report
    evidence_rows = "".join([
        f"<tr><td><b>{e['evidence_type']}</b></td><td>{e['description']}</td><td><span class='badge'>{e['verification_status']}</span></td><td>{e['collector']}</td></tr>"
        for e in data["evidence_items"]
    ])
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Case Report {data['case_number']} — SentinelFlow AI</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; color: #1e293b; padding: 40px; }}
        .header {{ border-bottom: 2px solid #0f172a; padding-bottom: 20px; margin-bottom: 25px; }}
        .title {{ font-size: 24px; font-weight: bold; color: #0f172a; margin: 0; }}
        .subtitle {{ font-size: 14px; color: #64748b; margin-top: 5px; }}
        .metadata-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; margin-bottom: 25px; }}
        .meta-item {{ font-size: 13px; }}
        .meta-label {{ font-weight: 600; color: #475569; }}
        .section-title {{ font-size: 16px; font-weight: 600; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px; margin-top: 25px; margin-bottom: 12px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 10px; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
        th {{ background: #f1f5f9; font-weight: 600; }}
        .badge {{ background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
        .limitations {{ background: #fffbeb; border: 1px solid #fef3c7; color: #92400e; padding: 12px; border-radius: 6px; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">SentinelFlow AI — Formal Investigation Dossier</h1>
        <div class="subtitle">Case Ref: {data['case_number']} | Generated: {data['generated_at']}</div>
    </div>
    
    <div class="metadata-grid">
        <div class="meta-item"><span class="meta-label">Title:</span> {data['title']}</div>
        <div class="meta-item"><span class="meta-label">Status:</span> {data['status']}</div>
        <div class="meta-item"><span class="meta-label">Priority:</span> {data['priority']}</div>
        <div class="meta-item"><span class="meta-label">Investigator:</span> {data['investigator_name']}</div>
        <div class="meta-item"><span class="meta-label">Reviewer:</span> {data['reviewer_name'] or 'Pending'}</div>
        <div class="meta-item"><span class="meta-label">Completeness:</span> {data['evidence_completeness_score']}%</div>
    </div>
    
    <div class="section-title">Case Summary & Disposition</div>
    <p><b>Summary:</b> {data['summary']}</p>
    <p><b>Final Disposition:</b> {data['disposition'] or 'PENDING_INVESTIGATION'}</p>
    <p><b>Investigator Rationale:</b> {data['disposition_rationale'] or 'Investigation actively ongoing. No final disposition submitted.'}</p>
    
    <div class="section-title">Verified Evidentiary Records ({len(data['evidence_items'])})</div>
    <table>
        <thead>
            <tr><th>Evidence Type</th><th>Description</th><th>Verification</th><th>Collector</th></tr>
        </thead>
        <tbody>
            {evidence_rows or "<tr><td colspan='4'>No evidentiary records registered.</td></tr>"}
        </tbody>
    </table>
    
    <div class="limitations">
        <b>Platform Methodology & Limitations:</b><br/>
        {data['methodology_and_limitations']}
    </div>
</body>
</html>
"""
    return Response(content=html_content, media_type="text/html")
