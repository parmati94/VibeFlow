import Alpine from 'alpinejs';

document.addEventListener('alpine:init', () => {
  Alpine.data('loginForm', () => ({
    username: '',
    password: '',
    loading: false,
    error: null,

    async login() {
      this.loading = true;
      this.error = null;
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: this.username, password: this.password }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Login failed');
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
