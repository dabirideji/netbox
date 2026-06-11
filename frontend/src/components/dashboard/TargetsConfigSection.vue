<script setup lang="ts">
import {
  PhCaretDown,
  PhCaretUp,
  PhDotsSixVertical,
  PhGlobeHemisphereWest,
  PhSpinner,
  PhWifiHigh,
} from '@phosphor-icons/vue';
import { TransitionGroup } from 'vue';
import { Button } from '../ui/button';
import { Pagination } from '../ui/pagination';
import DashboardSectionCard from './DashboardSectionCard.vue';
import TargetSourceDeleteModal from './TargetSourceDeleteModal.vue';
import TargetSourceTestModal from './TargetSourceTestModal.vue';
import TargetTaxonomyField from './TargetTaxonomyField.vue';
import { useTargetsConfigSection } from './useTargetsConfigSection';
import { TARGET_PROTOCOLS, TARGET_SCOPES, TARGET_TYPES } from '../../stores';
import { targetColorForSource } from '../../targetColors';
import { targetScopeHint, targetScopeLabel } from '../../targetScope';

const {
  targetsStore,
  personalisation,
  targetsPage,
  targetGroups,
  targetEnvironments,
  sortedTargets,
  form,
  isEditing,
  isLoading,
  isSaving,
  checkingId,
  isTestingForm,
  isReordering,
  error,
  draggingId,
  isSettling,
  onPointerDown,
  testModalOpen,
  testResult,
  testError,
  targetListScrollRef,
  deleteSourceModalOpen,
  pendingDeleteSource,
  deletingSource,
  displayTargets,
  protocolLabel,
  scopeCounts,
  scopeMetaLabel,
  targetSubtitle,
  useGroupDropdown,
  useEnvironmentDropdown,
  canDeleteGroup,
  canDeleteEnvironment,
  createGroupValue,
  createEnvironmentValue,
  removeGroupValue,
  removeEnvironmentValue,
  openDeleteSourceModal,
  closeDeleteSourceModal,
  confirmDeleteSource,
  closeTestModal,
  runFormTest,
  addTargetFromTest,
  isTargetExpanded,
  targetToggleLabel,
  toggleTarget,
  TARGETS_PAGE_SIZE,
} = useTargetsConfigSection();
</script>

