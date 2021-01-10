#!/usr/bin/env python3

import sys, os, signal

sys.path.append(os.path.dirname(sys.argv[0]) + '/.python/lib/python3.7/site-packages/')

import subprocess
import asyncio
from telegram import Telegram
from config import Config
from snai import Snai
from playtech import Playtech
from methods import Method1, Method2
from telethon.errors.rpcerrorlist import YouBlockedUserError

from PySide2 import QtCore, QtGui, QtWidgets, QtMultimedia
from asyncqt import QEventLoop, asyncSlot, asyncClose
import log
import logging
import traceback

VERSION = '1.1.6'

class Main(QtWidgets.QMainWindow):
    signalTele = QtCore.Signal()
    signalLogin = QtCore.Signal(Playtech)
    signalRoulette = QtCore.Signal(Playtech, int, object)
    objTelegram = None
    objConfig = None
    objPlaytech = None
    objMethod = None
    objLog = None
    abBotEnabled = None
    asArg = None
    bExitNoMsg = False

    def __init__(self, *args, **kwargs):
        super(Main, self).__init__()

        self.asArg = args[0]
        self.asArg.pop(0)

        self.statusBar().showMessage('In attesa di connessione ed autorizzazione Telegram')

        exitAct = QtWidgets.QAction('&Uscita', self)
        exitAct.setShortcut(QtGui.QKeySequence.Quit)
        exitAct.setStatusTip('Uscita applicazione')
        exitAct.triggered.connect(self.close)

        settingAct = QtWidgets.QAction('&Impostazioni', self)
        settingAct.setStatusTip('Impostazioni')
        settingAct.triggered.connect(self.settings)

        extractAct = QtWidgets.QAction('&Extract', self)
        extractAct.triggered.connect(self.extract)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(settingAct)
        fileMenu.addAction(extractAct)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAct)

        self.objConfig = Config()
        self.objConfig.loadConfig()

        if len(self.asArg) > 0:
            self.objConfig.asListBot = self.asArg

        log.initLog(self.objConfig.getLogFile())
        objLog = logging.getLogger()

        objLog.debug('Starting...')

        self.objTelegram = Telegram()
        bAuth, sErr = self.objTelegram.isAuthorized()
        if not bAuth:
            if sErr != '':
                QtWidgets.QMessageBox.critical(self, 'Errore', 'Errore: {}'.format(sErr), QtWidgets.QMessageBox.Ok)
            pnlCenter = TelegramPhone(self.objTelegram)
            self.statusBar().showMessage('In attesa autorizzazione Telegram')
            self.setCentralWidget(pnlCenter)
        else:
            self.doLogin()

        self.resize(400, 400)
        self.center()
        self.setWindowTitle('Roulette ET v{}'.format(VERSION))

        self.signalLogin.connect(self.doListRoulette)
        self.signalRoulette.connect(self.doRoulette)
        self.signalTele.connect(self.doLogin)

    @asyncClose
    async def closeEvent(self, event):
        if self.bExitNoMsg:
            event.accept()
            return
        msgExit = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, 'Chiusura', 'Stai uscendo, questo comporta anche la chiusura del browser\nVuoi continuare?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, self)
        msgExit.setDefaultButton(QtWidgets.QMessageBox.No)
        msgExit.setEscapeButton(QtWidgets.QMessageBox.No)
        reply = await self.dialog_async_exec(msgExit)
        if reply == QtWidgets.QMessageBox.Yes:
            if self.objPlaytech is not None:
                self.objPlaytech.disconnect()
            if self.objTelegram is not None:
                await self.objTelegram.disconnect()
                await asyncio.sleep(1)
            event.accept()
        else:
            event.ignore()

    def updateWindowsFlags(self, bChangeVisible=False):
        iFlag = self.windowFlags()
        if self.objConfig.getAlwaysOnTop():
            iFlag |= QtCore.Qt.WindowStaysOnTopHint
        else:
            iFlag &= ~(QtCore.Qt.WindowStaysOnTopHint)
        if bChangeVisible:
            self.setVisible(False)
        self.setWindowFlags(iFlag)
        if bChangeVisible:
            self.setVisible(True)

    def center(self):
        self.setGeometry(QtWidgets.QStyle.alignedRect(QtCore.Qt.LeftToRight, QtCore.Qt.AlignCenter, self.size(), QtGui.QGuiApplication.primaryScreen().availableGeometry(), ), )        

    def moveAngle(self, iWidth):
        objRect = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(0, 30, iWidth-10, objRect.height() - 50)

    @asyncSlot()
    async def doLogin(self):
        self.abBotEnabled = await self.verifyMember()
        #if self.objConfig.getAutoUpdate() and await self.checkUpdate():
        #    self.pdDown = QtWidgets.QProgressDialog('Scaricamento in corso nuova versione del software...', 'Annulla', 0, 100, self)
        #    self.pdDown.setWindowModality(QtCore.Qt.WindowModal)
        #    self.pdDown.canceled.connect(self.objTelegram.abortDownload)
        #    self.pdDown.setWindowTitle('Aggiornamento')
        #    self.pdDown.forceShow()
        #    sExe = os.path.join(self.objConfig.sConfDir, 'newversion.exe')
        #    await self.objTelegram.downloadFile(self.objConfig.ROULETTE_ID, self.updateProgress, sExe)
        #    if await self.objTelegram.waitDownload():
        #        await self.objTelegram.disconnect()
        #        await asyncio.sleep(0.5)
        #        subprocess.Popen([sExe, '/silent'], creationflags=0)
        #        self.bExitNoMsg = True
        #        QtCore.QTimer.singleShot(0, lambda: self.close())
        #    else:
        #        self.pdDown.cancel()

        pnlCenter = Login(True in self.abBotEnabled)
        self.statusBar().showMessage(self.tr('In attesa di login SNAI'))
        self.setCentralWidget(pnlCenter)

    def updateProgress(self, current, total):
        self.pdDown.setValue(int((current / total) * 100))
        #print('Downloaded', current, 'out of', total, 'bytes: {:.2%}'.format(current / total))

    async def verifyMember(self):
        abEnabled = [False] * len(self.objConfig.asListBot)
        await self.objTelegram.connect()
        iNdx = 0
        for sBot in self.objConfig.asListBot:
            try:
                await self.objTelegram.setNotify(sBot)
                await self.objTelegram.send_message(sBot, 'reset')
            except YouBlockedUserError:
                sName = await self.objTelegram.getName(sBot)
                dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, self.tr('Errore'), self.tr('Hai bloccato il bot {} e non posso parlarci!\nQuindi questo metodo non sarà usabile.'.format(sName)), QtWidgets.QMessageBox.Ok, self)
                await self.dialog_async_exec(dialog)
                await self.objTelegram.unblock(sBot)
                continue
            except:
                continue
            # TODO verify last messages without sleep
            await asyncio.sleep(1)
            aobjMsg = await self.objTelegram.get_messages(sBot, 2)
            if len(aobjMsg) == 2 and aobjMsg[1].message == 'reset' and aobjMsg[0].message == 'RESET EFFETTUATO':
                abEnabled[iNdx] = True
            iNdx += 1

        return abEnabled

    async def checkUpdate(self):
        #sMsg = await self.objTelegram.getPinnedMsg(self.objConfig.ROULETTE_ID)
        #if sMsg is not None and sMsg.startswith('Version'):
        #    sVersion = sMsg.split('\n')[0].split(' ')[1]
        #    if sVersion != VERSION:
        #        return True
        return False

    @asyncSlot()
    async def doListRoulette(self, objPlaytech):
        self.objPlaytech = objPlaytech
        pnlCenter = ListRoulette(objPlaytech)
        await pnlCenter.initMethods(self.objTelegram, self.abBotEnabled)
        self.setCentralWidget(pnlCenter)
        self.statusBar().showMessage(self.tr('In attesa di scelta roulette e metodo'))

    @asyncSlot()
    async def doRoulette(self, objPlaytech, iMethod, asBotName):
        self.objPlaytech = objPlaytech
        if iMethod == 0:
            self.objMethod = Method1()
        elif iMethod == 1:
            self.objMethod = Method2()
        pnlCenter = Roulette(objPlaytech, self.objTelegram, self.objConfig.asListBot[iMethod], self.objMethod, asBotName, iMethod)
        self.setCentralWidget(pnlCenter)
        self.statusBar().showMessage(self.tr('Roulette ') + objPlaytech.getRouletteName())

        objRect = QtGui.QGuiApplication.primaryScreen().availableGeometry()
        objRectWin = self.objPlaytech.getWinSize()

        iWidth = objRect.width() - int(objRectWin['width'])
        self.objPlaytech.moveWindow(iWidth, 0)
        QtCore.QTimer.singleShot(0, lambda: self.moveAngle(iWidth))

        loop = asyncio.get_event_loop()
        loop.create_task(pnlCenter.initNum())
        QtCore.QTimer.singleShot(100, lambda: self.updateWindowsFlags(True))

    def dialog_async_exec(self, dialog):
        future = asyncio.Future()
        dialog.finished.connect(lambda r: future.set_result(r))
        dialog.open()
        return future

    def settings(self):
        dlg = Settings(self)
        if dlg.exec_():
            aSet = dlg.getResult()
            self.objConfig.setFontSize(int(aSet[0]))
            self.objConfig.setOrderAlpha(aSet[1])
            self.objConfig.setTimeForBet(aSet[2])
            self.objConfig.setAutoupdate(aSet[3])
            self.objConfig.setAlwaysOnTop(aSet[4])
            self.centralWidget().updateConfig()
            if isinstance(self.centralWidget(), Roulette):
                self.updateWindowsFlags(True)

    def extract(self):
        asNum = self.objPlaytech.getLastNumber(600) # 512 is max, with 600 take all
        dlg = Extract(self)
        dlg.text(','.join(asNum))
        dlg.exec_()

