 #!/bin/bash

pnpm run build
sudo rm -R $HOME/homebrew/plugins/LegionCenter/
sudo cp -R ../legion-center/ $HOME/homebrew/plugins/LegionCenter/
sudo systemctl restart plugin_loader.service
