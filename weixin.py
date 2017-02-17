#!/bin/python
# -*- coding: utf-8

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

    def getUUID(self):
        data = {}
        data['appid'] = 'wx782c26e4c19acffb'
        data['redirect_uri'] = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage'
        data['fun'] = 'new'
        data['lang'] = 'zh_CN'
        data['_'] = '1388994062250'
        uri = "/jslogin?"
        url = "%s%s%s" % (self.domain, uri, urllib.urlencode(data))
        body = self.request.get(url)
        m = re.search('.*?uuid = \\"(.*?)\\"', body)
        return m.group(1)

    def getQRCode(self, UUID):
        url = "https://login.weixin.qq.com/qrcode/%s?t=webwx" % UUID
        body = self.request.get(url)
        QRcodeJpg = open("./%s.jpg" % UUID, "w")
        QRcodeJpg.write(body)
        QRcodeJpg.close()

    def genGetStatusUrl(self, UUID):
        data = {"uuid": UUID, "tip": "1", "_": int(time.time()), "r": random.random()}
        uri =  "/cgi-bin/mmwebwx-bin/login?"
        url = "%s%s%s" % (self.domain, uri, urllib.urlencode(data))
        return url

    def waitingScan(self, UUID):
        url = self.genGetStatusUrl(UUID)
        while True:
            try:
                body = self.request.get(url, 1)
                if body == "window.code=201;":  break #二维码被扫描
            except Exception, e:
                continue

    def getScanRet(self, UUID):
        url = self.genGetStatusUrl(UUID)
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
        self.baseRequest = {'Uin': self.wxuin, 
                            "Sid": self.wxsid, 
                            "Skey": self.skey, 
                            "DeviceID": self.deviceid
                           }
        self.user = []

    def winit(self):
        queryTuple = {"r": int(time.time())}
        query = urllib.urlencode(queryTuple)
        uri = "/cgi-bin/mmwebwx-bin/webwxinit?"
        url = "%s%s%s" % (self.domain, uri, query)
        data = json.dumps({'BaseRequest': self.baseRequest})
        body = self.request.post(url, data)
        self.__setSyncInfo(body)

    def __setSyncInfo(self, message):
        syncKey = ""
        message = json.loads(message)
        for item in message['SyncKey']['List']:
            syncKey += "%s_%s|" % (item['Key'], item['Val'])
        
        self.syncKey = syncKey.rstrip('|')
        self.syncKeyList = message['SyncKey']
        self.user = message['User']
    
    def wxStatusNotify(self):
        url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxstatusnotify?lang=Zh_cn&pass_ticket=%s" % \
              self.pass_ticket
        data = {"BaseRequest": self.baseRequest,
                "Code": 3,
                "FromUserName": self.user['UserName'],
                "ToUserName": self.user['UserName'],
                "ClientMsgId": 1487289439163}
        self.request.post(url, json.dumps(data))
    
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
        

    def poll(self):
        uri = "https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck?"
        queryDict = {}
        queryDict['r'] = int(time.time())
        queryDict['skey'] = self.skey
        queryDict['uin'] = self.wxuin 
        queryDict['sid'] = self.wxsid
        queryDict['deviceid'] = self.deviceid
        queryDict['synckey'] =  self.syncKey
        queryDict['_'] = int(time.time())
        queryString = urllib.urlencode(queryDict)
        url = "%s%s" % (uri, queryString)
        while True:
            body = self.request.get(url)
            if body == 'window.synccheck={retcode:"0",selector:"2"}':
                self.webwxsync()
            time.sleep(2)


def main():
    login = WeixinLogin()
    UUID = login.getUUID()
    login.getQRCode(UUID)
    print "下载二维码[%s.jpg],请扫描." % (UUID)
    login.waitingScan(UUID)
    print "扫描完成,请在手机确认登陆."
    body  = login.getScanRet(UUID)
    url = login.getScanRetRedirectUrl(body)
    print "开始登陆..."
    loginRetXml = login.newLogin(url)
    print "登陆成功:)"
    key = login.getwxsidAndwxuin(loginRetXml)
    weixin = Weixin(key)
    message = weixin.winit()
    weixin.wxStatusNotify()
    weixin.poll()

main()
