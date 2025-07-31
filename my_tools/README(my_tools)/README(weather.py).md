# Weather Tool

This tool allows the AI to retrieve current weather conditions and forecasts for any specified location using the Open-Meteo API. It integrates with `geopy` to convert location names into geographical coordinates.

## Purpose

To provide the AI with real-time and forecasted weather information, enabling it to answer user queries about current weather, upcoming forecasts, or past weather conditions for any given location.

## How to Use (for AI)

The AI should call the `get_openmeteo_weather` function when a user asks about weather, temperature, precipitation, or forecasts for a specific place.

## Function Details

### `get_openmeteo_weather(location: str, units: str='fahrenheit', request_types: str='current', forecast_days: int=7, past_days: int=0) -> str`

Gets current conditions and/or forecasts for a location using the Open-Meteo API.

**Description:**
Uses `geopy` to find coordinates for the location name provided. Returns weather data including temperature, precipitation, wind, weather codes, and potentially hourly/daily forecasts based on `request_types`.

**Parameters:**

*   **`location`** (`str`): The city and state/country, e.g., "Paris France", "London UK", "Topeka KS USA". **Required.**
*   **`units`** (`str`, *optional*): Temperature units (`'celsius'` or `'fahrenheit'`). Defaults to `'fahrenheit'`.
    *   *Allowed values:* `celsius`, `fahrenheit`
*   **`request_types`** (`str`, *optional*): Comma-separated list of data types: `'current'`, `'hourly'`, `'daily'`. Defaults to `'current'`. Example: `"current,hourly"`.
    *   *Allowed values:* `current`, `hourly`, `daily`
*   **`forecast_days`** (`int`, *optional*): Number of forecast days (1-16). Defaults to `7`. Applies only if `'hourly'` or `'daily'` is requested.
*   **`past_days`** (`int`, *optional*): Number of past days to include (0-92). Defaults to `0`. Applies only if `'hourly'` or `'daily'` is requested.

**Returns:**
`str`: A JSON string containing the weather data or an error message if the request fails.