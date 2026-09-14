import time
import sys

import config


_last_alert_time = 0


def trigger_alert(distance_m=None):
    global _last_alert_time

    if not config.AUDIO_ALERT_ENABLED:
        return

    current_time = time.time()

    if current_time - _last_alert_time < config.ALERT_COOLDOWN_SECONDS:
        return

    try:
        import subprocess

        subprocess.run(
            [
                "paplay",
                "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )

        _last_alert_time = current_time

    except Exception:
        try:
            import os

            os.system(
                f"beep -f {config.BEEP_FREQUENCY_HZ} "
                f"-l {config.BEEP_DURATION_MS} 2>/dev/null || true"
            )

            _last_alert_time = current_time

        except Exception:
            print(
                "Audio alert skipped (no audio device available)",
                file=sys.stderr,
            )