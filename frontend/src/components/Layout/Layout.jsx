import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, MessageCircle, Bot, Calendar } from 'lucide-react';

export default function Layout({ user, token, onLogout }) {
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', fontFamily: 'Inter, sans-serif' }}>
      {/* Sidebar */}
      <div style={{ width: '250px', background: '#2c3e50', color: 'white', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px', fontSize: '24px', fontWeight: 'bold', borderBottom: '1px solid #34495e' }}>
          Company HQ
        </div>
        
        <nav style={{ flex: 1, padding: '20px 0', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <NavLink 
            to="/" 
            onClick={() => {
              if (window.location.pathname === '/') {
                window.location.hash = '';
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }
            }}
            style={({ isActive }) => ({
              padding: '12px 20px', 
              color: isActive && window.location.hash !== '#leaves' ? 'white' : '#bdc3c7',
              textDecoration: 'none',
              background: isActive && window.location.hash !== '#leaves' ? '#34495e' : 'transparent',
              display: 'flex', alignItems: 'center', gap: '10px'
            })}
            end
          >
            <LayoutDashboard size={18} /> Dashboard
          </NavLink>

          {user && user.role === 'ceo' && (
            <NavLink 
              to="/#leaves" 
              onClick={(e) => {
                if (window.location.pathname === '/') {
                  e.preventDefault();
                  window.location.hash = 'leaves';
                  document.getElementById('leave-requests-section')?.scrollIntoView({ behavior: 'smooth' });
                }
              }}
              style={{
                padding: '12px 20px', 
                color: window.location.hash === '#leaves' && window.location.pathname === '/' ? 'white' : '#bdc3c7',
                textDecoration: 'none',
                background: window.location.hash === '#leaves' && window.location.pathname === '/' ? '#34495e' : 'transparent',
                display: 'flex', alignItems: 'center', gap: '10px'
              }}
            >
              <Calendar size={18} /> Leaves
            </NavLink>
          )}
          



          <NavLink 
            to="/ai-chat" 
            onClick={() => { window.location.hash = ''; }}
            style={({ isActive }) => ({
              padding: '12px 20px', 
              color: isActive ? 'white' : '#bdc3c7',
              textDecoration: 'none',
              background: isActive ? '#34495e' : 'transparent',
              display: 'flex', alignItems: 'center', gap: '10px'
            })}
          >
            <Bot size={18} /> AI Assistant
          </NavLink>
        </nav>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#ecf0f1', overflowY: 'auto' }}>
        <Outlet />
      </div>
    </div>
  );
}
