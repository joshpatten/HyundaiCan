# Installation Guide
This guide is intended to show a basic outline on how to install everything needed onto a Raspberry Pi 4. YMMV

## Prerequisites
1. Your Raspberry Pi should be running Raspbian with a GUI.
2. Your Raspberry Pi needs to be connected to the Internet

## Dependencies
Run the following commands to install the necessary prerequisites:

    cd ~
    apt install -y git wget openjdk-8-jdk python3-pip audacity libpulse-dev libavcodec-dev libavformat-dev libswresample-dev
    git clone https://github.com/Shulyaka/pareceive.git
    cd pareceive
    make
    sudo cp -a pareceive /usr/local/bin
    cd ..
    git clone https://github.com/joshpatten/HyundaiCan.git
    sudo cp HyundaiCan/receive.py /usr/local/bin
    sudo cp HyundaiCan/receive.ini /usr/local/etc
    cd /usr/local/etc
    sudo wget https://raw.githubusercontent.com/commaai/opendbc/master/hyundai_2015_mcan.dbc

# Optional Programs
Room EQ Wizard is useful for tuning a DSP, but is not required. To install Room EQ Wizard run the following commands:

    cd ~
    wget https://www.roomeqwizard.com/installers/REW_linux_5_19.sh
    chmod +x REW_linux_5_19.sh
    sudo ./REW_linux_5_19.sh

# Settings
Add the following 2 lines to **/boot/config.txt** to enable CANbus and HiFiBerry

    dtparam=spi=on
    dtoverlay=mcp2515-can0,oscillator=12000000,interrupt=25,spimaxfrequency=2000000
    dtoverlay=hifiberry-digi

Create the file **/etc/asound.conf** with the following contents:

    pcm.!default {
            type hw
            card 0
    }
    
    ctl.!default {
            type hw
            card 0
    }

To disable the (horrid) onboard audio modify the file **/etc/modprobe.d/raspi-blacklist.conf** and add the following line:

    blacklist snd_bcm2835

Enable running on startup. Run the following commands:

    mkdir -p ~/.config/lxsession/LXDE-pi
    cp /etc/xdg/lxsession/LXDE-pi/autostart ~/.config/lxsession/LXDE-pi

Add the following line to the end of **~/.config/lxsession/LXDE-pi**

    @lxterminal -e /usr/bin/python3 /usr/local/bin/receive.py /usr/local/etc/receive.ini
    
# Final Configuration
Run the following command to get a list of all pulseaudio devices:

    python3 /usr/local/bin/receive.py listaudio

You'll get a device list similar to this:

    ==========OUTPUTS==========
    description='Built-in Audio Digital Stereo (IEC958)', index=0, mute=0, name='alsa_output.platform-soc_sound.iec958-stereo', channels=2, volumes=[67% 67%]
    ------------
    ===========================
    ==========INPUTS===========
    description='Monitor of Built-in Audio Digital Stereo (IEC958)', index=0, mute=0, name='alsa_output.platform-soc_sound.iec958-stereo.monitor', channels=2, volumes=[100% 100%]
    ------------
    description='Built-in Audio Digital Stereo (IEC958)', index=1, mute=0, name='alsa_input.platform-soc_sound.iec958-stereo', channels=2, volumes=[100% 100%]
    ------------
    ===========================
    ======DEFAULT OUTPUT=======
    alsa_output.platform-soc_sound.iec958-stereo
    ===========================

You'll now need to set the appropriate device numbers (listed as **index** in the device list) for input and output and modify the file **/usr/local/etc/receive.ini**

# Further notes
The configuration item **veh_off_wait** is the number of seconds the raspberry pi will wait before shutting down. When configuring your 12 delay relay you'll need to set the value to be about 15 seconds higher that the value in the ini file to give the raspberry pi enough time to fully shut down.
