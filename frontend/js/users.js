import { api } from './api.js';

// Account state + admin user-management. Spread into the root `app` component.
// `currentUser`/`isAdmin` come from /api/auth/status (loaded in app.init).
export function users() {
  return {
    currentUser: null, // { username, is_admin }
    isAdmin: false,
    userList: [],
    usersLoading: false,

    // New-user form (hidden behind a "Create user" button until toggled open)
    showNewUser: false,
    newUser: { username: '', password: '', is_admin: false },
    creatingUser: false,

    // Custom modals (no browser confirm/prompt)
    deleteUserModal: { open: false, user: null },
    resetPwModal: { open: false, user: null, value: '', confirm: '', saving: false },

    // Change-own-password form
    pwForm: { current: '', next: '', confirm: '' },
    changingPw: false,

    // Sync preference toggle (optimistic; reverts on failure).
    savingPrefs: false,
    async toggleDuplicates() {
      if (!this.currentUser) return;
      const next = !this.currentUser.allow_duplicates;
      this.currentUser.allow_duplicates = next;
      this.savingPrefs = true;
      try {
        await api.updatePreferences({ allow_duplicates: next });
        this._toast(true, next ? 'Duplicate tracks will be kept.' : 'Duplicate tracks will be skipped.');
      } catch (e) {
        this.currentUser.allow_duplicates = !next;
        this._toast(false, e.message || 'Could not update preference.');
      } finally {
        this.savingPrefs = false;
      }
    },

    openNewUser() {
      this.newUser = { username: '', password: '', is_admin: false };
      this.showNewUser = true;
    },
    cancelNewUser() {
      this.showNewUser = false;
    },

    async loadUsers() {
      if (!this.isAdmin) return;
      this.usersLoading = true;
      try {
        this.userList = await api.listUsers();
      } catch (e) {
        this._toast(false, e.message || 'Could not load users.');
      } finally {
        this.usersLoading = false;
      }
    },

    async createUser() {
      const { username, password } = this.newUser;
      if (!username.trim() || !password) {
        this._toast(false, 'Username and password are required.');
        return;
      }
      this.creatingUser = true;
      try {
        await api.createUser({ ...this.newUser, username: username.trim() });
        this.newUser = { username: '', password: '', is_admin: false };
        this.showNewUser = false;
        await this.loadUsers();
        this._toast(true, 'User created.');
      } catch (e) {
        this._toast(false, e.message || 'Could not create user.');
      } finally {
        this.creatingUser = false;
      }
    },

    // ── Delete user (custom modal) ──
    askDeleteUser(u) {
      this.deleteUserModal = { open: true, user: u };
    },
    async confirmDeleteUser() {
      const u = this.deleteUserModal.user;
      this.deleteUserModal = { open: false, user: null };
      if (!u) return;
      try {
        await api.deleteUser(u.id);
        await this.loadUsers();
        this._toast(true, 'User deleted.');
      } catch (e) {
        this._toast(false, e.message || 'Could not delete user.');
      }
    },

    // ── Reset password (custom modal) ──
    askResetPassword(u) {
      this.resetPwModal = { open: true, user: u, value: '', confirm: '', saving: false };
    },
    async confirmResetPassword() {
      const m = this.resetPwModal;
      if (!m.value) {
        this._toast(false, 'Enter a new password.');
        return;
      }
      if (m.value !== m.confirm) {
        this._toast(false, "Passwords don't match.");
        return;
      }
      this.resetPwModal.saving = true;
      try {
        await api.resetUserPassword(m.user.id, m.value);
        this.resetPwModal = { open: false, user: null, value: '', confirm: '', saving: false };
        this._toast(true, 'Password reset.');
      } catch (e) {
        this.resetPwModal.saving = false;
        this._toast(false, e.message || 'Could not reset password.');
      }
    },

    async changeOwnPassword() {
      if (this.pwForm.next !== this.pwForm.confirm) {
        this._toast(false, "New passwords don't match.");
        return;
      }
      if (!this.pwForm.current || !this.pwForm.next) {
        this._toast(false, 'Fill in both password fields.');
        return;
      }
      this.changingPw = true;
      try {
        await api.changePassword(this.pwForm.current, this.pwForm.next);
        this.pwForm = { current: '', next: '', confirm: '' };
        this._toast(true, 'Password changed.');
      } catch (e) {
        this._toast(false, e.message || 'Could not change password.');
      } finally {
        this.changingPw = false;
      }
    },
  };
}
