import time
import subprocess
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.ssd1351 as ssd1351  # pylint: disable=unused-import
import configparser

# Read file with user defined settings
config = configparser.ConfigParser()
config.read(['/home/pi/oledscript/oledstatuspi.conf', '/home/pi/oledscript/oledstatuspi.local.conf'])
# Get name of the system from user settings
SysName = config['general']['SysName']
# Get rotation orientation of display
DisplayRotation = int(config['general']['DisplayRotation'])
# Get display font
FontLocation = config['general']['FontLocation']
FontSize = int(config['general']['FontSize'])

# Get performance variables from user settings (high refresh rates impact CPU usage significantly)
RefreshTime = float(config['performance']['RefreshTime'])
LoopsBeforeRefreshMedium = int(config['performance']['LoopsBeforeRefreshMedium'])
LoopsBeforeRefreshLow = int(config['performance']['LoopsBeforeRefreshLow'])
# Get configuration of status items
LINE01 = config['statusselection']['LINE01'].split(",")
LINE02 = config['statusselection']['LINE02'].split(",")
LINE03 = config['statusselection']['LINE03'].split(",")
LINE04 = config['statusselection']['LINE04'].split(",")
LINE05 = config['statusselection']['LINE05'].split(",")
LINE06 = config['statusselection']['LINE06'].split(",")
LINE07 = config['statusselection']['LINE07'].split(",")
LINE08 = config['statusselection']['LINE08'].split(",")
LINE09 = config['statusselection']['LINE09'].split(",")
LINE10 = config['statusselection']['LINE10'].split(",")
LINES = [LINE01, LINE02, LINE03, LINE04, LINE05, LINE06, LINE07, LINE08, LINE09, LINE10]

# Configuration for CS and DC pins (these are PiTFT defaults):
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D24)
reset_pin = digitalio.DigitalInOut(board.D25)
# Config for display baudrate (default max is 24mhz):
BAUDRATE = 24000000
# Setup SPI bus using hardware SPI:
spi = board.SPI()
disp = ssd1351.SSD1351(                         # 1.5" SSD1351
    spi,
    rotation=DisplayRotation,  # 2.2", 2.4", 2.8", 3.2" ILI9341
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
)
# pylint: enable=line-too-long
# Create blank image for drawing.
# Make sure to create image with mode 'RGB' for full color.
if disp.rotation % 180 == 90:
    height = disp.width  # we swap height/width to rotate it to landscape!
    width = disp.height
else:
    width = disp.width  # we swap height/width to rotate it to landscape!
    height = disp.height
image = Image.new("RGB", (width, height))
# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)
# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline="#000000", fill="#000000")
disp.image(image)

# Load a TTF font.
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
#font1 = ImageFont.truetype("/usr/share/fonts/truetype/VCR_OSD_MONO_1.001.ttf", 11)
font1 = ImageFont.truetype(FontLocation, FontSize)
# First define some constants to allow easy positioning of text.
padding = -2
indent = 1
spacing = font1.getsize("Test")[1]
x = 0
y = 0

# Prepare configuration for evaluation and drawing (expand the split lines)
numinserts = 0
for j in range(len(LINES)):
     if len(LINES[j+numinserts]) > 4:
          if LINES[j+numinserts][4] == "SPLIT":
               LINES.insert(j+1+numinserts, LINES[j+numinserts][5:])
               LINES[j+numinserts] = LINES[j+numinserts][0:4]
               LINES[j+numinserts] = ['S', 0, 0] + LINES[j+numinserts]
               LINES[j+1+numinserts] = ['S', -spacing, 66] + LINES[j+1+numinserts]
               numinserts += 1
          else:
               LINES[j+numinserts] = ['F', 0, 0] + LINES[j+numinserts]
     elif len(LINES[j+numinserts]) > 2:
          if LINES[j+numinserts][1] == "SPLIT":
               LINES.insert(j+1+numinserts, LINES[j+numinserts][2:])
               LINES[j+numinserts] = LINES[j+numinserts][0:1]
               LINES[j+numinserts] = ['S', 0, 0] + LINES[j+numinserts]
               LINES[j+1+numinserts] = ['S', -spacing, 66] + LINES[j+1+numinserts]
               numinserts += 1
          else:
               LINES[j+numinserts] = ['F', 0, 0] + LINES[j+numinserts]
     else:
          LINES[j+numinserts] = ['F', 0, 0] + LINES[j+numinserts]

