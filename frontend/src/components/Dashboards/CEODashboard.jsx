import React, { useState, useEffect, useMemo } from 'react';
import { LogOut, BarChart3, Users, LayoutDashboard, History, Filter, Search, X } from 'lucide-react';


const FILTERS = [
  { key: 'all',    label: 'All Time' },
  { key: 'daily',  label: 'Today'    },
  { key: 'weekly', label: 'This Week'},
  { key: 'yearly', label: 'This Year'},
];

export default function CEODashboard({ user, token, onLogout }) {
  const [teamTasks, setTeamTasks]       = useState([]);
  const [historyTasks, setHistoryTasks] = useState([]);
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [teamMembers, setTeamMembers]   = useState([]);
  const [taskFilter, setTaskFilter]     = useState('all');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [searchQuery, setSearchQuery]   = useState('');

  useEffect(() => {
    fetchTeamTasks('all');
    fetchLeaveRequests();
    fetchTeamMembers();
  }, []);

  useEffect(() => {
    if (window.location.hash === '#leaves') {
      setTimeout(() => {
        document.getElementById('leave-requests-section')?.scrollIntoView({ behavior: 'smooth' });
      }, 300);
    }
  }, []);

  // Keep summary stats always using full list
  const fetchTeamTasks = async (filter = 'all') => {
    try {
      const res = await fetch(`/api/tasks?filter=${filter}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) setTeamTasks(data.tasks);
    } catch (err) { console.error(err); }
  };

  const fetchHistoryTasks = async (filter) => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`/api/tasks?filter=${filter}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) setHistoryTasks(data.tasks);
    } catch (err) { console.error(err); }
    finally { setHistoryLoading(false); }
  };

  const handleFilterChange = (filter) => {
    setTaskFilter(filter);
    fetchHistoryTasks(filter);
  };

  // Load initial task history on mount
  useEffect(() => { fetchHistoryTasks('all'); }, []);

  const fetchLeaveRequests = async () => {
    try {
      const res = await fetch('/api/leaves', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setLeaveRequests(data.leaves);
    } catch (err) { console.error(err); }
  };

  const fetchTeamMembers = async () => {
    try {
      const res = await fetch('/api/users', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setTeamMembers(data.users);
    } catch (err) { console.error(err); }
  };

  const handleAssignManager = async (userId, managerId) => {
    try {
      const res = await fetch(`/api/users/${userId}/manager`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ manager_id: managerId }),
      });
      if ((await res.json()).success) fetchTeamMembers();
    } catch (err) { console.error(err); }
  };

  const handleUpdateRole = async (userId, newRole) => {
    try {
      const res = await fetch(`/api/users/${userId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ role: newRole }),
      });
      if ((await res.json()).success) {
        fetchTeamMembers();
        fetchLeaveRequests(); // Managers affect leave rendering
      }
    } catch (err) { console.error(err); }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Delete this user and all their data?')) return;
    try {
      const res = await fetch(`/api/users/${userId}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      if ((await res.json()).success) {
        fetchTeamMembers(); fetchTeamTasks('all'); fetchLeaveRequests(); fetchHistoryTasks(taskFilter);
      }
    } catch (err) { console.error(err); }
  };

  const handleDeleteLeave = async (leaveId) => {
    if (!window.confirm('Delete this leave? Balances will be reverted if it was approved.')) return;
    try {
      const res = await fetch(`/api/leaves/${leaveId}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      if ((await res.json()).success) { fetchLeaveRequests(); fetchTeamMembers(); }
    } catch (err) { console.error(err); }
  };

  const handleLeaveApproval = async (leaveId, status) => {
    try {
      const res = await fetch(`/api/leaves/${leaveId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status }),
      });
      const data = await res.json();
      if (data.success) { fetchLeaveRequests(); fetchTeamMembers(); }
      else alert(`❌ ${data.message}`);
    } catch (err) { console.error(err); }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Delete this task entry permanently?')) return;
    try {
      const res = await fetch(`/api/tasks/${taskId}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      if ((await res.json()).success) {
        fetchHistoryTasks(taskFilter);
        fetchTeamTasks('all'); // refresh stat card too
      }
    } catch (err) { console.error(err); }
  };

  // ── helper style ──
  const q = searchQuery.toLowerCase().trim();

  const filteredHistory = useMemo(() =>
    q ? historyTasks.filter(t =>
      (t.user_email || '').toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q) ||
      (t.employee_id || '').toLowerCase().includes(q)
    ) : historyTasks,
  [historyTasks, q]);

  const filteredMembers = useMemo(() =>
    q ? teamMembers.filter(m =>
      (m.email || '').toLowerCase().includes(q) ||
      (m.employee_id || '').toLowerCase().includes(q)
    ) : teamMembers,
  [teamMembers, q]);

  const filteredLeaves = useMemo(() =>
    q ? leaveRequests.filter(l =>
      (l.user_email || '').toLowerCase().includes(q) ||
      (l.reason || '').toLowerCase().includes(q)
    ) : leaveRequests,
  [leaveRequests, q]);

  const card = {
    background: 'white', borderRadius: '12px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.06)', padding: '20px',
  };
  const filterBtn = (active) => ({
    padding: '8px 18px', borderRadius: '20px', border: 'none', cursor: 'pointer',
    fontWeight: 600, fontSize: '13px', transition: 'all .2s',
    background: active ? '#8e44ad' : '#f0e6f8',
    color: active ? 'white' : '#8e44ad',
  });
  const th = { padding: '12px 14px', fontWeight: 600, fontSize: '13px', color: '#555' };
  const td = { padding: '12px 14px', fontSize: '14px', borderBottom: '1px solid #f0f0f0' };

  return (
    <div style={{ padding: '24px', fontFamily: 'Inter, sans-serif', background: '#f5f6fa', minHeight: '100vh' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '28px', padding: '20px 24px',
        background: 'linear-gradient(135deg, #8e44ad, #6c3483)', color: 'white', borderRadius: '14px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '26px', fontWeight: 700 }}>CEO Dashboard</h1>
          <p style={{ margin: '4px 0 0', color: '#e8daef', fontSize: '14px' }}>
            Company Overview & Performance Tracking
          </p>
        </div>
        <button onClick={onLogout} style={{ display: 'flex', alignItems: 'center', gap: '6px',
          padding: '9px 18px', background: 'rgba(255,255,255,0.15)', color: 'white',
          border: '1px solid rgba(255,255,255,0.3)', borderRadius: '8px', cursor: 'pointer' }}>
          <LogOut size={15} /> Logout
        </button>
      </div>

      {/* ── Stat Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '18px', marginBottom: '28px' }}>
        {[
          { icon: <Users size={22} />, label: 'Total Workforce',   value: teamMembers.length,                         bg: '#f5eef8', color: '#8e44ad' },
          { icon: <BarChart3 size={22} />, label: 'Completed Tasks', value: teamTasks.filter(t => t.status === 'completed').length, bg: '#eaf2f8', color: '#2980b9' },
          { icon: <LayoutDashboard size={22} />, label: 'Pending Leaves', value: leaveRequests.filter(l => l.status === 'pending').length, bg: '#fcf3cf', color: '#d4ac0d' },
        ].map(({ icon, label, value, bg, color }) => (
          <div key={label} style={{ ...card, display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ padding: '14px', background: bg, borderRadius: '50%', color }}>{icon}</div>
            <div>
              <div style={{ color: '#999', fontSize: '13px', marginBottom: '4px' }}>{label}</div>
              <div style={{ fontSize: '28px', fontWeight: 700, color: '#2c3e50' }}>{value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── Global Search Bar ── */}
      <div style={{ position: 'relative', marginBottom: '20px' }}>
        <Search size={17} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: '#aaa' }} />
        <input
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search by employee email, ID, task or leave reason…"
          style={{ width: '100%', padding: '12px 42px 12px 44px', border: '1px solid #ddd',
            borderRadius: '10px', fontSize: '14px', outline: 'none', background: 'white',
            boxShadow: '0 2px 8px rgba(0,0,0,0.06)', boxSizing: 'border-box' }}
        />
        {searchQuery && (
          <button onClick={() => setSearchQuery('')}
            style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', color: '#aaa', padding: '4px' }}>
            <X size={16} />
          </button>
        )}
      </div>
      {q && (
        <div style={{ marginBottom: '16px', padding: '8px 14px', background: '#f5eef8',
          borderRadius: '8px', fontSize: '13px', color: '#8e44ad', fontWeight: 500 }}>
          🔍 Results for "<strong>{searchQuery}</strong>" — {filteredHistory.length} task{filteredHistory.length !== 1 ? 's' : ''},&nbsp;
          {filteredMembers.length} member{filteredMembers.length !== 1 ? 's' : ''},&nbsp;
          {filteredLeaves.length} leave{filteredLeaves.length !== 1 ? 's' : ''}
        </div>
      )}

      {/* ── Task History with Filters ── */}
      <div style={{ ...card, marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#2c3e50' }}>
            <History size={20} color="#8e44ad" /> Task History
          </h2>
          {/* Filter Buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Filter size={16} color="#8e44ad" />
            {FILTERS.map(f => (
              <button
                key={f.key}
                onClick={() => handleFilterChange(f.key)}
                style={filterBtn(taskFilter === f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: '30px', color: '#999' }}>Loading…</div>
        ) : filteredHistory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px', color: '#bbb' }}>No tasks found{q ? ` for "${searchQuery}"` : ' for this period.'}.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#fafafa', textAlign: 'left' }}>
                <th style={th}>Employee</th>
                <th style={th}>Task Description</th>
                <th style={th}>Date & Time</th>
                <th style={th}>Status</th>
                <th style={th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.map(t => (
                <tr key={t.id} style={{ transition: 'background .15s' }}
                  onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={td}>
                    <div style={{ fontWeight: 600 }}>{hlText(t.user_email, q)}</div>
                    {t.employee_id && <div style={{ fontSize: '11px', color: '#aaa' }}>{t.employee_id}</div>}
                  </td>
                  <td style={{ ...td, maxWidth: '340px' }}>{hlText(t.description, q)}</td>
                  <td style={{ ...td, whiteSpace: 'nowrap', color: '#777' }}>
                    <div>{new Date(t.created_at).toLocaleDateString()}</div>
                    <div style={{ fontSize: '11px', color: '#bbb' }}>{new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                  </td>
                  <td style={td}>
                    <span style={{
                      padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700,
                      background: t.status === 'completed' ? '#d4edda' : '#fff3cd',
                      color:      t.status === 'completed' ? '#155724' : '#856404',
                    }}>
                      {t.status.toUpperCase()}
                    </span>
                  </td>
                  <td style={td}>
                    <button
                      onClick={() => handleDeleteTask(t.id)}
                      style={{ padding: '5px 12px', background: '#c0392b', color: 'white',
                        border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div style={{ marginTop: '12px', fontSize: '13px', color: '#aaa', textAlign: 'right' }}>
          {historyTasks.length} task{historyTasks.length !== 1 ? 's' : ''} shown
        </div>
      </div>

      {/* ── Workforce Table ── */}
      <div style={{ ...card, marginBottom: '24px' }}>
        <h2 style={{ marginTop: 0, color: '#2c3e50', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Users size={20} color="#8e44ad" /> Workforce
        </h2>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#fafafa', textAlign: 'left' }}>
              {['Username', 'Role', 'Total Leaves', 'Used Leaves', 'Manager', 'Actions'].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredMembers.map(m => (
              <tr key={m.id}
                onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                <td style={td}>
                    <div style={{ fontWeight: 600 }}>{hlText(m.email, q)}</div>
                    {m.employee_id && <div style={{ fontSize: '11px', color: '#aaa' }}>{hlText(m.employee_id, q)}</div>}
                </td>
                <td style={{ ...td, textTransform: 'capitalize', fontWeight: m.role === 'manager' ? 700 : 400 }}>
                  {m.id === user.id ? (
                    m.role
                  ) : (
                    <select value={m.role} onChange={e => handleUpdateRole(m.id, e.target.value)}
                      style={{ padding: '5px 8px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '13px', textTransform: 'capitalize', fontWeight: m.role === 'manager' ? 700 : 400 }}>
                      <option value="employee">Employee</option>
                      <option value="manager">Manager</option>
                    </select>
                  )}
                </td>
                <td style={td}>{m.total_leaves}</td>
                <td style={td}>{m.used_leaves}</td>
                <td style={td}>
                  {m.role === 'employee' ? (
                    <select value={m.manager_id || ''} onChange={e => handleAssignManager(m.id, e.target.value)}
                      style={{ padding: '5px 8px', borderRadius: '6px', border: '1px solid #ddd', fontSize: '13px' }}>
                      <option value="">Unassigned</option>
                      {teamMembers.filter(u => u.role === 'manager').map(mgr => (
                        <option key={mgr.id} value={mgr.id}>{mgr.email}</option>
                      ))}
                    </select>
                  ) : <span style={{ color: '#ccc' }}>—</span>}
                </td>
                <td style={td}>
                  {m.id !== user.id && (
                    <button onClick={() => handleDeleteUser(m.id)}
                      style={{ padding: '5px 12px', background: '#c0392b', color: 'white',
                        border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Leave Requests ── */}
      <div id="leave-requests-section" style={card}>
        <h2 style={{ marginTop: 0, color: '#2c3e50' }}>Company Leave Requests</h2>
        <p style={{ fontSize: '13px', color: '#888', marginTop: '-8px', marginBottom: '16px' }}>
          Includes all employee and manager leave requests. Only the CEO can approve/reject manager leaves.
        </p>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#fafafa', textAlign: 'left' }}>
              {['Employee', 'Role', 'Dates', 'Type', 'Reason', 'Status', 'Actions'].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredLeaves.map(l => {
              const member = teamMembers.find(m => m.email === l.user_email);
              const memberRole = member ? member.role : 'employee';
              const avail = member ? member.total_leaves - member.used_leaves : 0;
              const reqDays = l.type === 'half-day' ? 0.5 : Math.round((new Date(l.end_date) - new Date(l.start_date)) / 86400000) + 1;
              const overLimit = (l.type === 'regular' || l.type === 'half-day') && reqDays > avail;
              return (
                <tr key={l.id}
                  onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={td}>
                    <div style={{ fontWeight: 600 }}>{hlText(l.user_email, q)}</div>
                  </td>
                  <td style={td}>
                    <span style={{
                      padding: '3px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: 700,
                      textTransform: 'capitalize',
                      background: memberRole === 'manager' ? '#e8f4fd' : '#f0f0f0',
                      color: memberRole === 'manager' ? '#1a5276' : '#555',
                    }}>{memberRole}</span>
                  </td>
                  <td style={{ ...td, whiteSpace: 'nowrap' }}>
                    <div style={{ fontWeight: 600 }}>
                      {new Date(l.start_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })} → {new Date(l.end_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                    </div>
                    {(l.start_time || l.end_time) && (
                      <div style={{ fontSize: '11px', color: '#666', marginTop: '2px', fontWeight: 500 }}>
                        🕒 {l.start_time || '?'} - {l.end_time || '?'}
                      </div>
                    )}
                  </td>
                  <td style={{ ...td, textTransform: 'capitalize' }}>{l.type}</td>
                  <td style={{ ...td, maxWidth: '150px', color: '#666' }}>{l.reason}</td>
                  <td style={td}>
                    <span style={{
                      padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700,
                      background: l.status === 'approved' ? '#d4edda' : l.status === 'rejected' ? '#f8d7da' : '#fff3cd',
                      color:      l.status === 'approved' ? '#155724' : l.status === 'rejected' ? '#721c24' : '#856404',
                    }}>
                      {l.status.toUpperCase()}
                    </span>
                  </td>
                  <td style={td}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                      {l.status === 'pending' && (
                        <div style={{ display: 'flex', gap: '5px' }}>
                          <button onClick={() => handleLeaveApproval(l.id, 'approved')}
                            style={{ padding: '5px 10px', background: '#27ae60', color: 'white',
                              border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '11px', fontWeight: 700 }}>
                            ✓ Approve
                          </button>
                          <button onClick={() => handleLeaveApproval(l.id, 'rejected')}
                            style={{ padding: '5px 10px', background: '#e74c3c', color: 'white',
                              border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '11px', fontWeight: 700 }}>
                            ✗ Reject
                          </button>
                        </div>
                      )}
                      {l.status === 'approved' && (
                        <button onClick={() => {
                          if(window.confirm("Are you sure you want to reject this approved leave? This will override the manager's approval.")) {
                            handleLeaveApproval(l.id, 'rejected');
                          }
                        }}
                          style={{ padding: '4px 10px', background: '#e67e22', color: 'white',
                            border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '11px', fontWeight: 600 }}>
                          ✗ Reject (Override)
                        </button>
                      )}
                      {(l.type === 'regular' || l.type === 'half-day') && l.status === 'pending' && member && (
                        <div style={{ fontSize: '11px', color: overLimit ? '#e74c3c' : '#7f8c8d' }}>
                          {overLimit ? `⛔ ${avail} left, needs ${reqDays}` : `Balance: ${avail} left`}
                        </div>
                      )}
                      <button onClick={() => handleDeleteLeave(l.id)}
                        style={{ padding: '4px 10px', background: '#95a5a6', color: 'white',
                          border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '11px', fontWeight: 600 }}>
                        🗑 Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {leaveRequests.length === 0 && (
              <tr><td colSpan="7" style={{ padding: '24px', textAlign: 'center', color: '#bbb' }}>No leave requests found.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Floating Chatbot Assistant */}

    </div>
  );
}

// Highlight matching text in search results
function hlText(text, query) {
  if (!query || !text) return text;
  const str = String(text);
  const idx = str.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return str;
  return (
    <>
      {str.slice(0, idx)}
      <mark style={{ background: '#fff176', borderRadius: '3px', padding: '0 2px' }}>
        {str.slice(idx, idx + query.length)}
      </mark>
      {str.slice(idx + query.length)}
    </>
  );
}
