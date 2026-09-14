from pathlib import Path

from ament_index_python.packages import get_package_share_directory


PACKAGE_NAME = "hrc_proximity_monitor"

PACKAGE_SHARE_DIR = Path(
    get_package_share_directory(PACKAGE_NAME)
)

MODEL_PATH = PACKAGE_SHARE_DIR / "models" / "best_yolo11s.pt"

OUTPUT_DIR = Path.home() / "hrc_proximity_output"
LOG_DIR = OUTPUT_DIR / "logs"
SCREENSHOT_FOLDER = OUTPUT_DIR / "screenshots"

LOG_FILE_PATH = LOG_DIR / "events.csv"
SYSTEM_EVENTS_LOG_PATH = LOG_DIR / "system_events.csv"
SUMMARY_FILE_PATH = LOG_DIR / "session_summary.json"
DATABASE_PATH = LOG_DIR / "events.db"

CONFIDENCE_THRESHOLD = 0.40
YOLO_IMAGE_SIZE = 640

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS_TARGET = 30

PROXIMITY_BREACH_DISTANCE = 1.50
FRAMES_TO_CONFIRM_BREACH = 3
FRAMES_TO_CLEAR_BREACH = 5

DEPTH_SAMPLE_MARGIN_PERCENT = 0.15
DEPTH_SAMPLE_STEP = 5
DEPTH_HISTORY_LENGTH = 5

LOG_COOLDOWN_SECONDS = 3.0

BREACH_SCREENSHOT_COOLDOWN_SECONDS = 3.0
TIMER_SCREENSHOT_INTERVAL_SECONDS = 8.0

AUDIO_ALERT_ENABLED = True
BEEP_FREQUENCY_HZ = 1000
BEEP_DURATION_MS = 300
ALERT_COOLDOWN_SECONDS = 3.0

WINDOW_NAME = "ROS2 Depth-Aware Human Proximity Monitor"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 600
SHOW_OPENCV_WINDOW = True

COLOR_TOPIC = "/camera/camera/color/image_raw"
ALIGNED_DEPTH_TOPIC = (
    "/camera/camera/aligned_depth_to_color/image_raw"
)
CAMERA_INFO_TOPIC = "/camera/camera/color/camera_info"

CAMERA_FRAME_ID = "camera_color_optical_frame"