// Single global toast banner. _toast(ok, message) shows it; it auto-dismisses.
export function toast() {
  return {
    toastState: null, // { ok, message }
    _toastTimer: null,

    _toast(ok, message) {
      this.toastState = { ok, message };
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => (this.toastState = null), 4000);
    },

    dismissToast() {
      this.toastState = null;
    },
  };
}