class Extract(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super(Extract, self).__init__(*args, **kwargs)

        self.setWindowTitle('Extract numbers')

        self.txtNum = QtWidgets.QTextEdit()
        self.txtNum.setReadOnly(True)

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.txtNum)
        layout.addWidget(buttonBox)
        self.setLayout(layout)
        self.resize(300, 100)
        
    def text(self, sText):
        self.txtNum.append(sText)

class Settings(QtWidgets.QDialog):
    FONT_SIZES = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 24]
    objConfig = None

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)

        self.objConfig = Config()

        self.setWindowTitle('Impostazioni')

        self.cmbFontSize = QtWidgets.QComboBox()
        self.cmbFontSize.addItems([str(s) for s in self.FONT_SIZES])
        self.cmbFontSize.setCurrentText(str(self.objConfig.getFontSize()))
        self.cmbFontSize.setToolTip('Imposta la dimensione del testo nella videata della chat con il bot')

        self.chkOrderAlpha = QtWidgets.QCheckBox(self.tr("Ordinamento alfabetico"))
        self.chkOrderAlpha.setChecked(self.objConfig.getOrderAlpha())
        self.chkOrderAlpha.setToolTip('Ordina le roulette in ordine alfabetico invece dell\'ordinamento deciso da SNAI')

        self.txtTimeForBet = QtWidgets.QSpinBox()
        self.txtTimeForBet.setValue(self.objConfig.getTimeForBet())
        self.txtTimeForBet.setMinimum(0)
        self.txtTimeForBet.setMaximum(10)
        self.txtTimeForBet.setAlignment(QtCore.Qt.AlignRight)
        self.txtTimeForBet.setToolTip('E\' il tempo massimo in secondi che viene dato al software per puntare sulla roulette\npiù è alto e più punterà lentamente e viceversa\nverrà comunque tenuto conto del tempo rimanente')

        self.chkAutoUpdate = QtWidgets.QCheckBox(self.tr("Aggiornamenti automatici"))
        self.chkAutoUpdate.setChecked(self.objConfig.getAutoUpdate())
        self.chkAutoUpdate.setToolTip('Abilita gli aggiornamenti automatici del software scaricandoli dal canale ufficiale Roulette')

        self.chkAlwaysOnTop = QtWidgets.QCheckBox(self.tr("Finestra sempre in cima"))
        self.chkAlwaysOnTop.setChecked(self.objConfig.getAlwaysOnTop())
        self.chkAlwaysOnTop.setToolTip('Mantiene la finestra del software in cima a tutte le altre finestre')

        pnlFont = QtWidgets.QFormLayout()
        pnlFont.addRow(self.tr("Dimensione testo"), self.cmbFontSize)
        pnlFont.addRow(self.tr("Tempo per puntare"), self.txtTimeForBet)
        pnlFont.addRow(self.chkOrderAlpha)
        pnlFont.addRow(self.chkAutoUpdate)
        pnlFont.addRow(self.chkAlwaysOnTop)

        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(pnlFont)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        self.resize(300, 100)

    def getResult(self):
        return self.cmbFontSize.currentText(), self.chkOrderAlpha.isChecked(), self.txtTimeForBet.value(), self.chkAutoUpdate.isChecked(), self.chkAlwaysOnTop.isChecked()

