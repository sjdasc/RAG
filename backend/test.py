import requests
import os

BASE_URL = "http://127.0.0.1:8000"

# -------------------------------
# 1) 파일 업로드 테스트
# -------------------------------
def test_upload(filepath):
    if not os.path.exists(filepath):
        return f"❌ File not found: {filepath}"

    files = {"file": open(filepath, "rb")}
    res = requests.post(f"{BASE_URL}/upload", files=files)
    return res.json()


# -------------------------------
# 2) Reindex (Incremental Indexing)
# -------------------------------
def test_reindex():
    res = requests.get(f"{BASE_URL}/reindex")
    return res.json()

# -------------------------------
# 3) 검색 요청
# -------------------------------
def test_search(query):
    res = requests.get(f"{BASE_URL}/search?q={query}").json()

    print("\n📌 SEARCH RESULT")
    for r in res.get("results",[]):
        print(f"📄 {r['file']}")
        print(f"🔎 score: {r['score']}")
        print(f"📝 preview: {r['preview']}\n")


# -------------------------------
# 4) 문서 전체 조회
# -------------------------------
def test_documents(limit=20):
    res = requests.get(f"{BASE_URL}/documents", params={"limit": limit})
    return res.json()


# -------------------------------
# 5) 통계 조회
# -------------------------------
def test_stats():
    res = requests.get(f"{BASE_URL}/stats")
    return res.json()

def test_vectors(limit=5, dim=8):
    res = requests.get(f"{BASE_URL}/vectors", params={"limit": limit, "dim": dim})
    print(res.json())

# ===========================================================
# 📌 🔥 추가됨 → clear DB 전체 삭제
# ===========================================================
def test_clear():
    res = requests.get(f"{BASE_URL}/clear").json()

    deleted = res.get("deleted_docs", None)

    if deleted is not None:
        print(f"\n⚠ DB CLEARED → {deleted} docs removed")
    else:
        print("\n⚠ CLEAR EXECUTED — but no docs reported (DB may have been empty)")

    print("RETURN:", res)
    return res

def test_delete(filename):
    res = requests.get(f"{BASE_URL}/delete", params={"filename": filename}).json()
    print(f"\n🗑 DELETE → {res['filename']} / removed {res['deleted_count']} docs")
    print("deleted IDs:", res.get("deleted_ids", []))
    return res


# ===========================================================
# 실행 테스트
# ===========================================================
if __name__ == "__main__":
    print("\n========== 🔥 TEST START 🔥 ==========\n")

    # 1. 업로드
    print("\n📌 FILE UPLOAD TEST")
    print(test_upload("./data/bigdata_tech.txt"))        # 존재하는 파일로 변경해도 좋음

    # 2. Incremental Indexing
    print("\n📌 REINDEX TEST (Incremental)")
    print(test_reindex())

    # 3. 검색
    print("\n📌 SEARCH TEST")
    print(test_search("빅데이터"))
    
    # 4. 문서 확인
    print("\n📌 DOCUMENTS LIST")
    print(test_documents())

    # 5. 통계 확인
    print("\n📌 STATS CHECK")
    print(test_stats())
    
    # 6. vector 확인
    print("\n📌 VECTOR CHECK")
    print(test_vectors())
    
    # # 7. 전체 삭제
    # test_clear()

    print("\n========== 🎉 TEST FINISHED ==========\n")
