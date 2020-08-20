# -*- coding: utf-8 -*-

import blynklib     # Osnovna Blynk biblioteka
import blynktimer   # Podrška za tajmere u Blynk
import logging      # Biblioteka za upravljanje logovanjem
import os           # Omogućava pristup komandnoj liniji, tj nmap programu
from configobj import ConfigObj # Koristi se za čuvanje informacija u fajl, kako bi informacije ostale u slučaju restarta programa ili Raspberry Pi
from datetime import datetime, time, timedelta # biblioteke za vremenske funkcije
import RPi.GPIO as GPIO         # Biblioteka za rad sa GPIO pinovima
from TM1637 import FourDigit    # Modifikovana biblioteka za LED 7-segmentni displej
import Adafruit_DHT             # DHT senzor
import DS18B20 as ds            # DS senzor temperature
import yahooweather             # biblioteka za Yahoo Weather API



"""
  ___         _  _    _         _               _                 
 |_ _| _ __  (_)| |_ (_)  __ _ | |   ___   ___ | |_  _   _  _ __  
  | | | '_ \ | || __|| | / _` || |  / __| / _ \| __|| | | || '_ \ 
  | | | | | || || |_ | || (_| || |  \__ \|  __/| |_ | |_| || |_) |
 |___||_| |_||_| \__||_| \__,_||_|  |___/ \___| \__| \__,_|| .__/ 
                                                           |_|    
"""

_log = logging.getLogger('BlynkLog')
logFormatter = logging.Formatter("%(asctime)s [%(levelname)s]  %(message)s")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
_log.addHandler(consoleHandler)
_log.setLevel(logging.INFO)

WRITE_EVENT_PRINT_MSG = "[WRITE_VIRTUAL_PIN_EVENT] Pin: V{} Value: '{}'"
READ_PRINT_MSG = "[READ_VIRTUAL_PIN_EVENT] Pin: V{}"
TIMER_PRINT_MSG = "[TIMER_TRIGGERED_EVENT] Timer: {}"
NOTIFY_PRINT_MSG = "[NOTIFICATION_EVENT_SENT] Notification: {}"

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

FAN_DPIN = 4  			# GPIO pin za kontrolu ventilatora
TEMP_DPIN = 17  			# GPIO pin za DHT11 senzor
LIGH_DPIN = 26  			# GPIO pin za kontrolu svetla
TEMP_VPIN = 8			# Virtual pin za sobnu temperaturu
HUM_VPIN = 11			# virtual pin za vlažnost vazduha
DS_DPIN = 27  			# GPIO pin za DS18B20 senzor
DS_VPIN = 0 			# Virtualni pin za DS senzor
DS_ID = '28-0301A279DA24' 	# Jedinstveni ID DS18B20 senzora

GPIO.setup(FAN_DPIN, GPIO.OUT) # Postavlja se pin ventilator kao output
GPIO.setup(LIGH_DPIN, GPIO.OUT) # Postavlja se pin za svetlo kao output

COLD_COLOR = '#308AE4'		# Definisanje boja u HEX
NORM_COLOR = '#339933'
HOT_COLOR = '#E23201'
ERR_COLOR = '#444444'

params = ConfigObj('params.ini')
wantedTemp = float(params['wanted_temperature'])


BLYNK_AUTH = 'LE5PbkiWEbXDqjBgDfsUKKifX5BqaV-g'
blynk = blynklib.Blynk(
    BLYNK_AUTH,
    server='echelon.msat.rs',
    port=8080,
    log=_log.info)

timer = blynktimer.Timer()


def isMarkoPresent():
    os.system('nmap -sn 10.11.11.0/24 --min-parallelism 100 1> /dev/null')
    output = os.popen('/sbin/ip neigh')
    arplist = output.read()
    markophone = "78:62:56:aa:29:09"
    if markophone in arplist:
        _log.info('Provera prisutnosti vratila: True')
        return True
    else:
        _log.info('Provera prisutnosti vratila: False')
        return False


def sendNotification(notification):
    blynk.notify(notification)
    _log.info(NOTIFY_PRINT_MSG.format(notification))


