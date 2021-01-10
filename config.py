import platform, os
import configparser
import uuid
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

class _Config(object):
    sSession = None
    API_ID = PUT YOUR
    API_HASH = 'PUT YOUR'
    sUsername = None
    sPassword = None
    sLogFile = None
    INIFILE = 'roulette.ini'
    SESSIONFILE = 'roulette'
    LOGFILE = 'roulette.log'
    sB64Key = None
    sLastRoulette = None
    iLastMethod = 0
    iFontSize = 18
    iTimeForBet = 3
    bOrderAlpha = False
    bEncrypted = False
    asListBot = ['PUT YOUR', 'PUT YOUR']
    sSystem = None
    sConfDir = None
    bAutoUpdate = True
    bAlwaysOnTop = True

    def __init__(self):
        sPwd = str(uuid.getnode())
        salt = 'aggiun0_qualcosa_AllaPassword'.encode()
        kdf = PBKDF2HMAC( algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
        self.sB64Key = base64.urlsafe_b64encode(kdf.derive(sPwd.encode()))

    def loadConfig(self):
        self.sSystem = platform.system()
        if self.sSystem == 'Linux':
            self.sConfDir = os.path.join(os.environ['XDG_CONFIG_HOME'], 'roulette')
        elif self.sSystem == 'Windows':
            self.sConfDir = os.path.join(os.environ['APPDATA'], 'roulette')
        else:
            print('Unsupported platform')
            raise
        self.sCfgPath = os.path.join(self.sConfDir, self.INIFILE)
        self.sSession = os.path.join(self.sConfDir, self.SESSIONFILE)
        self.sLogFile = os.path.join(self.sConfDir, self.LOGFILE)
        if not os.path.exists(self.sConfDir):
            os.makedirs(self.sConfDir)
        self.objConfig = configparser.ConfigParser()
        if not os.path.exists(self.sCfgPath):
            self.objConfig['main'] = {}
            self.objConfig['main']['username'] = ''
            self.objConfig['main']['password'] = ''
            self.objConfig['main']['last_roulette'] = ''
            self.objConfig['main']['last_method'] = '0'
            self.objConfig['main']['font_size'] = str(self.iFontSize)
            self.objConfig['main']['order_alpha'] = '0'
            self.objConfig['main']['encrypted'] = '0'
            self.objConfig['main']['time_for_bet'] = str(self.iTimeForBet)
            self.objConfig['main']['autoupdate'] = '1'
            self.objConfig['main']['always_ontop'] = '1'
            with open(self.sCfgPath, 'w') as configfile:
                self.objConfig.write(configfile)
        
        self.objConfig.read(self.sCfgPath)

        try:
            self.bEncrypted = True if self.objConfig['main']['encrypted'] == '1' else False
            self.sUsername = self.decrypt(self.objConfig['main']['username'])
            self.sPassword = self.decrypt(self.objConfig['main']['password'])
            self.sLastRoulette = self.objConfig['main']['last_roulette']
            self.iLastMethod = int(self.objConfig['main']['last_method'])
            self.iFontSize = int(self.objConfig['main']['font_size'])
            self.bOrderAlpha = True if self.objConfig['main']['order_alpha'] == '1' else False
            self.iTimeForBet = int(self.objConfig['main']['time_for_bet'])
            self.bAutoUpdate = True if self.objConfig['main']['autoupdate'] == '1' else False
            self.bAlwaysOnTop = True if self.objConfig['main']['always_ontop'] == '1' else False
        except Exception:
            return False
        return True

    def getSession(self): return self.sSession
    def getUsername(self): return self.sUsername
    def getPassword(self): return self.sPassword
    def getLastRoulette(self): return self.sLastRoulette
    def getLastMethod(self): return self.iLastMethod
    def getLogFile(self): return self.sLogFile
    def getFontSize(self): return self.iFontSize
    def getOrderAlpha(self): return self.bOrderAlpha
    def getTimeForBet(self): return self.iTimeForBet
    def getAutoUpdate(self): return self.bAutoUpdate
    def getAlwaysOnTop(self): return self.bAlwaysOnTop

    def setLastRoulette(self, sLast):
        self.sLastRoulette = sLast
        self.objConfig['main']['last_roulette'] = sLast
        self.save()

    def setLastMethod(self, iLast):
        self.iLastMethod = iLast
        self.objConfig['main']['last_method'] = str(iLast)
        self.save()

    def setUsername(self, sValue):
        self.sUsername = sValue
        self.objConfig['main']['username'] = self.encrypt(sValue)
        self.objConfig['main']['encrypted'] = '1'
        self.save()

    def setPassword(self, sValue):
        self.sPassword = sValue
        self.objConfig['main']['password'] = self.encrypt(sValue)
        self.objConfig['main']['encrypted'] = '1'
        self.save()

    def setFontSize(self, iValue):
        self.iFontSize = iValue
        self.objConfig['main']['font_size'] = str(iValue)
        self.save()

    def setTimeForBet(self, iValue):
        self.iTimeForBet = iValue
        self.objConfig['main']['time_for_bet'] = str(iValue)
        self.save()

    def setOrderAlpha(self, bValue):
        self.bOrderAlpha = bValue
        self.objConfig['main']['order_alpha'] = '1' if bValue else '0'
        self.save()

    def setAutoupdate(self, bValue):
        self.bAutoUpdate = bValue
        self.objConfig['main']['autoupdate'] = '1' if bValue else '0'
        self.save()

    def setAlwaysOnTop(self, bValue):
        self.bAlwaysOnTop = bValue
        self.objConfig['main']['always_ontop'] = '1' if bValue else '0'
        self.save()

    def save(self):
        with open(self.sCfgPath, 'w') as configfile:
            self.objConfig.write(configfile)
 
    def getApi(self, iNdx):
        if iNdx == 1:
            return self.API_ID
        else:
            return self.API_HASH

    def bxor(self, ba1, ba2):
        return bytes([_a ^ _b for _a, _b in zip(ba1, ba2)])

    def encrypt(self, string):
        if string == '':
            return ''
        f = Fernet(self.sB64Key)
        return f.encrypt(string.encode()).decode()

    def decrypt(self, string):
        if not self.bEncrypted or string == '':
            return string
        f = Fernet(self.sB64Key)
        return f.decrypt(string.encode()).decode()

    def isWindows(self):
        return self.sSystem == 'Windows'

_config = _Config()

def Config(): return _config
