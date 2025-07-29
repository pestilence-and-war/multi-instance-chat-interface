# my_tools/weather.py

import openmeteo_requests
import requests_cache
from retry_requests import retry
import pandas as pd
import json
import time
import traceback
from datetime import datetime, timezone, timedelta

# --- Geocoding Setup ---
# Needs: pip install geopy
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    geolocator = Nominatim(user_agent="ai_tool_weather_checker/1.1") # Updated agent slightly
    GEOPY_AVAILABLE = True
except ImportError:
    print("Warning: geopy library not found. Location name lookup will not work. Install with: pip install geopy")
    GEOPY_AVAILABLE = False
    class GeocoderTimedOut(Exception): pass
    class GeocoderServiceError(Exception): pass

# --- API Client Setup ---
# Needs: pip install requests-cache retry-requests openmeteo-requests pandas
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# --- Fixed Variable Lists ---
DEFAULT_HOURLY_VARS = [
    "temperature_2m", "apparent_temperature", "precipitation_probability", "precipitation",
    "rain", "showers", "snowfall", "snow_depth", "weather_code", "visibility",
    "wind_gusts_10m", "wind_direction_10m", "wind_speed_10m", "cloud_cover",
    "relative_humidity_2m"
]
DEFAULT_DAILY_VARS = [
    "weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max",
    "apparent_temperature_min", "sunrise", "sunset", "precipitation_sum", "rain_sum",
    "showers_sum", "snowfall_sum", "precipitation_hours", "precipitation_probability_max",
    "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant", "uv_index_max"
]
DEFAULT_CURRENT_VARS = [
    "temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "precipitation",
    "rain", "showers", "snowfall", "weather_code", "cloud_cover", "wind_speed_10m",
    "wind_direction_10m", "wind_gusts_10m"
]


# --- Helper Functions (Implementations are the same as before) ---

def get_coordinates(location_name: str) -> tuple[float | None, float | None]:
    """Converts a location name to latitude and longitude using geopy."""
    if not GEOPY_AVAILABLE:
        print("Error: Geopy is not installed, cannot lookup coordinates by name.")
        return None, None
    try:
        location = geolocator.geocode(location_name, timeout=15)
        if location:
            print(f"Geocoded '{location_name}' to ({location.latitude:.4f}, {location.longitude:.4f})")
            return location.latitude, location.longitude
        else:
            print(f"Geocoding failed: Location '{location_name}' not found.")
            return None, None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding service error for '{location_name}': {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected geocoding error for '{location_name}': {e}")
        print(traceback.format_exc())
        return None, None

def decode_bytes(value):
    """Safely decodes bytes to utf-8 string, returns original value otherwise."""
    return value.decode('utf-8') if isinstance(value, bytes) else value

def format_timestamp(unix_ts: int | float, timezone_offset: int) -> str:
    """Formats a UNIX timestamp (seconds) into ISO 8601 format using the timezone offset."""
    try:
        tz = timezone(timedelta(seconds=timezone_offset))
        local_dt = datetime.fromtimestamp(unix_ts, tz)
        return local_dt.isoformat()
    except (ValueError, TypeError, OSError) as e:
        print(f"Error formatting timestamp {unix_ts} with offset {timezone_offset}: {e}")
        try:
            return datetime.fromtimestamp(unix_ts, timezone.utc).isoformat()
        except Exception:
            return str(unix_ts)

def get_wmo_description(code: int | float | None) -> str | None:
    """Returns a text description for a WMO weather code."""
    if code is None or pd.isna(code): return None
    try: code = int(code)
    except (ValueError, TypeError): return f"Invalid WMO Code ({code})"
    codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog or freezing fog", 48: "Fog or freezing fog",
        51: "Drizzle (Light)", 53: "Drizzle (Moderate)", 55: "Drizzle (Dense)",
        56: "Freezing Drizzle (Light)", 57: "Freezing Drizzle (Dense)",
        61: "Rain (Slight)", 63: "Rain (Moderate)", 65: "Rain (Heavy)",
        66: "Freezing Rain (Light)", 67: "Freezing Rain (Heavy)",
        71: "Snow fall (Slight)", 73: "Snow fall (Moderate)", 75: "Snow fall (Heavy)",
        77: "Snow grains",
        80: "Rain showers (Slight)", 81: "Rain showers (Moderate)", 82: "Rain showers (Violent)",
        85: "Snow showers (Slight)", 86: "Snow showers (Heavy)",
        95: "Thunderstorm (Slight or moderate)",
        96: "Thunderstorm with hail (Slight/Moderate)", 99: "Thunderstorm with hail (Heavy)"
    }
    return codes.get(code, f"WMO Code {code}")