def getAccuLevel(avgTmp):
    if avgTmp < -4:
        return 3
    elif -5 < avgTmp < 0:
        return 2.5
    elif -1 < avgTmp < 7:
        return 2
    elif 6 < avgTmp < 15:
        return 1.5
    elif 14 < avgTmp < 20:
        return 1
    elif 19 < avgTmp:
        return 'ugasen'


def isNotificationTime():
    now = datetime.now()
    # najranije vreme slanja notifikacije 21:01
    minNotifyTime = now.replace(hour=21, minute=10, second=00)
    # najkasnije vreme slanja notifikacije 23:10
    maxNotifyTime = now.replace(hour=23, minute=11, second=00)
    if maxNotifyTime > now > minNotifyTime:
        return True
    else:
        return False



def isSleepTime():
    now = datetime.now()
    # Vreme odlaska na spavanje
    startSleepTime = now.replace(hour=00, minute=1)
    # Vreme budjenja
    endSleepTime = startSleepTime+timedelta(hours=9)
    if endSleepTime > now > startSleepTime:
        return True
    else:
        return False



def maintainTemp(temp, mod):
    _log.info('Funkcija održavanja temperature pokrenuta')
    _log.info('Izabrana iz app: {}, trenutna: {}, modifikator: {}'.format(wantedTemp, temp, mod))
    if temp < wantedTemp + mod:
        GPIO.output(FAN_DPIN, 1)
        blynk.virtual_write(2, 1)
        _log.info('Sobna temperatura: {} je niža od izabrane sa modifikatorom {}, FAN ON'.format(temp, wantedTemp + mod))
    else:
        GPIO.output(FAN_DPIN, 0)
        blynk.virtual_write(2, 0)
        _log.info('Sobna temperatura: {} je viša od izabrane sa modifikatorom {}, FAN OFF'.format(temp, wantedTemp + mod))


"""
  ____   _                _     __     __ ____  ___  _   _                         _ 
 | __ ) | | _   _  _ __  | | __ \ \   / /|  _ \|_ _|| \ | |  _ __  ___   __ _   __| |
 |  _ \ | || | | || '_ \ | |/ /  \ \ / / | |_) || | |  \| | | '__|/ _ \ / _` | / _` |
 | |_) || || |_| || | | ||   <    \ V /  |  __/ | | | |\  | | |  |  __/| (_| || (_| |
 |____/ |_| \__, ||_| |_||_|\_\    \_/   |_|   |___||_| \_| |_|   \___| \__,_| \__,_|
            |___/                                                                   

"""


@blynk.handle_event('read V8')
def read_dht_sensor(pin):
    hum, temp =  Adafruit_DHT.read_retry(11, TEMP_DPIN)
    _log.info(READ_PRINT_MSG.format(pin))

    if temp:
        blynk.virtual_write(TEMP_VPIN, temp)
        _log.info(WRITE_EVENT_PRINT_MSG.format(TEMP_VPIN, temp))
        blynk.virtual_write(HUM_VPIN, hum)
        _log.info(WRITE_EVENT_PRINT_MSG.format(HUM_VPIN, hum))

    else:
        _log.error('Neuspelo čitanje DHT senzora')
        blynk.set_property(TEMP_VPIN, 'color', ERR_COLOR)
        blynk.virtual_write(TEMP_VPIN, 0)
        blynk.set_property(HUM_VPIN, 'color', ERR_COLOR)
        blynk.virtual_write(HUM_VPIN, 0)



"""
  ____   _                _     __     __ ____  ___  _   _                   _  _        
 | __ ) | | _   _  _ __  | | __ \ \   / /|  _ \|_ _|| \ | | __      __ _ __ (_)| |_  ___ 
 |  _ \ | || | | || '_ \ | |/ /  \ \ / / | |_) || | |  \| | \ \ /\ / /| '__|| || __|/ _ \
 | |_) || || |_| || | | ||   <    \ V /  |  __/ | | | |\  |  \ V  V / | |   | || |_|  __/
 |____/ |_| \__, ||_| |_||_|\_\    \_/   |_|   |___||_| \_|   \_/\_/  |_|   |_| \__|\___|
            |___/                                                                        

"""


