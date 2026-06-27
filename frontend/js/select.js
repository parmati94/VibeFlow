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
