"""In-process target scheduler with per-target intervals and bounded concurrency."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Any

from netbox.checks import run_check
from netbox.models import PingResult, Target
from netbox.state import MonitorState
from netbox.timeutils import now_ms

CheckRunner = Callable[[Target], PingResult | dict[str, Any]]
RenderCallback = Callable[[dict[str, Any]], None]


class TargetScheduler:
    """Run enabled targets on their own interval without requiring Redis or workers."""

    def __init__(
        self,
        state: MonitorState,
        max_workers: int = 8,
        jitter_ratio: float = 0.1,
        checker: CheckRunner = run_check,
    ) -> None:
        self.state = state
        self.max_workers = max(1, max_workers)
        self.jitter_ratio = max(0.0, min(jitter_ratio, 0.5))
        self.checker = checker
        self.next_due: dict[str, int] = {}
        self.inflight: dict[Future[PingResult | dict[str, Any]], Target] = {}

    def run(self, ends_at: int | None, render: RenderCallback | None = None) -> None:
        """Run checks until stopped or the optional deadline is reached."""

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while not self.state.stopping.is_set():
                current_time = now_ms()
                if ends_at is not None and current_time >= ends_at:
                    break

                targets = self.state.active_targets()
                target_map = {target.id: target for target in targets}
                self._drop_removed_targets(target_map)
                self._initialize_due_times(targets, current_time)
                self._submit_due_targets(executor, targets, current_time)
                self._collect_completed(render, timeout=0.2)

            self._drain_completed(render)

    def _drop_removed_targets(self, target_map: dict[str, Target]) -> None:
        """Forget due times for deleted or disabled targets."""

        for target_id in list(self.next_due):
            if target_id not in target_map:
                self.next_due.pop(target_id, None)

    def _initialize_due_times(self, targets: list[Target], current_time: int) -> None:
        """Schedule never-seen targets immediately."""

        for target in targets:
            self.next_due.setdefault(target.id, current_time)

    def _submit_due_targets(
        self,
        executor: ThreadPoolExecutor,
        targets: list[Target],
        current_time: int,
    ) -> None:
        """Submit due targets up to the configured concurrency limit."""

        running_ids = {target.id for target in self.inflight.values()}
        for target in targets:
            if len(self.inflight) >= self.max_workers:
                return
            if target.id in running_ids or self.next_due.get(target.id, current_time) > current_time:
                continue

            self.inflight[executor.submit(self.checker, target)] = target
            self.next_due[target.id] = current_time + target.interval_ms + self._jitter_ms(target)

    def _collect_completed(self, render: RenderCallback | None, timeout: float) -> None:
        """Persist completed checks and optionally render the latest summary."""

        if not self.inflight:
            time.sleep(timeout)
            return

        done, _ = wait(self.inflight.keys(), timeout=timeout, return_when=FIRST_COMPLETED)
        for future in done:
            target = self.inflight.pop(future)
            try:
                raw_result = future.result()
                result = raw_result.to_dict() if isinstance(raw_result, PingResult) else raw_result
            except Exception as error:  # noqa: BLE001 - scheduler converts executor failures into check results.
                result = {
                    "id": target.id,
                    "host": target.host,
                    "label": target.label,
                    "scope": target.scope,
                    "type": target.type,
                    "protocol": target.protocol,
                    "ok": False,
                    "latencyMs": None,
                    "error": str(error),
                    "checkedAt": now_ms(),
                    "durationMs": None,
                }
            summary = self.state.append_sample({"checkedAt": result["checkedAt"], "results": [result]})
            if render:
                render(summary)

    def _drain_completed(self, render: RenderCallback | None) -> None:
        """Persist any checks that finish during shutdown."""

        while self.inflight:
            self._collect_completed(render, timeout=0.1)

    def _jitter_ms(self, target: Target) -> int:
        """Return a small positive jitter to avoid synchronized probes."""

        max_jitter = int(target.interval_ms * self.jitter_ratio)
        return random.randint(0, max_jitter) if max_jitter > 0 else 0
