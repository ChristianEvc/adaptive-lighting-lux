"""Helper functions for the Adaptive Lighting custom components."""

from __future__ import annotations

import base64
import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp value between minimum and maximum."""
    return max(minimum, min(value, maximum))


def int_to_base36(num: int) -> str:
    """Convert an integer to its base-36 representation using numbers and uppercase letters.

    Base-36 encoding uses digits 0-9 and uppercase letters A-Z, providing a case-insensitive
    alphanumeric representation. The function takes an integer `num` as input and returns
    its base-36 representation as a string.

    Parameters
    ----------
    num
        The integer to convert to base-36.

    Returns
    -------
    str
        The base-36 representation of the input integer.

    Examples
    --------
    >>> num = 123456
    >>> base36_num = int_to_base36(num)
    >>> print(base36_num)
    '2N9'

    """
    alphanumeric_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    if num == 0:
        return alphanumeric_chars[0]

    base36_str = ""
    base = len(alphanumeric_chars)

    while num:
        num, remainder = divmod(num, base)
        base36_str = alphanumeric_chars[remainder] + base36_str

    return base36_str


def short_hash(string: str, length: int = 4) -> str:
    """Create a hash of 'string' with length 'length'."""
    return base64.b32encode(string.encode()).decode("utf-8").zfill(length)[:length]


def remove_vowels(input_str: str, length: int = 4) -> str:
    """Remove vowels from a string and return a string of length 'length'."""
    vowels = "aeiouAEIOU"
    output_str = "".join([char for char in input_str if char not in vowels])
    return output_str.zfill(length)[:length]


def color_difference_redmean(
    rgb1: tuple[float, float, float],
    rgb2: tuple[float, float, float],
) -> float:
    """Distance between colors in RGB space (redmean metric).

    The maximal distance between (255, 255, 255) and (0, 0, 0) ≈ 765.

    Sources:
    - https://en.wikipedia.org/wiki/Color_difference#Euclidean
    - https://www.compuphase.com/cmetric.htm
    """
    r_hat = (rgb1[0] + rgb2[0]) / 2
    delta_r, delta_g, delta_b = (
        (col1 - col2) for col1, col2 in zip(rgb1, rgb2, strict=True)
    )
    red_term = (2 + r_hat / 256) * delta_r**2
    green_term = 4 * delta_g**2
    blue_term = (2 + (255 - r_hat) / 256) * delta_b**2
    return math.sqrt(red_term + green_term + blue_term)


def parse_lux_curve(curve_str: str) -> list[tuple[float, float]]:
    """Parse a lux curve string into sorted (lux, value) pairs.

    Format: "lux1:val1, lux2:val2, ..." e.g. "0:100, 200:80, 500:40, 1000:10"
    """
    if not curve_str or not curve_str.strip():
        return []
    points: list[tuple[float, float]] = []
    for entry in curve_str.split(","):
        entry = entry.strip()
        if ":" not in entry:
            continue
        lux_str, val_str = entry.split(":", 1)
        points.append((float(lux_str.strip()), float(val_str.strip())))
    points.sort(key=lambda p: p[0])
    return points


def catmull_rom_interpolate(
    points: list[tuple[float, float]],
    x: float,
) -> float:
    """Interpolate using Catmull-Rom spline through sorted (x, y) points.

    Provides smooth C1-continuous interpolation. Outside the defined range,
    returns the nearest endpoint value.
    """
    if not points:
        msg = "No curve points defined"
        raise ValueError(msg)
    if len(points) == 1:
        return points[0][1]

    # Clamp to endpoints
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]

    # Two points: simple linear interpolation
    if len(points) == 2:
        t = (x - points[0][0]) / (points[1][0] - points[0][0])
        return points[0][1] + t * (points[1][1] - points[0][1])

    # Find the segment containing x
    seg = 0
    for i in range(len(points) - 1):
        if points[i][0] <= x <= points[i + 1][0]:
            seg = i
            break

    # Four control points (duplicate endpoints for edge segments)
    p0 = points[max(seg - 1, 0)][1]
    p1 = points[seg][1]
    p2 = points[seg + 1][1]
    p3 = points[min(seg + 2, len(points) - 1)][1]

    # Parameter t in [0, 1] within this segment
    t = (x - points[seg][0]) / (points[seg + 1][0] - points[seg][0])
    t2 = t * t
    t3 = t2 * t

    # Catmull-Rom polynomial
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def get_friendly_name(hass: HomeAssistant, entity_id: str) -> str:
    """Retrieve the friendly name of an entity."""
    state = hass.states.get(entity_id)
    if state and hasattr(state, "attributes"):
        attributes: dict[str, Any] = dict(getattr(state, "attributes", {}))
        return attributes.get("friendly_name", entity_id)
    return entity_id