#for j in range(len(LINES)):
#     print (LINES[j])

# Set a initial value for a few variables
SysUpLastPowerIssue = 0
ConnectionLastDown = 0
TimeDenom = 1
MediumRefreshCount = 1 #LoopsBeforeRefreshMedium
LowRefreshCount = 1 #LoopsBeforeRefreshLow
FirstRun = True
OddRun = True

# First, some checks are only one-off and need not to be checked repeatedly
# OS version (one-off as cannot change without reboot)
cmd = "cat /etc/os-release | grep CODENAME | sed -e 's/VERSION_CODENAME=//' -e 's/[a-z]/\\U&/g' | tr -d '\\n'"
SysOSversion = subprocess.check_output(cmd, shell=True).decode("utf-8")
# Number of cpu cores
cmd = "nproc"
NrCores = subprocess.check_output(cmd, shell=True).decode("utf-8")

def ServiceStatus(Service, Type):
     if Type == "SystemCtl":
          Before = "systemctl status"
          After = ""
     else:
          Before = "service"
          After = " status"
     #cmd1 = "{} {}{} | head -n 6 | grep \"active (running)\" -c | sed 's/1/\'OKx\'/; s/0/\'NOx\'/'".format(Before, Service, After)
     cmd1 = "{} {}{} | head -n 6 | sed -n -e 's/^.*Active: //p' | sed 's/failed/ERx/;s/inactive/NOx/;s/active (running)/OKx/;s/active (exited)/ERx/'".format(Before, Service, After)
     #print (cmd1)
     try:
          status = subprocess.check_output(cmd1, shell=True).decode("utf-8")[0:3]
     except subprocess.CalledProcessError as e:
          status = "--x"
     if len(status) == 0:
          status = "??x"
     #print (status)
     if status[0:2] == "OK":
          #cmd0 = "{} {}{} | grep 'Main PID' -m 1".format(Before, Service, After)
          #out = subprocess.check_output(cmd0, shell=True).decode("utf-8")
          #print ("start")
          #print (out)
          #print ("stop")
          cmd2a = "{} {}{} | grep 'Main PID' -m 1 | awk {}".format(Before, Service, After, "'{printf \"%0.f\", $3}'")
          cmd2b = "{} {}{} | grep -E '(├─|└─)' -m 1 | sed 's/─/ /' | awk {}".format(Before, Service, After, "'{printf \"%0.f\", $2}'")
          process = subprocess.check_output(cmd2a, shell=True).decode("utf-8")
          if len(process) < 1: # in this case, Main PID does not exist and running process needs to be identified from tree with cmd2b
               process = subprocess.check_output(cmd2b, shell=True).decode("utf-8")
          #print (len(process))
          cmd3 = "ps -p {} -o etimes= | awk {}".format(process, "'{printf \"%0.f\\n\", $1}'")
          uptimeS = subprocess.check_output(cmd3, shell=True).decode("utf-8")
          try:
               uptime = str(round(int(float(uptimeS)) / TimeDenom))
          except:
               uptime = ""
               print ("start:")
               print (cmd2a)
               print (cmd2b)
               print (process)
               print (cmd3)
               print (uptimeS)
     else:
          uptime = ""
     return status, uptime

def DriveStatus(Drive):
     cmd1 = "df | grep {} -c | sed 's/[1-9]/'OKx'/; s/[1-9][1-9]/'OKx'/; s/0/'NOx'/'".format(Drive)
     drivestatus = subprocess.check_output(cmd1, shell=True).decode("utf-8")
     if drivestatus[0:2] == "OK":
          cmd2 = "df | grep {} | awk {}".format(Drive, "'{sumU += $3; sumA +=$4} END {printf \"%.1f, %.0f\" , (sumU + sumA)/1024/1024/1024 , sumU/(sumU + sumA)*100}'")
          #print (cmd2)
          driveoutput = subprocess.check_output(cmd2, shell=True).decode("utf-8").split(", ")
          #print (driveoutput)
     else:
          driveoutput = "", ""
     return drivestatus, driveoutput[0], driveoutput[1]

