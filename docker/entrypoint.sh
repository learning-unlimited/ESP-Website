#!/bin/sh
set -eu

APP_ROOT="/workspace/esp"
LOCAL_SETTINGS="${APP_ROOT}/esp/local_settings.py"
DOCKER_LOCAL_SETTINGS="/workspace/docker/local_settings.py"

if [ ! -f "${LOCAL_SETTINGS}" ]; then
  cp "${DOCKER_LOCAL_SETTINGS}" "${LOCAL_SETTINGS}"
fi

if [ ! -e "${APP_ROOT}/public/media/images" ]; then
  ln -s "${APP_ROOT}/public/media/default_images" "${APP_ROOT}/public/media/images"
fi

if [ ! -e "${APP_ROOT}/public/media/styles" ]; then
  ln -s "${APP_ROOT}/public/media/default_styles" "${APP_ROOT}/public/media/styles"
fi

exec "$@"
