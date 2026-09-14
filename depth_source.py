from collections import defaultdict, deque

import numpy as np

from . import config


_history = defaultdict(
    lambda: deque(maxlen=config.DEPTH_HISTORY_LENGTH)
)


def _sample_region_distance(bbox, depth_image):
    if depth_image is None or depth_image.size == 0:
        return None

    image_height, image_width = depth_image.shape[:2]

    x1, y1, x2, y2 = map(int, bbox)

    x1 = max(0, min(x1, image_width - 1))
    x2 = max(0, min(x2, image_width - 1))
    y1 = max(0, min(y1, image_height - 1))
    y2 = max(0, min(y2, image_height - 1))

    if x2 <= x1 or y2 <= y1:
        return None

    margin_x = int(
        (x2 - x1) * config.DEPTH_SAMPLE_MARGIN_PERCENT
    )
    margin_y = int(
        (y2 - y1) * config.DEPTH_SAMPLE_MARGIN_PERCENT
    )

    inner_x1 = x1 + margin_x
    inner_x2 = x2 - margin_x
    inner_y1 = y1 + margin_y
    inner_y2 = y2 - margin_y

    if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
        inner_x1, inner_x2 = x1, x2
        inner_y1, inner_y2 = y1, y2

    region = depth_image[
        inner_y1:inner_y2 + 1:config.DEPTH_SAMPLE_STEP,
        inner_x1:inner_x2 + 1:config.DEPTH_SAMPLE_STEP,
    ]

    if region.size == 0:
        return None

    values = region.astype(np.float32).reshape(-1)

    if depth_image.dtype == np.uint16:
        values /= 1000.0

    values = values[
        np.isfinite(values)
        & (values > 0.0)
        & (values < 10.0)
    ]

    if values.size == 0:
        return None

    return float(np.median(values))


def get_distance(person_id, bbox, depth_image):
    raw_distance = _sample_region_distance(bbox, depth_image)

    if raw_distance is None:
        return None

    history = _history[person_id]
    history.append(raw_distance)

    return round(float(np.median(history)), 2)


def reset_history(person_id):
    _history.pop(person_id, None)


def estimate_xyz(bbox, distance_m, camera_info):
    if distance_m is None or camera_info is None:
        return None

    if len(camera_info.k) < 6:
        return None

    fx = float(camera_info.k[0])
    fy = float(camera_info.k[4])
    cx = float(camera_info.k[2])
    cy = float(camera_info.k[5])

    if fx <= 0.0 or fy <= 0.0:
        return None

    x1, y1, x2, y2 = bbox
    pixel_x = (x1 + x2) / 2.0
    pixel_y = (y1 + y2) / 2.0

    x = (pixel_x - cx) * distance_m / fx
    y = (pixel_y - cy) * distance_m / fy
    z = distance_m

    return (
        round(float(x), 3),
        round(float(y), 3),
        round(float(z), 3),
    )