# --- Main Tool Function ---

def get_openmeteo_weather(
    location: str,
    units: str = "fahrenheit",
    request_types: str = "current",
    forecast_days: int = 7,
    past_days: int = 0
) -> str:
    """Gets current conditions and/or forecasts for a location using the Open-Meteo API.

    Uses geopy to find coordinates for the location name provided. Returns weather data
    including temperature, precipitation, wind, weather codes, and potentially hourly/daily
    forecasts based on request_types.

    @param location (string): The city and state/country, e.g., "Paris France", "London UK", "Topeka KS USA". This is required.
    @param units (string): Temperature units ('celsius' or 'fahrenheit'). Optional. Defaults to 'fahrenheit'. enum:celsius,fahrenheit
    @param request_types (string): Comma-separated list of data types: 'current', 'hourly', 'daily'. Optional. Defaults to 'current'. Example: "current,hourly". enum:current,hourly,daily
    @param forecast_days (integer): Number of forecast days (1-16). Optional. Default: 7. Applies only if 'hourly' or 'daily' is requested.
    @param past_days (integer): Number of past days to include (0-92). Optional. Default: 0. Applies only if 'hourly' or 'daily' is requested.

    Returns:
        string: A JSON string containing the weather data or an error message.
    """
    print(f"--- Tool: get_openmeteo_weather called ---")
    print(f"Params: location='{location}', units='{units}', request_types='{request_types}', "
          f"forecast_days={forecast_days}, past_days={past_days}")

    # --- Geocode Location Name ---
    if not location or not isinstance(location, str):
        return json.dumps({
             "error": "Invalid location name provided. Please provide a city and state/country.",
             "status": "error_invalid_location_input"
        })

    latitude, longitude = get_coordinates(location)

    if latitude is None or longitude is None:
        err_msg = f"Could not find coordinates for location: '{location}'."
        if not GEOPY_AVAILABLE:
            err_msg += " Geocoding library (geopy) is not installed."
        else:
             err_msg += " Please try a more specific location (e.g., 'City, State/Country') or check the spelling."
        return json.dumps({"error": err_msg, "status": "error_geocoding" if GEOPY_AVAILABLE else "error_geocoding_setup"})

    # --- Prepare API Request ---
    forecast_days = 7 if forecast_days is None else max(1, min(int(forecast_days), 16))
    past_days = 0 if past_days is None else max(0, min(int(past_days), 92))
    units = units.lower() if units and isinstance(units, str) else "fahrenheit"
    if units not in ["celsius", "fahrenheit"]:
        print(f"Warning: Invalid units '{units}' provided. Defaulting to fahrenheit.")
        units = "fahrenheit"

    req_types_set = {rt.strip().lower() for rt in request_types.split(',') if rt.strip()} if request_types else {'current'}
    if not req_types_set.issubset({'current', 'hourly', 'daily'}):
         print(f"Warning: Invalid request_types found. Using 'current'. Input: '{request_types}'")
         req_types_set = {'current'}

    request_current = 'current' in req_types_set
    request_hourly = 'hourly' in req_types_set
    request_daily = 'daily' in req_types_set

    params = {
        "latitude": latitude, "longitude": longitude,
        "temperature_unit": units, "wind_speed_unit": "mph",
        "precipitation_unit": "inch", "timezone": "auto", "models": "best_match"
    }

    if request_current: params["current"] = DEFAULT_CURRENT_VARS
    if request_hourly: params["hourly"] = DEFAULT_HOURLY_VARS
    if request_daily: params["daily"] = DEFAULT_DAILY_VARS
    if request_hourly or request_daily:
        params["forecast_days"] = forecast_days
        if past_days > 0: params["past_days"] = past_days

    print(f"Constructed API Params for ({latitude:.4f}, {longitude:.4f}): {params}")

    # --- Call API and Process Response ---
    try:
        responses = openmeteo.weather_api("https://api.open-meteo.com/v1/forecast", params=params)
        response = responses[0]

        latitude_found = response.Latitude()
        longitude_found = response.Longitude()
        timezone_api = decode_bytes(response.Timezone())
        timezone_abbr_api = decode_bytes(response.TimezoneAbbreviation())
        utc_offset_seconds = response.UtcOffsetSeconds() if hasattr(response, 'UtcOffsetSeconds') and response.UtcOffsetSeconds() is not None else 0
        elevation = response.Elevation() if hasattr(response, 'Elevation') else None

        print(f"API Response Coords: {latitude_found:.4f}°N {longitude_found:.4f}°E, Elev: {elevation}m")
        print(f"API Response Timezone: {timezone_api} ({timezone_abbr_api}), Offset: {utc_offset_seconds}s")

        result_data = {
            "location_input": location,
            "location_found": f"{latitude_found:.4f}N, {longitude_found:.4f}E",
            "elevation_m": elevation, "timezone": timezone_api,
            "timezone_abbreviation": timezone_abbr_api, "utc_offset_seconds": utc_offset_seconds,
            "units": {
                "temperature": "°F" if units == "fahrenheit" else "°C",
                "wind_speed": params["wind_speed_unit"], "precipitation": params["precipitation_unit"],
                "humidity": "%", "visibility": "meters", "pressure": "hPa",
                "cloud_cover": "%", "snow_depth": params["precipitation_unit"],
                "uv_index": "UV Index"
            },
            "status": "success",
            "data_requested": {
                 "current": request_current, "hourly": request_hourly, "daily": request_daily,
                 "forecast_days": params.get("forecast_days"), "past_days": params.get("past_days")
            }
        }

        temp_unit_char = result_data["units"]["temperature"]
        precip_unit = result_data["units"]["precipitation"]
        wind_unit = result_data["units"]["wind_speed"]

        # --- Process Current Data ---
        if request_current and hasattr(response, 'Current') and callable(response.Current):
            current = response.Current()
            if current:
                current_data = {"time": format_timestamp(current.Time(), utc_offset_seconds)}
                values = {}
                for i in range(min(len(DEFAULT_CURRENT_VARS), current.VariablesLength())):
                    var_name = DEFAULT_CURRENT_VARS[i]
                    value = current.Variables(i).Value()
                    if pd.isna(value): value = None
                    values[var_name] = value

                processed_current = {}
                for name, value in values.items():
                    if value is None: continue
                    unit, description = None, None
                    if "temperature" in name: unit = temp_unit_char
                    elif "humidity" in name: unit = "%"
                    elif name in ["precipitation", "rain", "showers", "snowfall"]: unit = precip_unit
                    elif name == "cloud_cover": unit = "%"
                    elif "wind_speed" in name or "wind_gusts" in name: unit = wind_unit
                    elif "wind_direction" in name: unit = "degrees"
                    if name == "weather_code": description = get_wmo_description(value)
                    elif name == "is_day": description = "Daytime" if value == 1 else "Nighttime"

                    entry = {"value": round(value, 2) if isinstance(value, float) else value}
                    if unit: entry["unit"] = unit
                    if description: entry["description"] = description
                    processed_current[name] = entry

                if processed_current: current_data["data"] = processed_current
                else: current_data["message"] = "No current data values available."
                result_data["current_conditions"] = current_data
            else: result_data["current_conditions"] = {"message": "Current data block received but was empty."}
        elif request_current: result_data["current_conditions"] = {"message": "Current data requested but not found in API response."}

        # --- Process Hourly Data ---
        # (Implementation remains the same index-based parsing as previous correct version)
        if request_hourly and hasattr(response, 'Hourly') and callable(response.Hourly):
            hourly = response.Hourly()
            if hourly and hourly.VariablesLength() > 0:
                try:
                    hourly_times_raw = pd.to_datetime(hourly.Time(), unit="s", utc=True)
                    hourly_times_end_raw = pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True)
                    interval = pd.Timedelta(seconds=hourly.Interval())
                    hourly_times = pd.date_range(start=hourly_times_raw, end=hourly_times_end_raw, freq=interval, inclusive="left")
                    hourly_times_local_iso = [format_timestamp(ts.timestamp(), utc_offset_seconds) for ts in hourly_times]
                    time_range_valid = True
                except Exception as e:
                     print(f"Error generating hourly time range: {e}")
                     hourly_times_local_iso = []
                     time_range_valid = False
                     result_data["hourly_forecast"] = {"message": f"Error processing hourly time data: {e}"}

                if time_range_valid:
                    hourly_data_arrays = {}
                    num_vars_in_response = hourly.VariablesLength()
                    for i, name in enumerate(DEFAULT_HOURLY_VARS):
                        if i < num_vars_in_response:
                           try: hourly_data_arrays[name] = hourly.Variables(i).ValuesAsNumpy()
                           except Exception as e:
                                print(f"Error extracting hourly numpy array for '{name}' (index {i}): {e}")
                                hourly_data_arrays[name] = [None] * len(hourly_times)
                        else:
                            print(f"Warn: Hourly var '{name}' (idx {i}) missing. Padding.")
                            hourly_data_arrays[name] = [None] * len(hourly_times)

                    hourly_forecast_list = []
                    for t_idx, local_iso_time in enumerate(hourly_times_local_iso):
                        step_data = {"time": local_iso_time}
                        processed_hourly_step = {}
                        for name, arr in hourly_data_arrays.items():
                            value = arr[t_idx] if t_idx < len(arr) else None
                            if pd.isna(value): value = None
                            if value is None: continue
                            unit, description = None, None
                            if "temperature" in name: unit = temp_unit_char
                            elif "humidity" in name: unit = "%"
                            elif name in ["precipitation", "rain", "showers", "snowfall", "snow_depth"]: unit = precip_unit
                            elif "probability" in name: unit = "%"
                            elif name == "cloud_cover": unit = "%"
                            elif "wind_speed" in name or "wind_gusts" in name: unit = wind_unit
                            elif "wind_direction" in name: unit = "degrees"
                            elif name == "visibility": unit = "meters"
                            if name == "weather_code": description = get_wmo_description(value)

                            entry = {"value": round(value, 2) if isinstance(value, float) else value}
                            if unit: entry["unit"] = unit
                            if description: entry["description"] = description
                            processed_hourly_step[name] = entry
                        if processed_hourly_step:
                             step_data["data"] = processed_hourly_step
                             hourly_forecast_list.append(step_data)
                    if hourly_forecast_list: result_data["hourly_forecast"] = hourly_forecast_list
                    elif time_range_valid: result_data["hourly_forecast"] = {"message": "Hourly data block received but contained no valid data points."}

            else: result_data["hourly_forecast"] = {"message": "Hourly data block received but was empty."}
        elif request_hourly: result_data["hourly_forecast"] = {"message": "Hourly data requested but not found in API response."}


        # --- Process Daily Data ---
        # (Implementation remains the same index-based parsing as previous correct version)
        if request_daily and hasattr(response, 'Daily') and callable(response.Daily):
            daily = response.Daily()
            if daily and daily.VariablesLength() > 0:
                try:
                    daily_times_raw = pd.to_datetime(daily.Time(), unit="s", utc=True)
                    daily_times_end_raw = pd.to_datetime(daily.TimeEnd(), unit="s", utc=True)
                    interval = pd.Timedelta(seconds=daily.Interval())
                    daily_times = pd.date_range(start=daily_times_raw, end=daily_times_end_raw, freq=interval, inclusive="left")
                    daily_dates_local = [format_timestamp(ts.timestamp(), utc_offset_seconds).split('T')[0] for ts in daily_times]
                    time_range_valid = True
                except Exception as e:
                     print(f"Error generating daily time range: {e}")
                     daily_dates_local = []
                     time_range_valid = False
                     result_data["daily_forecast"] = {"message": f"Error processing daily time data: {e}"}

                if time_range_valid:
                    daily_data_arrays = {}
                    num_vars_in_response = daily.VariablesLength()
                    for i, name in enumerate(DEFAULT_DAILY_VARS):
                        if i < num_vars_in_response:
                            try:
                                if name in ["sunrise", "sunset"]: daily_data_arrays[name] = daily.Variables(i).ValuesInt64AsNumpy()
                                else: daily_data_arrays[name] = daily.Variables(i).ValuesAsNumpy()
                            except Exception as e:
                                print(f"Error extracting daily numpy array for '{name}' (index {i}): {e}")
                                daily_data_arrays[name] = [None] * len(daily_times)
                        else:
                             print(f"Warn: Daily var '{name}' (idx {i}) missing. Padding.")
                             daily_data_arrays[name] = [None] * len(daily_times)

                    daily_forecast_list = []
                    for d_idx, local_date in enumerate(daily_dates_local):
                        step_data = {"date": local_date}
                        processed_daily_step = {}
                        for name, arr in daily_data_arrays.items():
                            value = arr[d_idx] if d_idx < len(arr) else None
                            if pd.isna(value): value = None
                            if value is None: continue
                            unit, description = None, None
                            if "temperature" in name: unit = temp_unit_char
                            elif "_sum" in name or "precipitation_hours" in name: unit = precip_unit
                            elif "_max" in name and ("wind_speed" in name or "wind_gusts" in name): unit = wind_unit
                            elif "_max" in name and "probability" in name: unit = "%"
                            elif "_dominant" in name and "wind_direction" in name: unit = "degrees"
                            elif name == "uv_index_max":
                                 unit = "UV Index"
                                 value = round(value, 1) if isinstance(value, float) else value
                            elif name in ["sunrise", "sunset"]:
                                 try: value = format_timestamp(value, utc_offset_seconds)
                                 except Exception as ts_e:
                                     print(f"Error formatting sunrise/sunset timestamp {value}: {ts_e}")
                                     value = None
                            if name == "weather_code": description = get_wmo_description(value)

                            if value is not None:
                                entry = {"value": round(value, 2) if isinstance(value, float) and name != "uv_index_max" else value}
                                if unit: entry["unit"] = unit
                                if description: entry["description"] = description
                                processed_daily_step[name] = entry
                        if processed_daily_step:
                            step_data["data"] = processed_daily_step
                            daily_forecast_list.append(step_data)
                    if daily_forecast_list: result_data["daily_forecast"] = daily_forecast_list
                    elif time_range_valid: result_data["daily_forecast"] = {"message": "Daily data block received but contained no valid data points."}

            else: result_data["daily_forecast"] = {"message": "Daily data block received but was empty."}
        elif request_daily: result_data["daily_forecast"] = {"message": "Daily data requested but not found in API response."}

        # --- Final Status Check ---
        got_current = isinstance(result_data.get("current_conditions", {}).get("data"), dict) and result_data["current_conditions"]["data"]
        got_hourly = isinstance(result_data.get("hourly_forecast"), list) and result_data["hourly_forecast"]
        got_daily = isinstance(result_data.get("daily_forecast"), list) and result_data["daily_forecast"]
        if not (got_current or got_hourly or got_daily) and result_data.get("status") == "success":
             result_data["status"] = "success_no_data_retrieved"
             result_data["message"] = "API call succeeded but failed to retrieve any valid weather data."
             result_data.pop("current_conditions", None); result_data.pop("hourly_forecast", None); result_data.pop("daily_forecast", None)

        print(f"--- Tool Success: Returning weather data for '{location}' ---")
        return json.dumps(result_data, separators=(',', ':'), default=str)

    except openmeteo_requests.ApiError as e:
        print(f"Open-Meteo API Error: {e}")
        loc_info = f" for location '{location}' ({latitude:.4f}, {longitude:.4f})" if 'latitude' in locals() else ""
        return json.dumps({"error": f"Open-Meteo API Error{loc_info}: {str(e)}", "status": "error_api"})
    except Exception as e:
        print(f"Unexpected error in get_openmeteo_weather: {e}")
        print(traceback.format_exc())
        loc_info = f" for location '{location}'" if 'location' in locals() else ""
        return json.dumps({"error": f"An unexpected error occurred processing weather data{loc_info}: {str(e)}", "status": "error_unexpected"})


