"""
Simulator data generator engine.

Generates values for each pattern type based on elapsed time and configuration.
"""

from __future__ import annotations

import ast
import math
import operator
import random
from typing import Any


# ---------------------------------------------------------------------------
# Safe math evaluator for "formula" pattern
# ---------------------------------------------------------------------------

_SAFE_NAMES: dict[str, Any] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "pi": math.pi,
    "e": math.e,
    "random": random.random,
}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval_node(node: ast.AST, variables: dict[str, Any]) -> Any:
    """Recursively evaluate an AST node with a restricted set of operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body, variables)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")

    if isinstance(node, ast.Name):
        name = node.id
        if name in variables:
            return variables[name]
        if name in _SAFE_NAMES:
            return _SAFE_NAMES[name]
        raise ValueError(f"Unknown variable: {name}")

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval_node(node.left, variables)
        right = _safe_eval_node(node.right, variables)
        return _SAFE_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _safe_eval_node(node.operand, variables)
        return _SAFE_OPS[op_type](operand)

    if isinstance(node, ast.Call):
        func = _safe_eval_node(node.func, variables)
        if not callable(func):
            raise ValueError(f"Not callable: {func}")
        args = [_safe_eval_node(arg, variables) for arg in node.args]
        return func(*args)

    if isinstance(node, ast.IfExp):
        test = _safe_eval_node(node.test, variables)
        if test:
            return _safe_eval_node(node.body, variables)
        return _safe_eval_node(node.orelse, variables)

    if isinstance(node, ast.Compare):
        left = _safe_eval_node(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            right = _safe_eval_node(comparator, variables)
            if isinstance(op, ast.Gt):
                result = left > right
            elif isinstance(op, ast.Lt):
                result = left < right
            elif isinstance(op, ast.GtE):
                result = left >= right
            elif isinstance(op, ast.LtE):
                result = left <= right
            elif isinstance(op, ast.Eq):
                result = left == right
            elif isinstance(op, ast.NotEq):
                result = left != right
            else:
                raise ValueError(f"Unsupported comparison: {type(op).__name__}")
            if not result:
                return False
            left = right
        return True

    raise ValueError(f"Unsupported AST node: {type(node).__name__}")


def safe_eval_formula(expression: str, t: float) -> float:
    """Evaluate a mathematical expression with t as the time variable.

    Supports: sin, cos, tan, abs, min, max, sqrt, log, random, pi, e
    and basic arithmetic (+, -, *, /, %, **).
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid formula syntax: {exc}") from exc

    variables = {"t": t}
    result = _safe_eval_node(tree, variables)
    if isinstance(result, (int, float)):
        return float(result)
    return 0.0


# ---------------------------------------------------------------------------
# Value generators
# ---------------------------------------------------------------------------


def generate_value(
    pattern_type: str,
    config: dict[str, Any],
    elapsed_seconds: float,
    last_value: Any | None = None,
) -> Any:
    """Generate the next value for a given pattern type.

    Args:
        pattern_type: One of the supported pattern types.
        config: Pattern-specific configuration dictionary.
        elapsed_seconds: Seconds since the simulator started.
        last_value: The previously generated value (used by random_walk, manual).

    Returns:
        The generated value (float, dict for gps, bool for step with booleans, etc.)
    """
    generators = {
        "sine": _gen_sine,
        "random_walk": _gen_random_walk,
        "step": _gen_step,
        "ramp": _gen_ramp,
        "counter": _gen_counter,
        "gps_track": _gen_gps_track,
        "noise": _gen_noise,
        "formula": _gen_formula,
        "csv_replay": _gen_csv_replay,
        "manual": _gen_manual,
    }
    gen_fn = generators.get(pattern_type)
    if gen_fn is None:
        raise ValueError(f"Unknown pattern type: {pattern_type}")
    return gen_fn(config, elapsed_seconds, last_value)


# --- Individual generators ---


def _gen_sine(config: dict, elapsed: float, _last: Any) -> float:
    min_val = config.get("min", 0.0)
    max_val = config.get("max", 100.0)
    period = config.get("period_seconds", 86400)
    phase = config.get("phase_offset", 0.0)

    center = (min_val + max_val) / 2.0
    amplitude = (max_val - min_val) / 2.0
    if period <= 0:
        period = 86400
    value = center + amplitude * math.sin(2 * math.pi * elapsed / period + phase)
    return round(value, 4)


def _gen_random_walk(config: dict, _elapsed: float, last_value: Any) -> float:
    center = config.get("center", 50.0)
    volatility = config.get("volatility", 1.0)
    min_bound = config.get("min_bound", float("-inf"))
    max_bound = config.get("max_bound", float("inf"))

    if last_value is None:
        last_value = center
    else:
        last_value = float(last_value)

    step = random.gauss(0, volatility)
    value = last_value + step
    value = max(min_bound, min(max_bound, value))
    return round(value, 4)


