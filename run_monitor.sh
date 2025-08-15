#!/bin/bash
# This script starts the Autonomous Agentic Task-Flow System (AATFS) Event Monitor.

echo "Starting the AATFS Event Monitor..."
echo "The monitor will now watch the 'tasks/' directory for new tasks."
echo "Press Ctrl+C to stop the monitor."

# Run the Python script
# Using -u for unbuffered output so we can see logs in real-time.
python -u event_monitor.py
