from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import psycopg2.extras
import re

# Create blueprint
rbac_bp = Blueprint('rbac_bp', __name__)

# We need a reference to the main app's dependencies
# We'll set these up via a setup function or just import them
_get_db = None
_require_auth = None

def init_rbac(get_db_func, require_auth_decorator):
    global _get_db, _require_auth
    _get_db = get_db_func
    _require_auth = require_auth_decorator

# -----------------
# USERS API
# -----------------
@rbac_bp.route("/api/users", methods=["GET"])
def get_users():
    """List users based on role (CEO sees all, Manager sees their team)."""
    @_require_auth
    def _handler(current_user):
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # First get current user role
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u:
                    return jsonify({"success": False, "message": "User not found"}), 404
                role = u["role"]
                
                if role == 'ceo':
                    cur.execute("SELECT id, email, role, employee_id, manager_id, total_leaves, used_leaves FROM users ORDER BY id ASC")
                elif role == 'manager':
                    cur.execute("SELECT id, email, role, employee_id, manager_id, total_leaves, used_leaves FROM users WHERE role = 'employee' OR id = %s ORDER BY id ASC", (current_user["sub"],))
                else:
                    # Employee can see their own info and maybe their manager's basic info
                    cur.execute("SELECT id, email, role, employee_id, manager_id, total_leaves, used_leaves FROM users WHERE id = %s", (current_user["sub"],))
                
                users = cur.fetchall()
            return jsonify({"success": True, "users": [dict(user) for user in users]})
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/users/<int:user_id>/manager", methods=["PUT"])
def assign_manager(user_id):
    """CEO or Manager can assign a manager to a user."""
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        manager_id = data.get("manager_id")
        if manager_id == "":
            manager_id = None
        elif manager_id is not None:
            manager_id = int(manager_id)
        
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u or u["role"] not in ['ceo', 'manager']:
                    return jsonify({"success": False, "message": "Unauthorized"}), 403
                
                cur.execute("UPDATE users SET manager_id = %s WHERE id = %s RETURNING id", (manager_id, user_id))
                if cur.rowcount == 0:
                    return jsonify({"success": False, "message": "User not found"}), 404
            conn.commit()
            return jsonify({"success": True, "message": "Manager assigned"})
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/users/<int:user_id>/role", methods=["PUT"])
def update_role(user_id):
    """CEO can update a user's role (promote to manager, demote to employee)."""
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        new_role = data.get("role")
        if new_role not in ['employee', 'manager']:
            return jsonify({"success": False, "message": "Invalid role"}), 400
        
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u or u["role"] != 'ceo':
                    return jsonify({"success": False, "message": "Only CEO can change roles"}), 403
                
                # Prevent changing own role
                if user_id == current_user["sub"]:
                    return jsonify({"success": False, "message": "Cannot change your own role"}), 400
                
                cur.execute("UPDATE users SET role = %s WHERE id = %s RETURNING id", (new_role, user_id))
                if cur.rowcount == 0:
                    return jsonify({"success": False, "message": "User not found"}), 404
            conn.commit()
            return jsonify({"success": True, "message": f"User role updated to {new_role}"})
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """CEO can delete a user and cascade their data."""
    @_require_auth
    def _handler(current_user):
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u or u["role"] != 'ceo':
                    return jsonify({"success": False, "message": "Only CEO can delete users"}), 403
                
                # Prevent deleting oneself
                if user_id == current_user["sub"]:
                    return jsonify({"success": False, "message": "Cannot delete your own account"}), 400

                cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
                if cur.rowcount == 0:
                    return jsonify({"success": False, "message": "User not found"}), 404
            conn.commit()
            return jsonify({"success": True, "message": "User deleted"})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

# -----------------
# CHANGE PASSWORD (for logged-in users)
# -----------------
@rbac_bp.route("/api/change-password", methods=["POST"])
def change_password():
    """Authenticated users can change their own password."""
    @_require_auth
    def _handler(current_user):
        import hashlib, os
        data             = request.get_json() or {}
        current_password = (data.get("current_password") or "").strip()
        new_password     = (data.get("new_password") or "").strip()

        if not current_password or not new_password:
            return jsonify({"success": False, "message": "Current and new password are required"}), 400
        if len(new_password) < 6:
            return jsonify({"success": False, "message": "New password must be at least 6 characters"}), 400

        def _hash(pw):
            salt = os.environ.get("PASSWORD_SALT", "qa-chat-salt")
            return hashlib.sha256(f"{salt}{pw}".encode()).hexdigest()

        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT password FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u:
                    return jsonify({"success": False, "message": "User not found"}), 404

                if u["password"] != _hash(current_password):
                    return jsonify({"success": False, "message": "Current password is incorrect"}), 403

                cur.execute("UPDATE users SET password = %s WHERE id = %s", (_hash(new_password), current_user["sub"]))
            conn.commit()
            return jsonify({"success": True, "message": "Password changed successfully!"})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

