import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import SummaryMetricsSection from './SummaryMetricsSection.vue';
import type { TargetSummary } from '../../types';

const targets: TargetSummary[] = [
  {
    id: 'gateway',
    host: '192.168.1.1',
    label: 'Local Gateway',
    scope: 'gateway',
    type: 'host',
    protocol: 'icmp',
    group: 'Default',
    environment: 'local',
    enabled: true,
    intervalMs: 1000,
    timeoutMs: 900,
    config: {},
    currentStatus: 'operational',
    lastOk: true,
    lastLatencyMs: 12,
    lastCheckedAt: Date.now(),
    lastError: null,
    activeIncident: null,
    samples: 42,
    uptimePct: 99,
    packetLossPct: 1,
    avgLatencyMs: 14,
    minLatencyMs: 10,
    maxLatencyMs: 20,
    jitterMs: 2,
    recentFailures: 0,
    recentHighLatency: 0,
    history: [],
  },
  {
    id: 'dns',
    host: '1.1.1.1',
    label: 'Cloudflare DNS',
    scope: 'external',
    type: 'host',
    protocol: 'icmp',
    group: 'Default',
    environment: 'prod',
    enabled: true,
    intervalMs: 1000,
    timeoutMs: 900,
    config: {},
    currentStatus: 'degraded',
    lastOk: true,
    lastLatencyMs: 88,
    lastCheckedAt: Date.now(),
    lastError: null,
    activeIncident: null,
    samples: 18,
    uptimePct: 92,
    packetLossPct: 6,
    avgLatencyMs: 90,
    minLatencyMs: 70,
    maxLatencyMs: 120,
    jitterMs: 15,
    recentFailures: 1,
    recentHighLatency: 0,
    history: [],
  },
];

describe('SummaryMetricsSection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('shows overview metrics by default and switches to a selected source', async () => {
    const wrapper = mount(SummaryMetricsSection, {
      props: {
        sampleCount: 120,
        gatewayLatencyMs: 12,
        worstLoss: 6,
        worstJitter: 15,
        targets,
      },
    });

    expect(wrapper.text()).toContain('Gateway latency');
    expect(wrapper.text()).toContain('Worst packet loss');

    const dnsTab = wrapper.findAll('[role="tab"]').find((tab) => tab.text().includes('Cloudflare DNS'));
    expect(dnsTab).toBeTruthy();
    await dnsTab!.trigger('click');

    expect(wrapper.text()).toContain('Last latency');
    expect(wrapper.text()).toContain('88.0ms');
    expect(wrapper.text()).toContain('Packet loss');
    expect(wrapper.text()).not.toContain('Gateway latency');
  });
});
