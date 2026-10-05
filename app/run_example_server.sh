#!/usr/bin/env bash

# MaiPlan server configuration.
# Replace the five CHANGE_ME values before starting the API.
# Make the script executable with: chmod +x run_example_server.sh

sudo tailscale serve --bg --https=CHANGE_ME_HTTPS_PORT CHANGE_ME_PORT
ENV=CHANGE_ME_ENVIRONMENT_NAME uvicorn main:app --host CHANGE_ME_HOST --port CHANGE_ME_PORT --reload