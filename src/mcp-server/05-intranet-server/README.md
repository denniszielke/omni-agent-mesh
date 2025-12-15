# Weather MCP Server (04-weather-server)

This MCP server exposes simple tools for time-of-day–aware, **static** weather
information for six popular locations:

- Seattle (`America/Los_Angeles`)
- New York (`America/New_York`)
- London (`Europe/London`)
- Berlin (`Europe/Berlin`)
- Tokyo (`Asia/Tokyo`)
- Sydney (`Australia/Sydney`)

Weather text is deterministic and based only on the local time bucket
(morning, afternoon, evening, night) in each location.

## Tools

- `list_supported_locations()` – returns the list of supported city names.
- `get_weather_at_location(location: str)` – returns a static weather
  description for that city at its current local time.
- `get_weather_for_multiple_locations(locations: list[str])` – batch version
  returning an array of descriptions.

## Running locally

From this folder:

```bash
python run-mcp-weather.py
```

The SSE endpoint will be available on:

- `http://localhost:8002/sse`

Or build and run the Docker image:

```bash
docker build -t mcp-weather-server .
docker run --rm -p 8002:8002 mcp-weather-server
```