@blynk.handle_event('write V7')
def enable_LED_display(pin, value):
    _log.info(WRITE_EVENT_PRINT_MSG.format(pin, value))
    global displayenabled

    if value[0] == u'1':
        displayenabled = 'True'

    else:
        displayenabled = 'False'

    params['displayenabled'] = displayenabled
    params.write()


@blynk.handle_event('write V3')
def set_wantedTemp(pin, value):
    _log.info(WRITE_EVENT_PRINT_MSG.format(pin, value))
    global wantedTemp
    wantedTemp = float(value[0])
    params['wanted_temperature'] = wantedTemp
    params.write()

    if wantedTemp <= 18:
        blynk.set_property(pin, 'color', COLD_COLOR)
    if 19 <= wantedTemp <= 22:
        blynk.set_property(pin, 'color', NORM_COLOR)
    if wantedTemp > 22:
        blynk.set_property(pin, 'color', HOT_COLOR)


manualon = False # Status ventilatora

@blynk.handle_event('write V2')
def control_ta_fan(pin, value):
    _log.info(WRITE_EVENT_PRINT_MSG.format(pin, value))
    global manualon
    if value[0] == u'1':
        GPIO.output(FAN_DPIN, 1)
        manualon = True
    else:
        GPIO.output(FAN_DPIN, 0)
        manualon = False


@blynk.handle_event('write V1')
def light_switch(pin, value):
    _log.info(WRITE_EVENT_PRINT_MSG.format(pin, value))
    if value[0] == u'1':
        GPIO.output(LIGH_DPIN, 1)
    else:
        GPIO.output(LIGH_DPIN, 0)



@blynk.handle_event('write V9')
def manual_update(pin, value):
    if value[0] == u'1':
        _log.info(WRITE_EVENT_PRINT_MSG.format(pin, value))
        update_outside_temperature()



"""
  ____   _                _      _    _                             
 | __ ) | | _   _  _ __  | | __ | |_ (_) _ __ ___    ___  _ __  ___ 
 |  _ \ | || | | || '_ \ | |/ / | __|| || '_ ` _ \  / _ \| '__|/ __|
 | |_) || || |_| || | | ||   <  | |_ | || | | | | ||  __/| |   \__ \
 |____/ |_| \__, ||_| |_||_|\_\  \__||_||_| |_| |_| \___||_|   |___/
            |___/                                                   
"""


counter = 0  # brojac za proveru vlaznosti vazduha

@timer.register(interval=307)
def maintain_temp():
    _log.info(TIMER_PRINT_MSG.format(
        'Praćenje i održavanje temperature, svakih 307 sek'))
    global counter
    global temperature, humidity
    counter += 1
    markopresent = isMarkoPresent()

    hum, temp = Adafruit_DHT.read_retry(11, TEMP_DPIN)
    temperature = temp  # update global temperature
    humidity = hum
    if markopresent == True:
        _log.info('Marko je prisutan')
        if isSleepTime() == False:
            _log.info('Nije vreme spavanja.')
            if counter % 6 == 0:
                if hum > 69:
                    sendNotification('Trenutna vlažnost vazduha je previsoka.\n'
                                        'Provetrite prostoriju.')
                counter = 0

            if manualon == False:
                _log.info(
                    'Ventilator nije ručno uključen, radi se održavanje temperature')
                maintainTemp(temp, 0)

        else:  # if isSleepTime() == True
            _log.info('Vreme je spavanja')
            if manualon == False:
                _log.info(
                    'Ventilator nije ručno uključen, radi se noćno odrzavanje temperature.')
                maintainTemp(temp, -2)

    else:  # if markopresent == False
        _log.info('Korisnik nije prisutan')
        if manualon == False:
            _log.info('Ventilator nije ručno uključen')
            maintainTemp(temp, -2)

notification_sent = False  # Da li je poslata poruka o punjenju
lastAccuLevel = float(params['accumulation_level'])


