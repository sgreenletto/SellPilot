<script setup lang="ts">
import { X } from "@lucide/vue";

interface Props {
  modelValue: string;
  label?: string;
  placeholder?: string;
  clearable?: boolean;
  error?: string;
  disabled?: boolean;
  type?: "text" | "search" | "email" | "password";
}

const props = withDefaults(defineProps<Props>(), {
  label: "",
  placeholder: "",
  clearable: false,
  error: "",
  disabled: false,
  type: "text",
});

const emit = defineEmits<{
  "update:modelValue": [value: string];
  blur: [event: FocusEvent];
}>();

function updateValue(event: Event) {
  emit("update:modelValue", (event.target as HTMLInputElement).value);
}
</script>

<template>
  <label class="sp-input-field">
    <span v-if="props.label" class="sp-input-field__label">{{ props.label }}</span>
    <span :class="['sp-input-field__control', { 'sp-input-field__control--error': props.error }]">
      <span v-if="$slots.prefix" class="sp-input-field__prefix" aria-hidden="true">
        <slot name="prefix" />
      </span>
      <input
        :value="props.modelValue"
        :type="props.type"
        :placeholder="props.placeholder"
        :disabled="props.disabled"
        :aria-invalid="Boolean(props.error)"
        @input="updateValue"
        @blur="emit('blur', $event)"
      />
      <button
        v-if="props.clearable && props.modelValue && !props.disabled"
        type="button"
        class="sp-input-field__clear"
        aria-label="清空输入"
        @click="emit('update:modelValue', '')"
      >
        <X :size="14" />
      </button>
    </span>
    <span v-if="props.error" class="sp-input-field__error">{{ props.error }}</span>
  </label>
</template>

<style scoped>
.sp-input-field {
  display: grid;
  gap: var(--sp-space-2);
  min-width: 0;
}

.sp-input-field__label {
  color: var(--sp-color-text-secondary);
  font-size: var(--sp-font-xs);
  font-weight: 650;
}

.sp-input-field__control {
  display: flex;
  gap: var(--sp-space-2);
  align-items: center;
  min-height: 42px;
  padding: 0 var(--sp-space-4);
  background: var(--sp-color-surface);
  border: 1px solid var(--sp-border-strong);
  border-radius: var(--sp-radius-pill);
  transition:
    background var(--sp-transition-fast),
    border-color var(--sp-transition-fast),
    box-shadow var(--sp-transition-fast);
}

.sp-input-field__control:focus-within {
  background: var(--sp-color-surface-strong);
  border-color: var(--sp-color-accent-blue);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-color-accent-blue) 18%, transparent);
}

.sp-input-field__control--error {
  border-color: var(--sp-color-danger);
}

.sp-input-field__control input {
  width: 100%;
  min-width: 0;
  padding: 0;
  color: var(--sp-color-text);
  background: transparent;
  border: 0;
  outline: none;
}

.sp-input-field__control input::placeholder {
  color: var(--sp-color-text-muted);
}

.sp-input-field__prefix {
  color: var(--sp-color-text-muted);
}

.sp-input-field__clear {
  display: grid;
  place-items: center;
  padding: var(--sp-space-1);
  color: var(--sp-color-text-muted);
  cursor: pointer;
  background: transparent;
  border-radius: var(--sp-radius-pill);
}

.sp-input-field__error {
  color: var(--sp-color-danger);
  font-size: var(--sp-font-xs);
}
</style>
