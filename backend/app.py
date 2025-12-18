# app.py
import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from db.db import get_db, Base, engine
from db.models import Document, SearchLog
from loader import load_text
from indexer import rebuild_index, chroma

import numpy as np
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import CrossEncoder

# ================================
# 초기 세팅
# ================================
UPLOAD_DIR = "./data"
ALLOWED_EXT = {"txt", "pdf", "md", "docx", "pptx", "jpg", "jpeg", "png", "bmp", "tiff"}

app = FastAPI(title="FoundByMe API (Chroma + PostgreSQL)")

# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)

# 🚀 Re-ranker 모델 로드 (정확도 향상용)
# Cross-Encoder는 속도는 느리지만 정확도가 매우 높음
print("[APP] Loading Re-ranker model...")
# 다국어 지원 모델 사용 (BAAI/bge-reranker-v2-m3: 성능이 우수한 다국어 리랭커)
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
print("[APP] Re-ranker loaded.")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
print('1')
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"

# ======================================================
# 🔍 /search - 유사문서 top5 + PCA 3D
# ======================================================
@app.get("/search")
def search(q: str, session_id: str = "default"):

    if not q:
        raise HTTPException(status_code=400, detail="query required")

    # session_id 필터 적용
    where_filter = {"session_id": session_id} if session_id != "default" else None
    
    # 1. 1차 검색 (Vector Search) - 후보군을 넉넉하게(15~20개) 가져옴
    q_emb = chroma.embed([q])[0]
    candidate_k = 15
    result = chroma.collection.query(
        query_embeddings=[q_emb],
        n_results=candidate_k,
        where=where_filter
    )

    ids = result["ids"][0]
    docs = result["documents"][0] if result["documents"] else []
    metas = result["metadatas"][0] if result["metadatas"] else []
    
    real_k = len(ids)

    if real_k == 0:
        return {
            "query": q,
            "query_vector_3d": [0, 0, 0],
            "results": []
        }

    # 2. 2차 검색 (Re-ranking) - CrossEncoder로 정확도 순 정렬
    # (질문, 문서내용) 쌍을 만들어 점수 계산
    pairs = [[q, doc_text] for doc_text in docs]
    scores = reranker.predict(pairs)

    # 점수와 인덱스를 묶어서 정렬 (점수 높은)
    scored_results = []
    for i in range(real_k):
        scored_results.append({
            "index": i,
            "score": float(scores[i]),
            "id": ids[i],
            "doc": docs[i],
            "meta": metas[i]
        })
    
    # 점수 내림차순 정렬
    scored_results.sort(key=lambda x: x["score"], reverse=True)

    # 상위 5개만 선택
    top_k = 5
    final_results = scored_results[:top_k]
    
    # 3D 시각화를 위해 선택된 문서들의 Vector만 다시 가져오기 (최적화)
    final_ids = [res["id"] for res in final_results]
    
    # Embedding 가져오기
    doc_vecs = chroma.collection.get(ids=final_ids, include=["embeddings"])["embeddings"]
    query_vec = np.array(q_emb, dtype=np.float32)
    doc_vecs = np.array(doc_vecs, dtype=np.float32)

    # PCA
    if len(doc_vecs) > 0:
        X = np.vstack([query_vec, *doc_vecs])
    else:
        X = np.array([query_vec])
        
    if len(X) < 3:
         query_3d = [0, 0, 0]
         doc_3d = [[0,0,0]] * len(doc_vecs)
    else:
        pca = PCA(n_components=min(3, len(X)))
        X_3d = pca.fit_transform(X)
        if X_3d.shape[1] < 3:
            X_3d = np.pad(X_3d, ((0,0), (0, 3-X_3d.shape[1])), 'constant')
            
        query_3d = X_3d[0].tolist()
        doc_3d = X_3d[1:]
    
    results = []
    for i, res in enumerate(final_results):
        meta = res["meta"]
        results.append({
            "id": res["id"],
            "filename": meta.get("title"),
            "ext": meta.get("ext"),
            "page": meta.get("page", 1),
            "score": res["score"], 
            "vector_3d": doc_3d[i].tolist() if len(doc_3d) > i else [0,0,0],
            "preview": (res["doc"][:200] if res["doc"] else "").replace("\n", " "),
            "url": f"/api/files/{session_id}/{meta.get('title')}.{meta.get('ext')}"
        }) 
        
    # 사용자 요청: query_3d의 첫 번째 값에서 3을 뺌 
   
    
    return {
        "query": q,
        "query_vector_3d": query_3d,
        "results": results
    }

