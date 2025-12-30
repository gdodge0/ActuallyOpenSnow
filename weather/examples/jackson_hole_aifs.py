#!/usr/bin/env python3
"""Example comparing forecasts from different models for Jackson Hole.

This example demonstrates:
- Fetching forecasts from multiple models (GFS, IFS, AIFS)
- Comparing snowfall predictions across models
- Using forecast equivalence checking
- Serializing forecasts to JSON
"""

import json
from datetime import timedelta

from weather import MeteoClient, Forecast


def format_snow(value: float) -> str:
    """Format snow value for display."""
    if value < 0.1:
        return "trace"
    return f"{value:.1f}"


def print_model_comparison(forecasts: dict[str, Forecast]) -> None:
    """Print a comparison of forecasts from different models."""
    print(f"\n{'='*70}")
    print("MODEL COMPARISON - Jackson Hole Summit (3185m)")
    print(f"{'='*70}")

    # Print model run times
    print("\nModel Run Times:")
    for model_id, forecast in forecasts.items():
        print(f"  {model_id.upper():6s}: {forecast.model_run_utc}")

    # Show available variables per model
    print("\nAvailable Variables:")
    for model_id, forecast in forecasts.items():
        vars_list = list(forecast.hourly_data.keys())
        units_info = ", ".join(f"{v}({forecast.hourly_units.get(v, '?')})" for v in vars_list)
        print(f"  {model_id.upper():6s}: {units_info}")

    # Debug: Show raw snowfall data summary
    print("\nSnowfall Data Summary (raw values in stored unit):")
    for model_id, forecast in forecasts.items():
        if "snowfall" in forecast.hourly_data:
            snow_data = forecast.hourly_data["snowfall"]
            snow_unit = forecast.hourly_units.get("snowfall", "?")
            non_none = [v for v in snow_data if v is not None]
            non_zero = [v for v in non_none if v > 0]
            total_raw = sum(non_none) if non_none else 0
            print(f"  {model_id.upper():6s}: unit={snow_unit}, total={total_raw:.4f}, "
                  f"non-zero hours={len(non_zero)}/{len(snow_data)}, "
                  f"max={max(non_none) if non_none else 0:.4f}")
        else:
            print(f"  {model_id.upper():6s}: NO SNOWFALL DATA")

    # Get max forecast hours across all models
    max_hours = max(f.hours_available for f in forecasts.values())
    
    # Generate 24-hour periods for the full forecast range
    periods: list[tuple[str, int, int]] = []
    for start_h in range(0, max_hours, 24):
        end_h = min(start_h + 24, max_hours)
        day_num = start_h // 24 + 1
        periods.append((f"Day {day_num}", start_h, end_h))

    # Compare snowfall predictions by day
    print(f"\n{'='*70}")
    print("SNOWFALL BY DAY (inches)")
    print(f"{'='*70}")
    print(f"{'Period':<12} ", end="")
    for model_id in forecasts.keys():
        print(f"{model_id.upper():>10s}", end="")
    print()
    print("-" * 70)

    for period_name, start_h, end_h in periods:
        print(f"{period_name:<12} ", end="")
        for forecast in forecasts.values():
            try:
                # Skip if this period is beyond this model's forecast
                if start_h >= forecast.hours_available:
                    print(f"{'--':>10s}", end="")
                    continue
                    
                actual_end = min(end_h, forecast.hours_available)
                total = forecast.get_snowfall_total(
                    unit="in",
                    start=timedelta(hours=start_h),
                    end=timedelta(hours=actual_end),
                )
                print(f"{format_snow(total.value):>10s}", end="")
            except KeyError:
                print(f"{'no data':>10s}", end="")
            except Exception as e:
                print(f"{'err':>10s}", end="")
        print()

    # Snowfall totals table
    print(f"\n{'='*70}")
    print("SNOWFALL TOTALS (inches)")
    print(f"{'='*70}")
    print(f"{'Model':<12} {'Hours':>8} {'Days':>6} {'Total':>10} {'Per Day':>10}")
    print("-" * 70)
    
    for model_id, forecast in forecasts.items():
        try:
            hours = forecast.hours_available
            days = hours / 24
            total = forecast.get_snowfall_total(unit="in")
            per_day = total.value / days if days > 0 else 0
            print(f"{model_id.upper():<12} {hours:>8} {days:>6.1f} {format_snow(total.value):>10s} {format_snow(per_day):>10s}")
        except KeyError:
            print(f"{model_id.upper():<12} {'no snowfall data':>36}")
        except Exception as e:
            print(f"{model_id.upper():<12} {'error':>36}")

    # Compare precipitation predictions by day
    print(f"\n{'='*70}")
    print("PRECIPITATION BY DAY (inches)")
    print(f"{'='*70}")
    print(f"{'Period':<12} ", end="")
    for model_id in forecasts.keys():
        print(f"{model_id.upper():>10s}", end="")
    print()
    print("-" * 70)

    for period_name, start_h, end_h in periods:
        print(f"{period_name:<12} ", end="")
        for forecast in forecasts.values():
            try:
                # Skip if this period is beyond this model's forecast
                if start_h >= forecast.hours_available:
                    print(f"{'--':>10s}", end="")
                    continue
                    
                actual_end = min(end_h, forecast.hours_available)
                total = forecast.get_precipitation_total(
                    unit="in",
                    start=timedelta(hours=start_h),
                    end=timedelta(hours=actual_end),
                )
                print(f"{format_snow(total.value):>10s}", end="")
            except KeyError:
                print(f"{'no data':>10s}", end="")
            except Exception as e:
                print(f"{'err':>10s}", end="")
        print()

    # Precipitation totals table
    print(f"\n{'='*70}")
    print("PRECIPITATION TOTALS (inches)")
    print(f"{'='*70}")
    print(f"{'Model':<12} {'Hours':>8} {'Days':>6} {'Total':>10} {'Per Day':>10}")
    print("-" * 70)
    
    for model_id, forecast in forecasts.items():
        try:
            hours = forecast.hours_available
            days = hours / 24
            total = forecast.get_precipitation_total(unit="in")
            per_day = total.value / days if days > 0 else 0
            print(f"{model_id.upper():<12} {hours:>8} {days:>6.1f} {format_snow(total.value):>10s} {format_snow(per_day):>10s}")
        except KeyError:
            print(f"{model_id.upper():<12} {'no precip data':>36}")
        except Exception as e:
            print(f"{model_id.upper():<12} {'error':>36}")

    # Compare temperature predictions (daily at noon UTC)
    print(f"\n{'='*70}")
    print("TEMPERATURE PREDICTIONS (°F at 12:00 UTC)")
    print(f"{'='*70}")
    print(f"{'Date':<12} ", end="")
    for model_id in forecasts.keys():
        print(f"{model_id.upper():>10s}", end="")
    print()
    print("-" * 70)

    # Show temperature at noon each day for the full forecast range
    reference_forecast = next(iter(forecasts.values()))
    
    # Find the first noon (12:00 UTC)
    first_noon_idx = None
    for i, t in enumerate(reference_forecast.times_utc):
        if t.hour == 12:
            first_noon_idx = i
            break
    
    if first_noon_idx is not None:
        # Show every 24 hours starting from first noon
        for i in range(first_noon_idx, max_hours, 24):
            if i >= len(reference_forecast.times_utc):
                break
            time = reference_forecast.times_utc[i]
            print(f"{time.strftime('%Y-%m-%d'):<12} ", end="")
            for forecast in forecasts.values():
                if i >= len(forecast.times_utc):
                    print(f"{'--':>10s}", end="")
                    continue
                try:
                    temp = forecast.get_temperature_2m(unit="F")
                    if temp.values[i] is not None:
                        print(f"{temp.values[i]:>10.1f}", end="")
                    else:
                        print(f"{'N/A':>10s}", end="")
                except Exception:
                    print(f"{'err':>10s}", end="")
            print()


