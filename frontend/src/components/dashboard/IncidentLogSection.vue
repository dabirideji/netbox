<script setup lang="ts">
import { computed } from 'vue';
import { Pagination } from '../ui/pagination';
import { formatDateTime } from '../../format';
import type { StatusEvent } from '../../types';
import DashboardSectionCard from './DashboardSectionCard.vue';

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
</script>

<template>
  <DashboardSectionCard section-id="incidentLog" eyebrow="Incident log" title="Status changes" fullscreen>
    <template #meta>
      <span class="pill">{{ incidentPill }}</span>
    </template>

    <div class="events">
      <p v-if="!events.length" class="empty">No incidents yet. May the packets flow.</p>
      <article v-for="event in events" :key="`${event.targetId}-${event.at}-${event.to}`" class="event">
        <div class="event-copy">
          <strong>{{ event.targetLabel }}</strong>
          <small>{{ event.from }} → {{ event.to }}</small>
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
      @update:page="emit('update:page', $event)"
    />
  </DashboardSectionCard>
</template>
