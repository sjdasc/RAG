import { useChatStore } from "../../stores/useChatStore";
import {
  MessageSquare,
  Rocket,
  PlusCircle,
  Trash2,
} from "lucide-react";
import { Link } from "react-router-dom";
// import { deleteChat } from "../../stores/useChatStore";
import "../../styles/Sidebar.css";

const Sidebar = () => {
  const {
    chats,
    currentChatId,
    selectChat,
    createNewChat,
    deleteChat, // deleteChat 가져오기
    deleteAllChats,
  } = useChatStore();

  const handleDelete = (e, chatId) => {
    e.stopPropagation(); // 부모 div의 클릭 이벤트(채팅 선택)가 발생하지 않도록 막음
    if (
      window.confirm(
        "Would you like to delete this exploring history?"
      )
    ) {
      deleteChat(chatId);
    }
  };

  return (
    <aside className="sidebar-container">
      {/* 로켓 로고 */}
      <Link to="/" className="sidebar-logo">
        <Rocket size={24} />
        <span>StarShooting</span>
      </Link>

      {/* 새로운 탐사 버튼 */}
      <Link
        to="/"
        className="sidebar-new-chat-btn"
      >
        <PlusCircle size={20} />

        <button onClick={createNewChat}>
          <span>Start new exploring</span>
        </button>
      </Link>
      {/*채팅 목록영역 */}
      <div className="flex-1 overflow-y-auto pr-2">
        <h3 className="sidebar-history-title">
          Exploring History
        </h3>

        {chats.length === 0 ? (
          <p className="sidebar-history-empty">
            No exploring history found.
          </p>
        ) : (
          chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => selectChat(chat.id)}
              // group 클래스를 추가하여 호버 시 자식 요소(삭제 버튼)를 제어
              className={
                currentChatId === chat.id
                  ? "sidebar-history-item-active group"
                  : "sidebar-history-item group"
              }
            >
              <span className="truncate flex-1">
                {chat.title}
              </span>

              {/* 삭제 버튼: 평소엔 숨겨져 있다가(opacity-0), 마우스를 올리면 나타남(group-hover:opacity-100) */}
              <button
                onClick={(e) =>
                  handleDelete(e, chat.id)
                }
                className="sidebar-delete-btn"
                title="Delete chat"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>
      <div className="mt-4 pt-4 border-t border-space-border">
        <button
          onClick={() => {
            if (
              window.confirm(
                "Would you like to delete all exploring history?"
              )
            ) {
              deleteAllChats();
            }
          }}
          className="sidebar-delete-all-btn"
        >
          <Trash2 size={16} />
          <span>Delete all history</span>
        </button>
      </div>
      <div className="sidebar-user-info">
        User: Astronaut_01
      </div>
    </aside>
  );
};

export default Sidebar;
