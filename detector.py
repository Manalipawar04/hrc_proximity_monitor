from ultralytics import YOLO

from . import config


_model = None


def _get_model():
    global _model

    if _model is None:
        if not config.MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"YOLO model not found: {config.MODEL_PATH}"
            )

        _model = YOLO(str(config.MODEL_PATH))

    return _model


def detect_people(bgr_frame):
    model = _get_model()

    results = model.track(
        bgr_frame,
        conf=config.CONFIDENCE_THRESHOLD,
        classes=[0],
        persist=True,
        tracker="bytetrack.yaml",
        imgsz=config.YOLO_IMAGE_SIZE,
        verbose=False,
    )

    people = []

    if not results or results[0].boxes is None:
        return people

    boxes = results[0].boxes

    if boxes.id is None:
        return people

    for box, track_id in zip(boxes, boxes.id.tolist()):
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        people.append(
            {
                "id": int(track_id),
                "bbox": (
                    int(x1),
                    int(y1),
                    int(x2),
                    int(y2),
                ),
                "confidence": round(float(box.conf[0]), 2),
                "distance": None,
                "zone": "SAFE",
                "is_breach": False,
                "is_closest": False,
                "dwell_seconds": 0.0,
                "xyz": None,
            }
        )

    return people