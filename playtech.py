# -*- coding: utf-8 -*-

import os
import asyncio
import re
import logging
import time
from selenium import webdriver
from random import randint
from time import sleep

class Playtech:
    objBrowser = None
    bLogged = False
    chip_lock = None
    objLog = None
    tskUpdate = None
    divLastNum = None
    iCurSpin = 0
    MINSPIN = 6
    MAXSPIN = 7

    aNumRed = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
    aNumBlack = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

    def __init__(self):
        objOptions = webdriver.ChromeOptions()
        objOptions.add_argument("--disable-notifications")
        
        self.objBrowser = webdriver.Chrome(os.path.join(os.getcwd(),'chromedriver'), options=objOptions)
        self.normalSearch()
        self.objBrowser.minimize_window()
        self.chip_lock = asyncio.Lock()
        self.objLog = logging.getLogger()

    def get(self, sUrl):
        self.objBrowser.get(sUrl)
        
    def fastSearch(self):
        self.objBrowser.implicitly_wait(0.5)

    def normalSearch(self):
        self.objBrowser.implicitly_wait(3)

    def moveWindow(self, iX, iY):
        self.objBrowser.execute_script("window.moveTo(arguments[0],arguments[1]);", iX, iY)

    def disconnect(self):
        self.stopUpdate()
        if len(self.objBrowser.window_handles) > 1:
            self.objBrowser.close()
        self.objBrowser.switch_to.window(self.objBrowser.window_handles[0])

    def randomDelay(self, bBig=False):
        if bBig:
            sleep(randint(30,50)/10)
        else:
            sleep(randint(8,15)/10)

    def getRouletteButton(self, sNum):
        return self.objBrowser.find_element_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[contains(@class, "roulette-table-cell roulette-table-cell_straight-{} roulette-table-cell_group-straight roulette-table-cell_color")]'.format(sNum))

    def getHorseButton(self, aiNum):
        iMax = aiNum[1]
        iMin = aiNum[0]
        if aiNum[0] > aiNum[1]:
            iMax = aiNum[0]
        if aiNum[0] > aiNum[1]:
            iMin = aiNum[1]
        sNum2 = str(iMin)
        objElement = self.objBrowser.find_elements_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[contains(@class, "roulette-table-cell roulette-table-cell_straight-{} roulette-table-cell_group-straight roulette-table-cell_color")]/following-sibling::node()'.format(iMax))
        asNum = objElement[0].get_attribute('data-automation-locator').replace('betPlace.split-', '').split('-')
        if asNum[1] == sNum2:
            self.objLog.debug(objElement[0].get_attribute('data-automation-locator'))
            return objElement[0]
        asNum = objElement[1].get_attribute('data-automation-locator').replace('betPlace.split-', '').split('-')
        if asNum[0] == sNum2:
            self.objLog.debug(objElement[1].get_attribute('data-automation-locator'))
            return objElement[1]

    def click(self, objElement, closeFunction=None):
        self.objBrowser.execute_script("arguments[0].scrollIntoView();", objElement)
        try:
            objElement.click()
        except:
            if closeFunction is not None:
                closeFunction()
            try :
                self.objBrowser.execute_script("arguments[0].click();", objElement)
            except:
                return False
        return True

    #async def game2(self, asNum, sFichVal, iMaxTime):
        #self.select(sFichVal)
    #    await self.game(asNum, 1, iMaxTime)

    async def waitCountDown(self, bWait=False):
        while True:
            try:
                divTimer = self.objBrowser.find_element_by_xpath('//div[@class="round-timers round-timers_center-video"]/div[@class="timer-desktop"]/div[@class="timer-desktop__text"]')
                if divTimer is None:
                    if not bWait:
                        return False, None
                    else:
                        await asyncio.sleep(0.5)
                else:
                    return True, divTimer
            except:
                if not bWait:
                    return False, None
                else:
                    await asyncio.sleep(0.5)

    async def game(self, asNum, iNumChip, iMaxTime, bWait=False):
        bRet, divTimer = await self.waitCountDown(bWait)
        if not bRet:
            return False
        self.fastSearch()
        iTime = int(divTimer.text)
        iTime -= 3
        if iMaxTime < iTime:
            iTime = iMaxTime
        if iTime <= 0:
            iSleep = 0
        else:
            iSleep = iTime / len(asNum)
        self.iCurSpin = randint(self.MINSPIN, self.MAXSPIN)
        async with self.chip_lock:
            for sNum in asNum:
                objSvgNum = self.getRouletteButton(sNum)
                iCount = iNumChip
                while iCount > 0:
                    objSvgNum.click()
                    iCount -= 1
                await asyncio.sleep(iSleep)
        return True
    
    async def gameHorse(self, asNum, iNumChip, iMaxTime):
        self.fastSearch()
        try:
            divTimer = self.objBrowser.find_element_by_xpath('//div[@class="round-timers round-timers_center-video"]/div[@class="timer-desktop"]/div[@class="timer-desktop__text"]')
            if divTimer is None:
                return False
        except:
            return False
        iTime = int(divTimer.text)
        iTime -= 3
        if iMaxTime < iTime:
            iTime = iMaxTime
        if iTime <= 0:
            iSleep = 0
        else:
            iSleep = iTime / len(asNum)
        self.iCurSpin = randint(self.MINSPIN, self.MAXSPIN)
        async with self.chip_lock:
            aiGame = GameHorse.generateHorse(asNum)
            for aiNum in aiGame:
                if len(aiNum) == 2:
                    objSvgNum = self.getHorseButton(aiNum)
                else:
                    objSvgNum = self.getRouletteButton(str(aiNum[0]))
                iCount = iNumChip
                while iCount > 0:
                    objSvgNum.click()
                    iCount -= 1
                await asyncio.sleep(iSleep)
        return True

    def getHorse(self, asNum):
        sNum = str(GameHorse.generateHorse(asNum))
        sNum = sNum.replace(', ', ' ')
        sNum = sNum.replace('[[', '(')
        sNum = sNum.replace(']]', ']')
        sNum = sNum.replace('[', '(')
        sNum = sNum.replace(']', ')')
        return sNum

    def getCurrentChip(self):
        svgChips = self.objBrowser.find_element_by_xpath('//div[@class="arrow-slider__scrollable-content"]/*[local-name() = "svg" and contains(@class, "arrow-slider__element_selected")]')
        find = re.findall('chip-svg_rate-(\d+)', svgChips.get_attribute('class'))
        iValue = int(find[0])
        if iValue == 10:
            iValue = 20
        return str(float(iValue)/100)

    async def gameNoDisconnect(self):
        self.fastSearch()
        while self.bLogged:
            try:
                divTimer = self.objBrowser.find_element_by_xpath('//div[@class="round-timers round-timers_center-video"]/div[@class="timer-desktop"]/div[@class="timer-desktop__text"]')
                if divTimer is not None and int(divTimer.text) <= 6:
                    break
            except:
                pass
            await asyncio.sleep(0.5)
        if not self.bLogged:
            return
        if self.iCurSpin != 0:
            return
        self.iCurSpin = randint(self.MINSPIN, self.MAXSPIN)
        svgChips = self.objBrowser.find_elements_by_xpath('//div[@class="arrow-slider__scrollable-content"]/*[local-name() = "svg"]')
        sClassCurrentChip = None
        objMinChip = svgChips[0]
        for objChip in svgChips:
            if objChip.get_attribute('class').find('arrow-slider__element_selected') != -1:
                sClassCurrentChip = objChip.get_attribute('class').replace(' arrow-slider__element_selected', '')
                break
        async with self.chip_lock:
            objMinChip.click()
            iChoose = randint(1,3)
            objSvg1 = None
            objSvg2 = None
            if iChoose == 1:
                objSvg1 = self.objBrowser.find_element_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[@class="roulette-table-cell roulette-table-cell_side-red roulette-table-cell_group-fifty-fifty"]')
                objSvg2 = self.objBrowser.find_element_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[@class="roulette-table-cell roulette-table-cell_side-black roulette-table-cell_group-fifty-fifty"]')
            elif iChoose == 2:
                objSvg1 = self.objBrowser.find_element_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[@class="roulette-table-cell roulette-table-cell_side-odd roulette-table-cell_group-fifty-fifty"]')
                objSvg2 = self.objBrowser.find_element_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[@class="roulette-table-cell roulette-table-cell_side-even roulette-table-cell_group-fifty-fifty"]')
            elif iChoose == 3:
                objSvg1 = self.objBrowser.find_element_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[@class="roulette-table-cell roulette-table-cell_side-low roulette-table-cell_group-fifty-fifty"]')
                objSvg2 = self.objBrowser.find_element_by_xpath('//div[@class="roulette-game-area__row"]/div[@class="roulette-game-area__col roulette-game-area__col_middle"]/div[@class="roulette-game-area__main-digital-table"]/div[@class="with-size-wrapper"]/*[local-name() = "svg"]/*[local-name() = "g"]/*[@class="roulette-table-cell roulette-table-cell_side-high roulette-table-cell_group-fifty-fifty"]')
            if objSvg1 is not None and objSvg2 is not None:
                objSvg1.click()
                objSvg2.click()

            svgChips = self.objBrowser.find_elements_by_xpath('//div[@class="arrow-slider__scrollable-content"]/*[local-name() = "svg"]')
            for objChip in svgChips:
                if objChip.get_attribute('class') == sClassCurrentChip:
                    objChip.click()
                    break

    def getWinSize(self):
        return self.objBrowser.get_window_size()

    def getLastNumber(self, iCount):
        self.objDivHistoryLine = self.objBrowser.find_element_by_xpath('//div[@class="roulette-history-line"]/div[@class="history-item history-item_last"]')

        cmdHistory = self.objBrowser.find_element_by_xpath('//li[@data-automation-locator="button.extenededHistory"]')
        if not self.click(cmdHistory):
            return
        self.fastSearch()
        try:
            #print(self.objBrowser.find_element_by_xpath('//div[@class="game-modals"]/div[@class="modal-container modal-notification_desktop modal-notification_center-video modal-notification_desktop_win-notification modal-container_sprol"]'))
            while self.objBrowser.find_element_by_xpath('//div[@class="game-modals"]/div[@class="modal-container modal-notification_desktop modal-notification_center-video modal-notification_desktop_win-notification modal-container_sprol"]') is not None:
                time.sleep(3)
        except:
            pass
        divHistory = self.objBrowser.find_element_by_xpath('//div[@class="roulette-extended-history__items roulette-history-items"]')
        divLastNum = divHistory.find_element_by_xpath('.//div[@class="history-item history-item_last"]')
        self.divLastNum = self.objBrowser.find_element_by_xpath('//div[@class="roulette-history-line"]/div[@class="history-item history-item_last"]')
        self.objLog.debug('check div before initNum {}'.format(self.divLastNum.get_attribute('class')))
        aSpanNum = divHistory.find_elements_by_xpath('.//div[contains(@class, "history-item")]/div[contains(@class, "history-item__regular regular-item")]/span')

        # TODO check if number is changing
        if divLastNum.get_attribute('class').find('history-item_last') == -1:
            self.objLog.debug('change from last item retake numbers')
            divLastNum = divHistory.find_element_by_xpath('.//div[@class="history-item history-item_last"]')
            aSpanNum = divHistory.find_elements_by_xpath('.//div[contains(@class, "history-item")]/div[contains(@class, "history-item__regular regular-item")]/span')
        self.objLog.debug(divLastNum.get_attribute('class'))
        iNdx = 0
        asNum = []
        for sNum in aSpanNum:
            if sNum.text != '':
                try:
                    int(sNum.text)
                except:
                    continue
                asNum.append(sNum.text)
                iNdx += 1
                if iNdx >= iCount:
                    break
        self.objLog.debug(divLastNum.get_attribute('class'))
        #TODO check for exception so close all unknow windows
        divClose = self.objBrowser.find_element_by_xpath('//div[@class="close-button modal-close-button"]')
        self.click(divClose, self.closeAllWindows)
        #divClose.click()
        return reversed(asNum)

    def closeAllWindows(self):
        self.objLog.error('close lock window')
        objButt = self.objBrowser.find_element_by_xpath('//button[@class="modal-footer-btn modal-footer-btn_resolve modal-footer-btn_full"]')
        self.click(objButt)

    def getColorForNum(self, sNum):
        sColor = "#00FF00"
        if int(sNum) in self.aNumRed:
            sColor = "#FF0000"
        elif int(sNum) in self.aNumBlack:
            sColor = "#000000"
        return sColor

    def getNameCroupier(self):
        return self.objBrowser.find_element_by_xpath('//div[@class="header__dealer-name"]').text

    def checkLastNum(self):
        self.objLog.debug('check div after initNum {}'.format(self.divLastNum.get_attribute('class')))

    def stopUpdate(self):
        if self.tskUpdate is not None:
            self.tskUpdate.cancel()

    def startUpdate(self, function):
        self.tskUpdate = asyncio.create_task(self.update_loop(function))

    async def update_loop(self, function):
        while self.bLogged:
            if self.objDivHistoryLine is not None:
                while self.objDivHistoryLine.get_attribute('class') == 'history-item history-item_last' and self.bLogged:
                    await asyncio.sleep(1)
                if not self.bLogged:
                    break
                self.objDivHistoryLine = self.objBrowser.find_element_by_xpath('//div[@class="roulette-history-line"]/div[@class="history-item history-item_last"]')
                spanNum = self.objDivHistoryLine.find_element_by_xpath('.//div[contains(@class, "history-item__regular regular-item")]/span')
                sSaldo = self.objBrowser.find_element_by_xpath('//div[@class="balance__value "]/div[@class="fit-container"]/div[@class="fit-container__content"]').text
                if function is not None:
                    await function(spanNum.text, sSaldo.split(' ')[1])
                self.iCurSpin -= 1
                if self.iCurSpin == 0:
                    self.objLog.debug('game no disconnect')
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.gameNoDisconnect())
            else:
                await asyncio.sleep(1)

