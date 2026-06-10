import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { fetchEvents, fetchHistory, fetchTargetHistory } from '../api';
import { parseDateRange, type TimestampRange } from '../range';
import type { HistoryPoint, StatusEvent, TargetHistorySeries } from '../types';
import { usePersonalisationStore } from './personalisation';

export const EVENT_PAGE_SIZE = 10;

export const useHistoryStore = defineStore(
  'history',
  () => {
    const points = ref<HistoryPoint[]>([]);
    const targetSeries = ref<TargetHistorySeries[]>([]);
    const events = ref<StatusEvent[]>([]);
    const eventTotal = ref(0);
    const rangeError = ref('');

    const eventOffset = computed(() => usePersonalisationStore().eventPage * EVENT_PAGE_SIZE);
    const isRangeActive = computed(
      () => Boolean(usePersonalisationStore().rangeFrom || usePersonalisationStore().rangeTo),
    );

    function selectedRange(): TimestampRange | null {
      const personalisation = usePersonalisationStore();
      try {
        rangeError.value = '';
        return parseDateRange({ from: personalisation.rangeFrom, to: personalisation.rangeTo });
      } catch (error) {
        rangeError.value = error instanceof Error ? error.message : 'Invalid date range';
        return null;
      }
    }

    function eventMatchesRange(event: StatusEvent): boolean {
      const range = selectedRange();
      if (!range) return false;
      if (range.from !== undefined && event.at < range.from) return false;
      if (range.to !== undefined && event.at > range.to) return false;
      return true;
    }

    async function refreshTargetHistory(): Promise<void> {
      const range = selectedRange();
      if (!range) return;

      try {
        targetSeries.value = (await fetchTargetHistory(360, range)).targets;
      } catch {
        targetSeries.value = targetSeries.value;
      }
    }

    async function refreshHistory(): Promise<void> {
      const range = selectedRange();
      if (!range) return;

      try {
        points.value = (await fetchHistory(360, range)).points;
      } catch {
        points.value = points.value;
      }
    }

    async function refreshEvents(): Promise<void> {
      const range = selectedRange();
      if (!range) return;

      const personalisation = usePersonalisationStore();

      try {
        const response = await fetchEvents(EVENT_PAGE_SIZE, range, eventOffset.value);
        events.value = response.events;
        eventTotal.value = response.total;

        const maxPage = Math.max(0, Math.ceil(response.total / EVENT_PAGE_SIZE) - 1);
        if (personalisation.eventPage > maxPage) {
          personalisation.setEventPage(maxPage);
          await refreshEvents();
        }
      } catch {
        events.value = events.value;
      }
    }

    async function refreshAll(): Promise<void> {
      await Promise.all([refreshHistory(), refreshTargetHistory(), refreshEvents()]);
    }

    function seedFromSummary(summaryEvents: StatusEvent[], pageSize = EVENT_PAGE_SIZE): void {
      events.value = [...summaryEvents].reverse().slice(0, pageSize);
      eventTotal.value = summaryEvents.length;
    }

    function handleStreamEvent(event: StatusEvent): void {
      if (!eventMatchesRange(event)) return;

      eventTotal.value += 1;
      const personalisation = usePersonalisationStore();
      if (personalisation.eventPage === 0) {
        events.value = [event, ...events.value].slice(0, EVENT_PAGE_SIZE);
      }
    }

    function resetPagination(): void {
      usePersonalisationStore().setEventPage(0);
    }

    function clearRangeError(): void {
      rangeError.value = '';
    }

    return {
      points,
      targetSeries,
      events,
      eventTotal,
      rangeError,
      isRangeActive,
      selectedRange,
      refreshHistory,
      refreshTargetHistory,
      refreshEvents,
      refreshAll,
      seedFromSummary,
      handleStreamEvent,
      resetPagination,
      clearRangeError,
    };
  },
  {
    persist: {
      key: 'netbox-history',
      storage: localStorage,
      pick: ['points', 'events', 'eventTotal'],
    },
  },
);
