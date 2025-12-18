import { create } from "zustand";

export const useChatStore = create(
  (set, get) => ({
    currentResult: null, // 현재 보고 있는 결과
    isLoading: false,
    // 추가!!!!!!
    // 채팅 목록 (각 채팅은 id, title, messages 등을 가짐)
    chats: [],
    // 현재 선택된 채팅 ID
    currentChatId: null,
    // 현재 채팅방의 문서 목록
    documents: [],

    // 새로운 채팅 생성 액션
    createNewChat: () => {
      const newChat = {
        id: Date.now(), // 고유 ID 생성 (간단히 타임스탬프 사용)
        title: `Exploration ${new Date().toLocaleTimeString()}`, // 기본 제목
        messages: [], // 빈 메시지 배열
      };

      set((state) => ({
        chats: [newChat, ...state.chats], // 새 채팅을 목록 맨 앞에 추가
        currentChatId: newChat.id, // 새로 만든 채팅을 현재 채팅으로 선택
        documents: [], // 새 채팅이므로 문서 목록 초기화
      }));
    },

    // 채팅 선택 액션
    selectChat: (chatId) => {
      const currentId = get().currentChatId;

      // 같은 채팅방을 클릭했을 때
      if (String(currentId) === String(chatId)) {
        // 문서는 유지하고(초기화 X), 결과 화면만 닫아서 홈으로 이동
        set({ currentResult: null });
        return;
      }

      // 다른 채팅방을 클릭했을 때: 해당 채팅방으로 전환
      set({
        currentChatId: chatId,
        currentResult: null, // 홈 화면으로 이동 (문서 목록 보기 위해)
        documents: [], // 로딩 전 초기화 (깜빡임 방지)
      });

      // 문서 목록 새로고침
      get().fetchDocuments(chatId);
    },

    // 문서 목록 가져오기
    fetchDocuments: async (chatId) => {
      if (!chatId) return;
      try {
        // 캐시 방지를 위해 타임스탬프 추가
        const response = await fetch(
          `/api/documents?session_id=${chatId}&_t=${Date.now()}`
        );
        if (response.ok) {
          console.log(response);
          const data = await response.json();

          set({
            documents: data.documents || [],
          });
        } else {
          console.error(
            "Failed to fetch documents: Server error"
          );
        }
      } catch (error) {
        console.error(
          "Failed to fetch documents:",
          error
        );
      }
    },

    // 파일을 쏘아올리는 동작 (API 연결)
    launchFiles: async (files) => {
      // 현재 채팅방 ID 확인 (없으면 생성하거나 에러 처리)
      let chatId = get().currentChatId;
      console.log(
        "Uploading files to chat ID:",
        chatId
      );
      if (!chatId) {
        // 채팅방이 없으면 새로 생성 후 ID 가져오기
        get().createNewChat();
        chatId = get().currentChatId;
      }

      set({ isLoading: true });

      const formData = new FormData();
      // FileList를 배열로 변환하여 추가
      Array.from(files).forEach((file) => {
        formData.append("files", file);
      });
      // 세션 ID 추가
      formData.append("session_id", chatId);

      try {
        const response = await fetch(
          "/api/upload",
          {
            method: "POST",
            body: formData,
          }
        );

        if (response.ok) {
          alert(
            `${files.length} star(s) launched successfully!`
          );
          // 업로드 후 인덱싱 요청 (세션 ID 포함)
          await fetch(
            `/api/reindex?session_id=${chatId}`
          );
          // 문서 목록 갱신 (await 추가하여 상태 업데이트 보장)
          await get().fetchDocuments(chatId);
        } else {
          alert("File upload failed");
        }
      } catch (error) {
        console.error(error);
        alert("Server connection error");
      } finally {
        set({ isLoading: false });
      }
    },

    // 질문하기 동작 (API 연결)
    askQuestion: async (query) => {
      // 현재 채팅방 ID 확인 (없으면 생성)
      let chatId = get().currentChatId;
      if (!chatId) {
        get().createNewChat();
        chatId = get().currentChatId;
      }

      set({ isLoading: true });

      try {
        const response = await fetch(
          "/api/chat",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              query,
              session_id: String(chatId), // 세션 ID 전달 (문자열 변환)
            }),
          }
        );
        console.log(response);
        const data = await response.json();
        console.log(data);
        set({
          isLoading: false,
          currentResult: {
            query: query,
            answer: data.answer, // 서버에서 온 답변
            sources: data.sources || [], // 서버에서 온 출처
            results: data.results || [], // 상세 결과 (벡터 포함)
            query_vector_3d:
              data.query_vector_3d || [0, 0, 0], // 쿼리 벡터
          },
        });
      } catch (error) {
        console.error(error);
        set({ isLoading: false });
        alert("Failed to receive an answer.");
      }
    },

    // --- 추가된 삭제 로직 ---
    deleteChat: async (chatId) => {
      // 1. 서버에 삭제 요청 (비동기)
      try {
        await fetch(`/api/session/${chatId}`, {
          method: "DELETE",
        });
      } catch (error) {
        console.error(
          "Failed to delete session data:",
          error
        );
      }

      set((state) => {
        // 2. 삭제할 채팅을 제외한 새 목록 생성
        const newChats = state.chats.filter(
          (chat) => chat.id !== chatId
        );

        // 3. 만약 현재 보고 있는 채팅을 삭제했다면?
        let newCurrentId = state.currentChatId;
        if (state.currentChatId === chatId) {
          // 남은 채팅이 있으면 첫 번째 것을 선택, 없으면 null
          newCurrentId =
            newChats.length > 0
              ? newChats[0].id
              : null;
        }

        // 4. 채팅방이 하나도 없게 되면 자동으로 새 채팅방 생성
        if (newChats.length === 0) {
          const newChat = {
            id: Date.now(),
            title: `New exploration ${new Date().toLocaleTimeString()}`,
            messages: [],
          };
          return {
            chats: [newChat],
            currentChatId: newChat.id,
            documents: [],
            currentResult: null,
          };
        }

        return {
          chats: newChats,
          currentChatId: newCurrentId,
          // 현재 보고 있던 채팅을 삭제했으면 문서 목록과 결과도 초기화
          documents:
            state.currentChatId === chatId
              ? []
              : state.documents,
          currentResult:
            state.currentChatId === chatId
              ? null
              : state.currentResult,
        };
      });
    },

    // --- 모든 채팅 삭제 로직 ---
    deleteAllChats: async () => {
      try {
        await fetch("/api/sessions", {
          method: "DELETE",
        });
      } catch (error) {
        console.error(
          "Failed to delete all sessions:",
          error
        );
      }

      // 모든 채팅 삭제 후 새 채팅 하나 생성
      const newChat = {
        id: Date.now(),
        title: `Exploration ${new Date().toLocaleTimeString()}`,
        messages: [],
      };

      set({
        chats: [newChat],
        currentChatId: newChat.id,
        documents: [],
        currentResult: null,
      });
    },

    // --- 추가된 이름 변경 로직 ---
    updateChatTitle: (chatId, newTitle) => {
      set((state) => ({
        chats: state.chats.map((chat) =>
          chat.id === chatId
            ? { ...chat, title: newTitle }
            : chat
        ),
      }));
    },
  })
);
