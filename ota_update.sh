#!/usr/bin/bash
# does the following:
# - Update LegionCenter Decky Plugin

if [ ! -f '/tmp/LegionCenter.tar.gz' ]; then
  echo "Failed to find downloaded plugin"
  exit -1
fi

DECKY_DIR="$HOME/homebrew/plugins"

if [ ! -d $DECKY_DIR ]; then
  echo "Failed to find DECKY_DIR at: "
  echo $DECKY_DIR
  exit -1
fi

rm -rf $DECKY_DIR/LegionCenter

tar -xzf /tmp/LegionCenter.tar.gz -C $DECKY_DIR

# install complete, remove files
rm  -rf /tmp/LegionCenter.tar.gz

systemctl restart plugin_loader.service
