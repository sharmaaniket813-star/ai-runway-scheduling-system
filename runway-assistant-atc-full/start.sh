#!/usr/bin/env bash
# Runway Assistant ATC — One-click start (Mac/Linux)
# Requires: Python 3 only. No pip. No installs.

echo ""
echo "✈  RUNWAY ASSISTANT ATC — Birmingham Airport (EGBB/BHX)"
echo "──────────────────────────────────────────────────────"
echo ""

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Enter your Anthropic API key (or press Enter to skip AI features):"
  read -r key
  if [ -n "$key" ]; then
    export ANTHROPIC_API_KEY="$key"
  fi
fi

echo ""
echo "▶  Starting server → http://localhost:8000"
echo "   Open that URL in your browser."
echo "   Press Ctrl+C to stop."
echo ""

cd "$(dirname "$0")/backend"
python3 server.py
