import { describe, expect, it } from 'vitest';
import {
  API_ERROR,
  MONITOR_STATUS,
  apiErrorBody,
  apiErrorCodeForMessage,
  isBackendUnavailableStatus,
  monitorStatusCode,
  monitorStatusSeverity,
  normalizeMonitorStatus,
  speedTestStatusCode,
  streamEventCode,
} from './responses';

describe('responses', () => {
  it('maps monitor statuses to stable codes and severities', () => {
    expect(MONITOR_STATUS.operational.severity).toBe(0);
    expect(monitorStatusCode('degraded')).toBe('MON-110');
    expect(monitorStatusSeverity('down')).toBe(2);
    expect(normalizeMonitorStatus('nope')).toBe('unknown');
  });

  it('maps speed and stream event codes', () => {
    expect(speedTestStatusCode('failed')).toBe('SPD-100');
    expect(streamEventCode('targets')).toBe('SSE-003');
    expect(streamEventCode('alert')).toBe('SSE-005');
  });

  it('builds API error payloads and resolves known messages', () => {
    expect(apiErrorBody(API_ERROR.queryRange.code, 'from must be less than or equal to to')).toEqual({
      code: 'API-4001',
      error: 'from must be less than or equal to to',
    });
    expect(apiErrorCodeForMessage('target was not found')).toBe('API-4040');
    expect(apiErrorCodeForMessage('protocol must be one of dns, http, https, icmp, tcp')).toBe('API-4006');
  });

  it('detects backend-unavailable HTTP statuses', () => {
    expect(isBackendUnavailableStatus(503)).toBe(true);
    expect(isBackendUnavailableStatus(400)).toBe(false);
  });
});
