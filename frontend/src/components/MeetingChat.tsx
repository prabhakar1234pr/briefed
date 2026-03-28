"use client";

import { useState, useCallback, useRef } from "react";
import {
  useExternalStoreRuntime,
  type ThreadMessageLike,
  type AppendMessage,
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
} from "@assistant-ui/react";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { askAgent } from "@/lib/meeting-api";

type Props = {
  agentId: string;
  agentName: string;
  meetingId: string;
  meetingStatus: string;
};

export function MeetingChat({ agentId, agentName, meetingId }: Props) {
  const [messages, setMessages] = useState<ThreadMessageLike[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const idCounter = useRef(0);

  const onNew = useCallback(
    async (message: AppendMessage) => {
      const userText =
        message.content
          ?.filter((p): p is { type: "text"; text: string } => p.type === "text")
          .map((p) => p.text)
          .join("\n") ?? "";

      if (!userText.trim()) return;

      setMessages((prev) => [
        ...prev,
        { role: "user" as const, content: [{ type: "text" as const, text: userText }] },
      ]);
      setIsRunning(true);

      try {
        const result = await askAgent(agentId, userText, meetingId);
        setMessages((prev) => [
          ...prev,
          { role: "assistant" as const, content: [{ type: "text" as const, text: result.answer }] },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant" as const, content: [{ type: "text" as const, text: `Error: ${String(err)}` }] },
        ]);
      } finally {
        setIsRunning(false);
      }
    },
    [agentId, meetingId],
  );

  const runtime = useExternalStoreRuntime({
    messages,
    isRunning,
    onNew,
    convertMessage: (msg: ThreadMessageLike) => msg,
  });

  return (
    <div className="meeting-chat-container">
      <div className="meeting-chat-header">
        <p className="meeting-chat-label">Ask {agentName}</p>
        <p className="meeting-chat-subtitle">
          Ask anything about this meeting using the knowledge base.
        </p>
      </div>

      <AssistantRuntimeProvider runtime={runtime}>
        <div className="meeting-chat-thread">
          <ThreadPrimitive.Root>
            <ThreadPrimitive.Viewport className="meeting-chat-viewport">
              <ThreadPrimitive.Messages
                components={{
                  UserMessage: UserMessage,
                  AssistantMessage: AssistantMessage,
                }}
              />
            </ThreadPrimitive.Viewport>

            <div className="meeting-chat-composer-wrap">
              <ComposerPrimitive.Root className="meeting-chat-composer">
                <ComposerPrimitive.Input
                  placeholder="What was decided about...?"
                  className="meeting-chat-input"
                />
                <ComposerPrimitive.Send className="meeting-chat-send">
                  {isRunning ? (
                    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
                      <circle cx="6.5" cy="6.5" r="4.5" stroke="rgba(255,255,255,0.3)" strokeWidth="1.4" />
                      <path d="M6.5 2a4.5 4.5 0 0 1 4.5 4.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" />
                    </svg>
                  ) : (
                    <span>&rarr;</span>
                  )}
                </ComposerPrimitive.Send>
              </ComposerPrimitive.Root>
            </div>
          </ThreadPrimitive.Root>
        </div>
      </AssistantRuntimeProvider>

      <style>{`
        .meeting-chat-container {
          background: rgba(59,130,246,0.04);
          border: 1px solid rgba(59,130,246,0.12);
          border-radius: var(--radius-lg, 12px);
          padding: 22px;
          display: flex;
          flex-direction: column;
          max-height: 480px;
        }
        .meeting-chat-header {
          margin-bottom: 14px;
        }
        .meeting-chat-label {
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0.1em;
          color: var(--text-tertiary);
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .meeting-chat-subtitle {
          font-size: 12px;
          color: var(--text-secondary);
          line-height: 1.6;
        }
        .meeting-chat-thread {
          flex: 1;
          min-height: 0;
          display: flex;
          flex-direction: column;
        }
        .meeting-chat-viewport {
          flex: 1;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 10px;
          max-height: 300px;
          padding: 4px 0;
        }
        .meeting-chat-viewport::-webkit-scrollbar {
          width: 4px;
        }
        .meeting-chat-viewport::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.1);
          border-radius: 4px;
        }
        .meeting-chat-msg {
          padding: 10px 12px;
          border-radius: 8px;
          font-size: 13px;
          line-height: 1.7;
          max-width: 95%;
        }
        .meeting-chat-msg-user {
          background: rgba(59,130,246,0.15);
          border: 1px solid rgba(59,130,246,0.2);
          color: var(--text-primary);
          align-self: flex-end;
        }
        .meeting-chat-msg-assistant {
          background: rgba(255,255,255,0.04);
          border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
          color: var(--text-secondary);
        }
        .meeting-chat-msg-role {
          font-size: 10px;
          font-weight: 500;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          color: var(--text-tertiary);
          margin-bottom: 4px;
        }
        .meeting-chat-composer-wrap {
          margin-top: 10px;
        }
        .meeting-chat-composer {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        .meeting-chat-input {
          flex: 1;
          background: var(--bg-elevated, #161b24);
          border: 1px solid var(--border-subtle, rgba(255,255,255,0.08));
          border-radius: 8px;
          padding: 10px 12px;
          font-size: 13px;
          color: var(--text-primary);
          outline: none;
          transition: border-color 0.15s;
          font-family: var(--font-sans);
        }
        .meeting-chat-input:focus {
          border-color: var(--accent, #3b82f6);
          box-shadow: 0 0 0 2px rgba(59,130,246,0.15);
        }
        .meeting-chat-input::placeholder {
          color: var(--text-tertiary);
        }
        .meeting-chat-send {
          flex-shrink: 0;
          padding: 10px 14px;
          background: var(--accent, #3b82f6);
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: background 0.15s;
          box-shadow: 0 0 16px rgba(59,130,246,0.25);
        }
        .meeting-chat-send:hover {
          background: #2563eb;
        }
        .meeting-chat-send:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="meeting-chat-msg meeting-chat-msg-user">
      <div className="meeting-chat-msg-role">You</div>
      <MessagePrimitive.Content />
    </MessagePrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="meeting-chat-msg meeting-chat-msg-assistant">
      <div className="meeting-chat-msg-role">Agent</div>
      <MessagePrimitive.Content />
    </MessagePrimitive.Root>
  );
}
