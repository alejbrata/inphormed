# app/api/pptx_claims.py
from fastapi import APIRouter, UploadFile, File
import tempfile
import shutil
from app.utils.claim_extractor import extract_claims_from_pptx, extract_claims_with_debug

router = APIRouter(prefix="/claims", tags=["claims"])

@router.post("/extract")
async def extract_from_pptx(file: UploadFile = File(...), debug: bool = False, per_slide: int = 1):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    if debug:
        items = extract_claims_with_debug(tmp_path, max_claims_per_slide=per_slide)
        return {"filename": file.filename, "claims_detected": len(items), "items": items}
    else:
        claims = extract_claims_from_pptx(tmp_path, max_claims_per_slide=per_slide)
        return {"filename": file.filename, "claims_detected": len(claims), "claims": claims}