def main() -> None:
    """Compare forecasts from different models."""
    print("Creating MeteoClient...")
    client = MeteoClient(cache_expire_after=1800)  # 30 min cache

    # Jackson Hole summit coordinates
    lat = 43.59724
    lon = -110.87115

    models = ["gfs", "ifs", "aifs"]
    forecasts: dict[str, Forecast] = {}

    # Fetch forecasts from each model
    for model_id in models:
        print(f"\nFetching {model_id.upper()} forecast...")
        try:
            forecast = client.get_forecast(
                lat=lat,
                lon=lon,
                model=model_id,
            )
            forecasts[model_id] = forecast
            print(f"  ✓ {forecast.hours_available} hours of data")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

    if not forecasts:
        print("No forecasts retrieved!")
        return

    # Print comparison
    print_model_comparison(forecasts)

    # Check equivalence between forecasts
    print(f"\n{'='*70}")
    print("FORECAST EQUIVALENCE")
    print(f"{'='*70}")

    model_ids = list(forecasts.keys())
    for i, model1 in enumerate(model_ids):
        for model2 in model_ids[i + 1 :]:
            is_eq = forecasts[model1].is_equivalent(forecasts[model2])
            status = "equivalent" if is_eq else "different"
            print(f"  {model1.upper()} vs {model2.upper()}: {status}")

    # Demonstrate serialization
    print(f"\n{'='*70}")
    print("SERIALIZATION DEMO")
    print(f"{'='*70}")

    # Serialize GFS forecast to JSON
    if "gfs" in forecasts:
        gfs_dict = forecasts["gfs"].to_dict()
        json_str = json.dumps(gfs_dict, indent=2, default=str)
        print(f"\nGFS forecast serialized to JSON ({len(json_str)} bytes)")
        print("Sample (first 500 chars):")
        print(json_str[:500] + "...")

        # Demonstrate deserialization
        restored = Forecast.from_dict(json.loads(json_str))
        print(f"\nRestored forecast: {restored.model_id}, {restored.hours_available} hours")

        # Verify equivalence
        if forecasts["gfs"].is_equivalent(restored):
            print("✓ Original and restored forecasts are equivalent")

    print(f"\n{'='*70}")
    print("Done!")


if __name__ == "__main__":
    main()