class CentralPanel(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

    def updateConfig(self):
        pass

class TelegramPhone(CentralPanel):
    def __init__(self, objTele):
        super().__init__()

        self.objTelegram = objTele
        self.pnlFields = QtWidgets.QGroupBox(self.tr("Telegram"))
        self.lblInfo = QtWidgets.QLabel(self.tr("Ancora non sono stato autorizzato ad accedere\nal tuo account Telegram.\nMi serve che tu inserisca il tuo numero di telefono\ne richiedi il codice con il tasto 'Richiedi codice'.\n"
                                                "Fatto questo Telegram ti invierà un codice nella\ntua app inseriscilo dentro il campo 'Codice' ed\neventualmente metti la password usata per\nl'autenticazione a 2 fattori se non sai\n"
                                                "cos'è probabilmente non l'hai abilitata perchè di\nbase è disabilita, in questo caso lascia pure il\ncampo vuoto e clicca il tasto 'Autorizza'\n\n"))
        self.txtPhone = QtWidgets.QLineEdit()
        self.txtPhone.setText('+39')
        self.txtPhone.returnPressed.connect(self.requestCode)

        self.txtCode = QtWidgets.QLineEdit()
        self.txtCode.setDisabled(True)
        self.txtCode.returnPressed.connect(self.authorize)

        self.txtPassword = QtWidgets.QLineEdit()
        self.txtPassword.setDisabled(True)
        self.txtPassword.setEchoMode(QtWidgets.QLineEdit.Password)
        self.txtPassword.returnPressed.connect(self.authorize)

        self.cmdRequest = QtWidgets.QPushButton(self.tr("Richiedi codice"))
        self.cmdRequest.setStyleSheet(
            "background-color: rgb(0, 209, 255);\n"
            "color: rgb(255, 255, 255);\n"
            "background-color: rgb(0, 0, 127);"
        )
        self.cmdRequest.clicked.connect(self.requestCode)
        self.cmdAuthorize = QtWidgets.QPushButton(self.tr("Autorizza"))
        self.cmdAuthorize.setStyleSheet(
            "background-color: rgb(0, 209, 255);\n"
            "color: rgb(255, 255, 255);\n"
            "background-color: rgb(0, 0, 127);"
        )
        self.cmdAuthorize.setDisabled(True)
        self.cmdAuthorize.clicked.connect(self.authorize)

        font = self.font()
        font.setPointSize(9)
        self.setFont(font)

        pnlMain = QtWidgets.QVBoxLayout(self)
        pnlMain.addWidget(self.pnlFields)

        pnlTele = QtWidgets.QFormLayout()

        pnlTele.addRow(self.lblInfo, )
        pnlTele.addRow(self.tr("Numero telefono:"), self.txtPhone)
        pnlTele.addRow(self.tr("Codice:"), self.txtCode)
        pnlTele.addRow(self.tr("Password:"), self.txtPassword)

        pnlMain = QtWidgets.QGridLayout()
        pnlMain.addLayout(pnlTele, 0, 0, 1, 2)
        pnlMain.addWidget(self.cmdRequest, 1, 0)
        pnlMain.addWidget(self.cmdAuthorize, 1, 1)

        self.pnlFields.setLayout(pnlMain)

    @asyncSlot()
    async def requestCode(self):
        self.txtCode.setDisabled(False)
        self.txtPassword.setDisabled(False)
        self.cmdAuthorize.setDisabled(False)
        self.txtCode.setFocus()
        if len(self.txtPhone.text()) > 8:
            await self.objTelegram.makeSession(self.txtPhone.text())
        else:
            QtWidgets.QMessageBox.critical(self, 'Errore', 'Il tuo numero sembra incompleto controllalo!', QtWidgets.QMessageBox.Ok)

    @asyncSlot()
    async def authorize(self):
        bLogin, iStatus, sErrorMsg = await self.objTelegram.makeSession2(self.txtPhone.text(), self.txtCode.text(), self.txtPassword.text())
        if not bLogin:
            if iStatus == 1:
                QtWidgets.QMessageBox.critical(self, 'Errore', "Codice errato!", QtWidgets.QMessageBox.Ok)
            elif iStatus == 2:
                QtWidgets.QMessageBox.critical(self, 'Errore', "Password errata!", QtWidgets.QMessageBox.Ok)
            else:
                QtWidgets.QMessageBox.critical(self, 'Errore', "Ci sono stati problemi con l'autorizzazione del client!\n{}".format(sErrorMsg), QtWidgets.QMessageBox.Ok)
        else:
            self.setVisible(False)
            self.parent().signalTele.emit()

class Login(CentralPanel):
    objSnai = None
    bValidMember = False
    objConfig = None
    objLog = None

    def __init__(self, bValidMember):
        super().__init__()
        self.bValidMember = bValidMember

        self.objConfig = Config()
        self.objLog = logging.getLogger()

        self.groupbox = QtWidgets.QGroupBox(self.tr("SNAI"))
        self.txtUser = QtWidgets.QLineEdit()
        self.txtUser.setText(self.objConfig.getUsername())

        self.txtPass = QtWidgets.QLineEdit()
        self.txtPass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.txtPass.returnPressed.connect(self.login)
        self.txtPass.setText(self.objConfig.getPassword())

        self.chkSaveUser = QtWidgets.QCheckBox(self.tr("Salva utente"))
        if self.txtUser.text() != '':
            self.chkSaveUser.setChecked(True)
        self.chkSavePass = QtWidgets.QCheckBox(self.tr("Salva password"))
        if self.txtPass.text() != '':
            self.chkSavePass.setChecked(True)

        self.cmdLogin = QtWidgets.QPushButton(self.tr("Login"))
        self.cmdLogin.setStyleSheet(
            ":enabled {background-color: rgb(0, 209, 255);\n"
            "color: rgb(255, 255, 255);\n"
            "background-color: rgb(0, 0, 127);}"
        )
        self.cmdLogin.clicked.connect(self.login)

        font = self.font()
        font.setPointSize(9)
        self.setFont(font)

        pnlMain = QtWidgets.QVBoxLayout(self)
        pnlMain.addWidget(self.groupbox)

        pnlLogin = QtWidgets.QFormLayout()

        pnlLogin.addRow(self.tr("Username:"), self.txtUser)
        pnlLogin.addRow(self.tr("Password:"), self.txtPass)
        pnlLogin.addRow(self.chkSaveUser, self.chkSavePass)

        pnlMain = QtWidgets.QVBoxLayout()
        pnlMain.addLayout(pnlLogin)
        pnlMain.addWidget(self.cmdLogin, alignment=QtCore.Qt.AlignHCenter)
        pnlMain.addStretch()

        self.groupbox.setLayout(pnlMain)

    def showEvent(self, event):
        super().showEvent(event)
        if self.txtUser.text() != '':
            self.txtPass.setFocus()
        if not self.bValidMember:
            self.cmdLogin.setDisabled(True)
            QtWidgets.QMessageBox.information(self, 'Abbonamento scaduto', 'Non hai nessun metodo roulette abilitato!', QtWidgets.QMessageBox.Ok)

    def login(self):
        if self.txtUser.text() == '':
            QtWidgets.QMessageBox.critical(self, 'Errore', "Campo username vuoto!", QtWidgets.QMessageBox.Ok)
            return
        if self.txtPass.text() == '':
            QtWidgets.QMessageBox.critical(self, 'Errore', "Campo password vuoto!", QtWidgets.QMessageBox.Ok)
            return
        if self.objSnai is None:
            try:
                self.objSnai = Snai()
            except Exception as ex:
                self.objLog.error('Exception login {}'.format(str(ex)))
                self.objLog.error(traceback.format_exc())
                QtWidgets.QMessageBox.critical(self, 'Errore', 'Ci sono stati problemi con il login {}'.format(str(ex)), QtWidgets.QMessageBox.Ok)
                return
            except:
                QtWidgets.QMessageBox.critical(self, 'Errore', 'Ci sono stati problemi con il login', QtWidgets.QMessageBox.Ok)
                self.objLog.error('Exception login')
                self.objLog.error(traceback.format_exc())
                return
        if not self.objSnai.login(self.txtUser.text(), self.txtPass.text()):
            QtWidgets.QMessageBox.critical(self, 'Errore', "Password od utente errato!", QtWidgets.QMessageBox.Ok)
        else:
            if self.chkSavePass.isChecked():
                self.objConfig.setPassword(self.txtPass.text())
            else:
                self.objConfig.setPassword('')
            if self.chkSaveUser.isChecked():
                self.objConfig.setUsername(self.txtUser.text())
            else:
                self.objConfig.setUsername('')
            self.parent().signalLogin.emit(self.objSnai)

class ListRoulette(CentralPanel):
    objPlaytech = None
    aRoulette = None
    objConfig = None

    def __init__(self, objPlaytech):
        super().__init__()

        self.objPlaytech = objPlaytech
        self.objConfig = Config()

        self.txtCashNow = QtWidgets.QLineEdit()
        self.txtCashNow.setReadOnly(True)
        self.txtCashNow.setAlignment(QtCore.Qt.AlignRight)

        self.txtCashGame = QtWidgets.QLineEdit()
        self.txtCashGame.setAlignment(QtCore.Qt.AlignRight)

        self.lstRoulette = QtWidgets.QListWidget()
        self.lstRoulette.setSizeAdjustPolicy(QtWidgets.QListWidget.AdjustToContents)
        #self.lstRoulette.itemDoubleClicked.connect(self.lstChoose)
        self.lstRoulette.setSortingEnabled(self.objConfig.getOrderAlpha())

        self.cmbMethods = QtWidgets.QComboBox()

        self.cmdGame = QtWidgets.QPushButton(self.tr("Avvia"))
        self.cmdGame.setStyleSheet(
            "background-color: rgb(0, 209, 255);\n"
            "color: rgb(255, 255, 255);\n"
            "background-color: rgb(0, 0, 127);"
        )
        self.cmdGame.clicked.connect(self.runRoulette)

        font = self.font()
        font.setPointSize(9)
        self.setFont(font)

        pnlCash = QtWidgets.QFormLayout()

        pnlCash.addRow(self.tr("Cassa attuale €"), self.txtCashNow)
        pnlCash.addRow(self.tr("Cassa da giocare €"), self.txtCashGame)
        pnlCash.addRow(self.tr("Metodi roulette"), self.cmbMethods)

        pnlMain = QtWidgets.QVBoxLayout(self)
        pnlMain.addLayout(pnlCash)
        pnlMain.addWidget(self.lstRoulette)
        pnlMain.addWidget(self.cmdGame, alignment=QtCore.Qt.AlignHCenter)

    async def initMethods(self, objTelegram, abBotEnabled):
        if self.objPlaytech is not None:
            self.aRoulette = self.objPlaytech.getRoulettes()
            for sRoulette in self.aRoulette:
                self.lstRoulette.addItem(sRoulette)
            sLastRoulette = self.objConfig.getLastRoulette()
            for iNdx in range(0, self.lstRoulette.count()):
                if self.lstRoulette.item(iNdx).text() == sLastRoulette:
                    self.lstRoulette.setCurrentRow(iNdx)
                    break
            if self.lstRoulette.currentRow() == -1 and self.lstRoulette.count() > 0:
                self.lstRoulette.setCurrentRow(0)
            sCash = self.objPlaytech.getCash()
            self.txtCashNow.setText(sCash)
            self.txtCashGame.setText(str(round(float(sCash.replace('.', '').replace(',', '.'))/5, 2)).replace('.', ','))

        iCur = int(self.objConfig.getLastMethod())
        iNdx = 0
        for sBot in self.objConfig.asListBot:
            sName = await objTelegram.getName(sBot)        
            self.cmbMethods.addItem(sName)
            self.cmbMethods.model().item(iNdx).setEnabled(abBotEnabled[iNdx])
            iNdx += 1
        if iCur > self.cmbMethods.count() - 1:
            iCur = self.cmbMethods.count() - 1
        if self.cmbMethods.model().item(iCur).isEnabled():
            self.cmbMethods.setCurrentIndex(iCur)
        else:
            for iNdx in range(0, self.cmbMethods.count()):
                if self.cmbMethods.model().item(iNdx).isEnabled():
                    self.cmbMethods.setCurrentIndex(iNdx)
                    break

    def lstChoose(self, qmodelindex):
        self.runRoulette()

    def runRoulette(self):
        sCashGame = self.txtCashGame.text().replace('.', '').replace(',', '.')
        if sCashGame.strip() == '':
            QtWidgets.QMessageBox.critical(self, self.tr('Credito errato'), self.tr('Bisogna specificare un credito d\'entrata'), QtWidgets.QMessageBox.Ok)
            return
        if float(sCashGame) > float(self.txtCashNow.text().replace('.', '').replace(',', '.')):
            QtWidgets.QMessageBox.critical(self, self.tr('Credito insufficiente'), self.tr("Purtroppo non posso fare miracoli non riesco ad avviare una\nroulette con più soldi di quelli che hai!\nMa chi può dirlo se dopo questa giocata ci posso riuscire..."), QtWidgets.QMessageBox.Ok)
            return
        if float(sCashGame) < 5.0:
            QtWidgets.QMessageBox.critical(self, self.tr('Credito troppo basso'), self.tr('Credito troppo basso per poter giocare'), QtWidgets.QMessageBox.Ok)
            return
        item = self.lstRoulette.currentItem()
        if item is not None:
            sRoulette = item.text()
            reply = QtWidgets.QMessageBox.question(self, 'Conferma cassa', 'Vuoi entrare nella roulette {}\ncon la cassa di {} €?'.format(sRoulette, sCashGame), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.No:
                return
            self.objConfig.setLastRoulette(sRoulette)
            self.objConfig.setLastMethod(self.cmbMethods.currentIndex())
            self.objPlaytech.runRoulette(self.aRoulette[sRoulette], sCashGame)
            asBotName = []
            for iNdx in range(self.cmbMethods.count()):
                if self.cmbMethods.model().item(iNdx).isEnabled():
                    asBotName.append(self.cmbMethods.itemText(iNdx))
            self.parent().signalRoulette.emit(self.objPlaytech, self.cmbMethods.currentIndex(), asBotName)
            
    def updateConfig(self):
        self.lstRoulette.setSortingEnabled(self.objConfig.getOrderAlpha())
        if self.lstRoulette.isSortingEnabled():
            self.lstRoulette.sortItems()

class Roulette(CentralPanel):
    objPlaytech = None
    objTelegram = None
    iFilterMsg = 0
    sBotName = None
    objMethod = None
    objLog = None
    asNumGame = None
    objConfig = None
    bIgnoreSound = False
    bAlreadySound = False
    bAutoGame = False
    tskAutoGame = None
    iLastFichesAG = 1
    iCountFiches = 5
    sNameCroupier = None
    iCountSpin = 0

    def __init__(self, objPlaytech, objTelegram, sBotName, objMethod, asBotName, iMethod):
        super().__init__()

        self.objPlaytech = objPlaytech
        self.objTelegram = objTelegram
        self.sBotName = sBotName
        self.objMethod = objMethod
        self.objLog = logging.getLogger()
        self.objConfig = Config()

        self.txtCashNow = QtWidgets.QLineEdit()
        self.txtCashNow.setReadOnly(True)
        self.txtCashNow.setAlignment(QtCore.Qt.AlignRight)

        bAddMethods = False
        if len(asBotName) > 1:
            self.cmbMethods = QtWidgets.QComboBox()
            bAddMethods = True
            for sName in asBotName:
                self.cmbMethods.addItem(sName) 
            self.cmbMethods.setCurrentIndex(iMethod)
            self.cmbMethods.currentTextChanged.connect(self.change_method)

        self.txtChat = QtWidgets.QTextEdit()
        self.txtChat.setReadOnly(True)

        self.cmdGame1 = QtWidgets.QPushButton(self.tr("Gioca pieni"))
        self.cmdGame1.clicked.connect(self.game1)

        if self.objTelegram.iID in self.objConfig.USERAUTOBOT:
            self.cmdGame2 = QtWidgets.QPushButton(self.tr("Autogame"))
            self.bAutoGame = True
        else:
            self.cmdGame2 = QtWidgets.QPushButton(self.tr("Gioca cavalli"))
        self.cmdGame2.clicked.connect(self.game2)
        #self.cmdGame2.setDisabled(True)

        self.updateConfig()

        pnlCash = QtWidgets.QFormLayout()
        pnlCash.addRow(self.tr("Cassa attuale €"), self.txtCashNow)
        if bAddMethods:
            pnlCash.addRow(self.tr("Metodi roulette"), self.cmbMethods)

        pnlMain = QtWidgets.QGridLayout(self)
        pnlMain.addLayout(pnlCash, 0, 0, 1, 2)
        pnlMain.addWidget(self.txtChat, 2, 0, 1, 2)
        pnlMain.addWidget(self.cmdGame1, 3, 0)
        pnlMain.addWidget(self.cmdGame2, 3, 1)

    async def initNum(self):
        if self.objPlaytech is not None and self.objTelegram is not None:
            self.sNameCroupier = self.objPlaytech.getNameCroupier()
            objEntity = await self.objTelegram.objTele.get_entity(self.sBotName)
            self.iFilterMsg = objEntity.id
            self.bIgnoreSound = True
            self.objTelegram.add_event_handler(self.telegram_recv)

            self.objLog.debug('Init num')
            aiNum = self.objPlaytech.getLastNumber(self.objMethod.EXTRACT_COUNT)
            iCount = 0
            for iNum in aiNum:
                self.insertNum(iNum)
                self.objLog.debug(iNum)
                await self.objTelegram.send_message(self.sBotName, iNum)
                iCount += 1
                if iCount > 38:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(0.1)
            self.objPlaytech.checkLastNum()
            if self.txtChat.textCursor().hasSelection():
                self.txtChat.textCursor().clearSelection()
            self.txtChat.moveCursor(QtGui.QTextCursor.End)
            self.txtChat.ensureCursorVisible()
            self.bIgnoreSound = False
            self.objMethod.resetInit()
            # start_update must be after getLastNumber
            self.objPlaytech.startUpdate(self.updateNum)

    async def updateNum(self, iNum, sSaldo):
        if self.txtChat.textCursor().hasSelection():
            self.txtChat.textCursor().clearSelection()
        self.txtChat.moveCursor(QtGui.QTextCursor.End)

        if self.sNameCroupier != self.objPlaytech.getNameCroupier():
            self.iCountSpin = 0
            self.sNameCroupier = self.objPlaytech.getNameCroupier()
            self.txtChat.append('<p style="text-align: center; margin:0">Cambio croupier {}</p>'.format(self.sNameCroupier))
            self.txtChat.setAlignment(QtCore.Qt.AlignCenter)

        self.iCountSpin += 1
        self.insertNum(iNum)
        self.txtChat.ensureCursorVisible()
        self.txtCashNow.setText(sSaldo)
        self.objMethod.newNum(iNum)
        bSound, sWav = self.objMethod.isPlayAlert()
        if bSound:
            QtMultimedia.QSound.play(sWav)
        await self.objTelegram.send_message(self.sBotName, iNum)

    async def telegram_recv(self, event):
        if self.iFilterMsg == event.user_id:
            sMsg, asNumGame, bAlighRigth = self.objMethod.send_message(event.message)
            if asNumGame is not None:
                self.asNumGame = asNumGame
            if self.txtChat.textCursor().hasSelection():
                self.txtChat.textCursor().clearSelection()
            self.txtChat.moveCursor(QtGui.QTextCursor.End)
            if self.objMethod.isWin():
                self.changeColorPrevBlock(self.objMethod.getWinColor())

            self.txtChat.append('<p style="text-align: {}; margin:0">{}</p>'.format(('right' if bAlighRigth else 'left'), sMsg.replace('\n','<br>')))
            self.txtChat.setAlignment(QtCore.Qt.AlignLeft if not bAlighRigth else QtCore.Qt.AlignRight)
            self.txtChat.ensureCursorVisible()
            if self.objMethod.isGameAutomatic():
                await self.gameAuto(self.objMethod.getFichesValue())
            bSound, sWav = self.objMethod.isPlayAlert()
            if bSound and not self.bIgnoreSound:
                QtMultimedia.QSound.play(sWav)
            if self.objMethod.isToForward() and not self.bIgnoreSound:
                self.txtChat.append('<p style="text-align: left; margin:0">Il croupier {} è presente da {} boules</p>'.format(self.sNameCroupier, self.iCountSpin))
                self.txtChat.setAlignment(QtCore.Qt.AlignLeft)
                self.txtChat.ensureCursorVisible()
                asyncio.create_task(self.forwardToChat())

    async def forwardToChat(self):
        if self.objTelegram.iID == self.objConfig.USERFORWARD:
            await asyncio.sleep(3)
            asMsg = []
            aobjMsg = await self.objTelegram.getMessages(self.iFilterMsg, 6)
            for objMsg in aobjMsg:
                asMsg.append(objMsg.message)
            asMsg = reversed(asMsg)
            await self.objTelegram.send_message(self.objConfig.FORWARD_CHANNEL, '{}'.format(self.objConfig.getLastRoulette()))
            for sMsg in asMsg:
                await self.objTelegram.send_message(self.objConfig.FORWARD_CHANNEL, sMsg)
            await self.objTelegram.send_message(self.objConfig.FORWARD_CHANNEL, 'Croupier {} che ha già fatto {} boules'.format(self.sNameCroupier, self.iCountSpin))

    # TODO when last number win don't appear oro argento and paracadute so no color for last block
    def changeColorPrevBlock(self, sColor):
        objDoc = self.txtChat.document()
        objBlock = objDoc.lastBlock()
        objCursor = QtGui.QTextCursor(objBlock)
        objCharFormat = objBlock.charFormat()
        objCharFormat.setForeground(QtGui.QColor(sColor))
        objFont = QtGui.QFont()
        objFont.setPointSize(self.objConfig.getFontSize()+2)
        objFont.setBold(True)
        objCharFormat.setFont(objFont);
        objCursor.setPosition(objBlock.position())
        objCursor.setPosition(objBlock.position() + objBlock.length() - 1, QtGui.QTextCursor.KeepAnchor)
        objCursor.setCharFormat(objCharFormat)
        objCursor.clearSelection()

    def insertNum(self, sNum):
        self.txtChat.append('<p style="text-align: right; margin:0"><font color="{}">{}</font></p>'.format(self.objPlaytech.getColorForNum(sNum), sNum))
        self.txtChat.setAlignment(QtCore.Qt.AlignRight)

    @asyncSlot()
    async def game1(self):
        await self.game(False)

    @asyncSlot()
    async def game2(self):
        if self.bAutoGame:
            if self.tskAutoGame is not None:
                self.tskAutoGame.cancel()
                self.cmdGame2.setText('Autogame')
                self.tskAutoGame = None
            else:
                self.tskAutoGame = asyncio.create_task(self.autoGame())
        else:
            await self.game(True)

    async def autoGame(self):
        self.cmdGame2.setText('Stop')
        # TODO understand because I must start from 5
        #iCount = 5
        while True:
            bRet = await self.objPlaytech.waitCountDown(True)
            if bRet[0] and self.asNumGame is not None:
                if self.objMethod.isWin():
                    if self.iLastFichesAG > 1:
                        self.iLastFichesAG -= 1
                    self.iCountFiches = 4
                else:
                    self.iCountFiches -= 1
                    if self.iCountFiches == 0:
                        self.iLastFichesAG += 1
                        self.iCountFiches = 4
                await self.objPlaytech.game(self.asNumGame, self.iLastFichesAG, self.objConfig.getTimeForBet())
                bRet = True
                while bRet:
                    bRet, ignore = await self.objPlaytech.waitCountDown(False)
                    await asyncio.sleep(0.5)
            await asyncio.sleep(1)

    async def gameAuto(self, sFichesValue):
        #self.objPlaytech.selectFiches(sFichesValue)
        #await self.objPlaytech.game(self.asNumGame, 1, self.objConfig.getTimeForBet())
        print('game auto {}'.format(sFichesValue))

    async def game(self, bHorse=False):
        if self.asNumGame is None:
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, self.tr('Errore'), self.tr('Ancora non ci sono numeri da giocare!'), QtWidgets.QMessageBox.Ok, self)
            await self.dialog_async_exec(dialog)
            return
        sChip = self.objPlaytech.getCurrentChip()

        if bHorse:
            sGame = self.objPlaytech.getHorse(self.asNumGame)
        else:
            sGame = ' '.join(self.asNumGame)

        font = QtGui.QFont()
        font.setPointSize(self.objConfig.getFontSize())

        dialog = QtWidgets.QInputDialog(self)
        dialog.setLabelText('Quante fiches da {} € vuoi puntare sui seguenti {}: {}?\nSe non vuoi proseguire clicca su Annulla.'.format(sChip, 'numeri' if not bHorse else 'cavalli',sGame))
        dialog.setWindowTitle('Numero di fiches')
        dialog.setIntValue(1)
        dialog.setIntMinimum(1)
        dialog.setFont(font)
        dialog.setInputMode(QtWidgets.QInputDialog.IntInput)
        dialog.setTextEchoMode(QtWidgets.QLineEdit.Normal)

        result = await self.dialog_async_exec(dialog)
        if not result:
            return
        iNumChip = dialog.intValue()

        bRet = False
        if not bHorse:
            bRet = await self.objPlaytech.game(self.asNumGame, iNumChip, self.objConfig.getTimeForBet())
        else:
            bRet = await self.objPlaytech.gameHorse(self.asNumGame, iNumChip, self.objConfig.getTimeForBet())
        if not bRet:
            dialog = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, self.tr('Errore'), self.tr('Bisogna giocare mentre è attivo il conto alla rovescia e prima che finisca!'), QtWidgets.QMessageBox.Ok, self)
            await self.dialog_async_exec(dialog)

    def dialog_async_exec(self, dialog):
        future = asyncio.Future()
        dialog.finished.connect(lambda r: future.set_result(r))
        dialog.open()
        return future

    def updateConfig(self):
        self.txtChat.setStyleSheet(
            "background-color: rgb(0, 120, 177);\n"
            "color: rgb(255, 255, 255);\n"
            "font: {}pt 'Sans';".format(self.objConfig.getFontSize())
        )
        self.cmdGame1.setStyleSheet(
            "color: rgb(255, 255, 255);\n"
            "background-color: rgb(0, 0, 127);\n"
            "font: {}pt;".format(self.objConfig.getFontSize())
        )
        self.cmdGame2.setStyleSheet(
            "color: rgb(255, 255, 255);\n"
            "background-color: rgb(0, 0, 127);\n"
            "font: {}pt;".format(self.objConfig.getFontSize())
        )

    @asyncSlot()
    async def change_method(self, value):
        iMethod = self.cmbMethods.currentIndex()
        if iMethod == 0:
            self.objMethod = Method1()
        elif iMethod == 1:
            self.objMethod = Method2()
        self.sBotName = self.objConfig.asListBot[iMethod]
        self.txtChat.append('<p style="text-align: center; margin:0">Cambio metodo</p>')
        self.txtChat.setAlignment(QtCore.Qt.AlignCenter)
        self.objPlaytech.stopUpdate()
        self.objTelegram.del_event_handler(self.telegram_recv)
        await self.objTelegram.send_message(self.sBotName, 'reset')
        await self.initNum()

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    objMain = Main(sys.argv)
    objMain.show()

    with loop:
        sys.exit(loop.run_forever())

if __name__ == '__main__':
    main()
