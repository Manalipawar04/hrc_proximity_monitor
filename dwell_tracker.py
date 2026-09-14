import time


_states = {}


def update(person_id, zone):
    now = time.monotonic()

    if person_id not in _states:
        _states[person_id] = {
            "zone": zone,
            "start_time": now,
        }
        return 0.0

    state = _states[person_id]

    if zone != state["zone"]:
        state["zone"] = zone
        state["start_time"] = now
        return 0.0

    return round(now - state["start_time"], 2)


def clear_state(person_id):
    _states.pop(person_id, None)