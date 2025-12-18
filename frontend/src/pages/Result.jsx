import React, { useEffect } from "react";
import Sidebar from "../components/layout/Sidebar";
import { useChatStore } from "../stores/useChatStore";
import {
  User,
  Bot,
  FileText,
  Box,
} from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import "../styles/Result.css";

const Result = () => {
  const {
    currentResult,
    documents,
    currentChatId,
    fetchDocuments,
  } = useChatStore();

  useEffect(() => {
    if (currentChatId && documents.length === 0) {
      fetchDocuments(currentChatId);
    }
  }, [
    currentChatId,
    documents.length,
    fetchDocuments,
  ]);

  // 결과가 없으면 홈으로 리다이렉트
  if (!currentResult) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="result-container">
      <Sidebar />
      <main className="result-main">
        <div className="result-content-wrapper">
          {/* 사용자 질문 */}
          <div className="result-query-wrapper">
            <div className="result-query-bubble">
              <p className="result-query-text">
                {currentResult.query}
              </p>
              <User
                className="result-user-icon"
                size={28}
              />
            </div>
          </div>

          {/* AI 답변 */}
          <div className="result-answer-wrapper">
            <div className="result-answer-bubble">
              <Bot
                className="result-bot-icon"
                size={32}
              />
              <div className="result-answer-content">
                {/* Best Match Section */}
                {currentResult.results &&
                  currentResult.results.length >
                    0 && (
                    <div className="result-best-match-card">
                      <div className="result-best-match-header">
                        <span className="result-best-match-label">
                          Best Match
                        </span>
                        <a
                          href={`${currentResult.results[0].url}#page=${currentResult.results[0].page}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="result-best-match-link"
                        >
                          <span>
                            Open p.
                            {
                              currentResult
                                .results[0].page
                            }
                          </span>
                        </a>
                      </div>
                      <p className="result-best-match-filename">
                        {
                          currentResult.results[0]
                            .filename
                        }
                      </p>
                    </div>
                  )}
                <p className="result-answer-text">
                  {currentResult.answer}
                </p>{" "}
                {/* 하단 액션 버튼들 */}
                <div className="result-actions-wrapper">
                  {/* 참조 소스 */}
                  <div className="result-sources-list">
                    {currentResult.sources
                      .slice(0, 5)
                      .map((source, idx) => (
                        <a
                          key={idx}
                          href={`${source.url}#page=${source.page}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="result-source-item"
                        >
                          <FileText size={12} />{" "}
                          {source.name} (p.
                          {source.page})
                        </a>
                      ))}
                  </div>

                  {/* 3D 시각화 이동 버튼 */}
                  <Link
                    to="/visualized"
                    className="result-visualize-btn"
                  >
                    <Box size={16} />
                    <span className="font-bold">
                      View in galaxy (3D
                      Visualize)
                    </span>
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* 문서 목록 표시 */}
          <div className="result-docs-section">
            <h3 className="result-docs-title">
              Currently exploring documents:
            </h3>
            {documents.length > 0 ? (
              <div className="result-docs-list">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="result-doc-item"
                  >
                    <FileText
                      size={14}
                      className="result-doc-icon"
                    />
                    <span className="result-doc-filename">
                      {doc.filename}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="result-docs-empty">
                No documents found.
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Result;
