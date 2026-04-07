"""Computed Variables Engine — evaluates formulas referencing other variables.

Formula syntax:
  - Reference variables by key: `temperature`, `humidity`, `sensor.pressure`
  - Math: +, -, *, /, **, %, abs(), min(), max(), round()
  - Constants: pi, e
  - Comparison: >, <, >=, <=, ==, !=
  - Boolean: and, or, not
  - Ternary: `value if condition else default`

Example formulas:
  - "temperature * 1.8 + 32"  (Celsius to Fahrenheit)
  - "(sensor1_temp + sensor2_temp) / 2"  (average)
  - "battery < 20"  (low battery flag)
  - "round(humidity, 1)"  (round to 1 decimal)
"""

import logging
import math
from typing import Any

logger = logging.getLogger("uvicorn.error")

# Safe builtins for formula evaluation
SAFE_BUILTINS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "int": int,
    "float": float,
    "bool": bool,
    "str": str,
    "len": len,
    "sum": sum,
    "pi": math.pi,
    "e": math.e,
    "sqrt": math.sqrt,
    "log": math.log,
    "sin": math.sin,
    "cos": math.cos,
    "ceil": math.ceil,
    "floor": math.floor,
    "True": True,
    "False": False,
    "None": None,
}


def evaluate_formula(formula: str, variables: dict[str, Any]) -> Any:
    """Evaluate a formula string with variable references.

    Args:
        formula: Math expression referencing variable keys
        variables: Dict of variable_key → current value

    Returns:
        Computed result, or None if evaluation fails
    """
    if not formula or not formula.strip():
        return None

    # Build safe namespace: builtins + variable values
    namespace = dict(SAFE_BUILTINS)
    for key, value in variables.items():
        # Replace dots in keys with underscores for Python compat
        safe_key = key.replace(".", "_").replace("-", "_")
        namespace[safe_key] = value
        # Also add original key if it's a simple name
        if key.isidentifier():
            namespace[key] = value

    try:
        # Replace dots in formula variable references
        safe_formula = formula
        for key in variables:
            if "." in key:
                safe_key = key.replace(".", "_").replace("-", "_")
                safe_formula = safe_formula.replace(key, safe_key)

        result = eval(safe_formula, {"__builtins__": {}}, namespace)  # noqa: S307
        return result
    except Exception as exc:
        logger.debug("computed_variable formula error: %s → %s", formula, exc)
        return None


async def compute_all(db) -> int:
    """Recompute all computed variables. Returns count of updated values."""
    from sqlalchemy import select
    from app.db.models.variables import VariableDefinition, VariableValue

    # Load all computed definitions
    res = await db.execute(
        select(VariableDefinition).where(
            VariableDefinition.formula.isnot(None),
            VariableDefinition.formula != "",
        )
    )
    computed_defs = list(res.scalars().all())
    if not computed_defs:
        return 0

    # Load all current variable values (global scope for now)
    res = await db.execute(select(VariableValue))
    all_values = {v.variable_key: v.value_json for v in res.scalars().all()}

    updated = 0
    for defn in computed_defs:
        result = evaluate_formula(defn.formula, all_values)
        if result is None:
            continue

        # Upsert the computed value
        existing = await db.execute(
            select(VariableValue).where(
                VariableValue.variable_key == defn.key,
                VariableValue.scope == defn.scope,
            )
        )
        val = existing.scalar_one_or_none()
        if val:
            val.value_json = result
            val.version = (val.version or 0) + 1
        else:
            db.add(VariableValue(
                variable_key=defn.key,
                scope=defn.scope,
                value_json=result,
                version=1,
            ))
        updated += 1

    await db.commit()
    return updated
