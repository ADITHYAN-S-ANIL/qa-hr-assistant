import React, { useState, useEffect, useRef } from 'react';
import { Send, User as UserIcon } from 'lucide-react';

export default function CompanyChat({ user, token }) {
  const [messages, setMessages] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    if (selectedUserId) {
      fetchMessages(selectedUserId);
      const interval = setInterval(() => fetchMessages(selectedUserId), 5000); // simple polling
      return () => clearInterval(interval);
    }
  }, [selectedUserId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/users', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) {
        // Filter out self
        setUsers(data.users.filter(u => u.id !== user.id));
      }
    } catch (err) { console.error(err); }
  };

  const fetchMessages = async (otherUserId) => {
    try {
      const res = await fetch(`/api/company/chat?user_id=${otherUserId}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setMessages(data.messages);
    } catch (err) { console.error(err); }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedUserId) return;
    try {
      const res = await fetch('/api/company/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ receiver_id: selectedUserId, content: newMessage })
      });
      const data = await res.json();
      if (data.success) {
        setNewMessage('');
        fetchMessages(selectedUserId);
      }
    } catch (err) { console.error(err); }
  };

  return (
    <div style={{ display: 'flex', height: '80vh', border: '1px solid #ddd', borderRadius: '12px', overflow: 'hidden', background: 'white' }}>
      {/* Sidebar - User List */}
      <div style={{ width: '300px', borderRight: '1px solid #ddd', background: '#f8f9fa', overflowY: 'auto' }}>
        <h3 style={{ padding: '20px', margin: 0, borderBottom: '1px solid #eee', background: '#fff' }}>Company Chat</h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {users.map(u => (
            <li 
              key={u.id} 
              onClick={() => setSelectedUserId(u.id)}
              style={{ 
                padding: '15px 20px', 
                borderBottom: '1px solid #eee', 
                cursor: 'pointer',
                background: selectedUserId === u.id ? '#eaf2f8' : 'transparent',
                display: 'flex', alignItems: 'center', gap: '10px'
              }}
            >
              <div style={{ padding: '8px', background: '#ccc', borderRadius: '50%', color: 'white' }}><UserIcon size={16} /></div>
              <div>
                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{u.email}</div>
                <div style={{ fontSize: '12px', color: '#777', textTransform: 'capitalize' }}>{u.role}</div>
              </div>
            </li>
          ))}
          {users.length === 0 && <li style={{ padding: '20px', color: '#777', textAlign: 'center' }}>No users available to chat.</li>}
        </ul>
      </div>

      {/* Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {selectedUserId ? (
          <>
            <div style={{ padding: '20px', borderBottom: '1px solid #ddd', background: '#fff', fontWeight: 'bold' }}>
              Chatting with {users.find(u => u.id === selectedUserId)?.email}
            </div>
            
            <div style={{ flex: 1, padding: '20px', overflowY: 'auto', background: '#fafafa' }}>
              {messages.length === 0 ? (
                <div style={{ textAlign: 'center', color: '#999', marginTop: '20px' }}>No messages yet. Say hi!</div>
              ) : (
                messages.map(m => {
                  const isMe = m.sender_id === user.id;
                  return (
                    <div key={m.id} style={{ display: 'flex', justifyContent: isMe ? 'flex-end' : 'flex-start', marginBottom: '15px' }}>
                      <div style={{ 
                        maxWidth: '70%', 
                        padding: '12px 16px', 
                        borderRadius: '16px', 
                        background: isMe ? '#3498db' : '#ecf0f1', 
                        color: isMe ? 'white' : '#333',
                        borderBottomRightRadius: isMe ? '4px' : '16px',
                        borderBottomLeftRadius: isMe ? '16px' : '4px'
                      }}>
                        <div style={{ fontSize: '14px' }}>{m.content}</div>
                        <div style={{ fontSize: '10px', color: isMe ? '#eaf2f8' : '#999', textAlign: 'right', marginTop: '4px' }}>
                          {new Date(m.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={sendMessage} style={{ padding: '20px', borderTop: '1px solid #ddd', background: '#fff', display: 'flex', gap: '10px' }}>
              <input 
                type="text" 
                value={newMessage} 
                onChange={e => setNewMessage(e.target.value)} 
                placeholder="Type your message..." 
                style={{ flex: 1, padding: '12px', border: '1px solid #ccc', borderRadius: '24px', outline: 'none' }} 
              />
              <button type="submit" style={{ padding: '12px', background: '#3498db', color: 'white', border: 'none', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '45px', height: '45px' }}>
                <Send size={18} />
              </button>
            </form>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
            Select a user from the sidebar to start chatting.
          </div>
        )}
      </div>
    </div>
  );
}
