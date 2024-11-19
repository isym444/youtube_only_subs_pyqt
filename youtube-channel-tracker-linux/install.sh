#!/bin/bash

# Create directories
mkdir -p ~/.local/bin
mkdir -p ~/.local/share/youtube-channel-tracker
mkdir -p ~/.local/share/applications

# Copy executable
cp youtube-channel-tracker ~/.local/share/youtube-channel-tracker/

# Create .desktop file
cat > ~/.local/share/applications/youtube-channel-tracker.desktop << EOL
[Desktop Entry]
Version=1.0
Name=YouTube Channel Tracker
Comment=Track YouTube channels and their latest videos
Exec=${HOME}/.local/share/youtube-channel-tracker/youtube-channel-tracker
Terminal=false
Type=Application
Categories=Utility;Network;
EOL

# Make files executable
chmod +x ~/.local/share/youtube-channel-tracker/youtube-channel-tracker
chmod +x ~/.local/share/applications/youtube-channel-tracker.desktop

echo "Installation complete! You should now see YouTube Channel Tracker in your applications menu."