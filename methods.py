# -*- coding: utf-8 -*-

import re
import logging

class Method:
    objLog = None

    def __init__(self):
        self.objLog = logging.getLogger()
 
    def newNum(self, iNum):
        pass

    def isWin(self):
        return False

    def getWinColor(self):
        return None

    def isToForward(self):
        return False

    def isGameAutomatic(self):
        return False

    def resetInit(self):
        pass

class Method1(Method):
    EXTRACT_COUNT = 52
    bSound = False

    def __init__(self):
        super().__init__()

    #def getCountExtractNumber(self): return self.EXTRACT_COUNT

    def send_message(self, sMsg):
        #match = re.match('\[(.*)\]', sMsg)
        match = re.match('\[(.*)\]\((.*)\)', sMsg)
        sGame = None
        if match is not None:
            sGame = [sNum.strip() for sNum in match[1].split(',')]
            sMsg = '<font color="Aqua"><b>{}</b></font> => {}'.format(match[2], match[1])
        if sMsg == 'Ritardo sequenza = 3':
            self.bSound = True
        else:
            self.bSound = False
        
        return sMsg, sGame, False
    
    def isPlayAlert(self):
        return self.bSound, 'resource/1.dat'

class Method2(Method):
    EXTRACT_COUNT = 50
    bSound = False
    iCountNum = -1
    bWin = False
    sWinColor = None
    bForward = False
    bWrongPrev = False
    #sOriginalMsg = None
    asNum = []
    bGameAutomatic = False
    sFichesValue = None

    def __init__(self):
        super().__init__()
        
    #def getCountExtractNumber(self): return self.EXTRACT_COUNT

    def send_message(self, sMsg):
        #self.sOriginalMsg = sMsg
        bRigthAligh = False
        if len(sMsg) < 5:
            bRigthAligh = True
        sMsg = sMsg.replace('\U0001F947', 'Oro ')
        sMsg = sMsg.replace('\U0001f948', 'Argento ')
        sMsg = sMsg.replace('\U0001fa82', 'Paracadute ')
        sMsg = sMsg.replace('\U0001f4a5', '***')
        #self.asNum = None
        self.bForward = False
        self.bGameAutomatic = False
        if sMsg.find('Previsione ottimale')!=-1 or sMsg.find('Previsione mix')!=-1 or \
           sMsg.find('Previsione GOLD')!=-1 or sMsg.find('Metodo paracadute')!=-1:
            if sMsg.find('Previsione ottimale')!=-1:
                self.bForward = True
            self.asNum = sMsg.split('\n')[1].split(',')
            if self.asNum[-1] == '':
                del self.asNum[-1]
            self.asNum[0] = self.asNum[0].split(' ')[-1]
        elif sMsg.find('Oro Argento ') == 0:
            asNum = sMsg.replace('Oro Argento ', '').split(',')
            if len(asNum) > 1:
                self.asNum = asNum
                if self.asNum[-1] == '':
                    del self.asNum[-1]
        elif sMsg.find('CICLO precedente concluso')!=-1:
            self.iCountNum = -1
            asLine = sMsg.split('\n')
            self.asNum = []
            # TODO improve code put in a function
            match = re.match('Oro(.*)Argento(.*)', asLine[2])
            sOro = match[1].strip()
            sArgento = match[2].strip()
            if sOro != '':
               asOro = sOro.split(',')
               if asOro[-1] == '':
                   del asOro[-1]
               asOro[0] = asOro[0].strip()
               for sNum in asOro:
                   self.asNum.append(sNum)
            if sArgento != '':
               asArgento = sArgento.split(',')
               if asArgento[-1] == '':
                   del asArgento[-1]
               asArgento[0] = asArgento[0].strip()
               for sNum in asArgento:
                   self.asNum.append(sNum)
            match = re.match('Paracadute(.*)', asLine[3])
            sPara = match[1].strip()
            if sPara != '':
               asPara = sPara.split(',')
               if asPara[-1] == '':
                   del asPara[-1]
               asPara[0] = asPara[0].strip()
               for sNum in asPara:
                   self.asNum.append(sNum)
            self.asNum = list(set(self.asNum))
            self.asNum.sort(key=int)
        elif sMsg.find('Colpi di attesa OPZIONALI') == 0:
            self.iCountNum = int(sMsg.replace('Colpi di attesa OPZIONALI ', ''))
            self.bWrongPrev = False
        elif sMsg.find('ok, gioco con le fishes da ') == 0:
            self.sFichesValue = sMsg.replace('ok, gioco con le fishes da ', '')
            self.bGameAutomatic = True
        sMsg = sMsg.strip()
        if sMsg == 'Oro' or sMsg == 'Argento' or sMsg == 'Paracadute' or sMsg == 'Oro Argento':
            self.bSound = False
            if sMsg.startswith('Oro'):
                self.sWinColor = 'Yellow'
            elif sMsg == 'Argento':
                self.sWinColor = '#A0A0A0'
            else:
                self.sWinColor = '#00FF00'
        sMsg = sMsg.replace('Oro', '<font color="Yellow"><b>Oro</b></font>')
        sMsg = sMsg.replace('Argento', '<font color="#A0A0A0"><b>Argento</b></font>')
        sMsg = sMsg.replace('Paracadute', '<font color="#00FF00"><b>Paracadute</b></font>')
        return sMsg, self.asNum, bRigthAligh

    def isPlayAlert(self):
        return self.bSound, 'resource/2.dat' if not self.bWrongPrev else 'resource/3.dat'

    def newNum(self, iNum):
        self.bWin = False
        if str(iNum) in self.asNum:
            self.bWin = True
        if self.bWin and self.iCountNum>0:
            self.bWrongPrev = True
        else:
            self.bWrongPrev = False
        self.iCountNum -= 1
        if self.iCountNum == 0 or self.bWrongPrev:
            self.iCountNum = -1
            self.bSound = True
        else:
            self.bSound = False

    def isWin(self):
        return self.bWin

    def getWinColor(self):
        return self.sWinColor

    def isToForward(self):
        return self.bForward

    def resetInit(self):
        self.iCountNum = -1
        self.bSound = False
        self.bWin = False
        self.bWrongPrev = False

    def isGameAutomatic(self):
        return self.bGameAutomatic

    def getFichesValue(self):
        return self.sFichesValue
