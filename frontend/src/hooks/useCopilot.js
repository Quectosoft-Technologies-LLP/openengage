// src/hooks/useCopilot.js — WebSocket hook for real-time AI Copilot
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_BASE = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

export function useCopilot(sessionId) {
  const [messages, setMessages]   = useState([]);
  const [isThinking, setThinking] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const thinkBuf = useRef('');

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/copilot/${sessionId}`);
    wsRef.current = ws;

    ws.onopen  = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);

      if (data.type === 'thinking') {
        setThinking(true);
        thinkBuf.current += data.content;
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === 'thinking') {
            return [...prev.slice(0, -1), { ...last, content: thinkBuf.current }];
          }
          return [...prev, { role: 'thinking', content: thinkBuf.current, id: Date.now() }];
        });
      }

      if (data.type === 'response') {
        setThinking(false);
        thinkBuf.current = '';
        setMessages(prev => {
          // Remove thinking bubble, add final response
          const filtered = prev.filter(m => m.role !== 'thinking');
          return [...filtered, {
            role: 'assistant',
            content: data.content,
            agent: data.agent,
            id: Date.now(),
          }];
        });
      }
    };

    return () => ws.close();
  }, [sessionId]);

  const send = useCallback((text) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    setMessages(prev => [...prev, { role: 'user', content: text, id: Date.now() }]);
    wsRef.current.send(text);
  }, []);

  const clear = useCallback(() => setMessages([]), []);

  return { messages, isThinking, connected, send, clear };
}