def _gen_step(config: dict, elapsed: float, _last: Any) -> Any:
    values = config.get("values", [0, 1])
    interval = config.get("interval_seconds", 60)
    if not values:
        return 0
    if interval <= 0:
        interval = 60
    index = int(elapsed / interval) % len(values)
    return values[index]


def _gen_ramp(config: dict, elapsed: float, _last: Any) -> float:
    start = config.get("start", 0.0)
    end = config.get("end", 100.0)
    duration = config.get("duration_seconds", 3600)
    loop = config.get("loop", True)

    if duration <= 0:
        duration = 3600

    if loop:
        progress = (elapsed % duration) / duration
    else:
        progress = min(elapsed / duration, 1.0)

    value = start + (end - start) * progress
    return round(value, 4)


def _gen_counter(config: dict, elapsed: float, _last: Any) -> float:
    start = config.get("start", 0.0)
    increment = config.get("increment", 1.0)
    interval = config.get("interval_seconds", 60)
    reset_at = config.get("reset_at", None)

    if interval <= 0:
        interval = 60

    ticks = int(elapsed / interval)
    value = start + ticks * increment

    if reset_at is not None and value >= reset_at:
        cycles = int((value - start) / (reset_at - start))
        value = value - cycles * (reset_at - start)

    return round(value, 4)


def _gen_gps_track(config: dict, elapsed: float, _last: Any) -> dict:
    waypoints = config.get("waypoints", [])
    speed_kmh = config.get("speed_kmh", 30.0)

    if not waypoints or len(waypoints) < 2:
        return {"lat": 0.0, "lng": 0.0}

    # Calculate total distance along waypoints (rough haversine)
    segments: list[tuple[float, int]] = []  # (distance_km, start_index)
    total_distance = 0.0
    for i in range(len(waypoints) - 1):
        d = _haversine_km(
            waypoints[i]["lat"], waypoints[i]["lng"],
            waypoints[i + 1]["lat"], waypoints[i + 1]["lng"],
        )
        segments.append((d, i))
        total_distance += d

    if total_distance == 0:
        return {"lat": waypoints[0]["lat"], "lng": waypoints[0]["lng"]}

    # Distance traveled so far
    speed_km_s = speed_kmh / 3600.0
    traveled = (speed_km_s * elapsed) % total_distance  # loop

    # Find which segment we're on
    cumulative = 0.0
    for seg_dist, seg_idx in segments:
        if cumulative + seg_dist >= traveled:
            # Interpolate within this segment
            frac = (traveled - cumulative) / seg_dist if seg_dist > 0 else 0.0
            lat = waypoints[seg_idx]["lat"] + frac * (
                waypoints[seg_idx + 1]["lat"] - waypoints[seg_idx]["lat"]
            )
            lng = waypoints[seg_idx]["lng"] + frac * (
                waypoints[seg_idx + 1]["lng"] - waypoints[seg_idx]["lng"]
            )
            return {"lat": round(lat, 6), "lng": round(lng, 6)}
        cumulative += seg_dist

    # Fallback: last point
    return {
        "lat": round(waypoints[-1]["lat"], 6),
        "lng": round(waypoints[-1]["lng"], 6),
    }


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _gen_noise(config: dict, _elapsed: float, _last: Any) -> float:
    center = config.get("center", 0.0)
    amplitude = config.get("amplitude", 1.0)
    value = center + random.uniform(-amplitude, amplitude)
    return round(value, 4)


def _gen_formula(config: dict, elapsed: float, _last: Any) -> float:
    expression = config.get("expression", "0")
    try:
        return round(safe_eval_formula(expression, elapsed), 4)
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0.0


def _gen_csv_replay(config: dict, elapsed: float, _last: Any) -> Any:
    data = config.get("data", [])
    loop = config.get("loop", True)

    if not data:
        return 0.0

    # data is an array of {timestamp, value} sorted by timestamp
    # timestamp can be relative seconds from start
    total_duration = data[-1].get("timestamp", 0) - data[0].get("timestamp", 0)
    if total_duration <= 0:
        return data[0].get("value", 0.0)

    if loop:
        t = (elapsed % total_duration) + data[0].get("timestamp", 0)
    else:
        t = min(elapsed, total_duration) + data[0].get("timestamp", 0)

    # Find bracketing entries and interpolate
    for i in range(len(data) - 1):
        t0 = data[i].get("timestamp", 0)
        t1 = data[i + 1].get("timestamp", 0)
        if t0 <= t <= t1:
            if t1 == t0:
                return data[i].get("value", 0.0)
            frac = (t - t0) / (t1 - t0)
            v0 = data[i].get("value", 0.0)
            v1 = data[i + 1].get("value", 0.0)
            if isinstance(v0, (int, float)) and isinstance(v1, (int, float)):
                return round(v0 + frac * (v1 - v0), 4)
            return v0

    return data[-1].get("value", 0.0)


def _gen_manual(config: dict, _elapsed: float, last_value: Any) -> Any:
    if last_value is not None:
        return last_value
    return config.get("initial_value", 0.0)