<template>
  <DashboardSectionCard section-id="targets" eyebrow="Configuration" title="Monitor sources">
    <template #meta>
      <span class="pill">{{ sortedTargets.length }} targets</span>
      <span v-if="scopeCounts.gateway" class="pill pill--scope pill--scope-gateway">
        <PhWifiHigh class="pill__icon" weight="bold" aria-hidden="true" />
        {{ scopeMetaLabel('gateway') }}
      </span>
      <span v-if="scopeCounts.external" class="pill pill--scope pill--scope-external">
        <PhGlobeHemisphereWest class="pill__icon" weight="bold" aria-hidden="true" />
        {{ scopeMetaLabel('external') }}
      </span>
    </template>

    <div class="target-config">
      <form class="target-form" @submit.prevent="targetsStore.saveForm">
        <div class="target-form__grid">
          <label class="field">
            <span>Label</span>
            <input v-model.trim="form.label" required maxlength="80" placeholder="API health" />
          </label>

          <label class="field">
            <span>Protocol</span>
            <select v-model="form.protocol">
              <option v-for="protocol in TARGET_PROTOCOLS" :key="protocol" :value="protocol">
                {{ protocol.toUpperCase() }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Type</span>
            <select v-model="form.type">
              <option v-for="targetType in TARGET_TYPES" :key="targetType" :value="targetType">
                {{ targetType }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Scope</span>
            <select v-model="form.scope" :title="targetScopeHint(form.scope)">
              <option v-for="scope in TARGET_SCOPES" :key="scope" :value="scope" :title="targetScopeHint(scope)">
                {{ targetScopeLabel(scope) }}
              </option>
            </select>
          </label>

          <TargetTaxonomyField
            v-model="form.group"
            label="Group"
            :options="targetGroups"
            :use-dropdown="useGroupDropdown"
            :can-delete="canDeleteGroup"
            :create-value="createGroupValue"
            :remove-value="removeGroupValue"
            placeholder="Default"
            required
          />

          <TargetTaxonomyField
            v-model="form.environment"
            label="Environment"
            :options="targetEnvironments"
            :use-dropdown="useEnvironmentDropdown"
            :can-delete="canDeleteEnvironment"
            :create-value="createEnvironmentValue"
            :remove-value="removeEnvironmentValue"
            placeholder="local"
            required
          />

          <label class="field">
            <span>Interval ms</span>
            <input v-model.number="form.intervalMs" required type="number" min="250" max="3600000" step="250" />
          </label>

          <label class="field">
            <span>Timeout ms</span>
            <input v-model.number="form.timeoutMs" required type="number" min="100" max="60000" step="100" />
          </label>

          <label class="field field--color">
            <span>Chart color</span>
            <div class="color-input">
              <input v-model="form.color" type="color" aria-label="Chart color picker" />
              <input
                v-model="form.color"
                type="text"
                pattern="^#[0-9a-fA-F]{6}$"
                maxlength="7"
                spellcheck="false"
                placeholder="#38bdf8"
              />
            </div>
          </label>
        </div>

        <div class="target-form__protocol">
          <p>{{ protocolLabel }} settings</p>

          <template v-if="form.protocol === 'http' || form.protocol === 'https'">
            <label class="field field--wide">
              <span>URL</span>
              <input v-model.trim="form.url" required type="url" placeholder="https://example.com/health" />
            </label>
            <label class="field">
              <span>Method</span>
              <select v-model="form.method">
                <option>GET</option>
                <option>HEAD</option>
                <option>POST</option>
              </select>
            </label>
            <label class="field">
              <span>Expected</span>
              <input v-model.number="form.expectedStatus" required type="number" min="100" max="599" />
            </label>
            <label class="field field--wide">
              <span>Keyword</span>
              <input v-model.trim="form.keyword" placeholder="optional body match" />
            </label>
          </template>

          <template v-else-if="form.protocol === 'tcp'">
            <label class="field field--wide">
              <span>Host</span>
              <input v-model.trim="form.host" required placeholder="example.com" />
            </label>
            <label class="field">
              <span>Port</span>
              <input v-model.number="form.port" required type="number" min="1" max="65535" />
            </label>
          </template>

          <template v-else-if="form.protocol === 'dns'">
            <label class="field field--wide">
              <span>Record</span>
              <input v-model.trim="form.recordName" required placeholder="example.com" />
            </label>
            <label class="field">
              <span>Type</span>
              <select v-model="form.recordType">
                <option>A</option>
                <option>AAAA</option>
                <option>CNAME</option>
                <option>MX</option>
                <option>TXT</option>
                <option>NS</option>
              </select>
            </label>
            <label class="field field--wide">
              <span>Expected value</span>
              <input v-model.trim="form.expectedValue" placeholder="optional resolved value" />
            </label>
          </template>

          <template v-else>
            <label class="field field--wide">
              <span>Host</span>
              <input v-model.trim="form.host" required placeholder="1.1.1.1" />
            </label>
          </template>
        </div>

        <label class="target-toggle">
          <input v-model="form.enabled" type="checkbox" />
          Enabled
        </label>

        <p v-if="error" class="target-error">{{ error }}</p>

        <div class="target-actions">
          <Button type="button" variant="ghost" size="sm" :disabled="isSaving || isTestingForm" @click="runFormTest">
            <span v-if="isTestingForm" class="target-check-label">
              <PhSpinner class="target-check-label__icon" weight="bold" aria-hidden="true" />
              Testing<span class="pill__dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
            </span>
            <template v-else>Test</template>
          </Button>
          <Button type="submit" size="sm" :disabled="isSaving || isTestingForm">
            <span v-if="isSaving" class="target-check-label">
              <PhSpinner class="target-check-label__icon" weight="bold" aria-hidden="true" />
              {{ isEditing ? 'Saving' : 'Adding' }}<span class="pill__dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
            </span>
            <template v-else>{{ isEditing ? 'Save target' : 'Add target' }}</template>
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="target-actions__reset"
            @click="targetsStore.resetForm"
          >
            {{ isEditing ? 'Cancel' : 'Reset' }}
          </Button>
        </div>
      </form>

      <div class="target-list-shell">
        <p v-if="!sortedTargets.length" class="empty target-list__empty">No targets configured yet.</p>
        <template v-else>
          <div ref="targetListScrollRef" class="target-list-scroll" :aria-busy="isLoading">
            <TransitionGroup
              name="target-reorder"
              tag="div"
              class="target-list"
              :class="{ 'is-reorder-settling': isSettling }"
            >
              <article
                v-for="target in displayTargets"
                :key="target.id"
                :data-target-id="target.id"
                :data-reorder-id="target.id"
                class="target-item"
                :class="{
                  'is-disabled': !target.enabled,
                  'is-expanded': isTargetExpanded(target.id),
                  'is-dragging': draggingId === target.id,
                }"
              >
                  <button
                    type="button"
                    class="target-drag-handle target-item__drag"
                    :aria-label="`Reorder ${target.label}`"
                    :disabled="isReordering || isSaving"
                    @pointerdown="onPointerDown(target.id, $event)"
                  >
                    <PhDotsSixVertical weight="bold" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    class="target-item__toggle"
                    :aria-expanded="isTargetExpanded(target.id)"
                    :aria-label="targetToggleLabel(target)"
                    @click="toggleTarget(target.id)"
                  >
                    <span class="target-item__summary">
                      <span
                        class="target-item__color"
                        :style="{ backgroundColor: targetColorForSource(target.config, target.id) }"
                        aria-hidden="true"
                      />
                      <strong class="target-item__label">{{ target.label }}</strong>
                      <span class="target-item__badges">
                        <span class="target-item__badge target-item__badge--scope">{{ targetScopeLabel(target.scope) }}</span>
                        <span class="target-item__badge">{{ target.enabled ? 'enabled' : 'paused' }}</span>
                      </span>
                    </span>
                    <PhCaretDown
                      v-if="!isTargetExpanded(target.id)"
                      class="target-item__chevron"
                      weight="bold"
                      aria-hidden="true"
                    />
                    <PhCaretUp v-else class="target-item__chevron" weight="bold" aria-hidden="true" />
                  </button>

                  <div v-show="isTargetExpanded(target.id)" class="target-item__body">
                    <small>{{ target.host }} · {{ targetSubtitle(target) }}</small>
                    <div class="target-item__actions">
                      <Button
                        type="button"
                        variant="ghost"
                        size="xs"
                        @click="targetsStore.runCheckNow(target.id)"
                        :disabled="checkingId === target.id"
                      >
                        <span v-if="checkingId === target.id" class="target-check-label">
                          <PhSpinner class="target-check-label__icon" weight="bold" aria-hidden="true" />
                          Checking<span class="pill__dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
                        </span>
                        <template v-else>Check</template>
                      </Button>
                      <Button type="button" variant="ghost" size="xs" @click="targetsStore.editTarget(target)">Edit</Button>
                      <Button type="button" variant="ghost" size="xs" @click="openDeleteSourceModal(target)">
                        Delete
                      </Button>
                    </div>
                  </div>
              </article>
            </TransitionGroup>
          </div>

          <Pagination
            v-if="sortedTargets.length"
            :current-page="targetsPage + 1"
            :total-items="sortedTargets.length"
            :items-per-page="TARGETS_PAGE_SIZE"
            :show-summary="false"
            @update:page="(page) => personalisation.setTargetsPage(Math.max(0, page - 1))"
          />
        </template>
      </div>
    </div>
  </DashboardSectionCard>

  <TargetSourceDeleteModal
    :open="deleteSourceModalOpen"
    :target="pendingDeleteSource"
    :deleting="deletingSource"
    @close="closeDeleteSourceModal"
    @confirm="confirmDeleteSource"
  />

  <TargetSourceTestModal
    :open="testModalOpen"
    :loading="isTestingForm"
    :result="testResult"
    :error="testError"
    :can-add="!isEditing"
    @close="closeTestModal"
    @add="addTargetFromTest"
  />
</template>
