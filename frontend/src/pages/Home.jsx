import React, {
  useState,
  useEffect,
} from "react";
import Sidebar from "../components/layout/Sidebar";
import {
  Search,
  UploadCloud,
  Sparkles,
  FileText,
} from "lucide-react";
import { useChatStore } from "../stores/useChatStore";
import { useNavigate } from "react-router-dom";
import "../styles/stars.css";
import "../styles/Home.css";

const Home = () => {
  const [query, setQuery] = useState("");
  const {
    launchFiles,
    askQuestion,
    isLoading,
    documents,
    currentChatId,
    fetchDocuments,
    createNewChat,
    chats, // chats 추가
  } = useChatStore();
  const navigate = useNavigate();

  // 앱 진입 시 또는 채팅방이 없을 때 자동으로 새 채팅방 생성 (Gemini 스타일)
  useEffect(() => {
    // 스토어의 최신 상태를 직접 확인하여 중복 생성 방지
    const state = useChatStore.getState();
    if (
      !state.currentChatId &&
      state.chats.length === 0
    ) {
      createNewChat();
    } else if (currentChatId) {
      fetchDocuments(currentChatId);
    }
  }, [
    currentChatId,
    chats.length,
    createNewChat,
    fetchDocuments,
  ]);

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      launchFiles(e.target.files);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    await askQuestion(query);
    navigate("/result"); // 결과 페이지로 이동
  };

  return (
    <div className="home-container">
      <div className="stars-container">
        <div className="stars-small"></div>
        <div className="stars-medium"></div>
        <div className="stars-large"></div>
      </div>
      <Sidebar />
      <main className="home-main">
        <div className="home-content-wrapper">
          <h1 className="home-title">
            Explore the Galaxy of Knowledge
          </h1>
          <p className="home-subtitle">
            Launch your materials like stars, and
            find answers through questions.
          </p>

          {/* 파일 업로드 (Launch) 버튼 */}
          <div className="home-upload-section">
            <input
              type="file"
              id="fileUpload"
              multiple
              className="hidden"
              onChange={handleFileChange}
            />
            <label
              htmlFor="fileUpload"
              className={`home-upload-label ${
                isLoading
                  ? "home-upload-label-loading"
                  : ""
              }`}
            >
              <UploadCloud size={24} />
              {isLoading
                ? "Ready to Launch..."
                : "Launch Files"}
            </label>
            <p className="home-upload-helper-text">
              Supports various lecture materials
              such as PDF, PPTX, DOCX
            </p>
          </div>

          {/* 검색창 */}
          <form
            onSubmit={handleSearch}
            className="home-search-form group"
          >
            <div className="home-search-wrapper">
              <Search
                className="home-search-icon"
                size={24}
              />
              <input
                type="text"
                value={query}
                onChange={(e) =>
                  setQuery(e.target.value)
                }
                placeholder="what do you want to ask?"
                className="home-search-input"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={
                  isLoading || !query.trim()
                }
                className="home-search-button"
              >
                <Sparkles size={24} />
              </button>
            </div>
          </form>

          {/* 문서 목록 표시 (추가됨) */}
          <div className="home-docs-section">
            <h3 className="home-docs-title">
              Currently exploring documents:
            </h3>
            {documents.length > 0 ? (
              <div className="home-docs-list">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="home-doc-item"
                  >
                    <FileText
                      size={14}
                      className="home-doc-icon"
                    />
                    <span className="home-doc-filename">
                      {doc.filename}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="home-docs-empty">
                No documents found.
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Home;
