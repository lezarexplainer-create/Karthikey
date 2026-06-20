#!/usr/bin/env bash
# Simple helper to run the Flask app in background on Termux / Linux
# Usage: ./run.sh start|stop|status
APP_NAME="karthikey_app"
PYTHON="python3"
PIDFILE="app.pid"
LOGFILE="app.log"

case "$1" in
  start)
    echo "Starting app..."
    nohup $PYTHON app.py > "$LOGFILE" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started with PID $(cat $PIDFILE)"
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      kill "$(cat $PIDFILE)" && rm -f "$PIDFILE"
      echo "Stopped"
    else
      echo "Not running (no $PIDFILE)"
    fi
    ;;
  status)
    if [ -f "$PIDFILE" ]; then
      echo "Running, PID $(cat $PIDFILE)"
    else
      echo "Not running"
    fi
    ;;
  *)
    echo "Usage: $0 start|stop|status"
    ;;
esac
