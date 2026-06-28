import Alpine from 'alpinejs';

// Reusable on-brand dropdown (replaces the browser's default <select>). Two-way bind a value
// with x-modelable + x-model:
//   <div x-data="vfselect(optionArray)" x-modelable="value" x-model="form.field"
//        @click.away="open = false" class="relative"> … </div>
// optionArray: [{ value, label }]. Selection writes `value`, which flows back to x-model.
Alpine.data('vfselect', (options = [], placeholder = 'Select…') => ({
  open: false,
  value: undefined,
  options,
  placeholder,

  get current() {
    return this.options.find((x) => String(x.value) === String(this.value)) || null;
  },
  get selectedLabel() {
    return this.current ? this.current.label : this.placeholder;
  },
  pick(v) {
    this.value = v;
    this.open = false;
  },
  isSelected(v) {
    return String(v) === String(this.value);
  },
}));

// On-brand month picker — a popover calendar (year nav + 12-month grid), like the browser's
// native month input but styled to match the app. Binds a 'YYYY-MM' string, same as vfselect:
//   <div x-data="vfmonthpicker('Jump to month…')" x-modelable="value" x-model="form.month" …>
// `choose(idx)` sets the value and returns it, so the markup can hand it to a callback:
//   @click="jumpToMonth(choose(idx))"
Alpine.data('vfmonthpicker', (placeholder = 'Pick a month…') => ({
  open: false,
  value: undefined, // 'YYYY-MM'
  placeholder,
  viewYear: new Date().getFullYear(),
  months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],

  get selectedLabel() {
    if (!this.value) return this.placeholder;
    const [y, m] = this.value.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString([], { month: 'long', year: 'numeric' });
  },
  toggle() {
    this.open = !this.open;
    // Open on the selected month's year, else the current year.
    if (this.open) this.viewYear = this.value ? Number(this.value.split('-')[0]) : new Date().getFullYear();
  },
  monthValue(idx) {
    return `${this.viewYear}-${String(idx + 1).padStart(2, '0')}`;
  },
  choose(idx) {
    this.value = this.monthValue(idx);
    this.open = false;
    return this.value;
  },
  isSelected(idx) {
    return this.value === this.monthValue(idx);
  },
  isFuture(idx) {
    const now = new Date();
    return this.viewYear > now.getFullYear()
      || (this.viewYear === now.getFullYear() && idx > now.getMonth());
  },
  get canNext() {
    return this.viewYear < new Date().getFullYear();
  },
  prevYear() {
    this.viewYear -= 1;
  },
  nextYear() {
    if (this.canNext) this.viewYear += 1;
  },
}));
