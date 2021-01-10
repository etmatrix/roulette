# -*- coding: utf-8 -*-

import asyncio
from telethon.sync import TelegramClient, errors, functions, types, events
from datetime import datetime

from config import Config

class Telegram():
    objConfig = None
    objTele = None
    functionHandler = None
    iID = -1
    tskDownload = None

    def __init__(self):
        self.objConfig = Config()

        self.objTele = TelegramClient(self.objConfig.getSession(), self.objConfig.getApi(1), self.objConfig.getApi(2), loop=asyncio.get_event_loop())
        self.objTele.add_event_handler(self.event_handler)

    async def send_message(self, sDestination, sMessage):
        try:
            await self.objTele.send_message(sDestination, sMessage)
        except errors.FloodWaitError:
            await asyncio.sleep(1)

    async def get_messages(self, sDestination, iCount=100):
        try:
            return await self.objTele.get_messages(sDestination, iCount)
        except errors.FloodWaitError:
            await asyncio.sleep(1)
            return []

    @events.register(events.Raw(types.UpdateShortMessage))
    async def event_handler(self, event):
        if self.functionHandler is not None:
            await self.functionHandler(event)

    def add_event_handler(self, function):
        self.functionHandler = function

    def del_event_handler(self, function):
        self.functionHandler = None

    async def connect(self):
        if self.objTele.is_connected():
            self.iID = await self.objTele.get_peer_id('me')
            return True
        else:
            return self.isAuthorized()

    async def disconnect(self):
        self.objTele.remove_event_handler(self.event_handler)
        if self.objTele.is_connected():
            await self.objTele.disconnect()

    def isAuthorized(self):
        try:
            self.objTele.connect()
        except ConnectionError as err:
            return False, str(err)
        return self.objTele.is_user_authorized(), ''

    async def makeSession(self, sPhone):
        await self.objTele.connect()
        bAuthorized = await self.objTele.is_user_authorized()
        if not bAuthorized:
            await self.objTele.send_code_request(sPhone)

    async def makeSession2(self, sPhone, sCode, sPassword):
        bTwoStep = False
        try:
            await self.objTele.sign_in(code=sCode)
        except errors.SessionPasswordNeededError:
            bTwoStep = True
        except errors.PhoneCodeInvalidError:
            return False, 1, ''
        except Exception as ex:
            return False, 0, str(ex)
        if bTwoStep:
            try:
                await self.objTele.sign_in(phone=sPhone, password=sPassword)
            except errors.PasswordHashInvalidError:
                return False, 2, ''
            except Exception as ex:
                return False, 0, str(ex)
        self.objTele.session.save()
        return True, 0, ''
    
    async def getNotify(self, sUser):
        return await self.objTele(functions.account.GetNotifySettingsRequest(peer=sUser))

    async def setNotify(self, sUser, bMute=True):
        date = datetime(2038, 1, 19, 3, 14, 7) if bMute else datetime.fromtimestamp(0)
        await self.objTele(functions.account.UpdateNotifySettingsRequest(peer=sUser, settings=types.InputPeerNotifySettings(show_previews=False, mute_until=date)))

    async def unblock(self, sUser):
        await self.objTele(functions.contacts.UnblockRequest(id=sUser))

    async def getName(self, sUser):
        objEnt = await self.objTele.get_entity(sUser)
        return sUser if objEnt.first_name == '' else objEnt.first_name

    async def getMessages(self, iID, iCount):
        objEnt = await self.objTele.get_entity(types.PeerUser(iID))
        return await self.objTele.get_messages(entity=objEnt, limit=iCount)

    async def getPinnedMsg(self, iChannelID):
        objEnt = await self.objTele.get_entity(types.PeerChannel(iChannelID))
        objChInfo = await self.objTele(functions.channels.GetFullChannelRequest(objEnt))
        iMsgId = objChInfo.full_chat.pinned_msg_id
        if iMsgId is not None:
            aobjMsg = await self.objTele(functions.messages.GetHistoryRequest(objEnt, limit=1, offset_date=None, offset_id=iMsgId + 1, max_id=0, min_id=0, add_offset=0, hash=0))
            if aobjMsg is not None:
                return aobjMsg.messages[0].message
            else:
                return None
        else:
            return None

    async def downloadFile(self, iChannelID, callback, sDestination):
        objEnt = await self.objTele.get_entity(types.PeerChannel(iChannelID))
        objChInfo = await self.objTele(functions.channels.GetFullChannelRequest(objEnt))
        iMsgId = objChInfo.full_chat.pinned_msg_id
        if iMsgId is not None:
            aobjMsg = await self.objTele(functions.messages.GetHistoryRequest(objEnt, limit=1, offset_date=None, offset_id=iMsgId + 1, max_id=0, min_id=0, add_offset=0, hash=0))
            if aobjMsg is not None and aobjMsg.messages[0].media is not None:
                if aobjMsg.messages[0].media.document.mime_type == 'application/x-ms-dos-executable' and self.objConfig.isWindows():
                    self.tskDownload = asyncio.create_task(self.objTele.download_media(message=aobjMsg.messages[0], progress_callback=callback, file=sDestination))

    def abortDownload(self):
        if self.tskDownload is not None:
            self.tskDownload.cancel()

    async def waitDownload(self):
        if self.tskDownload is not None:
            await asyncio.wait({self.tskDownload})
            if self.tskDownload.cancelled():
                return False
            else:
                #print(self.tskDownload.result())
                return True
        return False