class GameHorse:
    aiHorseRoul = { 0: [1, 2, 3], 1: [0, 4, 2], 2: [0, 3, 1, 5], 3: [0, 2, 6], 4: [1, 7, 5], 5: [2, 4, 6, 8], 6: [3, 5, 9], 7: [4, 8, 10], 8: [5, 7, 9, 11], 
                    9: [6, 8, 12], 10: [7, 11, 13], 11: [8, 10, 12, 14], 12: [9, 11, 15], 13: [10, 14, 16], 14: [11, 13, 15, 17], 15: [12, 14, 18], 
                    16: [13, 17, 19], 17: [14, 16, 18, 20], 18: [15, 17, 21], 19: [16, 20, 22], 20: [17, 19, 21, 23], 21: [18, 20, 24], 22: [19, 23, 25], 
                    23: [20, 22, 24, 26], 24: [21, 23, 27], 25: [22, 26, 28], 26: [23, 25, 27, 29], 27: [24, 26, 30], 28: [25, 29, 31], 29: [26, 28, 30, 32], 
                    30: [27, 29, 33], 31: [28, 32, 34], 32: [29, 31, 33, 35], 33: [30, 32, 36], 34: [31, 35], 35: [32, 34, 36], 36: [33, 35]}

    @staticmethod
    def generateHorse(aiNum):
        aiRemove = [0] * len(aiNum)
        aiGame = []

        aiHorseGamed = []
        for iNdx, iNum in enumerate(aiNum):
            iNum = int(iNum)
            if aiRemove[iNdx] == 1:
                continue
            bFound = False
            for iHorse in GameHorse.aiHorseRoul[iNum]:
                if iHorse in aiHorseGamed:
                    continue
                for iNdx2, iNum2 in enumerate(aiNum):
                    iNum2 = int(iNum2)
                    if aiRemove[iNdx2] == 1:
                       continue
                    if iHorse == iNum2:
                        bFound = True
                        aiGame.append([iNum, iHorse])
                        aiHorseGamed.append(iNum)
                        aiHorseGamed.append(iHorse)
                        aiRemove[iNdx2] = 1
                        break
                if bFound:
                    break
            if not bFound:
                aiGame.append([iNum])
        return aiGame
