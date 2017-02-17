#!/bin/python
# -*- coding: utf-8

import os
import re
import time
import json
import urllib
import urllib2
import cookielib
import random

class MyRequest():
    cj = cookielib.LWPCookieJar()
    cookieSupport = urllib2.HTTPCookieProcessor(cj)
    opener = urllib2.build_opener(cookieSupport, urllib2.HTTPHandler)
    urllib2.install_opener(opener)

    def __init__(self):
        pass

    def post(self, url, data, timeout=10):
        request = urllib2.Request(url, data)
        request = self.addHeader(request)
        return urllib2.urlopen(request, timeout=timeout).read()

    def get(self, url, timeout=10):
        request = urllib2.Request(url)
        request = self.addHeader(request)
        return urllib2.urlopen(request, timeout=timeout).read()

    def addHeader(self, request):
        request.add_header('User-Agent', "Mozilla/5.0 (Windows NT 6.1; WOW64;")
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
        request.add_header('Cache-Control', 'no-cache')
        request.add_header('Accept', '*/*')
        request.add_header('Connection', 'Keep-Alive')
        return request

class WeixinLogin():
    def __init__(self): 
        self.domain = "https://login.weixin.qq.com"
        self.request = MyRequest()
        self.UUID = ''

    def wxNewLoginPage(self):
        data = {}
        data['appid'] = 'wx782c26e4c19acffb'
        data['redirect_uri'] = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage'
        data['fun'] = 'new'
        data['_'] = int(time.time())
        uri = "/jslogin?"
        url = "%s%s%s" % (self.domain, uri, urllib.urlencode(data))
        body = self.request.get(url)
        m = re.search('.*?uuid = \\"(.*?)\\"', body)
        self.UUID =  m.group(1)


    def getQRCode(self):
        url = "https://login.weixin.qq.com/qrcode/%s?t=webwx" % self.UUID
        body = self.request.get(url)
        QRcodeJpg = open("./%s.jpg" % self.UUID, "w")
        QRcodeJpg.write(body)
        QRcodeJpg.close()

    def genGetStatusUrl(self):
        data = {"uuid": self.UUID, "tip": "1", "_": int(time.time()), "r": random.random()}
        uri =  "/cgi-bin/mmwebwx-bin/login?"
        url = "%s%s%s" % (self.domain, uri, urllib.urlencode(data))
        return url

    def waitingScan(self):
        url = self.genGetStatusUrl()
        while True:
            try:
                body = self.request.get(url, 1)
                if body == "window.code=201;":  break #二维码被扫描
            except Exception, e:
                continue

    def getScanRet(self):
        url = self.genGetStatusUrl()
        while True:
            body = self.request.get(url)
            if body != "window.code=201;": break
        return body
    
    def getScanRetRedirectUrl(self, body):
        m = re.search('.*?window.redirect_uri=\\"(.*?)\\.*"', body)
        return m.group(1) if m else None

    def newLogin(self, url):
        url = "%s&fun=new" % url
        body = self.request.get(url)
        return body

    def getwxsidAndwxuin(self, body):
        m = re.search('.*?<skey>(.*?)</skey><wxsid>(.*?)</wxsid><wxuin>(.*?)</wxuin><pass_ticket>(.*?)</pass_ticket>.*', body)
        return  {"skey": m.group(1), "wxsid": m.group(2), "wxuin": m.group(3), "pass_ticket": m.group(4)} if m else None

    def login(self):
        self.wxNewLoginPage()
        self.getQRCode()
        print "下载二维码[%s.jpg],请扫描." % (self.UUID)
        self.waitingScan()
        print "扫描完成,请在手机确认登陆."
        body  = self.getScanRet()
        url = self.getScanRetRedirectUrl(body)
        print "开始登陆..."
        loginRetXml = self.newLogin(url)
        print "登陆成功:)"
        key = self.getwxsidAndwxuin(loginRetXml)
        return key