def TestConnection(Servers, ConnectionLastDown):
     Servers = Servers.split(";")
     #print (Servers)
     ConnectionUp = int(SysUpS) - int(ConnectionLastDown) # calculate time without internet down
     ConnectionUp = str(round(ConnectionUp/TimeDenom)) # convert to string
     #ConnectionUp = str(round(ConnectionUp)) # convert to string
     #ConnectionUpspaces = "   "[0:3-len(ConnectionUp)] # calculate trailing spaces for dashboard
     pingsuccesscount = 0
     for i in range(len(Servers)):
          cmd = "/bin/ping -c 1 -w 2 {} | grep {} -c".format(Servers[i], "\'1 received\'")
          try:
               pingsuccesscount += int(subprocess.check_output(cmd, shell=True).decode("utf-8"))
          except subprocess.CalledProcessError as e:
               nothing = 0
          if pingsuccesscount == len(Servers):
               ConnectionStatus = 'OKx'
          elif pingsuccesscount > 0:
               ConnectionStatus = 'OKp'
          else:
               ConnectionLastDown = SysUpS # Update last known moment with internet down (measured in time up of device)
               ConnectionStatus = 'NOd'
               ConnectionUp = ""
     return ConnectionStatus, ConnectionUp, ConnectionLastDown

def SetColor(Service):
     if Service[0:3] in ('OKx'):
          StatCol = "#00FF00"
     elif Service[0:3] in ('T1n', 'T2n', 'T3n', 'UVn', 'NOd', 'ERx'):
          StatCol = "#FF5733"
     elif Service[0:3] in ('T1p', 'T2p', 'T3p', 'UVp', 'OKp'):
          StatCol = "#FCA903"
     else:
          StatCol = "#808080"
     return StatCol

