import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, MessageSquare, Trash2, PlusCircle, Search, User } from 'lucide-react';

export default function Chat({ user, token, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [modelChoice, setModelChoice] = useState('qwen');
  const [searchQuery, setSearchQuery] = useState('');

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const authHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await fetch('/api/sessions', { headers: authHeaders });
      const data = await res.json();
      if (data.success) setSessions(data.sessions);
    } catch (e) {
      console.error('Failed to load sessions', e);
    }
  };

  const openSession = async (session) => {
    setActiveSession(session);
    setMessages([]);
    try {
      const res = await fetch(`/api/sessions/${session.id}/messages`, { headers: authHeaders });
      const data = await res.json();
      if (data.success) {
        setMessages(data.messages.map((m) => ({
          text: m.content,
          sender: m.role === 'assistant' ? 'bot' : 'user',
        })));
      }
    } catch (e) {
      console.error('Failed to load messages', e);
    }
  };

  const startNewChat = () => {
    setActiveSession(null);
    setMessages([]);
  };

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE', headers: authHeaders });
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (activeSession?.id === sessionId) startNewChat();
    } catch (e) {
      console.error('Failed to delete session', e);
    }
  };

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    const msgToSend = input;
    if (!msgToSend.trim() || isLoading) return;

    const userMessage = { text: msgToSend, sender: 'user' };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          message: msgToSend,
          session_id: activeSession?.id ?? null,
          chat_mode: 'general',
          model_choice: modelChoice,
        }),
      });

      const data = await res.json();

      if (data.success) {
        setMessages((prev) => [...prev, { text: data.reply, sender: 'bot' }]);
        if (!activeSession && data.session_id) {
          const newSession = { id: data.session_id, title: msgToSend.substring(0, 40) + '...' };
          setActiveSession(newSession);
          setSessions((prev) => [newSession, ...prev]);
        }
      } else {
        setMessages((prev) => [...prev, { text: `Error: ${data.message}`, sender: 'bot' }]);
      }
    } catch (e) {
      console.error('Chat error', e);
      setMessages((prev) => [...prev, { text: 'Connection error. Please try again.', sender: 'bot' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredSessions = sessions.filter(s => s.title?.toLowerCase().includes(searchQuery.toLowerCase()));

  const cardStyle = {
    background: 'white', borderRadius: '12px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.06)', overflow: 'hidden'
  };

  const parseText = (text) => {
    // Basic Markdown parser for tables and bold
    const boldParsed = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return <div dangerouslySetInnerHTML={{ __html: boldParsed.replace(/\n/g, '<br/>') }} />;
  };

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, sans-serif', background: '#f5f6fa', minHeight: '100vh', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '20px 24px',
        background: 'linear-gradient(135deg, #2980b9, #2c3e50)', color: 'white', borderRadius: '14px', flexShrink: 0 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Bot size={28} /> HR Intelligence Assistant
          </h1>
        </div>
      </div>

      {/* ── Main Workspace ── */}
      <div style={{ display: 'flex', gap: '20px', flex: 1, minHeight: 0 }}>
        


        {/* Main Chat Interface */}
        <div style={{ ...cardStyle, flex: 1, display: 'flex', flexDirection: 'column' }}>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {messages.length === 0 ? null : (
              messages.map((msg, i) => (
                <div key={i} style={{ display: 'flex', gap: '16px', flexDirection: msg.sender === 'user' ? 'row-reverse' : 'row' }}>
                  <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: msg.sender === 'user' ? '#eaf2f8' : '#f5f6fa', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {msg.sender === 'user' ? <User size={18} color="#2980b9" /> : <Bot size={18} color="#8e44ad" />}
                  </div>
                  <div style={{ maxWidth: '80%', padding: '16px 20px', borderRadius: '12px', fontSize: '14px', lineHeight: 1.6, background: msg.sender === 'user' ? '#2980b9' : '#f8f9fa', color: msg.sender === 'user' ? 'white' : '#333', border: msg.sender === 'user' ? 'none' : '1px solid #eef0f2', borderTopRightRadius: msg.sender === 'user' ? 0 : '12px', borderTopLeftRadius: msg.sender === 'bot' ? 0 : '12px', boxShadow: '0 2px 5px rgba(0,0,0,0.02)' }}>
                    {parseText(msg.text)}
                  </div>
                </div>
              ))
            )}
            
            {isLoading && (
              <div style={{ display: 'flex', gap: '16px' }}>
                 <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#f5f6fa', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Bot size={18} color="#8e44ad" />
                  </div>
                  <div style={{ padding: '16px 20px', borderRadius: '12px', borderTopLeftRadius: 0, background: '#f8f9fa', border: '1px solid #eef0f2', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#bbb', animation: 'blink 1.4s infinite both' }} />
                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#bbb', animation: 'blink 1.4s infinite both', animationDelay: '0.2s' }} />
                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#bbb', animation: 'blink 1.4s infinite both', animationDelay: '0.4s' }} />
                  </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={{ padding: '20px', borderTop: '1px solid #f0f0f0', background: '#fafbfc' }}>
            <form onSubmit={handleSend} style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', background: 'white', border: '1px solid #ddd', borderRadius: '10px', padding: '10px 14px', boxShadow: '0 2px 6px rgba(0,0,0,0.02)' }}>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend(e);
                  }
                }}
                placeholder="Ask your HR Intelligence Assistant..."
                style={{ flex: 1, border: 'none', outline: 'none', resize: 'none', padding: '6px 0', fontSize: '14px', fontFamily: 'inherit', color: '#333', maxHeight: '150px', background: 'transparent' }}
                disabled={isLoading}
              />
              <button 
                type="submit" 
                disabled={!input.trim() || isLoading}
                style={{ background: input.trim() && !isLoading ? '#2980b9' : '#e0e0e0', color: 'white', border: 'none', borderRadius: '8px', width: '38px', height: '38px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: input.trim() && !isLoading ? 'pointer' : 'default', transition: 'background .2s', flexShrink: 0 }}
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>

      </div>
      
      <style>{`
        @keyframes blink {
          0% { opacity: 0.2; }
          20% { opacity: 1; }
          100% { opacity: 0.2; }
        }
      `}</style>
    </div>
  );
}
