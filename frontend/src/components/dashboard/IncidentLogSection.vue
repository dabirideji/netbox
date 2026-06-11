<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { Pagination } from '../ui/pagination';
import { formatDateTime } from '../../format';
import { monitorStatusDefinition } from '../../responses';
import { useHistoryStore } from '../../stores/history';
import type { Status, StatusEvent } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';

const { loadingPage } = storeToRefs(useHistoryStore());

const props = defineProps<{
  events: StatusEvent[];
  eventTotal: number;
  eventPage: number;
  eventPageSize: number;
}>();

const emit = defineEmits<{
  'update:page': [page: number];
}>();

const incidentPill = computed(() => `${props.eventTotal} incident${props.eventTotal === 1 ? '' : 's'}`);

function statusClass(status: Status): string {
  return monitorStatusDefinition(status).cssClass;
}
</script>

<template>
  <DashboardSectionCard section-id="incidentLog" eyebrow="Incident log" title="Status changes" fullscreen>
    <template #meta>
      <span class="pill">{{ incidentPill }}</span>
    </template>

    <div class="events">
      <p v-if="!events.length" class="empty">No incidents yet. May the packets flow.</p>
      <article
        v-for="event in events"
        :key="`${event.targetId}-${event.at}-${event.to}`"
        class="event"
        :class="`event--${statusClass(event.to)}`"
      >
        <div class="event-copy">
          <strong>{{ event.targetLabel }}</strong>
          <div class="event-transition">
            <span class="status" :class="statusClass(event.from)">
              <span class="dot" aria-hidden="true" />
              {{ monitorStatusDefinition(event.from).label }}
            </span>
            <span class="event-transition__arrow" aria-hidden="true">→</span>
            <span class="status" :class="statusClass(event.to)">
              <span class="dot" aria-hidden="true" />
              {{ monitorStatusDefinition(event.to).label }}
            </span>
          </div>
        </div>
        <time class="event-time" :datetime="new Date(event.at).toISOString()">
          {{ formatDateTime(event.at) }}
        </time>
      </article>
    </div>

    <Pagination
      :current-page="eventPage + 1"
      :total-items="eventTotal"
      :items-per-page="eventPageSize"
      :loading-page="loadingPage"
      @update:page="emit('update:page', $event)"
    />
  </DashboardSectionCard>
</template>