@timer.register(interval=1801)
def accuLevelNotify():
    global notification_sent  # boolean da li je poruka poslata
    global lastAccuLevel  # oznacava koliko je pec punjena juce
    _log.info(TIMER_PRINT_MSG.format('Tajmer za obaveštenje o punjenju'))
    if isNotificationTime() == True:  # ako je sada vreme za obavestenje
        # Proveriti da li je korisnik kuci
        _log.info('Notification time = True')
        if isMarkoPresent() == True:
            _log.info('MarkoPresent = True')

            if notification_sent == False:
                _log.info('Notification sent: False')
                tomorrowAvg = yahooweather.getTomorrowAvg(
                    'petrovac, rs')
                accuLevel = getAccuLevel(tomorrowAvg)
                if accuLevel != lastAccuLevel:
                    sendNotification('Sutra se očekuje prosečna temperatura {}°C.\n'\
'Termostat TA peći postaviti na {}.'.format(tomorrowAvg, accuLevel))        
                    notification_sent = True
                    lastAccuLevel = accuLevel
                    params['accumulation_level'] = lastAccuLevel
                    params.write()
        else:
            _log.info('MarkoPresent = False')
    else:
        notification_sent = False
        _log.info('Notification time = False')



@timer.register(interval=3601)
def update_outside_temperature():
    _log.info(TIMER_PRINT_MSG.format(
        'Ažuriranje spoljne temperature i ta peći'))
    try:
        outside_weather = yahooweather.getCurrentTemp('petrovac, rs')
        blynk.virtual_write(4, outside_weather)
        _log.info(TIMER_PRINT_MSG.format(
            'Spoljna temperatura ažurirana {}°C'.format(outside_weather)))
    except:
        _log.error('Neuspelo ažuriranje spoljne temperature')

    try:
        ta_temp = round(ds.read(True, DS_DPIN, DS_ID), 1)
        _log.info('Očitana temperatura sa DS senzora: {}°C'.format(ta_temp))
        if ta_temp is not None:
            blynk.virtual_write(DS_VPIN, ta_temp)
            if ta_temp <= temperature:
                sendNotification('TA peć je prazna, uključite akumulaciju')
    except:
        _log.error('Došlo je do greške prilikom čitanja DS senzora')
        blynk.virtual_write(DS_VPIN, 0)



########################
#   Display functions  #
########################
dis = FourDigit()
display_counter = 0
displayenabled = params['displayenabled']
humidity, temperature = Adafruit_DHT.read_retry(11, TEMP_DPIN)


def display_date():
    dis.setColon(False)
    dis.show(datetime.now().strftime('%d%m'))


def display_time():
    dis.setColon(True)
    dis.show(datetime.now().strftime('%H%M'))


def display_temperature():
    dis.setColon(False)
    dis.show(str(temperature)[0:2] + ' C')


def display_humidity():
    dis.setColon(False)
    dis.show(str(humidity)[0:2] + 'rH')

def show_on_display():
    global display_counter
    if display_counter == 0:
        display_date()
        display_counter = 1
    elif display_counter == 1:
        display_time()
        display_counter = 2
    elif display_counter == 2:
        display_temperature()
        display_counter = 3
    elif display_counter == 3:
        display_humidity()
        display_counter = 0
    else:
        dis.show('Err')

@timer.register(interval=5)
def trigger_display_change():
    if displayenabled == 'True': # configobj vraca string
        if isSleepTime() == True:
            dis.setLuminosity(1)
        else:
            dis.setLuminosity(6)
        show_on_display()
    else:
        dis.erase()


"""
  ____   _                _                        _          _                      
 | __ ) | | _   _  _ __  | | __  _ __ ___    __ _ (_) _ __   | |  ___    ___   _ __  
 |  _ \ | || | | || '_ \ | |/ / | '_ ` _ \  / _` || || '_ \  | | / _ \  / _ \ | '_ \ 
 | |_) || || |_| || | | ||   <  | | | | | || (_| || || | | | | || (_) || (_) || |_) |
 |____/ |_| \__, ||_| |_||_|\_\ |_| |_| |_| \__,_||_||_| |_| |_| \___/  \___/ | .__/ 
            |___/                                                             |_|   
"""


while True:
    blynk.run()
    timer.run()
