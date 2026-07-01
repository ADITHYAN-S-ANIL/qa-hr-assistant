import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Bot, User, Loader2 } from 'lucide-react';

export default function FloatingChatbot({ token }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, sender: 'bot', text: 'Hello! I am Llama Mqwen. You can ask me things like:\n"What tasks were completed by employee@example.com?" or "What is the status of john@example.com?"' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [messages, isOpen]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = { id: Date.now(), sender: 'user', text: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: userMsg.text })
      });
      const data = await res.json();
      
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: data.reply || 'Sorry, I encountered an unexpected error.'
      }]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: 'Network error. Please try again later.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999, fontFamily: 'Inter, sans-serif' }}>
      
      {/* Chat Window */}
      {isOpen && (
        <div style={{
          position: 'absolute', bottom: '70px', right: '0',
          width: '350px', height: '500px',
          background: 'white', borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden', border: '1px solid #eee'
        }}>
          {/* Header */}
          <div style={{
            background: 'linear-gradient(135deg, #2980b9, #2c3e50)',
            color: 'white', padding: '16px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bot size={20} />
              <div style={{ fontWeight: 600, fontSize: '15px' }}>Llama Mqwen</div>
            </div>
            <button onClick={() => setIsOpen(false)} style={{
              background: 'none', border: 'none', color: 'white', cursor: 'pointer', padding: '4px'
            }}>
              <X size={18} />
            </button>
          </div>

          {/* Messages Area */}
          <div style={{
            flex: 1, padding: '16px', overflowY: 'auto',
            background: '#f8f9fa', display: 'flex', flexDirection: 'column', gap: '12px'
          }}>
            {messages.map(m => (
              <div key={m.id} style={{
                display: 'flex', flexDirection: m.sender === 'user' ? 'row-reverse' : 'row', gap: '8px'
              }}>
                <div style={{
                  width: '28px', height: '28px', borderRadius: '50%', flexShrink: 0,
                  background: m.sender === 'user' ? '#34495e' : '#2980b9',
                  display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'white'
                }}>
                  {m.sender === 'user' ? <User size={14} /> : <Bot size={14} />}
                </div>
                <div style={{
                  background: m.sender === 'user' ? '#2c3e50' : 'white',
                  color: m.sender === 'user' ? 'white' : '#333',
                  padding: '10px 14px', borderRadius: '12px',
                  borderTopRightRadius: m.sender === 'user' ? '4px' : '12px',
                  borderTopLeftRadius: m.sender === 'bot' ? '4px' : '12px',
                  boxShadow: '0 2px 5px rgba(0,0,0,0.05)',
                  fontSize: '13.5px', lineHeight: '1.5',
                  whiteSpace: 'pre-wrap', maxWidth: '80%'
                }}>
                  {m.text}
                </div>
              </div>
            ))}
            {isLoading && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: '#2980b9', display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'white' }}>
                  <Bot size={14} />
                </div>
                <div style={{ background: 'white', padding: '10px 14px', borderRadius: '12px', borderTopLeftRadius: '4px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', display: 'flex', alignItems: 'center', gap: '6px', color: '#888', fontSize: '13px' }}>
                  <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form onSubmit={handleSend} style={{
            padding: '14px', background: 'white', borderTop: '1px solid #eee',
            display: 'flex', gap: '8px'
          }}>
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about tasks or status..."
              style={{
                flex: 1, padding: '10px 14px', border: '1px solid #ddd', borderRadius: '20px',
                outline: 'none', fontSize: '14px'
              }}
            />
            <button type="submit" disabled={isLoading || !input.trim()} style={{
              background: '#2980b9', color: 'white', border: 'none', borderRadius: '50%',
              width: '40px', height: '40px', display: 'flex', justifyContent: 'center', alignItems: 'center',
              cursor: (isLoading || !input.trim()) ? 'not-allowed' : 'pointer',
              opacity: (isLoading || !input.trim()) ? 0.6 : 1
            }}>
              <Send size={16} style={{ marginLeft: '-2px' }} />
            </button>
          </form>
        </div>
      )}

      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '60px', height: '60px', borderRadius: '50%',
          background: 'linear-gradient(135deg, #2980b9, #2c3e50)', color: 'white',
          border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
          cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center',
          transition: 'transform 0.2s', transform: isOpen ? 'scale(0.9)' : 'scale(1)'
        }}
      >
        {isOpen ? <X size={28} /> : <MessageSquare size={28} />}
      </button>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
