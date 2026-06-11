<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { PhCaretDown, PhPlus, PhSpinner, PhTrash } from '@phosphor-icons/vue';
import { Button } from '../ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { SectionModal } from '../ui/section-modal';

const model = defineModel<string>({ required: true });

const props = withDefaults(
  defineProps<{
    label: string;
    options: string[];
    useDropdown: boolean;
    canDelete?: (value: string) => boolean;
    createValue?: (value: string) => Promise<void> | void;
    removeValue?: (value: string) => Promise<void> | void;
    placeholder?: string;
    maxlength?: number;
    required?: boolean;
  }>(),
  {
    canDelete: () => false,
    placeholder: '',
    maxlength: 60,
    required: false,
  },
);

const open = ref(false);
const createModalOpen = ref(false);
const deleteModalOpen = ref(false);
const draft = ref('');
const creating = ref(false);
const deleting = ref(false);
const pendingDeleteValue = ref<string | null>(null);

const displayOptions = computed(() => {
  const options = [...props.options];
  const current = model.value.trim();
  if (current && !options.includes(current)) {
    options.push(current);
    options.sort((left, right) => left.localeCompare(right));
  }
  return options;
});

const createModalTitle = computed(() => `New ${props.label.toLowerCase()}`);
const deleteModalTitle = computed(() => `Delete ${props.label.toLowerCase()}`);

function selectOption(value: string): void {
  model.value = value;
  open.value = false;
}

function openCreateModal(): void {
  open.value = false;
  draft.value = '';
  createModalOpen.value = true;
}

function closeCreateModal(): void {
  if (creating.value) return;
  createModalOpen.value = false;
  draft.value = '';
}

function openDeleteModal(value: string, event: MouseEvent): void {
  event.preventDefault();
  event.stopPropagation();
  if (!props.canDelete(value) || deleting.value) return;

  open.value = false;
  pendingDeleteValue.value = value;
  deleteModalOpen.value = true;
}

function closeDeleteModal(): void {
  if (deleting.value) return;
  deleteModalOpen.value = false;
  pendingDeleteValue.value = null;
}

async function submitCreate(): Promise<void> {
  const value = draft.value.trim();
  if (!value || creating.value || !props.createValue) return;

  creating.value = true;
  try {
    await props.createValue(value);
    model.value = value;
    createModalOpen.value = false;
    draft.value = '';
  } finally {
    creating.value = false;
  }
}

async function confirmDelete(): Promise<void> {
  const value = pendingDeleteValue.value;
  if (!value || deleting.value || !props.removeValue || !props.canDelete(value)) return;

  deleting.value = true;
  try {
    await props.removeValue(value);
    if (model.value === value) {
      model.value = props.options.find((option) => option !== value) ?? '';
    }
    deleteModalOpen.value = false;
    pendingDeleteValue.value = null;
  } finally {
    deleting.value = false;
  }
}

watch(open, (isOpen) => {
  if (!isOpen) draft.value = '';
});
</script>

<template>
  <label v-if="!useDropdown" class="field">
    <span>{{ label }}</span>
    <input
      v-model.trim="model"
      :required="required"
      :maxlength="maxlength"
      :placeholder="placeholder"
    />
  </label>

  <div v-else class="field target-taxonomy-field">
    <span>{{ label }}</span>
    <Popover v-model:open="open">
      <PopoverTrigger>
        <button
          type="button"
          class="target-taxonomy-field__trigger"
          :aria-label="`Choose ${label.toLowerCase()}`"
          :aria-expanded="open"
        >
          <span class="target-taxonomy-field__value" :class="{ 'is-placeholder': !model }">
            {{ model || placeholder }}
          </span>
          <PhCaretDown class="target-taxonomy-field__chevron" weight="bold" aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent class="target-taxonomy-field__menu">
        <div class="target-taxonomy-field__options" role="listbox" :aria-label="label">
          <div
            v-for="option in displayOptions"
            :key="option"
            class="target-taxonomy-field__option"
            :class="{ 'is-selected': option === model }"
          >
            <button
              type="button"
              class="target-taxonomy-field__option-button"
              role="option"
              :aria-selected="option === model"
              @click="selectOption(option)"
            >
              {{ option }}
            </button>
            <button
              v-if="options.includes(option) && canDelete(option)"
              type="button"
              class="target-taxonomy-field__delete"
              :aria-label="`Delete ${label.toLowerCase()} ${option}`"
              :disabled="deleting"
              @click="openDeleteModal(option, $event)"
            >
              <PhTrash weight="bold" aria-hidden="true" />
            </button>
          </div>
        </div>
        <button
          type="button"
          class="target-taxonomy-field__create"
          :aria-label="`Create ${label.toLowerCase()}`"
          @click="openCreateModal"
        >
          <PhPlus weight="bold" aria-hidden="true" />
        </button>
      </PopoverContent>
    </Popover>
    <input
      v-model="model"
      class="target-taxonomy-field__mirror"
      tabindex="-1"
      aria-hidden="true"
      :required="required"
      :maxlength="maxlength"
    />

    <Teleport to="body">
      <div v-if="createModalOpen" class="target-taxonomy-modal">
      <SectionModal mode="modal" :title="createModalTitle" @close="closeCreateModal">
        <form class="target-taxonomy-modal__form" @submit.prevent="submitCreate">
          <label class="field field--wide">
            <span>Name</span>
            <input
              v-model.trim="draft"
              :maxlength="maxlength"
              :placeholder="placeholder"
              :disabled="creating"
              autofocus
              required
            />
          </label>
          <div class="target-taxonomy-modal__actions">
            <Button type="button" variant="ghost" size="sm" :disabled="creating" @click="closeCreateModal">
              Cancel
            </Button>
            <Button type="submit" size="sm" :disabled="!draft.trim() || creating">
              <PhSpinner
                v-if="creating"
                class="target-taxonomy-modal__spinner"
                weight="bold"
                aria-hidden="true"
              />
              <span>{{ creating ? 'Creating' : 'Create' }}</span>
            </Button>
          </div>
        </form>
      </SectionModal>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="deleteModalOpen" class="target-taxonomy-modal">
      <SectionModal mode="modal" :title="deleteModalTitle" @close="closeDeleteModal">
        <div class="target-taxonomy-modal__form">
          <p class="target-taxonomy-modal__message">
            Remove <strong>{{ pendingDeleteValue }}</strong> from your {{ label.toLowerCase() }} list?
          </p>
          <div class="target-taxonomy-modal__actions">
            <Button type="button" variant="ghost" size="sm" :disabled="deleting" @click="closeDeleteModal">
              Cancel
            </Button>
            <Button type="button" size="sm" :disabled="deleting" @click="confirmDelete">
              <PhSpinner
                v-if="deleting"
                class="target-taxonomy-modal__spinner"
                weight="bold"
                aria-hidden="true"
              />
              <span>{{ deleting ? 'Deleting' : 'Delete' }}</span>
            </Button>
          </div>
        </div>
      </SectionModal>
      </div>
    </Teleport>
  </div>
</template>
