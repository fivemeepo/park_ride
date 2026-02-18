#!/bin/bash

# Sync parking database from remote server
# Runs every 5 minutes via launchd

REMOTE_HOST="wangyf@10.251.232.45"
REMOTE_PATH="/home/wangyf/python/park_ride/parking_data.db"
LOCAL_PATH="/Users/bytedance/work/python/park_ride/parking_data.db"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting sync..."

# Use SSH config and try with explicit options
scp -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=30 \
    "${REMOTE_HOST}:${REMOTE_PATH}" "${LOCAL_PATH}"

SCP_EXIT=$?
if [ $SCP_EXIT -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Sync completed successfully"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Sync failed with exit code $SCP_EXIT"
    kinit
    exit 1
fi
