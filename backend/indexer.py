# indexer.py
import os
import glob
from typing import List

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select

from db.db import SessionLocal
from db.models import Document
from loader import load_text
from chroma_engine import ChromaEngine

load_dotenv()
chroma = ChromaEngine()
DATA_DIR = os.getenv("DATA_DIR", "./data")


def scan_files() -> List[str]:
    patterns = ["*.txt", "*.pdf", "*.md", "*.docx", "*.pptx"]
    files: List[str] = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(DATA_DIR, "**", p), recursive=True))
    return sorted(set(files))


def upsert_documents(db: Session, file_paths: List[str], session_id: str) -> List[int]:
    """
    1) PostgreSQL documents 테이블 upsert
    2) 같은 시점에 Chroma에도 저장
    """
    doc_ids: List[int] = []

    chroma_ids = []
    chroma_docs = []
    chroma_metas = []

    for path in file_paths:
        chunks = load_text(path)
        if not chunks:
            continue

        title = os.path.basename(path).rsplit(".", 1)[0]
        full_content = "\n\n".join([c['content'] for c in chunks])

        # PostgreSQL upsert
        stmt = select(Document).where(Document.path == path)
        existing = db.execute(stmt).scalar_one_or_none()

        if existing:
            existing.title = title
            existing.content = full_content
            existing.session_id = session_id  
            db.flush()
            doc_id = existing.id
        else:
            doc = Document(path=path, title=title, content=full_content, session_id=session_id )
            db.add(doc)
            db.flush()
            doc_id = doc.id

        doc_ids.append(doc_id)

        # metadata
        ext = path.split(".")[-1].lower()
        
        # Extract session_id from path (assuming data/{session_id}/{filename})
        rel_path = os.path.relpath(path, DATA_DIR)
        parts = rel_path.split(os.sep)
        
        # if len(parts) > 1:
        #     session_id = parts[0]
        # else:
        #     session_id = "default"
        
        file_session_id = parts[0] if len(parts) > 1 else "default"

        for chunk in chunks:
            # ID format: {doc_id}_{page}
            chroma_ids.append(f"{doc_id}_{chunk['page']}")
            chroma_docs.append(chunk['content'])
            chroma_metas.append({
                "title": title,
                "ext": ext,
                "path": path,
                # "session_id": session_id,
                "session_id": file_session_id,
                "page": chunk['page']
            })

    db.commit()

    # 🔥 Chroma 업로드 (한 번만)
    chroma.collection.add(
        ids=chroma_ids,
        documents=chroma_docs,
        metadatas=chroma_metas
    )

    return doc_ids


def rebuild_index(session_id: str):
    print("[INDEX] Scanning files...")
    file_paths = scan_files()
    print(f"[INDEX] Found {len(file_paths)} files.")

    if not file_paths:
        print("[INDEX] No files found. Abort.")
        return

    db: Session = SessionLocal()

    try:
        print("[INDEX] Clearing Chroma collection...")
        chroma.clear_all()

        print("[INDEX] Upserting documents into PostgreSQL + Chroma...")
        upsert_documents(db, file_paths, session_id=session_id)

        print("[INDEX] Done.")
    finally:
        db.close()


if __name__ == "__main__":
    rebuild_index()
