import { api } from './api.js';

// Per-user Discord notification settings. Spread into the root `app` component.
// Opened as a modal from the Settings panel.
export function notifications() {
  return {
    showNotifications: false,
    notif: {
      webhook_url: '',
      enabled: false,
      on_failure: true,
      on_revocation: true,
      on_success: false,
    },
    notifLoading: false,
    notifSaving: false,
    notifTesting: false,

    // Fetch config into state without opening the modal — keeps the Settings row's on/off
    // indicator accurate from boot. Silent on failure (the row just shows the default).
    async loadNotifications() {
      try {
        const cfg = await api.getNotifications();
        this.notif = { ...this.notif, ...cfg, webhook_url: cfg.webhook_url || '' };
      } catch (e) {
        /* non-fatal: leave defaults */
      }
    },

    async openNotifications() {
      this.showNotifications = true;
      this.notifLoading = true;
      try {
        await this.loadNotifications();
      } finally {
        this.notifLoading = false;
      }
    },

    closeNotifications() {
      this.showNotifications = false;
    },

    async saveNotifications() {
      if (this.notif.enabled && !this.notif.webhook_url.trim()) {
        this._toast(false, 'Enter a webhook URL to enable notifications.');
        return;
      }
      this.notifSaving = true;
      try {
        const saved = await api.saveNotifications({
          ...this.notif,
          webhook_url: this.notif.webhook_url.trim() || null,
        });
        this.notif = { ...this.notif, ...saved, webhook_url: saved.webhook_url || '' };
        this._toast(true, 'Notification settings saved.');
        this.showNotifications = false;
      } catch (e) {
        this._toast(false, e.message || 'Could not save notification settings.');
      } finally {
        this.notifSaving = false;
      }
    },

    async testNotification() {
      if (!this.notif.webhook_url.trim()) {
        this._toast(false, 'Enter a webhook URL to test.');
        return;
      }
      this.notifTesting = true;
      try {
        await api.testNotification(this.notif.webhook_url.trim());
        this._toast(true, 'Test sent — check your Discord channel.');
      } catch (e) {
        this._toast(false, e.message || 'Test failed.');
      } finally {
        this.notifTesting = false;
      }
    },
  };
}