# =====================================
# 💬 /chat (RAG Mock)
# =====================================
@app.post("/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    search_results = search(req.query, session_id=req.session_id)
    
    # Save query log
    try:
        # 이전 질문 기록 삭제 (한 번에 하나의 질문만 유지)
        db.execute(delete(SearchLog).where(SearchLog.session_id == req.session_id))
        
        log = SearchLog(
            query=req.query, 
            session_id=req.session_id, 
            top_k=5, 
            results_count=len(search_results.get("results", []))
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Error saving search log: {e}")
    
    sources = []
    context = ""
    
    if "results" in search_results:
        for res in search_results["results"]:
            sources.append({
                "name": res["filename"],
                "url": res.get("url", ""),
                "preview": res.get("preview", ""),
                "page": res.get("page", 1)
            })
            context += f"- {res['filename']} (p.{res.get('page', 1)})\n"
    
    if not context:
        answer = "관련된 문서를 찾을 수 없습니다. 문서를 업로드했는지 확인해주세요."
    else:
        answer = f"'{req.query}'에 대해 다음 문서들을 찾았습니다:\n\n{context}"

    return {
        "query": req.query,
        "answer": answer,
        "sources": sources,
        "results": search_results.get("results", []),
        "query_vector_3d": search_results.get("query_vector_3d", [0,0,0])
    }


# ======================================================
# 📤 /upload - 파일 업로드
# ======================================================
@app.post("/upload")
def upload_file(
    files: List[UploadFile] = File(...),
    session_id: str = Form("default")
):
    saved_files = []
    errors = []

    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    for file in files:
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXT:
            errors.append(f"❌ {file.filename}: 지원하지 않는 파일 형식 ({ext})")
            continue

        save_path = f"{session_dir}/{file.filename}"
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        saved_files.append(file.filename)

    return {
        "status": "completed",
        "saved": saved_files,
        "errors": errors,
        "session_id": session_id,
        "info": "📌 파일 저장완료 → /reindex 호출 시 인덱싱 수행"
    }

# =====================================
# 📂 파일 다운로드/열기
# =====================================
@app.get("/files/{session_id}/{filename}")
def get_file(session_id: str, filename: str):
    file_path = os.path.join(UPLOAD_DIR, session_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "File not found"}


# ======================================================
# 🔄 /reindex - 전체 재인덱싱
# ======================================================
@app.get("/reindex")
def reindex(session_id: str = "default"):
    rebuild_index(session_id)
    # global chroma
    # chroma = ChromaEngine()  # reload - No need, using shared instance
    return {"status": "Success", "session_id": session_id}


# ======================================================
# 📄 /documents - 문서 목록 조회
# ======================================================
@app.get("/documents")
def list_documents(session_id: str = "default", limit: int = 100, db: Session = Depends(get_db)):
    try:
        # SQL DB에서 파일 목록 조회 (중복 없이 파일 단위로)
        stmt = select(Document).where(
            (Document.path.like(f"%/{session_id}/%")) | 
            (Document.path.like(f"%\\{session_id}\\%"))
        )
        docs = db.execute(stmt).scalars().all()
        
        result = []
        for doc in docs:
            ext = doc.path.split(".")[-1]
            result.append({
                "id": str(doc.id),
                "filename": f"{doc.title}.{ext}", # 확장자 포함
                "preview": doc.content[:50] if doc.content else "",
                "type": ext
            })
        return {"count": len(result), "documents": result}
    except Exception as e:
        print(f"Error listing documents: {e}")
        return {"documents": []}
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================
# 📊 /stats - 확장자별 통계
# ======================================================
@app.get("/stats")
def stats():
    rows = chroma.collection.get(include=["metadatas"])
    metas = rows["metadatas"]

    stat = {}
    for meta in metas:
        ext = meta.get("ext", "txt")
        stat[ext] = stat.get(ext, 0) + 1

    return {
        "total_docs": len(metas),
        "by_extension": stat
    }

# =====================================
# 🌌 /galaxy (3D 시각화)
# =====================================
@app.get("/galaxy")
def galaxy_view(session_id: str = "default", query: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        where_filter = {"session_id": session_id} if session_id != "default" else None
        
        results = chroma.collection.get(
            where=where_filter,
            include=["metadatas", "embeddings"]
        )
        
        ids = results["ids"]
        metas = results["metadatas"]
        embeddings = results["embeddings"]
        
        if not ids:
            return []

        vectors = []
        metadata_list = []
        
        for i, vec in enumerate(embeddings):
            vectors.append(vec)
            metadata_list.append({
                "id": ids[i],
                "label": metas[i].get("title", "unknown"),
                "type": metas[i].get("ext", "txt"),
                "page": metas[i].get("page", 1),
                "filename": metas[i].get("title", "unknown"),
                "isQuery": False
            })
            
        # Fetch all queries for this session from DB
        try:
            logs = db.execute(select(SearchLog).where(SearchLog.session_id == session_id)).scalars().all()
            queries = [log.query for log in logs]
            
            # Add current query if provided and not in logs
            if query and query not in queries:
                queries.append(query)
            
            # Deduplicate
            unique_queries = list(set(queries))
            
            if unique_queries:
                q_embeddings = chroma.embed(unique_queries)
                for q_text, q_vec in zip(unique_queries, q_embeddings):
                     vectors.append(q_vec)
                     metadata_list.append({
                        "id": f"query_{hash(q_text)}",
                        "label": f"Question: {q_text}",
                        "type": "query",
                        "isQuery": True
                    })
        except Exception as e:
            print(f"Error fetching queries: {e}")
            # Fallback to just the current query if DB fails
            if query:
                qvec = chroma.embed([query])[0]
                vectors.append(qvec)
                metadata_list.append({
                    "id": "query",
                    "label": f"Question: {query}",
                    "type": "query",
                    "isQuery": True
                })

        X = np.array(vectors)
        
        if len(X) < 3:
             points = []
             for i, meta in enumerate(metadata_list):
                points.append({
                    "id": meta["id"],
                    "position": [np.random.uniform(-5, 5), np.random.uniform(-5, 5), np.random.uniform(-5, 5)],
                    "color": "#FDE047" if meta["isQuery"] else "#8B5CF6",
                    "label": meta["label"],
                    "page": meta.get("page", 1),
                    "isQuery": meta["isQuery"]
                })
             return points

        # 1. PCA 수행 (전체 데이터의 구조 파악)
        pca = PCA(n_components=3)
        X_3d = pca.fit_transform(X)
        
        # 중심점 맞추기 (평균을 0으로)
        X_3d = X_3d - np.mean(X_3d, axis=0)
        
        # 스케일링 (화면에 꽉 차게)
        max_val = np.max(np.abs(X_3d))
        if max_val > 0:
            X_3d = (X_3d / max_val) * 60

        points = []
        for i, coord in enumerate(X_3d):
            meta = metadata_list[i]
            
            color = "#8B5CF6"
            if meta["isQuery"]:
                color = "#FDE047"
            elif meta["type"] in ["pdf"]:
                color = "#F43F5E"
            elif meta["type"] in ["txt", "md"]:
                color = "#06B6D4"
            elif meta["type"] in ["pptx", "ppt"]:
                color = "#F97316"

            points.append({
                "id": meta["id"],
                "position": coord.tolist(),
                "color": color,
                "label": meta["label"],
                "page": meta.get("page", 1),
                "isQuery": meta["isQuery"],
                "url": f"/api/files/{session_id}/{meta.get('filename')}.{meta.get('type')}#page={meta.get('page', 1)}" if not meta["isQuery"] else None
            })
            
        return points

    except Exception as e:
        print(f"Galaxy View Error: {e}")
        return []

# ======================================================
# ③ delete_session : 채팅방 삭제
# ======================================================
@app.delete("/session/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    print(f"Request to delete session: {session_id}")
    
    # 1. SQL DB 삭제 (Python에서 경로 검사로 확실하게 처리)
    try:
        # 모든 문서 조회 (ID와 Path만)
        docs = db.execute(select(Document.id, Document.path)).all()
        ids_to_delete = []
        
        for doc_id, path in docs:
            # 경로 정규화 (모든 구분자를 /로 변경)
            norm_path = path.replace("\\", "/")
            # session_id가 경로의 일부인지 확인 (예: data/session_id/file.pdf)
            parts = norm_path.split("/")
            if session_id in parts:
                ids_to_delete.append(doc_id)
        
        if ids_to_delete:
            db.execute(delete(Document).where(Document.id.in_(ids_to_delete)))
            db.commit()
            print(f"Deleted {len(ids_to_delete)} documents from SQL DB.")
        else:
            print("No documents found in SQL DB for this session.")
            
    except Exception as e:
        print(f"Error deleting from SQL: {e}")
        db.rollback()

    # 2. ChromaDB 삭제
    try:
        chroma.collection.delete(where={"session_id": session_id})
        print(f"Deleted vectors for session {session_id} from ChromaDB.")
    except Exception as e:
        print(f"Error deleting from ChromaDB: {e}")

    # 3. 로컬 파일 삭제
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    if os.path.exists(session_dir):
        try:
            shutil.rmtree(session_dir)
            print(f"Deleted local directory: {session_dir}")
        except Exception as e:
            print(f"Error deleting local directory: {e}")
            # Windows에서 파일이 사용 중일 경우 실패할 수 있음
            return {"status": "PARTIAL_ERROR", "message": str(e)}
    else:
        print(f"Local directory not found: {session_dir}")

    return {
        "status": "DELETED",
        "session_id": session_id
    }

# ======================================================
# ④ delete_all_sessions : 모든 채팅방 삭제
# ======================================================
@app.delete("/sessions")
def delete_all_sessions(db: Session = Depends(get_db)):
    print("Request to delete ALL sessions")
    
    # 1. SQL DB 삭제 (모든 문서 및 로그 삭제)
    try:
        db.execute(delete(Document))
        db.execute(delete(SearchLog))
        db.commit()
        print("Deleted all documents and logs from SQL DB.")
    except Exception as e:
        print(f"Error deleting all from SQL: {e}")
        db.rollback()

    # 2. ChromaDB 삭제 (전체 삭제)
    try:
        # 모든 데이터 삭제를 위해 get()으로 ID를 가져와서 삭제하거나 reset() 사용
        # 여기서는 collection의 모든 데이터를 삭제
        ids = chroma.collection.get()['ids']
        if ids:
            chroma.collection.delete(ids=ids)
        print("Deleted all vectors from ChromaDB.")
    except Exception as e:
        print(f"Error deleting all from ChromaDB: {e}")

    # 3. 로컬 파일 삭제 (data 폴더 내의 모든 하위 폴더/파일 삭제)
    if os.path.exists(UPLOAD_DIR):
        for item in os.listdir(UPLOAD_DIR):
            item_path = os.path.join(UPLOAD_DIR, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"Error deleting {item}: {e}")
        print("Deleted all local files.")

    return {"status": "ALL_DELETED"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
