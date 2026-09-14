import cv2

from . import config


COLORS = {
    "SAFE": (0, 255, 0),
    "PROXIMITY_BREACH": (0, 0, 255),
    "NO_DEPTH": (0, 165, 255),
}


def draw_boxes(frame, people):
    frame_height, frame_width = frame.shape[:2]

    for person in people:
        x1, y1, x2, y2 = person["bbox"]

        x1 = max(0, min(x1, frame_width - 1))
        x2 = max(0, min(x2, frame_width - 1))
        y1 = max(0, min(y1, frame_height - 1))
        y2 = max(0, min(y2, frame_height - 1))

        color = COLORS.get(person.get("zone"), (0, 255, 0))

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        distance = person.get("distance")

        if distance is None:
            label = (
                f"ID:{person['id']} "
                f"NO DEPTH "
                f"{person.get('zone', 'NO_DEPTH')}"
            )
        else:
            label = (
                f"ID:{person['id']} "
                f"{distance:.2f}m "
                f"{person.get('zone', 'SAFE')}"
            )

        label_y = max(20, y1 - 10)

        cv2.putText(
            frame,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

        xyz = person.get("xyz")

        if xyz is not None:
            x, y, z = xyz
            xyz_label = f"XYZ: {x:.2f}, {y:.2f}, {z:.2f} m"

            cv2.putText(
                frame,
                xyz_label,
                (x1, min(frame_height - 10, y2 + 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
            )


def draw_info_panel(frame, fps, people_count):
    cv2.rectangle(frame, (0, 0), (300, 48), (30, 30, 30), -1)

    panel_text = f"FPS: {fps:.1f} | People: {people_count}"

    cv2.putText(
        frame,
        panel_text,
        (10, 31),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )


def draw_breach_text(frame, breach_occurred):
    if not breach_occurred:
        return

    text = "PROXIMITY BREACH"

    (text_width, _), _ = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        3,
    )

    x = max(10, (frame.shape[1] - text_width) // 2)

    cv2.rectangle(
        frame,
        (x - 10, 52),
        (x + text_width + 10, 92),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        frame,
        text,
        (x, 82),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 255),
        3,
    )