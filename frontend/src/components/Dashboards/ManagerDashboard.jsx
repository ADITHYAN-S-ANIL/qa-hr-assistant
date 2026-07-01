import React, { useState, useEffect, useMemo } from 'react';
import { LogOut, Users, CheckSquare, CalendarDays, Search, X, Calendar, TrendingUp, History, Trash2, Info, ShieldAlert } from 'lucide-react';


export default function ManagerDashboard({ user, token, onLogout }) {
  const [teamTasks, setTeamTasks]         = useState([]);
  const [leaveRequests, setLeaveRequests] = useState([]);
  const [myLeaves, setMyLeaves]           = useState([]);
  const [teamMembers, setTeamMembers]     = useState([]);
  const [myUser, setMyUser]               = useState(user);
  const [activeTab, setActiveTab]         = useState('tasks');
  const [searchQuery, setSearchQuery]     = useState('');

  // Leave application form state
  const [leaveData, setLeaveData] = useState({ start_date: '', end_date: '', start_time: '', end_time: '', type: 'regular', reason: '' });

  useEffect(() => {
    fetchTeamTasks();
    fetchLeaveRequests();
    fetchTeamMembers();
    fetchMyUser();
  }, []);

  const fetchMyUser = async () => {
    try {
      const res  = await fetch('/api/me', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setMyUser(data.user);
    } catch (err) { console.error(err); }
  };

  const fetchTeamTasks = async () => {
    try {
      const res  = await fetch('/api/tasks', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setTeamTasks(data.tasks);
    } catch (err) { console.error(err); }
  };

  const fetchLeaveRequests = async () => {
    try {
      const res  = await fetch('/api/leaves', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) {
        const all = data.leaves;
        // Separate: my own leaves vs team member leaves
        setMyLeaves(all.filter(l => l.user_id === user.id));
        setLeaveRequests(all.filter(l => l.user_id !== user.id));
      }
    } catch (err) { console.error(err); }
  };

  const fetchTeamMembers = async () => {
    try {
      const res  = await fetch('/api/users', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setTeamMembers(data.users);
    } catch (err) { console.error(err); }
  };

  const handleLeaveAction = async (leaveId, status) => {
    try {
      const res  = await fetch(`/api/leaves/${leaveId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status }),
      });
      const data = await res.json();
      if (data.success) {
        fetchLeaveRequests();
        fetchTeamMembers();
      } else {
        alert(`❌ ${data.message}`);
      }
    } catch (err) { console.error(err); }
  };

  // Submit manager's own leave
  const submitLeave = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/leaves', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(leaveData),
      });
      const data = await res.json();
      if (data.success) {
        setLeaveData({ start_date: '', end_date: '', start_time: '', end_time: '', type: 'regular', reason: '' });
        fetchLeaveRequests();
        fetchMyUser();
        alert('✅ Leave request submitted! The CEO will review your request. Check "My Leave History" tab.');
      } else {
        alert(`❌ ${data.message}`);
      }
    } catch (err) { console.error(err); }
  };

  // Submit manager's comp-off
  const submitCompOff = async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
      start_date: form.start.value,
      end_date: form.end.value,
      start_time: form.start_time.value,
      end_time: form.end_time.value,
      type: 'comp-off',
      reason: form.reason.value,
    };
    try {
      const res = await fetch('/api/leaves', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        form.reset();
        fetchLeaveRequests();
        fetchMyUser();
        alert('✅ Comp-off request submitted! The CEO will review it. Check "My Leave History" tab.');
      } else {
        alert(`❌ ${data.message}`);
      }
    } catch (err) { console.error(err); }
  };

  // Cancel manager's own pending leave
  const cancelMyLeave = async (leaveId) => {
    if (!window.confirm('Cancel this leave request? It will be permanently removed.')) return;
    try {
      const res = await fetch(`/api/leaves/${leaveId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) {
        fetchLeaveRequests();
        fetchMyUser();
      } else {
        alert(data.message || 'Failed to cancel leave request');
      }
    } catch (err) { console.error(err); }
  };

  // ── Filtered data ──────────────────────────────────────────
  const q = searchQuery.toLowerCase().trim();

  const filteredTasks = useMemo(() =>
    q ? teamTasks.filter(t =>
      (t.user_email || '').toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q) ||
      (t.employee_id || '').toLowerCase().includes(q)
    ) : teamTasks,
  [teamTasks, q]);

  const filteredLeaves = useMemo(() =>
    q ? leaveRequests.filter(l =>
      (l.user_email || '').toLowerCase().includes(q) ||
      (l.reason || '').toLowerCase().includes(q)
    ) : leaveRequests,
  [leaveRequests, q]);

  const filteredMembers = useMemo(() =>
    q ? teamMembers.filter(m =>
      (m.email || '').toLowerCase().includes(q) ||
      (m.employee_id || '').toLowerCase().includes(q) ||
      (m.role || '').toLowerCase().includes(q)
    ) : teamMembers,
  [teamMembers, q]);
  // ──────────────────────────────────────────────────────────

  const available = myUser.total_leaves - myUser.used_leaves;
  const pct       = Math.max(0, Math.min(100, (available / (myUser.total_leaves || 1)) * 100));
  const balColor  = pct > 50 ? '#27ae60' : pct > 20 ? '#f39c12' : '#e74c3c';

  const th = { padding: '12px 14px', fontWeight: 600, fontSize: '13px', color: '#555', textAlign: 'left' };
  const td = { padding: '12px 14px', fontSize: '14px', borderBottom: '1px solid #f0f0f0' };

  const tabBtn = (active, color = '#2980b9') => ({
    flex: 1, padding: '11px 8px', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600,
    display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px', fontSize: '13px',
    background: active ? color : '#ecf0f1',
    color:      active ? 'white' : '#555',
    transition: 'all 0.2s',
  });

  const badge = (status) => ({
    padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700,
    background: status === 'approved' ? '#d4edda' : ['rejected','declined','cancelled'].includes(status) ? '#f8d7da' : '#fff3cd',
    color:      status === 'approved' ? '#155724' : ['rejected','declined','cancelled'].includes(status) ? '#721c24' : '#856404',
  });

  const pendingMyLeaves = myLeaves.filter(l => l.status === 'pending').length;
  const pendingTeamLeaves = leaveRequests.filter(l => l.status === 'pending').length;

  return (
    <div style={{ padding: '22px', maxWidth: '1100px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '22px', padding: '20px 24px',
        background: 'linear-gradient(135deg, #2c3e50, #34495e)', color: 'white', borderRadius: '14px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 700 }}>Manager Dashboard</h1>
          <p style={{ margin: '4px 0 0', color: '#bdc3c7', fontSize: '13px' }}>Managing Team Operations — {user.email}</p>
        </div>
        <button onClick={onLogout}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '9px 18px',
            background: 'rgba(231,76,60,0.85)', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
          <LogOut size={15} /> Logout
        </button>
      </div>

      {/* ── My Leave Balance Card ── */}
      <div style={{ background: 'white', borderRadius: '12px', padding: '18px 22px', marginBottom: '20px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.06)', borderLeft: `5px solid ${balColor}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <div>
            <div style={{ fontSize: '13px', color: '#888', marginBottom: '3px' }}>My Annual Leave Balance</div>
            <div style={{ fontSize: '26px', fontWeight: 700, color: balColor }}>
              {available} <span style={{ fontSize: '14px', color: '#aaa', fontWeight: 400 }}>/ {myUser.total_leaves} days remaining</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '14px', textAlign: 'center' }}>
            <div style={{ padding: '8px 14px', background: '#eaf4fb', borderRadius: '8px' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#2980b9' }}>{myUser.used_leaves}</div>
              <div style={{ fontSize: '11px', color: '#7f8c8d' }}>Used</div>
            </div>
            <div style={{ padding: '8px 14px', background: '#eafaf1', borderRadius: '8px' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#27ae60' }}>{available}</div>
              <div style={{ fontSize: '11px', color: '#7f8c8d' }}>Remaining</div>
            </div>
            <div style={{ padding: '8px 14px', background: '#f5eef8', borderRadius: '8px' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#8e44ad' }}>{myUser.total_leaves}</div>
              <div style={{ fontSize: '11px', color: '#7f8c8d' }}>Total</div>
            </div>
          </div>
        </div>
        <div style={{ height: '6px', background: '#ecf0f1', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: balColor, borderRadius: '4px', transition: 'width 0.5s ease' }} />
        </div>
      </div>

      {/* ── Global Search Bar (for team tabs) ── */}
      <div style={{ position: 'relative', marginBottom: '16px' }}>
        <Search size={17} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: '#aaa' }} />
        <input
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search team by email, ID, task description…"
          style={{ width: '100%', padding: '11px 42px 11px 44px', border: '1px solid #ddd',
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
        <div style={{ marginBottom: '14px', padding: '8px 14px', background: '#eaf4fb',
          borderRadius: '8px', fontSize: '13px', color: '#2980b9', fontWeight: 500 }}>
          🔍 Results for "<strong>{searchQuery}</strong>" — {filteredTasks.length} task{filteredTasks.length !== 1 ? 's' : ''},{' '}
          {filteredLeaves.length} leave request{filteredLeaves.length !== 1 ? 's' : ''},{' '}
          {filteredMembers.length} team member{filteredMembers.length !== 1 ? 's' : ''}
        </div>
      )}

      {/* ── Tabs ── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {/* Team tabs */}
        <button onClick={() => setActiveTab('tasks')} style={tabBtn(activeTab === 'tasks', '#2980b9')}>
          <CheckSquare size={16} /> Team Tasks
          {q && filteredTasks.length > 0 && <span style={{ background: '#fff', color: '#2980b9', borderRadius: '10px', padding: '0 6px', fontSize: '11px' }}>{filteredTasks.length}</span>}
        </button>
        <button onClick={() => setActiveTab('leaves')} style={{ ...tabBtn(activeTab === 'leaves', '#f39c12'), position: 'relative' }}>
          <CalendarDays size={16} /> Leave Approvals
          {pendingTeamLeaves > 0 && <span style={{ background: '#e74c3c', color: 'white', borderRadius: '10px', padding: '0 6px', fontSize: '11px' }}>{pendingTeamLeaves}</span>}
        </button>
        <button onClick={() => setActiveTab('team')} style={tabBtn(activeTab === 'team', '#27ae60')}>
          <Users size={16} /> Team Performance
          {q && filteredMembers.length > 0 && <span style={{ background: '#fff', color: '#27ae60', borderRadius: '10px', padding: '0 6px', fontSize: '11px' }}>{filteredMembers.length}</span>}
        </button>

        {/* Divider */}
        <div style={{ width: '1px', background: '#ddd', margin: '0 4px' }} />

        {/* My personal leave tabs */}
        <button onClick={() => setActiveTab('apply')} style={tabBtn(activeTab === 'apply', '#16a085')}>
          <Calendar size={16} /> Apply Leave
        </button>
        <button onClick={() => setActiveTab('compoff')} style={tabBtn(activeTab === 'compoff', '#8e44ad')}>
          <TrendingUp size={16} /> Claim Comp-Off
        </button>
        <button onClick={() => setActiveTab('myhistory')} style={{ ...tabBtn(activeTab === 'myhistory', '#c0392b'), position: 'relative' }}>
          <History size={16} /> My Leave History
          {pendingMyLeaves > 0 && <span style={{ background: '#e74c3c', color: 'white', borderRadius: '10px', padding: '0 6px', fontSize: '11px' }}>{pendingMyLeaves}</span>}
        </button>
      </div>

      {/* ══════════ TEAM TABS ══════════ */}

      {/* ── Team Tasks ── */}
      {activeTab === 'tasks' && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}>
          <h2 style={{ marginTop: 0, color: '#2c3e50' }}>Daily Task Updates</h2>
          {filteredTasks.length === 0
            ? <p style={{ color: '#bbb', textAlign: 'center', padding: '30px' }}>No tasks found{q ? ` for "${searchQuery}"` : ''}.</p>
            : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8f9fa' }}>
                    <th style={th}>Employee</th>
                    <th style={th}>Task Description</th>
                    <th style={th}>Date</th>
                    <th style={th}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTasks.map(t => (
                    <tr key={t.id}
                      onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={td}>
                        <div style={{ fontWeight: 600 }}>{highlight(t.user_email, q)}</div>
                        {t.employee_id && <div style={{ fontSize: '11px', color: '#aaa' }}>{t.employee_id}</div>}
                      </td>
                      <td style={td}>{highlight(t.description, q)}</td>
                      <td style={{ ...td, color: '#888', whiteSpace: 'nowrap' }}>{new Date(t.created_at).toLocaleDateString()}</td>
                      <td style={td}>
                        <span style={{ padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700,
                          background: t.status === 'completed' ? '#d4edda' : '#fff3cd',
                          color:      t.status === 'completed' ? '#155724' : '#856404' }}>
                          {t.status.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          }
        </div>
      )}

      {/* ── Leave Approvals (team members only) ── */}
      {activeTab === 'leaves' && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}>
          <h2 style={{ marginTop: 0, color: '#2c3e50' }}>Team Leave Requests</h2>
          <div style={{ background: '#e8f4fd', border: '1px solid #bee3f8', borderRadius: '8px',
            padding: '10px 14px', marginBottom: '16px', fontSize: '13px', color: '#2b6cb0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldAlert size={15} />
            Your own leave requests are reviewed by the <strong>CEO</strong>. This tab only shows your <strong>team members'</strong> requests.
          </div>
          {filteredLeaves.length === 0
            ? <p style={{ color: '#bbb', textAlign: 'center', padding: '30px' }}>No team leave requests found{q ? ` for "${searchQuery}"` : ''}.</p>
            : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8f9fa' }}>
                    <th style={th}>Employee</th>
                    <th style={th}>Dates</th>
                    <th style={th}>Type</th>
                    <th style={th}>Reason</th>
                    <th style={th}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeaves.map(l => {
                    const member    = teamMembers.find(m => m.email === l.user_email);
                    const avail     = member ? member.total_leaves - member.used_leaves : 0;
                    const reqDays   = l.type === 'half-day' ? 0.5 : Math.round((new Date(l.end_date) - new Date(l.start_date)) / 86400000) + 1;
                    const overLimit = (l.type === 'regular' || l.type === 'half-day') && reqDays > avail;
                    return (
                      <tr key={l.id}
                        onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <td style={{ ...td, fontWeight: 600 }}>{highlight(l.user_email, q)}</td>
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
                        <td style={td}>{highlight(l.reason, q)}</td>
                        <td style={td}>
                          {l.status === 'pending' ? (
                            <div>
                              <div style={{ display: 'flex', gap: '6px', marginBottom: (l.type === 'regular' || l.type === 'half-day') ? '6px' : '0' }}>
                                <button onClick={() => handleLeaveAction(l.id, 'approved')}
                                  style={{ padding: '6px 12px', background: '#27ae60', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}>
                                  Approve
                                </button>
                                <button onClick={() => handleLeaveAction(l.id, 'rejected')}
                                  style={{ padding: '6px 12px', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 600, fontSize: '12px' }}>
                                  Reject
                                </button>
                              </div>
                              {(l.type === 'regular' || l.type === 'half-day') && member && (
                                <div style={{ fontSize: '11px', color: overLimit ? '#e74c3c' : '#7f8c8d' }}>
                                  {overLimit ? `⛔ Insufficient balance (${avail} left, needs ${reqDays})` : `Balance: ${avail} left`}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontWeight: 700, color: l.status === 'approved' ? '#27ae60' : '#e74c3c' }}>
                              {l.status.toUpperCase()}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )
          }
        </div>
      )}

      {/* ── Team Performance ── */}
      {activeTab === 'team' && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}>
          <h2 style={{ marginTop: 0, color: '#2c3e50' }}>Team Members</h2>
          {filteredMembers.length === 0
            ? <p style={{ color: '#bbb', textAlign: 'center', padding: '30px' }}>No members found{q ? ` for "${searchQuery}"` : ''}.</p>
            : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8f9fa' }}>
                    <th style={th}>Username</th>
                    <th style={th}>Employee ID</th>
                    <th style={th}>Role</th>
                    <th style={th}>Leaves Used / Total</th>
                    <th style={th}>Task Count</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMembers.map(m => {
                    const memberTaskCount = teamTasks.filter(t => t.user_email === m.email).length;
                    return (
                      <tr key={m.id}
                        onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <td style={td}>{highlight(m.email, q)}</td>
                        <td style={td}>{highlight(m.employee_id || '—', q)}</td>
                        <td style={{ ...td, textTransform: 'capitalize' }}>{m.role}</td>
                        <td style={td}>
                          <span style={{ color: m.used_leaves >= m.total_leaves ? '#e74c3c' : '#27ae60', fontWeight: 600 }}>
                            {m.used_leaves}
                          </span>
                          <span style={{ color: '#aaa' }}> / {m.total_leaves}</span>
                        </td>
                        <td style={td}>
                          <span style={{ background: '#eaf4fb', color: '#2980b9', padding: '3px 10px',
                            borderRadius: '12px', fontWeight: 700, fontSize: '13px' }}>
                            {memberTaskCount}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )
          }
        </div>
      )}

      {/* ══════════ PERSONAL LEAVE TABS ══════════ */}

      {/* ── Apply Leave ── */}
      {activeTab === 'apply' && (
        <div style={{ background: 'white', padding: '22px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: '#2c3e50' }}>
            <Calendar color="#16a085" size={20} /> Apply for Leave
          </h2>

          {/* CEO approval notice */}
          <div style={{ background: '#e8f8f5', border: '1px solid #a3d9cc', borderRadius: '8px',
            padding: '12px 16px', marginBottom: '20px', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <ShieldAlert size={16} color="#0e6655" style={{ flexShrink: 0, marginTop: 2 }} />
            <span style={{ fontSize: '13px', color: '#0e6655' }}>
              As a manager, your leave requests will be <strong>reviewed and approved by the CEO</strong>.
              You currently have <strong>{available} leave day(s) remaining</strong>.
            </span>
          </div>

          <form onSubmit={submitLeave} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'flex', gap: '15px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>Leave Type</label>
                <select
                  value={leaveData.type}
                  onChange={e => {
                    const type = e.target.value;
                    setLeaveData({ ...leaveData, type, end_date: type === 'half-day' ? leaveData.start_date : leaveData.end_date });
                  }}
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px', background: 'white' }}
                >
                  <option value="regular">Regular Leave</option>
                  <option value="half-day">Half-Day Leave (0.5 Days)</option>
                </select>
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>Start Date</label>
                <input type="date" required value={leaveData.start_date}
                  onChange={e => {
                    const val = e.target.value;
                    setLeaveData(prev => ({ ...prev, start_date: val, end_date: prev.type === 'half-day' ? val : prev.end_date }));
                  }}
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>End Date</label>
                <input type="date" required value={leaveData.end_date}
                  disabled={leaveData.type === 'half-day'}
                  onChange={e => setLeaveData({ ...leaveData, end_date: e.target.value })}
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px',
                    backgroundColor: leaveData.type === 'half-day' ? '#f0f0f0' : 'white' }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '15px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>Start Time</label>
                <input type="time" required value={leaveData.start_time || ''}
                  onChange={e => setLeaveData({ ...leaveData, start_time: e.target.value })}
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>End Time</label>
                <input type="time" required value={leaveData.end_time || ''}
                  onChange={e => setLeaveData({ ...leaveData, end_time: e.target.value })}
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px' }} />
              </div>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>Reason</label>
              <textarea required value={leaveData.reason}
                onChange={e => setLeaveData({ ...leaveData, reason: e.target.value })}
                placeholder="Reason for leave"
                style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px', minHeight: '80px' }} />
            </div>

            {leaveData.start_date && leaveData.end_date && (() => {
              const s = new Date(leaveData.start_date);
              const e = new Date(leaveData.end_date);
              const days = leaveData.type === 'half-day' ? 0.5 : (e >= s ? Math.round((e - s) / 86400000) + 1 : 0);
              const overLimit = days > available;
              return days > 0 ? (
                <div style={{ padding: '10px 14px', borderRadius: '8px', fontSize: '13px',
                  background: overLimit ? '#f8d7da' : '#d4edda',
                  border: `1px solid ${overLimit ? '#f5c6cb' : '#c3e6cb'}`,
                  color: overLimit ? '#721c24' : '#155724' }}>
                  {overLimit
                    ? `⛔ You requested ${days} day(s) but only have ${available} remaining.`
                    : `✅ Requesting ${days} day(s). After approval: ${available - days} remaining.`}
                </div>
              ) : null;
            })()}

            <button type="submit"
              disabled={(() => {
                if (!leaveData.start_date || !leaveData.end_date) return false;
                const s = new Date(leaveData.start_date);
                const e = new Date(leaveData.end_date);
                const days = leaveData.type === 'half-day' ? 0.5 : (e >= s ? Math.round((e - s) / 86400000) + 1 : 0);
                return days > available;
              })()}
              style={{ padding: '12px', background: '#16a085', color: 'white', border: 'none',
                borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
              Submit Leave Request → CEO for Approval
            </button>
          </form>
        </div>
      )}

      {/* ── Claim Comp-Off ── */}
      {activeTab === 'compoff' && (
        <div style={{ background: 'white', padding: '22px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: '#2c3e50' }}>
            <TrendingUp color="#8e44ad" size={20} /> Claim Compensatory Off (Comp-Off)
          </h2>

          <div style={{ background: '#f5eef8', border: '1px solid #d7bde2', borderRadius: '8px',
            padding: '12px 16px', marginBottom: '20px', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <ShieldAlert size={16} color="#6c3483" style={{ flexShrink: 0, marginTop: 2 }} />
            <span style={{ fontSize: '13px', color: '#6c3483' }}>
              Your comp-off requests will be <strong>reviewed and approved by the CEO</strong>.
              Once approved, your leave balance will increase by the number of extra days worked.
            </span>
          </div>

          <div style={{ background: '#eafaf1', border: '1px solid #a9dfbf', borderRadius: '8px',
            padding: '14px 16px', marginBottom: '20px' }}>
            <div style={{ fontWeight: 700, color: '#1e8449', marginBottom: '6px' }}>How Comp-Off works:</div>
            <ol style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#196f3d', lineHeight: '1.8' }}>
              <li>You worked on a <strong>weekend or public holiday</strong>.</li>
              <li>Submit a comp-off request with the date(s) you worked.</li>
              <li>The <strong>CEO</strong> approves the request.</li>
              <li>Once approved, your <strong>leave balance increases</strong> by the number of extra days worked.</li>
            </ol>
          </div>

          <form onSubmit={submitCompOff} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ display: 'flex', gap: '15px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>
                  Holiday/Weekend Date You Worked
                </label>
                <input type="date" name="start" required
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>End Date</label>
                <input type="date" name="end" required
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px' }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '15px' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>Start Time</label>
                <input type="time" name="start_time" required
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>End Time</label>
                <input type="time" name="end_time" required
                  style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px' }} />
              </div>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px', fontWeight: 500 }}>
                What work did you do? (Description)
              </label>
              <textarea name="reason" required placeholder="e.g. Handled project deployment on 25th May (Sunday)"
                style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px', minHeight: '80px' }} />
            </div>
            <button type="submit"
              style={{ padding: '12px', background: '#8e44ad', color: 'white', border: 'none',
                borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
              Submit Comp-Off Request → CEO for Approval
            </button>
          </form>
        </div>
      )}

      {/* ── My Leave History ── */}
      {activeTab === 'myhistory' && (
        <div style={{ background: 'white', padding: '22px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0, color: '#2c3e50' }}>
            <History color="#c0392b" size={20} /> My Leave History
          </h2>

          {/* Summary pills */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
            {[
              { label: 'Total',    value: myLeaves.length,                                                        bg: '#f5eef8', color: '#8e44ad' },
              { label: 'Pending',  value: myLeaves.filter(l => l.status === 'pending').length,                    bg: '#fff3cd', color: '#856404' },
              { label: 'Approved', value: myLeaves.filter(l => l.status === 'approved').length,                   bg: '#d4edda', color: '#155724' },
              { label: 'Rejected', value: myLeaves.filter(l => ['rejected','declined','cancelled'].includes(l.status)).length, bg: '#f8d7da', color: '#721c24' },
            ].map(({ label, value, bg, color }) => (
              <div key={label} style={{ padding: '10px 16px', background: bg, borderRadius: '8px', textAlign: 'center', minWidth: '75px' }}>
                <div style={{ fontSize: '22px', fontWeight: 700, color }}>{value}</div>
                <div style={{ fontSize: '11px', color, opacity: 0.85 }}>{label}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#fff8e1', border: '1px solid #ffe082', borderRadius: '8px',
            padding: '10px 14px', marginBottom: '16px', fontSize: '13px', color: '#6d4c00' }}>
            💡 Only <strong>pending</strong> leave requests can be cancelled. Approved/rejected ones cannot be removed by you.
            Your requests are reviewed by the <strong>CEO</strong>.
          </div>

          {myLeaves.length === 0 ? (
            <p style={{ color: '#bbb', textAlign: 'center', padding: '30px' }}>
              You haven't applied for any leaves yet. Use the <strong>Apply Leave</strong> or <strong>Claim Comp-Off</strong> tabs.
            </p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa', textAlign: 'left' }}>
                  <th style={th}>Date Range</th>
                  <th style={th}>Type</th>
                  <th style={th}>Reason</th>
                  <th style={th}>Status</th>
                  <th style={th}>Action</th>
                </tr>
              </thead>
              <tbody>
                {myLeaves.map(l => {
                  const start = new Date(l.start_date), end = new Date(l.end_date);
                  const days  = l.type === 'half-day' ? 0.5 : Math.round((end - start) / 86400000) + 1;
                  return (
                    <tr key={l.id} style={{ borderBottom: '1px solid #eee' }}
                      onMouseEnter={e => e.currentTarget.style.background = '#fafafa'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '12px', whiteSpace: 'nowrap' }}>
                        <div style={{ fontWeight: 500 }}>
                          {new Date(l.start_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })} → {new Date(l.end_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                        </div>
                        {(l.start_time || l.end_time) && (
                          <div style={{ fontSize: '12px', color: '#666', marginTop: '2px', fontWeight: 500 }}>
                            🕒 {l.start_time || '?'} - {l.end_time || '?'}
                          </div>
                        )}
                        <div style={{ fontSize: '11px', color: '#aaa', marginTop: '2px' }}>{days} day{days !== 1 ? 's' : ''}</div>
                      </td>
                      <td style={{ padding: '12px', textTransform: 'capitalize', fontSize: '14px' }}>{l.type}</td>
                      <td style={{ padding: '12px', color: '#555', fontSize: '14px', maxWidth: '200px' }}>{l.reason}</td>
                      <td style={{ padding: '12px' }}>
                        <span style={badge(l.status)}>{l.status.toUpperCase()}</span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        {l.status === 'pending' ? (
                          <button
                            onClick={() => cancelMyLeave(l.id)}
                            style={{ display: 'flex', alignItems: 'center', gap: '5px',
                              padding: '6px 12px', background: '#e74c3c', color: 'white',
                              border: 'none', borderRadius: '5px', cursor: 'pointer',
                              fontSize: '12px', fontWeight: 600 }}
                            title="Cancel this pending leave request"
                          >
                            <Trash2 size={13} /> Cancel
                          </button>
                        ) : (
                          <span style={{ fontSize: '12px', color: '#bbb', fontStyle: 'italic' }}>
                            {l.status === 'approved' ? '✓ Approved by CEO' : '✗ Cannot cancel'}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Floating Chatbot Assistant */}

    </div>
  );
}

// Highlight matching search text
function highlight(text, query) {
  if (!query || !text) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: '#fff176', borderRadius: '3px', padding: '0 2px' }}>
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}