# --- Example Test block ---
if __name__ == '__main__':
    print("--- Testing get_openmeteo_weather Tool ---")
    if not GEOPY_AVAILABLE:
         print("\n !!! Cannot run tests: geopy library is required. Install with: pip install geopy !!!\n")
         exit()

    test_cases = [ # Same test cases as before
        {"location": "London, UK", "units": "celsius", "request_types": "current"},
        {"location": "Tokyo, Japan", "units": "celsius", "request_types": "current,hourly", "forecast_days": 1},
        {"location": "New York, NY USA", "units": "fahrenheit", "request_types": "daily", "forecast_days": 3},
        {"location": "Berlin, Germany", "request_types": "current,hourly,daily", "forecast_days": 2, "past_days": 1},
        {"location": "Sydney, Australia", "request_types": "hourly", "forecast_days": 1},
        {"location": "Oslo, Norway", "request_types": "current,daily"},
        {"location": "Cairo, Egypt", "request_types": "daily", "forecast_days": 5},
        {"location": "Paris, France", "request_types": "current,hourly,daily", "past_days":3, "forecast_days":1},
        {"location": "NotARealPlace123xyz", "request_types": "current"}, # Geocoding failure
        {"location": ""}, # Invalid input
        {"location": "Zagreb, Croatia", "units":"celsius", "request_types":"current,daily", "past_days":1, "forecast_days":2},
    ]
    # ... (rest of the test execution logic remains the same) ...
    for i, case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Requesting: {case}")
        start_time = time.time()
        result_json = get_openmeteo_weather(**case)
        end_time = time.time()
        print(f"Execution Time: {end_time - start_time:.2f} seconds")
        print("Raw Result:", result_json[:700] + "..." if len(result_json) > 700 else result_json)
        try:
            parsed_result = json.loads(result_json)
            print("Formatted Result Status:", parsed_result.get("status"))
            print("Formatted Result (Top Level Keys):", list(parsed_result.keys()))
            if "error" in parsed_result: print("  Error Message:", parsed_result["error"])
            # ... (optional detail printing logic remains the same) ...
        except json.JSONDecodeError as e: print(f"Error decoding result JSON: {e}")
        except Exception as e: print(f"Error processing result structure: {e}"); print(traceback.format_exc())
        if i < len(test_cases) - 1: time.sleep(1.1)
    print("\n--- Testing Complete ---")