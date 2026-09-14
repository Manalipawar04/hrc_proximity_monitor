import time
from pathlib import Path

import cv2

import config


class ScreenshotManager:
    def __init__(self):
        config.SCREENSHOT_FOLDER.mkdir(parents=True, exist_ok=True)

        self.last_breach_screenshot_time = 0
        self.last_timer_screenshot_time = 0

    def check_and_capture(self, frame, closest_distance, fps, any_breach):
        current_time = time.time()

        if any_breach:
            if (
                current_time
                - self.last_breach_screenshot_time
                >= config.BREACH_SCREENSHOT_COOLDOWN_SECONDS
            ):
                self._capture(
                    frame,
                    "breach",
                    closest_distance,
                    fps,
                )
                self.last_breach_screenshot_time = current_time

        else:
            if (
                current_time
                - self.last_timer_screenshot_time
                >= config.TIMER_SCREENSHOT_INTERVAL_SECONDS
            ):
                self._capture(
                    frame,
                    "timer",
                    closest_distance,
                    fps,
                )
                self.last_timer_screenshot_time = current_time

    def _capture(self, frame, trigger_type, closest_distance, fps):
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        if closest_distance is not None:
            filename = (
                f"screenshot_{trigger_type}_"
                f"{timestamp}_"
                f"dist{closest_distance:.2f}m_"
                f"fps{fps:.1f}.png"
            )
        else:
            filename = (
                f"screenshot_{trigger_type}_"
                f"{timestamp}_"
                f"nodistance_"
                f"fps{fps:.1f}.png"
            )

        filepath = config.SCREENSHOT_FOLDER / filename

        cv2.imwrite(str(filepath), frame)