while True:
     # Draw a black filled box to clear the image.
     #draw.rectangle((0, 0, width, height), outline=0, fill=0)

     if LowRefreshCount == 1:
          # IP address (only in rare cases it changes during a running session)
          #cmd = "hostname -I | cut -d' ' -f1 | tr -d ."
          cmd = "hostname -I | cut -d' ' -f1"
          IP = subprocess.check_output(cmd, shell=True).decode("utf-8").split(".")
          #print (IP)
          if len(IP)>2:
               IP1 = IP[0] + "   "[0:len(IP[1])] + IP[2]
               IP2 = "   "[0:len(IP[0])] + IP[1] + "   "[0:len(IP[2])] + IP[3]
          else:
               IP1 = ""
               IP2 = ""
          # Disk usage root partition
          cmd = 'df -h | awk \'$NF=="/"{printf "%s", $5}\''
          Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")
          Diskspaces = "  "[0:4-len(Disk)]
          # Determine how granular up time needs to be displayed (close to boot up it is displayed in sec)
          cmd = "cat /proc/uptime | awk '{printf \"%.0f\", $1}'"
          SysUpS = subprocess.check_output(cmd, shell=True).decode("utf-8")
          if int(SysUpS) < 900:
               SysUp = SysUpS
               UnitTime = "SECS"
               TimeDenom = 1
          elif int(SysUpS) < 720*60:
               UnitTime = "MINS"
               SysUp = str(round(int(SysUpS) / 60))
               TimeDenom = 60
          else:
               UnitTime = "DAYS"
               SysUp = str(round(int(SysUpS) / (3600*24)))
               TimeDenom = 3600*24
          SysUpspaces = "   "[0:3-len(SysUp)]

          #LowRefreshCount = 1
     else:
          none=0
          #LowRefreshCount += 1

     cmd = "top -bn1 | grep load | awk {}{}{}".format("'{printf \"%.0f\", $(NF-2)*100/", NrCores, "}'") #need to adjust to number of cores (currently 4)
     CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
     CPUspaces = "  "[0:3-len(CPU)]

     cmd = "cat /sys/class/thermal/thermal_zone0/temp |  awk '{printf \"%.0f\", $(NF-0) / 1000}'"  # pylint: disable=line-too-long
     Temp = subprocess.check_output(cmd, shell=True).decode("utf-8")#

     cmd = "free -m | awk 'NR==2{printf \"%.0f\", $3*100/$2 }'"
     RAM = subprocess.check_output(cmd, shell=True).decode("utf-8")
     RAMspaces = "  "[0:3-len(RAM)]

     cmd = "vcgencmd get_throttled | sed s/'throttled=0x'// | perl -ne 'printf \"%020b\\n\", hex($_)'"
     ThrottleAll = subprocess.check_output(cmd, shell=True).decode("utf-8")
     Throttle = int(ThrottleAll[0:4]) + int(ThrottleAll[16:20]) + 1111
     Throttle = str(Throttle)

     if Throttle[3:4] == '3':
          Power = 'UVn'
          SysUpLastPowerIssue = SysUpS # Update last known moment with power issue (measured in time up of device)
     elif Throttle[3:4] == '2':
          Power = 'UVp'
     else:
          Power = 'OKx'

     PowerUp = int(SysUpS) - int(SysUpLastPowerIssue) # calculate time without power issue
     PowerUp = str(round(PowerUp/TimeDenom)) # convert to string
     #PowerUpspaces = "   "[0:3-len(PowerUp)] # calculate trailing spaces for dashboard

     if Throttle[1:2] == '3':
          Sys = 'T3n'
     elif Throttle[2:3] == '3':
          Sys = 'T2n'
     elif Throttle[0:1] == '3':
          Sys = 'T1n'
     elif Throttle[1:2] == '2':
          Sys = 'T3p'
     elif Throttle[2:3] == '2':
          Sys = 'T2p'
     elif Throttle[0:1] == '2':
          Sys = 'T1p'
     else:
          Sys = 'OKx'

     # Create screen picture
     x = indent
     y = padding

     draw.rectangle((0, y+1, 128, y + 3 * font1.getsize("Test")[1]), outline="#000000", fill="#000000")

     draw.text((x, y), "T    |CPU    |RAM    ".format(Temp, CPUspaces, CPU, RAMspaces, RAM), font=font1, fill="#0077FF")
     draw.text((x, y), "  {}C    {}{}%    {}{}%".format(Temp, CPUspaces, CPU, RAMspaces, RAM), font=font1, fill="#FFFFFF")
     y += font1.getsize("Test")[1]
     draw.text((x, y), "DISK    |", font=font1, fill="#0077FF")
     draw.text((x, y), "    {}{}".format(Diskspaces, Disk), font=font1, fill="#FFFFFF")
     draw.text((x, y), "         {}".format(IP1), font=font1, fill="#FFFFFF")
     draw.text((x, y), "         {}".format(IP2), font=font1, fill="#FF00FF")
     y += font1.getsize("Test")[1]
     #draw.rectangle((x-1, y+1, x-1+width, y+9), outline=(11, 103, 97), fill=(11, 103, 97))
     #draw.rectangle((x+1, y+2, x+6, y+7), outline="#0077FF", fill="#0077FF")
     if OddRun:
          draw.rectangle((x+2, y+2, x+4, y+4), outline="#00FF00", fill="#00FF00")
          draw.rectangle((x+6, y+6, x+8, y+8), outline="#00FF00", fill="#00FF00")
          draw.rectangle((x+6, y+2, x+8, y+4), outline="#0077FF", fill="#0077FF")
          draw.rectangle((x+2, y+6, x+4, y+8), outline="#0077FF", fill="#0077FF")
          OddRun = False
     else:
          draw.rectangle((x+6, y+2, x+8, y+4), outline="#00FF00", fill="#00FF00")
          draw.rectangle((x+2, y+6, x+4, y+8), outline="#00FF00", fill="#00FF00")
          draw.rectangle((x+2, y+2, x+4, y+4), outline="#0077FF", fill="#0077FF")
          draw.rectangle((x+6, y+6, x+8, y+8), outline="#0077FF", fill="#0077FF")
          OddRun = True
     draw.text((x, y), "  SERVICE UP ({})".format(UnitTime), font=font1, fill="#0077FF")

     #y += spacing
     #y += spacing
     #StatusColor = SetColor(Power)
     #draw.rectangle((x-1, y+1, x+12, y+9), outline=StatusColor, fill=StatusColor)
     #draw.text((x, y), "{}                   ".format(Power[0:2]), font=font1, fill="#000000")

     for i in range(len(LINES)):
          y += spacing + LINES[i][1]

          if LINES[i][3] == 'System':
               StatusColor = SetColor(Sys)
               if LINES[i][0] == 'S':
                    draw.rectangle((0 + LINES[i][2], y, 64 + LINES[i][2], y + spacing), outline=0, fill=0)
                    draw.text((x-3+LINES[i][2], y), "   {}".format(SysName[0:4]), font=font1, fill="#FFFFFF")
                    draw.text((x+LINES[i][2], y), "      {}{}".format("     "[:1+3-len(SysUp)], SysUp), font=font1, fill="#FFFFFF")
               else:
                    draw.rectangle((0, y, 128, y + spacing), outline=0, fill=0)
                    draw.text((x-3, y), "   {} {}".format(SysName, SysOSversion), font=font1, fill="#FFFFFF")
                    draw.text((x, y), "    {}{}".format("                 "[:17-len(SysUp)], SysUp), font=font1, fill="#FFFFFF")
               draw.rectangle((x-1+LINES[i][2], y+1, x+12+LINES[i][2], y+9), outline=StatusColor, fill=StatusColor)
               draw.text((x+LINES[i][2], y), "{}                   ".format(Sys[0:2]), font=font1, fill="#000000")

          if LINES[i][3] == 'Power':
               StatusColor = SetColor(Power)
               if LINES[i][0] == 'S':
                    draw.rectangle((0 + LINES[i][2], y, 64 + LINES[i][2], y + spacing), outline=0, fill=0)
                    draw.text((x-3+LINES[i][2], y), "   PWR", font=font1, fill="#0077FF")
                    draw.text((x+LINES[i][2], y), "      {}{}".format("     "[:1+3-len(PowerUp)], PowerUp), font=font1, fill="#0077FF")
               else:
                    draw.rectangle((0, y, 128, y + spacing), outline=0, fill=0)
                    #draw.text((x-3, y), "   {} {}".format(SysName, SysOSversion), font=font1, fill="#FFFFFF")
                    draw.text((x-3, y), "   POWER", font=font1, fill="#0077FF")
                    draw.text((x, y), "    {}{}".format("                 "[:17-len(PowerUp)], PowerUp), font=font1, fill="#0077FF")
               draw.rectangle((x-1+LINES[i][2], y+1, x+12+LINES[i][2], y+9), outline=StatusColor, fill=StatusColor)
               draw.text((x+LINES[i][2], y), "{}                   ".format(Power[0:2]), font=font1, fill="#000000")

          elif (LINES[i][3] == '0' and FirstRun) or (LINES[i][3] == 'H') or (LINES[i][3] == 'M' and MediumRefreshCount == 1) or (LINES[i][3] == 'L' and LowRefreshCount == 1):
               if LINES[i][0] == 'S':
                    draw.rectangle((0 + LINES[i][2], y, 64 + LINES[i][2], y + spacing), outline=0, fill=0)
               else:
                    draw.rectangle((0, y, 128, y + spacing), outline=0, fill=0)
               if LINES[i][4] in ("Service", "SystemCtl"):
                    LINESTATUS = LINES[i] + list(ServiceStatus(LINES[i][5], LINES[i][4]))
                    StatusColor = SetColor(LINESTATUS[7])
                    draw.rectangle((x-1+LINES[i][2], y+1, x+12+LINES[i][2], y+9), outline=StatusColor, fill=StatusColor)
                    draw.text((x+LINES[i][2], y), "{}                   ".format(LINESTATUS[7][0:2]), font=font1, fill="#000000")
                    if LINES[i][0] == 'S':
                         draw.text((x-3+LINES[i][2], y), "   {}".format(LINESTATUS[6]), font=font1, fill=StatusColor)
                         draw.text((x+LINES[i][2], y), "      {}{}".format("     "[:1+3-len(LINESTATUS[8])], LINESTATUS[8]), font=font1, fill=StatusColor)
                    else:
                         draw.text((x-3, y), "   {}".format(LINESTATUS[6]), font=font1, fill=StatusColor)
                         draw.text((x, y), "   {}{}".format("                 "[:1+17-len(LINESTATUS[8])], LINESTATUS[8]), font=font1, fill=StatusColor)
               elif LINES[i][4] == 'Drive':
                    LINESTATUS = LINES[i] + list(DriveStatus(LINES[i][5]))
                    StatusColor = SetColor(LINESTATUS[7])
                    draw.rectangle((x-1+LINES[i][2], y+1, x+12+LINES[i][2], y+9), outline=StatusColor, fill=StatusColor)
                    draw.text((x+LINES[i][2], y), "{}                   ".format(LINESTATUS[7][0:2]), font=font1, fill="#000000")
                    draw.text((x-3, y), "   {}".format(LINESTATUS[6]), font=font1, fill=StatusColor)
                    draw.text((x, y), "             {}{}{}{}%".format("    "[0:4-len(LINESTATUS[8])], LINESTATUS[8], "   "[0:3-len(LINESTATUS[9])], LINESTATUS[9]), font=font1, fill=StatusColor)
               elif LINES[i][4] == 'Connectivity':
                    if len(LINES[i]) == 7:
                         LINES[i] = LINES[i] + [ConnectionLastDown]
                    LINESTATUS = LINES[i] + list(TestConnection(LINES[i][6], LINES[i][7]))
                    LINES[i][7] = LINESTATUS[10]
                    StatusColor = SetColor(LINESTATUS[8])
                    draw.rectangle((x-1+LINES[i][2], y+1, x+12+LINES[i][2], y+9), outline=StatusColor, fill=StatusColor)
                    draw.text((x+LINES[i][2], y), "{}                   ".format(LINESTATUS[8][0:2]), font=font1, fill="#000000")
                    if LINES[i][0] == 'S':
                         draw.text((x-3+LINES[i][2], y), "   {}".format(LINESTATUS[5]), font=font1, fill=StatusColor)
                         draw.text((x+LINES[i][2], y), "      {}{}".format("     "[:1+3-len(LINESTATUS[9])], LINESTATUS[9]), font=font1, fill=StatusColor)
                    else:
                         draw.text((x-3, y), "   {}".format(LINESTATUS[5]), font=font1, fill=StatusColor)
                         draw.text((x, y), "   {}{}".format("                 "[:1+17-len(LINESTATUS[9])], LINESTATUS[9]), font=font1, fill=StatusColor)
                    #print (LINESTATUS)
#                    draw.text((x-3, y), "   {}{}{}".format(LINESTATUS[5],"                 "[:1+17-len(LINESTATUS[5])-len(LINESTATUS[9])],LINESTATUS[9]), font=font1, fill=StatusColor)
               elif LINES[i][4] == 'Header':
                    draw.text((x, y), LINES[i][5], font=font1, fill="#0077FF")
                    FirstRun = False
               else:
                    Non = 0
          else:
               Non = 1

     if MediumRefreshCount == LoopsBeforeRefreshMedium:
          MediumRefreshCount = 1
     else:
          MediumRefreshCount += 1
     if LowRefreshCount == LoopsBeforeRefreshLow:
          LowRefreshCount = 1
     else:
          LowRefreshCount += 1

     # Display image.
     disp.image(image)

     #if LowRefreshCount == 1:
     image.save("/dev/shm/oledstatuspi.gif", "GIF")
     time.sleep(RefreshTime)


