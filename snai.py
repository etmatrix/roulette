# -*- coding: utf-8 -*-

import time
#import asyncio
from playtech import Playtech
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException
from selenium.webdriver.common.action_chains import ActionChains
from random import randint
import logging

class Snai(Playtech):
    URLBASE = 'https://www.snai.it/casino/live'
    objDivHistoryLine = None
    sLastRoulette = None
    objLog = None

    def __init__(self):
        super().__init__()
        self.iCurSpin = randint(self.MINSPIN, self.MAXSPIN)
        self.objLog = logging.getLogger()

    def login(self, sUser, sPass):
        self.get(self.URLBASE)
        #time.sleep(1)
        self.fastSearch()
        try:
            cmdAccept = self.objBrowser.find_element_by_xpath('//button[@class="btn-primary accept-btn"]')
            cmdAccept.click()
        except NoSuchElementException:
            pass
        finally:
            self.normalSearch()

        self.objBrowser.minimize_window()
        try:
            cmdAccedi = self.objBrowser.find_element_by_id('accedi-button')
            cmdAccedi.click()
        except:
            return
        txtUser = self.objBrowser.find_element_by_id('edit-name')
        txtPass = self.objBrowser.find_element_by_id('edit-pass')
        txtUser.send_keys(sUser)
        txtPass.send_keys(sPass)
        cmdAccedi = self.objBrowser.find_element_by_id('edit-submit--2')
        cmdAccedi.click()
        self.fastSearch()
        try:
            self.objBrowser.find_element_by_id('saldo_user')
            self.bLogged = True
            return True
        except NoSuchElementException:
            return False
        finally:
            self.normalSearch()

    def getCash(self):
        return self.objBrowser.find_element_by_id('saldo_user').text.split(' ')[0]

    def getRoulettes(self):
        self.fastSearch()
        self.objBrowser.maximize_window()
        try:
            divClose = self.objBrowser.find_element_by_xpath('//div[@class="dy-lb-close"]')
            if divClose is not None:
                divClose.click()
        except:
            pass
        cmdRoulette = self.objBrowser.find_element_by_xpath('//div[@class="textIconCasino roulette"]')
        if cmdRoulette is not None:
            if not self.click(cmdRoulette):
                self.objLog.error('Click button div[@class="textIconCasino roulette"] fail!')
                return
        else:
            self.objLog.error('Button roulette missing! xpath search //div[@class="textIconCasino roulette"]')
            return
        # TODO improve wait
        time.sleep(1) # wait javascript end filter

        aRoomRoulette = []
        while True:
            aRoomRoulette = self.objBrowser.find_elements_by_xpath('.//div[@class="roomCasinoLive ng-scope"]')
            if len(aRoomRoulette) == 0:
                self.objLog.warning('No roulette found with xpath .//div[@class="roomCasinoLive ng-scope"] try to refresh page')
                self.objBrowser.refresh();
            else:
                break
            time.sleep(1)

        asRoulette = {}
        for roulette in aRoomRoulette:
            divOverLay = roulette.find_element_by_xpath('.//div[@class="overlay"]')
            if divOverLay is not None:
                divStatus = divOverLay.find_element_by_xpath('.//div[1]')
                if divStatus.get_attribute('class').find('firstColumnInactive') == -1:
                    divRoom = divOverLay.find_element_by_xpath('.//div[@class="secondColumn"]/div[@class="roomName ng-binding cool-link"]')
                    asRoulette[divRoom.text] = roulette
            else:
                self.objLog.error('I can\'t find div overlay xpath search .//div[@class="overlay"]')
        self.objBrowser.minimize_window()
        self.normalSearch()
        return asRoulette

    def getRouletteName(self): return self.sLastRoulette

    def runRoulette(self, objRoulette, sSaldo):
        self.objBrowser.maximize_window()
        self.fastSearch()
        try:
            divClose = objRoulette.find_element_by_xpath('//div[@class="dy-lb-close"]')
            if divClose is not None:
                divClose.click()
        except:
            pass
        self.normalSearch()
        divOverLay = objRoulette.find_element_by_xpath('.//div[@class="overlay"]')
        divStatus = divOverLay.find_element_by_xpath('.//div[1]')
        if divStatus.get_attribute('class').find('firstColumnInactive') == -1:
            self.sLastRoulette = divOverLay.find_element_by_xpath('.//div[@class="secondColumn"]/div[@class="roomName ng-binding cool-link"]').text
            self.objBrowser.execute_script("arguments[0].scrollIntoView();", objRoulette)
            divButton = objRoulette.find_element_by_xpath('.//div[@class="overlay"]/div[@class="firstColumn ng-scope"]/div[@class="playButton shine"]')
            hover = ActionChains(self.objBrowser).move_to_element(divButton)
            hover.perform()
            if not self.click(divButton):
                self.objLog.error('div[@class="playButton shine"] fail click')
                return

        self.objBrowser.minimize_window()
        self.objBrowser.switch_to.window(self.objBrowser.window_handles[1])

        # on slow pc best while true
        # TODO put a timeout
        # class of messagebox div class=modal-container modal-confirm_desktop modal-confirm_desktop_with-icon
        while True:
            try:
                divMoney = self.objBrowser.find_element_by_xpath('//div[@class="bring-money"]')
                if divMoney is not None:
                    break
                self.objLog.error('Wait div[@class="bring-money"]')
                time.sleep(0.5)
            except:
                pass
        if self.sLastRoulette == 'Speed Roulette':
            self.MINSPIN = 13
            self.MAXSPIN = 18
        '''
        toggle toggle_animate toggle_checked
        
        welcome-modal
        '''
        '''
        1283.761021789
        1283.867325798
        1284.398147957
        1284.426582655
        1285.922807187
        1285.99618652
        1286.896604853
        1287.558475904
        '''
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))
        # random button with discount not always exist
        try:
            cmdButtonRandom = self.objBrowser.find_element_by_xpath('//button[@class="modal-footer-btn modal-footer-btn_resolve modal-footer-btn_full"]')
            if cmdButtonRandom is not None and cmdButtonRandom.text != 'Conferma':
                self.click(cmdButtonRandom)
        except:
            pass
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))
        self.fastSearch()
        try:
            divWelcome = self.objBrowser.find_element_by_xpath('//div[@class="welcome-footer__close-button"]')
            if divWelcome is not None:
                self.objLog.debug('found //div[@class="welcome-footer__close-button"]')
                divToggle = self.objBrowser.find_element_by_xpath('//div[@class="toggle toggle_animate"]')
                if divToggle is not None:
                    self.objLog.debug('found div[@class="toggle toggle_animate"]')
                    divToggle.click()
                self.click(divWelcome)
        except:
            pass
        self.normalSearch()
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))

        txtSaldo = divMoney.find_element_by_xpath('.//div[@class="modal-content"]/div[@class="modal-input"]/input')
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))
        txtSaldo.send_keys(sSaldo)
        cmdConf = divMoney.find_element_by_xpath('.//div[@class="modal-footer"]/button')
        self.randomDelay()
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))
        self.click(cmdConf)
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))
        self.randomDelay()
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))
        cmdConf = self.objBrowser.find_element_by_xpath('//button[@class="modal-footer-btn modal-footer-btn_resolve modal-footer-btn_full"]')
        time.sleep(0.6)
        self.click(cmdConf)
        #print(time.clock_gettime(time.CLOCK_MONOTONIC))

    def disconnect(self):
        self.bLogged = False
        #time.sleep(1)
        super().disconnect()
        self.fastSearch()
        try:
            link = self.objBrowser.find_element_by_id('logout')
            link.click()
        except NoSuchElementException:
            pass
        except NoSuchWindowException:
            pass
        self.objBrowser.quit()
