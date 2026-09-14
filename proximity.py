from . import config


_states = {}


def _raw_zone(distance_m):
    if distance_m < config.PROXIMITY_BREACH_DISTANCE:
        return "PROXIMITY_BREACH"

    return "SAFE"


def _update_state(person_id, distance_m):
    raw_zone = _raw_zone(distance_m)

    if person_id not in _states:
        _states[person_id] = {
            "confirmed_zone": "SAFE",
            "candidate_zone": "SAFE",
            "candidate_frames": 0,
        }

    state = _states[person_id]

    if raw_zone == state["confirmed_zone"]:
        state["candidate_zone"] = raw_zone
        state["candidate_frames"] = 0
        return state["confirmed_zone"]

    if raw_zone != state["candidate_zone"]:
        state["candidate_zone"] = raw_zone
        state["candidate_frames"] = 1
    else:
        state["candidate_frames"] += 1

    entering_breach = (
        state["confirmed_zone"] == "SAFE"
        and raw_zone == "PROXIMITY_BREACH"
    )

    required_frames = (
        config.FRAMES_TO_CONFIRM_BREACH
        if entering_breach
        else config.FRAMES_TO_CLEAR_BREACH
    )

    if state["candidate_frames"] >= required_frames:
        state["confirmed_zone"] = raw_zone
        state["candidate_zone"] = raw_zone
        state["candidate_frames"] = 0

    return state["confirmed_zone"]


def evaluate_proximity(people):
    valid_people = [
        person
        for person in people
        if person.get("distance") is not None
    ]

    closest_id = None

    if valid_people:
        closest_id = min(
            valid_people,
            key=lambda person: person["distance"],
        )["id"]

    for person in people:
        person["is_closest"] = person["id"] == closest_id

        if person.get("distance") is None:
            person["zone"] = "NO_DEPTH"
            person["is_breach"] = False
            continue

        zone = _update_state(
            person["id"],
            person["distance"],
        )

        person["zone"] = zone
        person["is_breach"] = zone == "PROXIMITY_BREACH"

    return people


def clear_state(person_id):
    _states.pop(person_id, None)