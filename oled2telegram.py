import requests
from PIL import Image
import json
import configparser
import time

# Read file with user defined settings
config = configparser.ConfigParser()
config.read(['/home/pi/oledscript/oledstatuspi.conf', '/home/pi/oledscript/oledstatuspi.local.conf'])
# Get name of the system from user settings
bot_token = config['telegram']['bot_token']
bot_chatID = config['telegram']['bot_chatID']
ImageFilePath = config['telegram']['ImageFilePath']
#'/dev/shm/oledstatuspi.gif'
ImageFilePathOut = config['telegram']['ImageFilePathOut']
#'/dev/shm/oledstatuspout.gif'
CODEWORD = config['telegram']['CODEWORD']

def getupdates_telegram(bot_token, update_id):
    send_text = 'https://api.telegram.org/bot' + bot_token + '/getUpdates?offset=' + str(update_id) + '&timeout=50'
    print (send_text)
    response = requests.get(send_text)
    print (response.content)
    return response.json()

def telegram_bot_sendtext(bot_message, bot_token, bot_chatID):
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    return response.json()

def sendImage(ImageFilePathOut, bot_token, bot_chatID):
    url = "https://api.telegram.org/bot" + bot_token + "/sendPhoto";
    files = {'photo': open(ImageFilePathOut, 'rb')}
    data = {'chat_id' : bot_chatID}
    r = requests.post(url, files=files, data=data)

update_id = 0
count = 0
Match = False
#print (count)

# Sleep 15 seconds to prevent error at reboot (other python script needs to have created the output file)
time.sleep(15) 

while True:
     telegram = getupdates_telegram(bot_token, update_id)
     print (telegram)
     if telegram['ok']:
          telegramMSG = telegram['result']
          for i in range(len(telegramMSG)):
               telegramMSGx = telegramMSG[i]
               update_id = telegramMSGx['update_id']
               try:
                    text = telegramMSGx['message']['text']
               except:
                    text = ''
               finally:
                    #print (update_id)
                    #print (text)
                    if CODEWORD in text:
                         Match = True
                         #print ('Match')
                    if "Debug" in text:
                         Debug = True
                         DebugOut1 = telegram_bot_sendtext(str(telegramMSG), bot_token, bot_chatID)
                         DebugOut2 = telegram_bot_sendtext('https://api.telegram.org/bot' + bot_token + '/getUpdates?offset=' + str(update_id) + '&timeout=50', bot_token, bot_chatID)
               update_id += 1

          if Match:
               image = Image.open(ImageFilePath, 'r')
               background = Image.new('RGB', (256, 130), (0, 0, 0))
               offset = (64, 1)
               background.paste(image, offset)
               background.save(ImageFilePathOut)
               test2 = sendImage(ImageFilePathOut, bot_token, bot_chatID)
               #print (test2)
               # Reset Match to catch new matches in next cycle
               Match = False
               # Add a delay to allow other machines to catch the Codeword request too
               # (otherwise the first script to catch the request message will delete it immediately
               time.sleep(7)
     else:
          #print ('Telegram error')
          update_id = 0 #reset update id
          time.sleep(5)

     count += 1