# -----------------
# TASKS API
# -----------------
@rbac_bp.route("/api/tasks", methods=["GET"])
def get_tasks():
    @_require_auth
    def _handler(current_user):
        conn = _get_db()
        # ?filter=daily | weekly | yearly  (CEO only)
        date_filter = request.args.get("filter", "all")
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                role = u["role"] if u else 'employee'

                if role == 'ceo':
                    if date_filter == 'daily':
                        date_clause = "AND t.date = CURRENT_DATE"
                    elif date_filter == 'weekly':
                        date_clause = "AND t.date >= CURRENT_DATE - INTERVAL '7 days'"
                    elif date_filter == 'yearly':
                        date_clause = "AND t.date >= CURRENT_DATE - INTERVAL '1 year'"
                    else:
                        date_clause = ""

                    cur.execute(f"""
                        SELECT t.*, u.email as user_email, u.employee_id
                        FROM tasks t JOIN users u ON t.user_id = u.id
                        WHERE 1=1 {date_clause}
                        ORDER BY t.created_at DESC
                    """)
                elif role == 'manager':
                    cur.execute("""
                        SELECT t.*, u.email as user_email, u.employee_id 
                        FROM tasks t JOIN users u ON t.user_id = u.id 
                        WHERE u.role = 'employee' OR t.user_id = %s 
                        ORDER BY t.created_at DESC
                    """, (current_user["sub"],))
                else:
                    cur.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC", (current_user["sub"],))
                
                tasks = cur.fetchall()
            return jsonify({"success": True, "tasks": [dict(t) for t in tasks]})
        finally:
            conn.close()
    return _handler()


@rbac_bp.route("/api/tasks", methods=["POST"])
def create_task():
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        description = data.get("description", "").strip()
        status = data.get("status", "pending")
        
        if not description:
            return jsonify({"success": False, "message": "Description is required"}), 400
            
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO tasks (user_id, description, status) VALUES (%s, %s, %s) RETURNING *",
                    (current_user["sub"], description, status)
                )
                task = cur.fetchone()
            conn.commit()
            return jsonify({"success": True, "task": dict(task)}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        status      = data.get("status")
        description = data.get("description", "").strip()

        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Verify task exists and belongs to this user (employees can only edit their own)
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                role = u["role"] if u else 'employee'

                cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
                task = cur.fetchone()
                if not task:
                    return jsonify({"success": False, "message": "Task not found"}), 404

                if role == 'employee' and task['user_id'] != current_user["sub"]:
                    return jsonify({"success": False, "message": "You can only edit your own tasks"}), 403

                # Build dynamic update
                fields, values = [], []
                if status and status in ('pending', 'completed'):
                    fields.append("status = %s")
                    values.append(status)
                if description:
                    fields.append("description = %s")
                    values.append(description)
                if not fields:
                    return jsonify({"success": False, "message": "Nothing to update"}), 400

                fields.append("updated_at = NOW()")
                values.append(task_id)
                cur.execute(
                    f"UPDATE tasks SET {', '.join(fields)} WHERE id = %s RETURNING *",
                    values
                )
                updated = cur.fetchone()
            conn.commit()
            return jsonify({"success": True, "task": dict(updated)})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """CEO can delete any task from the history."""
    @_require_auth
    def _handler(current_user):
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u or u["role"] != 'ceo':
                    return jsonify({"success": False, "message": "Only CEO can delete tasks"}), 403

                cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,))
                if cur.rowcount == 0:
                    return jsonify({"success": False, "message": "Task not found"}), 404
            conn.commit()
            return jsonify({"success": True, "message": "Task deleted"})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()


