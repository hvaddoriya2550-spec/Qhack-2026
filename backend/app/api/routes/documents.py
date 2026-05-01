from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.project import Project

router = APIRouter()


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    from pypdf import PdfReader
    import io

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


@router.post("/upload/{project_id}")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a PDF document and extract text for RAG.

    The extracted text is stored on the project and made available
    to the research agent as additional context.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file type
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read and extract text
    pdf_bytes = await file.read()
    if len(pdf_bytes) < 100:
        raise HTTPException(status_code=400, detail="File too small")

    try:
        text = _extract_pdf_text(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    # Store on project
    docs = project.documents or []
    docs.append({
        "filename": filename,
        "text": text,
        "uploaded_at": datetime.utcnow().isoformat(),
    })
    project.documents = docs
    await db.commit()

    return {
        "filename": filename,
        "pages": text.count("\n\n") + 1,
        "chars": len(text),
        "project_id": project_id,
    }


@router.get("/{project_id}")
async def list_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all uploaded documents for a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return [
        {"filename": d["filename"], "chars": len(d.get("text", "")), "uploaded_at": d.get("uploaded_at")}
        for d in (project.documents or [])
    ]
