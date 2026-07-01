import React, { useState, useEffect } from 'react';
import { LogOut, CheckCircle, Calendar, PlusCircle, Pencil, X, Check, TrendingUp, Info, History, Trash2 } from 'lucide-react';

export default function EmployeeDashboard({ user: initialUser, token, onLogout }) {
  const [tasks, setTasks]       = useState([]);
  const [leaves, setLeaves]     = useState([]);
  const [liveUser, setLiveUser] = useState(initialUser);
  const [newTask, setNewTask]   = useState('');
  const [newTaskStatus, setNewTaskStatus] = useState('pending');
  const [activeTab, setActiveTab] = useState('tasks');

  // Leave form state
  const [leaveData, setLeaveData] = useState({ start_date: '', end_date: '', start_time: '', end_time: '', type: 'regular', reason: '' });

  // Inline edit state
  const [editingId, setEditingId]     = useState(null);
  const [editText, setEditText]       = useState('');
  const [editLoading, setEditLoading] = useState(false);

  useEffect(() => { fetchTasks(); fetchLeaves(); fetchUser(); }, []);

  const fetchUser = async () => {
    try {
      const res  = await fetch('/api/me', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setLiveUser(data.user);
    } catch (err) { console.error(err); }
  };

  const fetchTasks = async () => {
    try {
      const res  = await fetch('/api/tasks', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setTasks(data.tasks);
    } catch (err) { console.error(err); }
  };

  const fetchLeaves = async () => {
    try {
      const res  = await fetch('/api/leaves', { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (data.success) setLeaves(data.leaves);
    } catch (err) { console.error(err); }
  };

  const submitTask = async (e) => {
    e.preventDefault();
    if (!newTask.trim()) return;
    try {
      const res  = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ description: newTask, status: newTaskStatus }),
      });
      const data = await res.json();
      if (data.success) { 
        setNewTask(''); 
        setNewTaskStatus('pending');
        fetchTasks(); 
      }
    } catch (err) { console.error(err); }
  };

  const submitLeave = async (e) => {
    e.preventDefault();
    try {
      const res  = await fetch('/api/leaves', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(leaveData),
      });
      const data = await res.json();
      if (data.success) {
        setLeaveData({ start_date: '', end_date: '', start_time: '', end_time: '', type: 'regular', reason: '' });
        fetchLeaves();
        fetchUser();
        alert('✅ Leave request submitted! Check Leave History tab to track its status.');
      } else {
        alert(data.message);
      }
    } catch (err) { console.error(err); }
  };

  // Cancel a pending leave request (employee can only cancel their own pending leaves)
  const cancelLeave = async (leaveId) => {
    if (!window.confirm('Cancel this leave request? It will be permanently removed.')) return;
    try {
      const res = await fetch(`/api/leaves/${leaveId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) {
        fetchLeaves();
        fetchUser();
      } else {
        alert(data.message || 'Failed to cancel leave request');
      }
    } catch (err) { console.error(err); }
  };

  // ── Inline edit ───────────────────────────────────────────
  const startEdit  = (task) => { setEditingId(task.id); setEditText(task.description); };
  const cancelEdit = () => { setEditingId(null); setEditText(''); };
  const saveEdit   = async (taskId) => {
    if (!editText.trim()) return;
    setEditLoading(true);
    try {
      const res  = await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ description: editText.trim() }),
      });
      const data = await res.json();
      if (data.success) { setEditingId(null); fetchTasks(); }
      else alert(data.message || 'Update failed');
    } catch (err) { console.error(err); }
    finally { setEditLoading(false); }
  };

  const toggleTaskStatus = async (taskId, currentStatus) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
    try {
      const res = await fetch(`/api/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status: newStatus }),
      });
      const data = await res.json();
      if (data.success) fetchTasks();
      else alert(data.message || 'Failed to update task status');
    } catch (err) { console.error(err); }
  };
  // ─────────────────────────────────────────────────────────

  const available = liveUser.total_leaves - liveUser.used_leaves;
  const pct       = Math.max(0, Math.min(100, (available / liveUser.total_leaves) * 100));
  const barColor  = pct > 50 ? '#27ae60' : pct > 20 ? '#f39c12' : '#e74c3c';

  const tabBtn = (active, color = '#3498db') => ({
    flex: 1, padding: '11px', border: 'none', borderRadius: '7px', cursor: 'pointer', fontWeight: 600,
    background: active ? color : '#ecf0f1', color: active ? 'white' : '#555',
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
    transition: 'all 0.2s',
  });

  const badge = (status) => ({
    padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700,
    background: status === 'approved' ? '#d4edda' : (status === 'rejected' || status === 'declined' || status === 'cancelled') ? '#f8d7da' : '#fff3cd',
    color:      status === 'approved' ? '#155724' : (status === 'rejected' || status === 'declined' || status === 'cancelled') ? '#721c24' : '#856404',
  });

  const pendingCount = leaves.filter(l => l.status === 'pending').length;

  return (
    <div style={{ padding: '20px', maxWidth: '820px', margin: '0 auto', fontFamily: 'Inter, sans-serif' }}>

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '20px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '22px', color: '#1a1a1a' }}>Employee Dashboard</h1>
          <p style={{ margin: '4px 0 0', color: '#888', fontSize: '13px' }}>Welcome back, {liveUser.email}</p>
        </div>
        <button onClick={onLogout} style={{ display: 'flex', alignItems: 'center', gap: '5px',
          padding: '8px 16px', background: '#e74c3c', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
          <LogOut size={15} /> Logout
        </button>
      </div>

      {/* ── Leave Balance Card ── */}
      <div style={{ background: 'white', borderRadius: '12px', padding: '20px', marginBottom: '20px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.06)', borderLeft: `5px solid ${barColor}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
          <div>
            <div style={{ fontSize: '13px', color: '#888', marginBottom: '4px' }}>Annual Leave Balance</div>
            <div style={{ fontSize: '28px', fontWeight: 700, color: barColor }}>
              {available} <span style={{ fontSize: '16px', color: '#aaa', fontWeight: 400 }}>/ {liveUser.total_leaves} days</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '20px', textAlign: 'center' }}>
            <div style={{ padding: '10px 16px', background: '#eaf4fb', borderRadius: '8px' }}>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#2980b9' }}>{liveUser.used_leaves}</div>
              <div style={{ fontSize: '11px', color: '#7f8c8d' }}>Used</div>
            </div>
            <div style={{ padding: '10px 16px', background: '#eafaf1', borderRadius: '8px' }}>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#27ae60' }}>{available}</div>
              <div style={{ fontSize: '11px', color: '#7f8c8d' }}>Remaining</div>
            </div>
            <div style={{ padding: '10px 16px', background: '#f5eef8', borderRadius: '8px' }}>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#8e44ad' }}>{liveUser.total_leaves}</div>
              <div style={{ fontSize: '11px', color: '#7f8c8d' }}>Total</div>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ height: '8px', background: '#ecf0f1', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: barColor,
            borderRadius: '4px', transition: 'width 0.5s ease' }} />
        </div>

        {/* Explanation row */}
        <div style={{ display: 'flex', gap: '20px', marginTop: '12px', fontSize: '12px', color: '#888' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#e74c3c', display: 'inline-block' }} />
            Regular leave taken → balance decreases
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#27ae60', display: 'inline-block' }} />
            Working on holiday (Comp-Off approved) → balance increases
          </span>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <button onClick={() => setActiveTab('tasks')} style={tabBtn(activeTab === 'tasks', '#3498db')}>
          <CheckCircle size={15} /> Daily Tasks
        </button>
        <button onClick={() => setActiveTab('leaves')} style={tabBtn(activeTab === 'leaves', '#f39c12')}>
          <Calendar size={15} /> Apply Leave
        </button>
        <button onClick={() => setActiveTab('compoff')} style={tabBtn(activeTab === 'compoff', '#27ae60')}>
          <TrendingUp size={15} /> Claim Comp-Off
        </button>
        <button onClick={() => setActiveTab('history')} style={{ ...tabBtn(activeTab === 'history', '#8e44ad'), position: 'relative' }}>
          <History size={15} /> Leave History
          {pendingCount > 0 && (
            <span style={{
              background: '#e74c3c', color: 'white', borderRadius: '10px', padding: '1px 6px',
              fontSize: '11px', fontWeight: 700, marginLeft: '2px',
            }}>{pendingCount}</span>
          )}
        </button>
      </div>

      {/* ── Tasks Tab ── */}
      {activeTab === 'tasks' && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0 }}>
            <CheckCircle color="#27ae60" size={20} /> Add Daily Task
          </h2>
          <form onSubmit={submitTask} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <input type="text" value={newTask} onChange={e => setNewTask(e.target.value)}
              placeholder="What task are you working on?"
              style={{ flex: 1, padding: '10px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '14px' }}
              required />
            <select value={newTaskStatus} onChange={e => setNewTaskStatus(e.target.value)}
              style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '14px', backgroundColor: 'white' }}>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
            </select>
            <button type="submit"
              style={{ padding: '10px 20px', background: '#27ae60', color: 'white', border: 'none',
                borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <PlusCircle size={16} /> Add
            </button>
          </form>

          <h3 style={{ marginBottom: '10px' }}>My Tasks</h3>
          {tasks.length === 0
            ? <p style={{ color: '#bbb', textAlign: 'center', padding: '20px' }}>No tasks submitted yet.</p>
            : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {tasks.map(t => (
                  <li key={t.id} style={{ padding: '14px', borderBottom: '1px solid #f0f0f0' }}>
                    {editingId === t.id ? (
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <input value={editText} onChange={e => setEditText(e.target.value)}
                          style={{ flex: 1, padding: '8px 10px', border: '2px solid #3498db',
                            borderRadius: '6px', fontSize: '14px', outline: 'none' }}
                          autoFocus
                          onKeyDown={e => { if (e.key === 'Enter') saveEdit(t.id); if (e.key === 'Escape') cancelEdit(); }}
                        />
                        <button onClick={() => saveEdit(t.id)} disabled={editLoading}
                          style={{ padding: '7px 10px', background: '#27ae60', color: 'white',
                            border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                          <Check size={16} />
                        </button>
                        <button onClick={cancelEdit}
                          style={{ padding: '7px 10px', background: '#e74c3c', color: 'white',
                            border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                          <X size={16} />
                        </button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <button
                            onClick={() => toggleTaskStatus(t.id, t.status)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                              display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.1s ease' }}
                            title={`Mark as ${t.status === 'completed' ? 'pending' : 'completed'}`}
                            onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.95)'}
                            onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
                          >
                            {t.status === 'completed' ? (
                              <CheckCircle size={20} color="#27ae60" style={{ fill: '#e8f8f0' }} />
                            ) : (
                              <div style={{ width: '18px', height: '18px', borderRadius: '50%',
                                border: '2px solid #bdc3c7', transition: 'border-color 0.2s' }} />
                            )}
                          </button>
                          <div>
                            <div style={{
                              fontSize: '15px',
                              textDecoration: t.status === 'completed' ? 'line-through' : 'none',
                              color: t.status === 'completed' ? '#7f8c8d' : '#2c3e50',
                              transition: 'all 0.2s', textAlign: 'left'
                            }}>
                              {t.description}
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '3px' }}>
                              <span style={{ fontSize: '11px', color: '#bbb' }}>
                                {new Date(t.created_at).toLocaleDateString()} {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                              <span style={{
                                fontSize: '10px', padding: '2px 6px', borderRadius: '4px', fontWeight: 600, textTransform: 'uppercase',
                                background: t.status === 'completed' ? '#e8f8f0' : '#fef5e7',
                                color: t.status === 'completed' ? '#27ae60' : '#f39c12'
                              }}>
                                {t.status || 'pending'}
                              </span>
                            </div>
                          </div>
                        </div>
                        <button onClick={() => startEdit(t)}
                          style={{ display: 'flex', alignItems: 'center', gap: '5px', padding: '6px 12px',
                            background: '#eaf4fb', color: '#2980b9', border: '1px solid #aed6f1',
                            borderRadius: '6px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
                          <Pencil size={13} /> Edit
                        </button>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )
          }
        </div>
      )}

      {/* ── Apply Leave Tab ── */}
      {activeTab === 'leaves' && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0 }}>
            <Calendar color="#f39c12" size={20} /> Apply for Regular Leave
          </h2>

          <div style={{ background: '#fff3cd', border: '1px solid #ffeaa7', borderRadius: '8px',
            padding: '12px 16px', marginBottom: '20px', display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <Info size={16} color="#856404" style={{ flexShrink: 0, marginTop: 2 }} />
            <span style={{ fontSize: '13px', color: '#856404' }}>
              Each approved regular leave will deduct from your balance.
              Currently you have <strong>{available} leaves remaining</strong>.
              After submitting, check the <strong>Leave History</strong> tab to track status.
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
                    ? `⛔ You requested ${days} day(s) but only have ${available} day(s) remaining. Reduce the dates.`
                    : `✅ Requesting ${days} day(s). After approval: ${available - days} day(s) remaining.`}
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
              style={{
                padding: '12px', background: '#f39c12', color: 'white', border: 'none',
                borderRadius: '6px', fontWeight: 'bold',
                cursor: (() => {
                  if (!leaveData.start_date || !leaveData.end_date) return 'pointer';
                  const s = new Date(leaveData.start_date);
                  const e = new Date(leaveData.end_date);
                  const days = leaveData.type === 'half-day' ? 0.5 : (e >= s ? Math.round((e - s) / 86400000) + 1 : 0);
                  return days > available ? 'not-allowed' : 'pointer';
                })(),
                opacity: (() => {
                  if (!leaveData.start_date || !leaveData.end_date) return 1;
                  const s = new Date(leaveData.start_date);
                  const e = new Date(leaveData.end_date);
                  const days = leaveData.type === 'half-day' ? 0.5 : (e >= s ? Math.round((e - s) / 86400000) + 1 : 0);
                  return days > available ? 0.5 : 1;
                })()
              }}>
              Submit Leave Request
            </button>
          </form>
        </div>
      )}

      {/* ── Comp-Off Tab ── */}
      {activeTab === 'compoff' && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0 }}>
            <TrendingUp color="#27ae60" size={20} /> Claim Compensatory Off (Comp-Off)
          </h2>

          <div style={{ background: '#eafaf1', border: '1px solid #a9dfbf', borderRadius: '8px',
            padding: '14px 16px', marginBottom: '20px' }}>
            <div style={{ fontWeight: 700, color: '#1e8449', marginBottom: '6px' }}>How Comp-Off works:</div>
            <ol style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#196f3d', lineHeight: '1.8' }}>
              <li>You worked on a <strong>weekend or public holiday</strong>.</li>
              <li>Submit a comp-off request with the date(s) you worked.</li>
              <li>Your Manager approves the request.</li>
              <li>Once approved, <strong>your leave balance increases</strong> by the number of extra days worked.</li>
            </ol>
            <div style={{ marginTop: '10px', fontSize: '13px', color: '#1e8449' }}>
              Example: Balance is 15 → Manager approves 1-day comp-off → Balance becomes 16 ✅
            </div>
          </div>

          <form onSubmit={(e) => {
            e.preventDefault();
            const form = e.target;
            const start = form.start.value;
            const end   = form.end.value;
            const start_time = form.start_time.value;
            const end_time = form.end_time.value;
            const reason = form.reason.value;
            fetch('/api/leaves', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ start_date: start, end_date: end, start_time, end_time, type: 'comp-off', reason }),
            })
            .then(r => r.json())
            .then(data => {
              if (data.success) { form.reset(); fetchLeaves(); fetchUser(); alert('✅ Comp-off request submitted! Check Leave History tab to track it.'); }
              else alert(data.message);
            });
          }}
          style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
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
              <textarea name="reason" required placeholder="e.g. Worked on project deployment on 25th May (Sunday)"
                style={{ width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '6px', minHeight: '80px' }} />
            </div>
            <button type="submit"
              style={{ padding: '12px', background: '#27ae60', color: 'white', border: 'none',
                borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
              Submit Comp-Off Request
            </button>
          </form>
        </div>
      )}

      {/* ── Leave History Tab ── */}
      {activeTab === 'history' && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: 0 }}>
            <History color="#8e44ad" size={20} /> My Leave History
          </h2>

          {/* Summary stat pills */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
            {[
              { label: 'Total Requests', value: leaves.length, bg: '#f5eef8', color: '#8e44ad' },
              { label: 'Pending', value: leaves.filter(l => l.status === 'pending').length, bg: '#fff3cd', color: '#856404' },
              { label: 'Approved', value: leaves.filter(l => l.status === 'approved').length, bg: '#d4edda', color: '#155724' },
              { label: 'Rejected/Declined', value: leaves.filter(l => ['rejected', 'declined', 'cancelled'].includes(l.status)).length, bg: '#f8d7da', color: '#721c24' },
            ].map(({ label, value, bg, color }) => (
              <div key={label} style={{ padding: '10px 16px', background: bg, borderRadius: '8px', textAlign: 'center', minWidth: '80px' }}>
                <div style={{ fontSize: '22px', fontWeight: 700, color }}>{value}</div>
                <div style={{ fontSize: '11px', color, opacity: 0.85 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Info about cancel */}
          <div style={{ background: '#f0f3f8', border: '1px solid #d0d7e3', borderRadius: '8px',
            padding: '10px 14px', marginBottom: '16px', fontSize: '13px', color: '#555' }}>
            💡 You can only <strong>cancel pending</strong> leave requests. Approved or rejected leaves cannot be cancelled.
          </div>

          {leaves.length === 0 ? (
            <p style={{ color: '#bbb', textAlign: 'center', padding: '30px' }}>No leave requests found.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa', textAlign: 'left' }}>
                  <th style={{ padding: '12px', fontWeight: 600, fontSize: '13px', color: '#555' }}>Date Range</th>
                  <th style={{ padding: '12px', fontWeight: 600, fontSize: '13px', color: '#555' }}>Type</th>
                  <th style={{ padding: '12px', fontWeight: 600, fontSize: '13px', color: '#555' }}>Reason</th>
                  <th style={{ padding: '12px', fontWeight: 600, fontSize: '13px', color: '#555' }}>Status</th>
                  <th style={{ padding: '12px', fontWeight: 600, fontSize: '13px', color: '#555' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {leaves.map(l => {
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
                            onClick={() => cancelLeave(l.id)}
                            style={{
                              display: 'flex', alignItems: 'center', gap: '5px',
                              padding: '6px 12px', background: '#e74c3c', color: 'white',
                              border: 'none', borderRadius: '5px', cursor: 'pointer',
                              fontSize: '12px', fontWeight: 600,
                            }}
                            title="Cancel this pending leave request"
                          >
                            <Trash2 size={13} /> Cancel
                          </button>
                        ) : (
                          <span style={{ fontSize: '12px', color: '#bbb', fontStyle: 'italic' }}>
                            {l.status === 'approved' ? '✓ Approved' : '✗ Cannot cancel'}
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

    </div>
  );
}
