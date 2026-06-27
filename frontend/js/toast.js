// Single global toast banner. _toast(ok, message) shows it; it auto-dismisses.
export function toast() {
  return {
    toastState: null, // { ok, message } — kept during the fade so the color doesn't flip
    toastVisible: false,
    _toastTimer: null,

    _toast(ok, message) {
      this.toastState = { ok, message };
      this.toastVisible = true;
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => (this.toastVisible = false), 4000);
    },

    dismissToast() {
      this.toastVisible = false;
    },
  };
}
