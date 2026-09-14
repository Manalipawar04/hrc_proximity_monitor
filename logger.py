import csv
import json
import sqlite3
import time

from . import config


class SessionLogger:
    def __init__(self):
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        config.SCREENSHOT_FOLDER.mkdir(parents=True, exist_ok=True)

        self._init_csv()
        self._init_db()

        self.session_start_time = time.monotonic()
        self.frame_count = 0
        self.breach_count = 0
        self.last_breach_log_time = {}

    def _init_csv(self):
        with open(
            config.LOG_FILE_PATH,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "timestamp",
                    "person_id",
                    "distance_m",
                    "zone",
                    "dwell_seconds",
                ]
            )

        with open(
            config.SYSTEM_EVENTS_LOG_PATH,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(
                ["timestamp", "event_type", "details"]
            )

    def _init_db(self):
        with sqlite3.connect(str(config.DATABASE_PATH)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    person_id INTEGER NOT NULL,
                    distance_m REAL NOT NULL,
                    zone TEXT NOT NULL,
                    dwell_seconds REAL NOT NULL
                )
                """
            )

    def next_frame(self, people_count):
        self.frame_count += 1

    def log_breach(
        self,
        person_id,
        distance_m,
        zone,
        dwell_seconds,
    ):
        now = time.monotonic()
        last_time = self.last_breach_log_time.get(person_id, 0.0)

        if now - last_time < config.LOG_COOLDOWN_SECONDS:
            return False

        timestamp = time.time()

        with open(
            config.LOG_FILE_PATH,
            "a",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    timestamp,
                    person_id,
                    distance_m,
                    zone,
                    dwell_seconds,
                ]
            )

        with sqlite3.connect(str(config.DATABASE_PATH)) as connection:
            connection.execute(
                """
                INSERT INTO events
                (timestamp, person_id, distance_m, zone, dwell_seconds)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    person_id,
                    distance_m,
                    zone,
                    dwell_seconds,
                ),
            )

        self.last_breach_log_time[person_id] = now
        self.breach_count += 1

        return True

    def log_system_event(self, event_type, details):
        timestamp = time.time()

        with open(
            config.SYSTEM_EVENTS_LOG_PATH,
            "a",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)
            writer.writerow(
                [timestamp, event_type, details]
            )

    def write_summary(self):
        duration = time.monotonic() - self.session_start_time

        summary = {
            "session_duration_seconds": round(duration, 2),
            "total_frames": self.frame_count,
            "total_logged_breaches": self.breach_count,
            "average_fps": round(
                self.frame_count / duration if duration > 0.0 else 0.0,
                2,
            ),
        }

        with open(
            config.SUMMARY_FILE_PATH,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(summary, file, indent=2)

        return summary