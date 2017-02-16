#!/bin/python
# -*- coding: utf-8

import re
import time
import json
import urllib
import urllib2
import cookielib
import urlparse

class MyRequest():
    def __init__(self):
        cj = cookielib.LWPCookieJar()
        cookieSupport = urllib2.HTTPCookieProcessor(cj)
        opener = urllib2.build_opener(cookieSupport, urllib2.HTTPHandler)
        urllib2.install_opener(opener)

    def post(self, url, data, timeout=5):
        request = urllib2.Request(url, data)
        request = self.addHeader(request)
        return urllib2.urlopen(request, timeout=timeout).read()

    def get(self, url, timeout=5):
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
        print url
        body = self.request.get(url)
        QRcodeJpg = open("./%s.jpg" % UUID, "w")
        QRcodeJpg.write(body)
        QRcodeJpg.close()

    def genGetStatusUrl(self, UUID):
        data = {"uuid": UUID, "tip": "1", "_": "1388975894359"}
        uri =  "/cgi-bin/mmwebwx-bin/login?"
        url = "%s%s%s" % (self.domain, uri, urllib.urlencode(data))
        return url

    def waitingScan(self, UUID):
        url = self.genGetStatusUrl(UUID)
        print url 
        while True:
            try:
                body = self.request.get(url, 1)
                if body == "window.code=201;":  # 二维码被扫描
                    break
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
        m = re.search('.*?<skey>(.*?)</skey><wxsid>(.*?)</wxsid><wxuin>(.*?)</wxuin>.*', body)
        return  {"skey": m.group(1), "wxsid": m.group(2), "wxuin": m.group(3)} if m else None


class Weixin():
    def __init__(self, key):
        self.domain = "https://wx.qq.com"
        self.request = MyRequest()
        self.skey = key['skey']
        self.wxsid = key['wxsid']
        self.wxuin = key['wxuin']

    def syncMsg(self):
        queryTuple = {'r': int(time.time())}
        query = urllib.urlencode(queryTuple)
        uri = "/cgi-bin/mmwebwx-bin/webwxinit?"
        url = "%s%s%s" % (self.domain, uri, query)
        print url

        data = json.dumps({'BaseRequest': 
                    {'Uin': self.wxuin, 
                     "Sid": self.wxsid, 
                     "Skey": "", 
                     "DeviceID": "e1615250492"
                    }
                })
        print data
        body = self.request.post(url, data)
        print body


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
    weixin.syncMsg()

main()
