#!/bin/sh

export APP_MODULE=server:cardanodatos
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8001}

exec uvicorn --reload --host $HOST --port $PORT $APP_MODULE