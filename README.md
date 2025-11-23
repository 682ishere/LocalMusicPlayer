# Local Music Player

A Python-based open-source music player capable of downloading individual tracks or playlists from YouTube and managing local playlists.

<p float="left">
  <img src="localMusicPlayer/Images/image1.png" width="45%" />
  <img src="localMusicPlayer/Images/image2.png" width="45%" /> 
</p>


# Installation
## Any OS
### Download Requirements
    ```bash
    pip install -r requirements.txt
    ```

### For "externally-managed-environment" Error
    ```bash
    pip install -r requirements.txt --break-system-packages
    ```

## Run
    ```bash
    python localmusic.py
    ```

## How To Use
1. **Upon launching, select a Main Directory where you want to store your music.**

2. **Create subfolders manually inside this Main Directory.**

3. **The application will recognize these subfolders as Playlists.**
   
# Linux Native Integration (.desktop)
## Open Terminal:
    ```bash
    nano ~/.local/share/applications/localmusicplayer.desktop
    ```
## Paste And Edit This:
    ```bash
     [Desktop Entry]
     Version=1.0
     Type=Application
     Name=A Music Player
     # CHANGE THIS PATH to where your "localmusic.py" is located
     Exec=/usr/bin/python3 /home/YOUR_NAME/localmusic.py
     Icon=/home/YOUR_NAME/logo.png
     Categories=Audio;Music;Player;
     Terminal=false
     StartupNotify=true
    ```
### Update the desktop database:
    ```bash
    update-desktop-database ~/.local/share/applications/
    ```
