from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx, os, json

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ScanRequest(BaseModel):
    media_type: str
    data: str
    doc_type: str

@router.post("/scan")
async def scan_document(req: ScanRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(400, "ANTHROPIC_API_KEY not configured on the server")

    if req.doc_type == "invoice":
        prompt = 'Extract invoice data and return ONLY this JSON (no markdown): {"client_name":"","client_email":"","issue_date":"YYYY-MM-DD","due_date":"YYYY-MM-DD","tax_rate":15,"notes":"","items":[{"description":"","quantity":1,"unit_price":0}]}'
    else:
        prompt = 'Extract transaction data and return ONLY this JSON (no markdown): {"type":"income","amount":0,"description":"","category":"","date":"YYYY-MM-DD","reference":""}'

    content_item = {
        "type": "document" if req.media_type == "application/pdf" else "image",
        "source": {"type": "base64", "media_type": req.media_type, "data": req.data}
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 1000,
                  "messages": [{"role": "user", "content": [content_item, {"type": "text", "text": prompt}]}]}
        )

    if resp.status_code != 200:
        raise HTTPException(500, f"Claude API error: {resp.text[:200]}")

    text = "".join(c.get("text","") for c in resp.json().get("content",[]))
    clean = text.replace("```json","").replace("```","").strip()
    try:
        return json.loads(clean)
    except:
        raise HTTPException(500, f"Parse error: {clean[:200]}")
