#!/usr/bin/env python3
"""Quick start example demonstrating basic usage of the weather package.

This example shows how to:
- Create a MeteoClient
- Fetch a forecast for a mountain location
- Access hourly data with unit conversion
- Get snow totals for different time periods
"""

from datetime import timedelta

from weather import MeteoClient


def main() -> None:
    """Demonstrate basic weather package usage."""
    # Create client with default settings (caching + retries enabled)
    print("Creating MeteoClient...")
    client = MeteoClient()

    # Jackson Hole, WY - a famous ski resort
    lat = 43.4799
    lon = -110.7624
    summit_elevation = 3185  # meters (Rendezvous Mountain summit)

    print(f"\nFetching forecast for Jackson Hole ({lat}, {lon})...")
    print(f"Summit elevation: {summit_elevation}m")

    # Get forecast using GFS model with elevation override
    forecast = client.get_forecast(
        lat=lat,
        lon=lon,
        model="gfs",
        elevation=summit_elevation,
    )

    # Print metadata
    print(f"\n{'='*60}")
    print("FORECAST METADATA")
    print(f"{'='*60}")
    print(f"Model: {forecast.model_id.upper()}")
    print(f"Model run: {forecast.model_run_utc}")
    print(f"Forecast hours: {forecast.hours_available}")
    print(f"Requested location: ({forecast.lat}, {forecast.lon})")
    print(f"API grid point: ({forecast.api_lat}, {forecast.api_lon})")
    print(f"Elevation: {forecast.elevation_m}m")

    # Get temperature in Fahrenheit (for US users)
    temps_f = forecast.get_temperature_2m(unit="F")
    print(f"\n{'='*60}")
    print("TEMPERATURE (next 12 hours)")
    print(f"{'='*60}")
    for i in range(min(12, len(forecast.times_utc))):
        time = forecast.times_utc[i]
        temp = temps_f.values[i]
        print(f"  {time.strftime('%Y-%m-%d %H:%M')} UTC: {temp:.1f}°F")

    # Get wind speed in mph
    winds_mph = forecast.get_wind_speed_10m(unit="mph")
    gusts_mph = forecast.get_wind_gusts_10m(unit="mph")
    print(f"\n{'='*60}")
    print("WIND (next 12 hours)")
    print(f"{'='*60}")
    for i in range(min(12, len(forecast.times_utc))):
        time = forecast.times_utc[i]
        wind = winds_mph.values[i]
        gust = gusts_mph.values[i]
        print(f"  {time.strftime('%Y-%m-%d %H:%M')} UTC: {wind:.0f} mph (gusts {gust:.0f} mph)")

    # Get freezing level in feet
    freeze_ft = forecast.get_freezing_level_height(unit="ft")
    print(f"\n{'='*60}")
    print("FREEZING LEVEL (next 12 hours)")
    print(f"{'='*60}")
    for i in range(min(12, len(forecast.times_utc))):
        time = forecast.times_utc[i]
        level = freeze_ft.values[i]
        if level is not None:
            print(f"  {time.strftime('%Y-%m-%d %H:%M')} UTC: {level:.0f} ft")

    # Get snow totals for different periods
    print(f"\n{'='*60}")
    print("SNOWFALL TOTALS")
    print(f"{'='*60}")

    # Next 24 hours
    snow_24h = forecast.get_snowfall_total(
        unit="in",
        start=timedelta(hours=0),
        end=timedelta(hours=24),
    )
    print(f"  Next 24 hours: {snow_24h.value:.1f} inches")

    # Next 48 hours
    snow_48h = forecast.get_snowfall_total(
        unit="in",
        start=timedelta(hours=0),
        end=timedelta(hours=48),
    )
    print(f"  Next 48 hours: {snow_48h.value:.1f} inches")

    # Next 72 hours
    snow_72h = forecast.get_snowfall_total(
        unit="in",
        start=timedelta(hours=0),
        end=timedelta(hours=72),
    )
    print(f"  Next 72 hours: {snow_72h.value:.1f} inches")

    # Full forecast period
    snow_total = forecast.get_snowfall_total(unit="in")
    print(f"  Full forecast ({forecast.hours_available}h): {snow_total.value:.1f} inches")

    # Show accumulated snowfall over time
    print(f"\n{'='*60}")
    print("ACCUMULATED SNOWFALL (inches)")
    print(f"{'='*60}")
    snow_accum = forecast.get_snowfall_accumulated(unit="in")
    # Show every 6 hours
    for i in range(0, min(len(forecast.times_utc), 96), 6):
        time = forecast.times_utc[i]
        accum = snow_accum.values[i]
        print(f"  {time.strftime('%Y-%m-%d %H:%M')} UTC: {accum:.1f} inches")

    print(f"\n{'='*60}")
    print("Done!")


if __name__ == "__main__":
    main()

