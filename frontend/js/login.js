import Alpine from 'alpinejs';

document.addEventListener('alpine:init', () => {
  Alpine.data('loginForm', () => ({
    mode: 'login', // 'login' | 'setup'
    ready: false,
    username: '',
    password: '',
    confirm: '',
    loading: false,
    error: null,

    async init() {
      // First run (no account set up yet) → show the create-admin form instead of login.
      try {
        const res = await fetch('/api/auth/status', { credentials: 'include' });
        const data = await res.json();
        if (data.needs_setup) this.mode = 'setup';
      } catch {
        /* fall back to login mode */
      }
      this.ready = true;
    },

    async submit() {
      if (this.mode === 'setup' && this.password !== this.confirm) {
        this.error = "Passwords don't match";
        return;
      }
      this.loading = true;
      this.error = null;
      const url = this.mode === 'setup' ? '/api/auth/setup' : '/api/auth/login';
      try {
        const res = await fetch(url, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: this.username, password: this.password }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || (this.mode === 'setup' ? 'Setup failed' : 'Login failed'));
        }
        window.location.href = '/';
      } catch (e) {
        this.error = e.message;
      } finally {
        this.loading = false;
      }
    },
  }));
});

window.Alpine = Alpine;
Alpine.start();
