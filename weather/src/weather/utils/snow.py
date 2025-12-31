"""Snow calculation utilities.

This module provides functions for calculating snowfall from precipitation
using temperature-dependent snow-to-liquid ratios.
"""

from __future__ import annotations


def get_snow_ratio(temp_c: float) -> float:
    """Get the snow-to-liquid ratio based on temperature.
    
    The ratio represents how many units of snow result from 1 unit of
    liquid water equivalent precipitation. Colder temperatures produce
    lighter, fluffier snow with higher ratios.
    
    Uses linear interpolation between reference points for smooth transitions.
    
    Args:
        temp_c: Temperature in Celsius.
        
    Returns:
        Snow-to-liquid ratio (e.g., 15.0 means 15:1).
        
    References:
        - National Weather Service snow ratio guidelines
        - Roebber et al. (2003) snow-to-liquid ratio climatology
    """
    # Reference points: (temperature_celsius, ratio)
    # Sorted from warmest to coldest
    reference_points = [
        (2.0, 0.0),    # Above freezing threshold - rain
        (0.0, 8.0),    # Freezing - heavy, wet snow
        (-3.0, 10.0),  # Just below freezing
        (-6.0, 12.0),  # Cold
        (-9.0, 15.0),  # Colder - good powder
        (-12.0, 18.0), # Very cold - dry powder
        (-15.0, 20.0), # Extremely cold
        (-20.0, 25.0), # Arctic cold
        (-25.0, 30.0), # Ultra-cold "cold smoke"
    ]
    
    # Above warmest reference point
    if temp_c >= reference_points[0][0]:
        return reference_points[0][1]
    
    # Below coldest reference point
    if temp_c <= reference_points[-1][0]:
        return reference_points[-1][1]
    
    # Find the two reference points to interpolate between
    for i in range(len(reference_points) - 1):
        t1, r1 = reference_points[i]
        t2, r2 = reference_points[i + 1]
        
        if t2 <= temp_c < t1:
            # Linear interpolation: ratio = r1 + (r2 - r1) * (t1 - temp) / (t1 - t2)
            fraction = (t1 - temp_c) / (t1 - t2)
            return r1 + (r2 - r1) * fraction
    
    # Fallback (shouldn't reach here)
    return 10.0


def calculate_snowfall_from_precip(
    precip_mm: float,
    temp_c: float,
    freezing_level_m: float | None = None,
    elevation_m: float | None = None,
) -> tuple[float, bool]:
    """Calculate snowfall from liquid precipitation.
    
    Uses temperature-dependent snow-to-liquid ratios to convert
    liquid precipitation to snowfall depth.
    
    Args:
        precip_mm: Precipitation in millimeters (liquid water equivalent).
        temp_c: Temperature in Celsius at the location.
        freezing_level_m: Optional freezing level height in meters.
        elevation_m: Optional elevation of the location in meters.
        
    Returns:
        Tuple of (snowfall_cm, is_snow) where:
        - snowfall_cm: Calculated snowfall in centimeters
        - is_snow: Whether precipitation falls as snow (vs rain)
    """
    if precip_mm is None or precip_mm <= 0:
        return 0.0, False
    
    if temp_c is None:
        # No temperature data - use conservative 10:1 ratio
        return precip_mm / 10.0, True
    
    # Determine if precipitation is snow or rain
    is_snow = temp_c <= 2  # Snow threshold
    
    # If we have freezing level and elevation, use that for better determination
    if freezing_level_m is not None and elevation_m is not None:
        # If location is above freezing level, it's snow
        # Add some buffer (300m) for mixed precipitation zone
        if elevation_m > freezing_level_m + 300:
            is_snow = True
        elif elevation_m < freezing_level_m - 300:
            is_snow = False
        # Otherwise use temperature
    
    if not is_snow:
        return 0.0, False
    
    # Get temperature-based ratio
    ratio = get_snow_ratio(temp_c)
    
    if ratio <= 0:
        return 0.0, False
    
    # Calculate snowfall: precip_mm * ratio / 10 gives cm
    # (because 10mm water = 1cm at 10:1 ratio)
    snowfall_cm = precip_mm * ratio / 10.0
    
    return snowfall_cm, True


def calculate_hourly_snowfall(
    precip_values: tuple[float | None, ...],
    temp_values: tuple[float | None, ...],
    freezing_levels: tuple[float | None, ...] | None = None,
    elevation_m: float | None = None,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[bool, ...]]:
    """Calculate enhanced snowfall for hourly data series.
    
    Args:
        precip_values: Hourly precipitation in mm.
        temp_values: Hourly temperature in Celsius.
        freezing_levels: Optional hourly freezing level heights in meters.
        elevation_m: Optional location elevation in meters.
        
    Returns:
        Tuple of:
        - snowfall_cm: Enhanced snowfall values in cm
        - rain_mm: Rain values in mm (precipitation that doesn't fall as snow)
        - is_snow: Boolean indicating if each hour has snow
    """
    snowfall_cm: list[float] = []
    rain_mm: list[float] = []
    is_snow_flags: list[bool] = []
    
    for i, precip in enumerate(precip_values):
        temp = temp_values[i] if i < len(temp_values) else None
        freezing_level = None
        if freezing_levels and i < len(freezing_levels):
            freezing_level = freezing_levels[i]
        
        if precip is None or precip <= 0:
            snowfall_cm.append(0.0)
            rain_mm.append(0.0)
            is_snow_flags.append(False)
            continue
        
        snow, is_snow = calculate_snowfall_from_precip(
            precip_mm=precip,
            temp_c=temp if temp is not None else 0.0,
            freezing_level_m=freezing_level,
            elevation_m=elevation_m,
        )
        
        snowfall_cm.append(snow)
        rain_mm.append(0.0 if is_snow else precip)
        is_snow_flags.append(is_snow)
    
    return tuple(snowfall_cm), tuple(rain_mm), tuple(is_snow_flags)