class Weixin():
    def __init__(self, key):
        self.domain = "https://wx.qq.com"
        self.request = MyRequest()
        self.skey = key['skey']
        self.wxsid = key['wxsid']
        self.wxuin = key['wxuin']
        self.pass_ticket = key['pass_ticket']
        self.deviceid = "e1615250492"
        self.syncKey = ''
        self.syncKeyList = []
        self.baseRequest = {
            'Uin': self.wxuin, 
            "Sid": self.wxsid, 
            "Skey": self.skey, 
            "DeviceID": self.deviceid
        }
        self.user = []
        self.seq = 0
        self.members = {}

    def winit(self):
        queryTuple = {"r": int(time.time())}
        query = urllib.urlencode(queryTuple)
        uri = "/cgi-bin/mmwebwx-bin/webwxinit?"
        url = "%s%s%s" % (self.domain, uri, query)
        data = json.dumps({'BaseRequest': self.baseRequest})
        body = self.request.post(url, data)
        self.__setSyncInfo(body)

    def __setSyncInfo(self, message):
        message = json.loads(message)
        self.syncKeyList = message['SyncKey']
        self.syncKey = '|'.join([str(keyVal['Key']) + '_' + \
                str(keyVal['Val']) for keyVal in self.syncKeyList['List']])
        self.user = message['User']
        self.members[self.user['UserName']] = self.user['NickName']
    
    def wxStatusNotify(self):
        url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxstatusnotify?lang=Zh_cn&pass_ticket=%s" % \
              self.pass_ticket
        data = {
            "BaseRequest": self.baseRequest,
            "Code": 3,
            "FromUserName": self.user['UserName'],
            "ToUserName": self.user['UserName'],
            "ClientMsgId": 1487289439163
        }
        self.request.post(url, json.dumps(data))

    def __changeSeq(self, body):
        self.seq = body['Seq']

    def __setMembers(self, body):
        for item in body['MemberList']:
            self.members[item['UserName']] = item['NickName']

    def wxGetConcat(self):
        uri = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?"
        queryDict = {}
        queryDict['pass_ticket'] = self.pass_ticket
        queryDict['r'] = int(time.time())
        queryDict['seq'] = 0
        queryDict['skey'] = self.skey
        url = "%s%s" % (uri, urllib.urlencode(queryDict))
        body = json.loads(self.request.get(url))
        self.__changeSeq(body)
        self.__setMembers(body)
    
    def webwxsync(self):
        uri = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync?"
        queryDict = {}
        queryDict['sid'] = self.wxsid
        queryDict['skey'] = self.skey
        queryDict['pass_ticket'] = self.pass_ticket
        queryString = urllib.urlencode(queryDict)
        url = "%s%s" % (uri, queryString)
        data = {
            "BaseRequest": self.baseRequest,
            "SyncKey": self.syncKeyList,
            "rr": ~int(time.time()) 
        }
        body  = json.loads(self.request.post(url, json.dumps(data)))
        self.syncKeyList = body['SyncKey']
        self.syncKey = '|'.join([str(item['Key']) + '_' + \
                    str(item['Val']) for item in self.syncKeyList['List']])
        for msg in body['AddMsgList']:
            print "from[%s]->to[%s], content[%s]" % (self.members[msg['FromUserName']], self.members[msg['ToUserName']], msg['Content'])
            if self.__isRedPacket(msg['Content']):
                self.__redPacketNotify(self.members[msg['FromUserName']])

    def __isRedPacket(self, content):
        m = re.search(u".*收到红包，请在手机上查看.*", content)
        return True if m else False

    def __redPacketNotify(self, f):
        os.system("notify-send --icon=gtk-info 红包提醒 '收到来自%s的红包'" % f)

    def poll(self):
        uri = "https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck?"
        queryDict = {}
        queryDict['r'] = int(time.time())
        queryDict['skey'] = self.skey
        queryDict['uin'] = self.wxuin 
        queryDict['sid'] = self.wxsid
        queryDict['deviceid'] = self.deviceid
        queryDict['_'] = int(time.time())
        while True:
            queryDict['synckey'] =  self.syncKey
            queryString = urllib.urlencode(queryDict)
            url = "%s%s" % (uri, queryString)
            try:
                body = self.request.get(url)
                if body == 'window.synccheck={retcode:"0",selector:"2"}':
                    self.webwxsync()
            except Exception,e:
                pass
            time.sleep(1)

    def run(self):
        self.winit()
        self.wxGetConcat()
        self.wxStatusNotify()
        weixin.poll()


if __name__ == '__main__':
    wxlogin = WeixinLogin()
    key = wxlogin.login()
    weixin = Weixin(key)
    weixin.run()