# -----------------
# LEAVES API
# -----------------
@rbac_bp.route("/api/leaves", methods=["GET"])
def get_leaves():
    @_require_auth
    def _handler(current_user):
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                role = u["role"] if u else 'employee'

                if role == 'ceo':
                    cur.execute("SELECT l.*, u.email as user_email FROM leaves l JOIN users u ON l.user_id = u.id ORDER BY l.created_at DESC")
                elif role == 'manager':
                    cur.execute("""
                        SELECT l.*, u.email as user_email 
                        FROM leaves l JOIN users u ON l.user_id = u.id 
                        WHERE u.role = 'employee' OR l.user_id = %s 
                        ORDER BY l.created_at DESC
                    """, (current_user["sub"],))
                else:
                    cur.execute("SELECT * FROM leaves WHERE user_id = %s ORDER BY created_at DESC", (current_user["sub"],))
                
                leaves = cur.fetchall()
            return jsonify({"success": True, "leaves": [dict(l) for l in leaves]})
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/leaves", methods=["POST"])
def apply_leave():
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        start_date = data.get("start_date")
        end_date   = data.get("end_date")
        start_time = data.get("start_time")
        end_time   = data.get("end_time")
        ltype      = data.get("type", "regular")
        reason     = data.get("reason", "")

        if not start_date or not end_date:
            return jsonify({"success": False, "message": "Start and end dates required"}), 400
        if not start_time or not end_time:
            return jsonify({"success": False, "message": "Start and end times required"}), 400

        # Calculate number of days requested
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt   = datetime.strptime(end_date,   '%Y-%m-%d')
            if end_dt < start_dt:
                return jsonify({"success": False, "message": "End date cannot be before start date"}), 400
            
            if ltype == 'half-day':
                if start_date != end_date:
                    return jsonify({"success": False, "message": "Half-day leave must start and end on the same day"}), 400
                days = 0.5
            else:
                days = float((end_dt - start_dt).days + 1)
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format"}), 400

        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # For regular or half-day leave — check if employee has enough balance
                if ltype in ('regular', 'half-day'):
                    cur.execute("SELECT total_leaves, used_leaves FROM users WHERE id = %s", (current_user["sub"],))
                    u = cur.fetchone()
                    available = float(u['total_leaves'] - u['used_leaves'])
                    if days > available:
                        return jsonify({
                            "success": False,
                            "message": f"Insufficient leave balance. You requested {days} day(s) but only have {available} day(s) remaining."
                        }), 400

                cur.execute(
                    "INSERT INTO leaves (user_id, start_date, end_date, start_time, end_time, type, reason) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *",
                    (current_user["sub"], start_date, end_date, start_time, end_time, ltype, reason)
                )
                leave = cur.fetchone()
            conn.commit()
            return jsonify({"success": True, "leave": dict(leave)}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/leaves/<int:leave_id>/approve", methods=["POST"])
def approve_leave(leave_id):
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        status = data.get("status") # 'approved' or 'rejected'
        if status not in ['approved', 'rejected']:
            return jsonify({"success": False, "message": "Invalid status"}), 400
            
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Check if current user is manager or ceo
                cur.execute("SELECT role, id FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u or u["role"] not in ['ceo', 'manager']:
                    return jsonify({"success": False, "message": "Unauthorized"}), 403

                cur.execute("SELECT * FROM leaves WHERE id = %s", (leave_id,))
                leave = cur.fetchone()
                if not leave:
                    return jsonify({"success": False, "message": "Leave not found"}), 404

                # Manager cannot approve/reject their own leave — only CEO can
                if u["role"] == 'manager' and leave['user_id'] == u['id']:
                    return jsonify({"success": False, "message": "You cannot approve your own leave. It must be approved by the CEO."}), 403
                
                # If approving a regular/half-day leave — check balance first
                if status == 'approved' and leave['status'] != 'approved':
                    start = datetime.strptime(str(leave['start_date']), '%Y-%m-%d')
                    end   = datetime.strptime(str(leave['end_date']),   '%Y-%m-%d')
                    days  = 0.5 if leave['type'] == 'half-day' else float((end - start).days + 1)

                    if leave['type'] in ('regular', 'half-day'):
                        cur.execute("SELECT total_leaves, used_leaves FROM users WHERE id = %s", (leave['user_id'],))
                        emp = cur.fetchone()
                        available = float(emp['total_leaves'] - emp['used_leaves'])

                        if days > available:
                            return jsonify({
                                "success": False,
                                "message": f"Cannot approve: employee only has {available} leave day(s) remaining but this request is for {days} day(s)."
                            }), 400

                        cur.execute("UPDATE users SET used_leaves = used_leaves + %s WHERE id = %s", (days, leave['user_id']))

                    elif leave['type'] == 'comp-off':
                        cur.execute("UPDATE users SET total_leaves = total_leaves + %s WHERE id = %s", (days, leave['user_id']))

                # If rejecting/cancelling an already approved leave — revert balance
                elif status == 'rejected' and leave['status'] == 'approved':
                    start = datetime.strptime(str(leave['start_date']), '%Y-%m-%d')
                    end   = datetime.strptime(str(leave['end_date']),   '%Y-%m-%d')
                    days  = 0.5 if leave['type'] == 'half-day' else float((end - start).days + 1)

                    if leave['type'] in ('regular', 'half-day'):
                        cur.execute("UPDATE users SET used_leaves = GREATEST(0.0, used_leaves - %s) WHERE id = %s", (days, leave['user_id']))
                    elif leave['type'] == 'comp-off':
                        cur.execute("UPDATE users SET total_leaves = GREATEST(16.0, total_leaves - %s) WHERE id = %s", (days, leave['user_id']))
                
                # Update leave status
                cur.execute("UPDATE leaves SET status = %s WHERE id = %s RETURNING *", (status, leave_id))
                updated_leave = cur.fetchone()
                        
            conn.commit()
            return jsonify({"success": True, "leave": dict(updated_leave)})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/leaves/<int:leave_id>/decline", methods=["POST"])
def decline_leave(leave_id):
    """Allows an employee to decline/cancel their own leave request (both pending and approved)."""
    @_require_auth
    def _handler(current_user):
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM leaves WHERE id = %s", (leave_id,))
                leave = cur.fetchone()
                if not leave:
                    return jsonify({"success": False, "message": "Leave request not found"}), 404
                
                # Verify that current user is manager or ceo
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u or u["role"] not in ['ceo', 'manager']:
                    return jsonify({"success": False, "message": "Unauthorized: Only managers and CEO can decline leave requests"}), 403
                
                if leave['status'] in ('declined', 'cancelled'):
                    return jsonify({"success": False, "message": "Leave is already declined/cancelled"}), 400
                
                old_status = leave['status']
                
                # Update status to 'declined'
                cur.execute("UPDATE leaves SET status = 'declined', updated_at = NOW() WHERE id = %s RETURNING *", (leave_id,))
                updated_leave = cur.fetchone()
                
                # Revert user balance if it was already approved
                if old_status == 'approved':
                    start = datetime.strptime(str(leave['start_date']), '%Y-%m-%d')
                    end   = datetime.strptime(str(leave['end_date']),   '%Y-%m-%d')
                    days  = 0.5 if leave['type'] == 'half-day' else float((end - start).days + 1)
                    
                    if leave['type'] in ('regular', 'half-day'):
                        cur.execute("UPDATE users SET used_leaves = GREATEST(0.0, used_leaves - %s) WHERE id = %s", (days, leave['user_id']))
                    elif leave['type'] == 'comp-off':
                        cur.execute("UPDATE users SET total_leaves = GREATEST(16.0, total_leaves - %s) WHERE id = %s", (days, leave['user_id']))
                        
            conn.commit()
            return jsonify({"success": True, "leave": dict(updated_leave)})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/leaves/<int:leave_id>", methods=["DELETE"])
def delete_leave(leave_id):
    @_require_auth
    def _handler(current_user):
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role, id FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if not u:
                    return jsonify({"success": False, "message": "User not found"}), 404

                cur.execute("SELECT * FROM leaves WHERE id = %s", (leave_id,))
                leave = cur.fetchone()
                if not leave:
                    return jsonify({"success": False, "message": "Leave not found"}), 404

                is_ceo = u["role"] == 'ceo'
                is_own_pending = (leave['user_id'] == u['id'] and leave['status'] == 'pending')

                # CEO can delete any leave; employees can only cancel their own pending requests
                if not is_ceo and not is_own_pending:
                    if leave['user_id'] == u['id']:
                        return jsonify({"success": False, "message": "You can only cancel pending leave requests"}), 403
                    return jsonify({"success": False, "message": "Unauthorized: cannot delete this leave"}), 403

                # If approved (CEO action), revert the user's leave balances
                if leave['status'] == 'approved':
                    start = datetime.strptime(str(leave['start_date']), '%Y-%m-%d')
                    end = datetime.strptime(str(leave['end_date']), '%Y-%m-%d')
                    days = 0.5 if leave['type'] == 'half-day' else float((end - start).days + 1)

                    if leave['type'] in ('regular', 'half-day'):
                        cur.execute("UPDATE users SET used_leaves = GREATEST(0.0, used_leaves - %s) WHERE id = %s", (days, leave['user_id']))
                    elif leave['type'] == 'comp-off':
                        cur.execute("UPDATE users SET total_leaves = GREATEST(16.0, total_leaves - %s) WHERE id = %s", (days, leave['user_id']))

                cur.execute("DELETE FROM leaves WHERE id = %s", (leave_id,))

            conn.commit()
            return jsonify({"success": True, "message": "Leave request cancelled/deleted successfully"})
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

# -----------------
# COMPANY CHAT API
# -----------------
@rbac_bp.route("/api/company/chat", methods=["GET"])
def get_company_messages():
    @_require_auth
    def _handler(current_user):
        other_user_id = request.args.get("user_id")
        
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if other_user_id:
                    cur.execute("""
                        SELECT cm.*, s.email as sender_email, r.email as receiver_email
                        FROM company_messages cm
                        JOIN users s ON cm.sender_id = s.id
                        LEFT JOIN users r ON cm.receiver_id = r.id
                        WHERE (cm.sender_id = %s AND cm.receiver_id = %s) OR (cm.sender_id = %s AND cm.receiver_id = %s)
                        ORDER BY cm.created_at ASC
                    """, (current_user["sub"], other_user_id, other_user_id, current_user["sub"]))
                else:
                    cur.execute("""
                        SELECT cm.*, s.email as sender_email, r.email as receiver_email
                        FROM company_messages cm
                        JOIN users s ON cm.sender_id = s.id
                        LEFT JOIN users r ON cm.receiver_id = r.id
                        WHERE cm.sender_id = %s OR cm.receiver_id = %s
                        ORDER BY cm.created_at ASC
                    """, (current_user["sub"], current_user["sub"]))
                messages = cur.fetchall()
            return jsonify({"success": True, "messages": [dict(m) for m in messages]})
        finally:
            conn.close()
    return _handler()

@rbac_bp.route("/api/company/chat", methods=["POST"])
def send_company_message():
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        receiver_id = data.get("receiver_id")
        content = data.get("content", "").strip()
        
        if not receiver_id or not content:
            return jsonify({"success": False, "message": "Receiver and content required"}), 400
            
        conn = _get_db()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Basic RBAC: Employees can chat with managers, managers can chat with employees.
                # Just saving the message for now
                cur.execute(
                    "INSERT INTO company_messages (sender_id, receiver_id, content) VALUES (%s, %s, %s) RETURNING *",
                    (current_user["sub"], receiver_id, content)
                )
                msg = cur.fetchone()
            conn.commit()
            return jsonify({"success": True, "message": dict(msg)}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "message": str(e)}), 500
        finally:
            conn.close()
    return _handler()

# -----------------
# AI CHATBOT API
# -----------------
@rbac_bp.route("/api/chatbot", methods=["POST"])
def ai_chatbot():
    @_require_auth
    def _handler(current_user):
        data = request.get_json() or {}
        msg = data.get("message", "").strip()
        
        if not msg:
            return jsonify({"success": False, "reply": "I didn't catch that. How can I help you?"})
            
        conn = _get_db()
        user_role = 'employee'  # default
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT role FROM users WHERE id = %s", (current_user["sub"],))
                u = cur.fetchone()
                if u:
                    user_role = u["role"]
        except Exception as e:
            return jsonify({"success": False, "reply": f"Error checking authorization: {str(e)}"})
        finally:
            conn.close()
            
        try:
            # Import dynamically to avoid circular imports
            from app import invoke_query_reply
            
            reply = invoke_query_reply(msg, history=[], user_id=current_user["sub"], chat_mode='general', user_role=user_role)
            return jsonify({"success": True, "reply": reply})
        except Exception as e:
            return jsonify({"success": False, "reply": f"Error processing AI request: {str(e)}"})
            
    return _handler()
