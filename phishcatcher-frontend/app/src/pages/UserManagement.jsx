/**
 * UserManagement.jsx
 * Admin page: searchable user table with edit modal, activate/deactivate toggle, delete.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Search, UserCheck, UserX, Edit2, Trash2,
  X, Loader2, Users, AlertTriangle,
} from 'lucide-react';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';

const PAGE_SIZE = 25;

/* ─── Delete Confirmation Modal ──────────────────────────────────────────── */
function DeleteModal({ user, onClose, onConfirm }) {
  const [password, setPassword] = useState('');
  const [confirming, setConfirming] = useState(false);

  const handleConfirm = async () => {
    if (!password.trim()) {
      toast.error('Admin password is required');
      return;
    }
    setConfirming(true);
    try {
      await onConfirm(user.id, { password });
      onClose();
    } catch (err) {
      toast.error(err.message ?? 'Failed to delete user');
    } finally {
      setConfirming(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-[98] bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="fixed inset-x-4 top-1/2 -translate-y-1/2 z-[99] max-w-md mx-auto rounded-2xl p-6 space-y-4"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>Delete User</h3>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>This action cannot be undone</p>
          </div>
        </div>
        
        <div className="space-y-3">
          <div className="p-3 rounded-xl"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
            <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>{user.email}</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {user.full_name || 'No name provided'}
            </p>
          </div>
          
          <div>
            <label className="form-label">Admin Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter your password to confirm"
              className="input-base"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="btn-ghost flex-1 h-10 justify-center text-sm">Cancel</button>
          <button
            onClick={handleConfirm}
            disabled={confirming || !password.trim()}
            className="btn-danger flex-1 h-10 justify-center text-sm"
          >
            {confirming ? <><Loader2 className="w-4 h-4 animate-spin mr-1" />Deleting...</> : 'Delete User'}
          </button>
        </div>
      </div>
    </>
  );
}

/* ─── Edit modal ────────────────────────────────────────────────────────── */
function EditModal({ user, onClose, onSave }) {
  const [name,    setName]    = useState(user.full_name ?? '');
  const [saving,  setSaving]  = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await adminApi.updateUser(user.id, { full_name: name });
      onSave({ ...user, full_name: name });
      toast.success('User updated');
      onClose();
    } catch (err) {
      toast.error(err.message ?? 'Failed to update user');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-[98] bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="fixed inset-x-4 top-1/2 -translate-y-1/2 z-[99] max-w-md mx-auto rounded-2xl p-6 space-y-4"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>Edit user</h3>
          <button onClick={onClose} style={{ color: 'var(--text-muted)' }}><X className="w-5 h-5" /></button>
        </div>
        <div>
          <label className="form-label">Email</label>
          <input type="email" value={user.email} disabled className="input-base opacity-60 cursor-not-allowed" />
        </div>
        <div>
          <label className="form-label">Full name</label>
          <input type="text" value={name} onChange={e => setName(e.target.value)} className="input-base" />
        </div>
        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="btn-ghost flex-1 h-10 justify-center text-sm">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex-1 h-10 justify-center text-sm">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save changes'}
          </button>
        </div>
      </div>
    </>
  );
}

/* ─── Main ─────────────────────────────────────────────────────────────── */
export default function UserManagement() {
  const [users,    setUsers]   = useState([]);
  const [loading,  setLoading] = useState(true);
  const [search,   setSearch]  = useState('');
  const [page,     setPage]    = useState(1);
  const [hasMore,  setHasMore] = useState(false);
  const [editing,  setEditing] = useState(null);
  const [toggling, setToggling]= useState(null);
  const [deleting, setDeleting]= useState(null);
  const [deleteModal, setDeleteModal] = useState(null);

  const load = useCallback(async (pg = 1, reset = true, q = search) => {
    setLoading(true);
    try {
      const res  = await adminApi.listUsers({ page: pg, pageSize: PAGE_SIZE, search: q || undefined });
      const list = res.users ?? res.items ?? (Array.isArray(res) ? res : []);
      setUsers(prev => reset ? list : [...prev, ...list]);
      setHasMore(list.length === PAGE_SIZE);
      setPage(pg);
    } catch (err) {
      toast.error(err.message ?? 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const timer = setTimeout(() => load(1, true, search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const handleToggleActive = async user => {
    setToggling(user.id);
    try {
      await adminApi.updateUser(user.id, { is_active: !user.is_active });
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, is_active: !u.is_active } : u));
      toast.success(`User ${user.is_active ? 'deactivated' : 'activated'}`);
    } catch (err) {
      toast.error(err.message ?? 'Failed to update user');
    } finally {
      setToggling(null);
    }
  };

  const handleDelete = async (userId, passwordData) => {
    setDeleting(userId);
    try {
      await adminApi.deleteUser(userId, passwordData);
      setUsers(prev => prev.filter(u => u.id !== userId));
      toast.success('User deleted');
    } catch (err) {
      toast.error(err.message ?? 'Failed to delete user');
    } finally {
      setDeleting(null);
    }
  };

  const handleDeleteClick = user => {
    setDeleteModal(user);
  };

  const handleSaveEdit = updated => {
    setUsers(prev => prev.map(u => u.id === updated.id ? updated : u));
  };

  return (
    <div className="animate-fade-in">
      {/* Edit modal */}
      {editing && (
        <EditModal
          user={editing}
          onClose={() => setEditing(null)}
          onSave={handleSaveEdit}
        />
      )}

      {/* Delete confirmation modal */}
      {deleteModal && (
        <DeleteModal
          user={deleteModal}
          onClose={() => setDeleteModal(null)}
          onConfirm={handleDelete}
        />
      )}

      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="page-title">User Management</h1>
          <p className="page-subtitle">{users.length} users loaded</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-5">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Search by email or name…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="input-base pl-10 pr-9"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-2xl overflow-hidden"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        {loading && users.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading users…</p>
          </div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-10 h-10 mx-auto mb-4 opacity-25" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {search ? 'No users match your search.' : 'No users found.'}
            </p>
          </div>
        ) : (
          <>
            <table className="table-base">
              <thead>
                <tr>
                  <th>User</th>
                  <th className="hidden sm:table-cell">Role</th>
                  <th>Status</th>
                  <th className="hidden lg:table-cell">Joined</th>
                  <th className="hidden md:table-cell">MFA</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td>
                      <div>
                        <p className="font-500 text-sm" style={{ color: 'var(--text-primary)' }}>
                          {u.full_name || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No name</span>}
                        </p>
                        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{u.email}</p>
                      </div>
                    </td>
                    <td className="hidden sm:table-cell">
                      <span className={u.role === 'admin' ? 'badge badge-brand' : 'badge badge-muted'}>
                        {u.role ?? 'user'}
                      </span>
                    </td>
                    <td>
                      <span className={u.is_active ? 'badge badge-success' : 'badge badge-danger'}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="hidden lg:table-cell">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td className="hidden md:table-cell">
                      <span className={u.mfa_enabled ? 'badge badge-success' : 'badge badge-muted'}>
                        {u.mfa_enabled ? 'On' : 'Off'}
                      </span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        {/* Edit */}
                        <button
                          onClick={() => setEditing(u)}
                          title="Edit user"
                          className="p-1.5 rounded-lg transition-opacity hover:opacity-70"
                          style={{ color: 'var(--brand)' }}
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        {/* Toggle active */}
                        <button
                          onClick={() => handleToggleActive(u)}
                          disabled={toggling === u.id}
                          title={u.is_active ? 'Deactivate' : 'Activate'}
                          className="p-1.5 rounded-lg transition-opacity hover:opacity-70 disabled:opacity-40"
                          style={{ color: u.is_active ? 'var(--threat)' : 'var(--success)' }}
                        >
                          {toggling === u.id
                            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            : u.is_active ? <UserX className="w-3.5 h-3.5" /> : <UserCheck className="w-3.5 h-3.5" />
                          }
                        </button>
                        {/* Delete */}
                        <button
                          onClick={() => handleDeleteClick(u)}
                          disabled={deleting === u.id}
                          title="Delete user"
                          className="p-1.5 rounded-lg transition-opacity hover:opacity-70 disabled:opacity-40"
                          style={{ color: 'var(--danger)' }}
                        >
                          {deleting === u.id
                            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            : <Trash2 className="w-3.5 h-3.5" />
                          }
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {hasMore && (
              <div className="p-4 text-center" style={{ borderTop: '1px solid var(--border)' }}>
                <button
                  onClick={() => load(page + 1, false)}
                  disabled={loading}
                  className="btn-ghost text-sm h-9 px-6"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Load more'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}