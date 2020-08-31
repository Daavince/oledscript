# Oledscript
This is a project that displays a status dashboard on an oled display connected to GPIO pins on a linux system.
It is tested with Raspberry Pi 4 and 3B+. The status dashboard has a fixed part with Temp, CPU and mem usage, boot disk % used, ip addres,
throttle status, undervoltage status and a configurable part (through *.conf file) which allows to setup 
1) internet connectivity monitoring based on a list of servers to ping
2) status check of SystemCtl or Service running on the system
3) mounted drive connectivity and used disk %

![Example OLED running on Raspberry](https://github.com/Daavince/oledscript/blob/master/img/A0B4DA71-DE2C-4019-8153-48288BDFE438.jpeg)

The purpose is to be able to monitor a headless raspberry without the need to SSH into the device too often to check on various things
