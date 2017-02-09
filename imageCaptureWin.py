#coding:gbk
import requests
from bs4 import BeautifulSoup
import re
import urllib
import time
import os.path
import sys
reload(sys)
sys.setdefaultencoding("gbk")
import threading
import signal
import math
import time
from urlparse import urlparse
HTTP_HEADER = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
SEARCH_URL = ""
PWD=os.getcwd()
SITE = "https://www.goodfon.su"
SUFFIX = '.jpg'
TIME_OUT = 15
DOWNLOAD_COUNT = 0
THREAD_COUNT = 4
STOP = False
mutex = threading.Lock()

class WorkThread(threading.Thread):
    def __init__(self, imageUrls):
        threading.Thread.__init__(self, name = "WorkThread")
        self.__imageUrls = imageUrls
    def run(self):
        global STOP
        for imageUrl in self.__imageUrls:
            if STOP:
                return
            downloadImage(imageUrl)
def getOriginalImageUrl(url):
    page= requests.session().get(url, headers=HTTP_HEADER, timeout=TIME_OUT)
    content = page.content#.decode(Coding).encode('utf-8')
    contentSoup = BeautifulSoup(content, 'html.parser')
    contentA = contentSoup.find('a', {'itemprop':'contentUrl'})
    contentUrl = SITE + contentA.get('href')
    return getImageUrl(contentUrl)

def getImageUrl(url):
    page= requests.session().get(url, headers=HTTP_HEADER, timeout=TIME_OUT)
    content = page.content#.decode(Coding).encode('utf-8')
    contentSoup = BeautifulSoup(content, 'html.parser')
    contentA = contentSoup.find('a', {'id':'im'})
    contentUrl = contentA.get('href')
    return contentUrl

def getOriginalImageUrlFromBadfon(url):
    page= requests.session().get(url, headers=HTTP_HEADER, timeout=TIME_OUT)
    content = page.content#.decode(Coding).encode('utf-8')
    contentSoup = BeautifulSoup(content, 'html.parser')

    allResolutionA = contentSoup.find_all('a', {'target':'_blank'})
    contentUrl = ""
    for resolution in allResolutionA:
        if resolution.string is not None:
            contentUrl = resolution.get("href")
            if isHttpUrl(contentUrl) is not True:
                parseObject = urlparse(url)
                contentUrl = parseObject.scheme + "://" + parseObject.netloc + contentUrl
    return getImageUrl(contentUrl)

def downloadImage(url):
    global DOWNLOAD_COUNT
    fileName = os.path.basename(url)
    saveDir = os.path.join(PWD, "downloaded")
    if mutex.acquire():
        if not os.path.exists(saveDir):
            os.makedirs(saveDir)
        mutex.release()
    filePath = os.path.join(saveDir, fileName)
    if os.path.exists(filePath):
        print "图片本地已存在:" + url
        return
    print "下载图片:" + url
    photoResult = requests.get(url,stream=True)
    with open(filePath, 'wb') as fd:
        for chunk in photoResult.iter_content():
            if STOP:
                os.remove(filePath)
                break
            fd.write(chunk)
    if mutex.acquire():
        DOWNLOAD_COUNT +=1
        mutex.release()
def getPageImageUrls(page, totalCount):
    url = SEARCH_URL + "&page=%d" % page
    page= requests.session().get(url, headers=HTTP_HEADER, timeout=TIME_OUT)
    content = page.content#.decode(Coding).encode('utf-8')
    contentSoup = BeautifulSoup(content, 'html.parser')
    thumbnail = contentSoup.find_all('a',{'itemprop':'url'})
    global DOWNLOAD_COUNT
    global STOP
    if len(thumbnail) is 0:
        print url + ":没有找到任何结果"
        sys.exit()
    imageUrls = []
    count = 0
    for photo in thumbnail:
        path = photo.get('href')
        detailUrl = ""
        if STOP:
            return []
        if isHttpUrl(path):
            parseObject = urlparse(path)
            netloc = parseObject.netloc
            if netloc == "www.badfon.ru":
                detailUrl = path
        else:
            detailUrl = SITE + photo.get('href')
        if detailUrl == "":
            print "无法识别URL:" + path
            continue
        imageUrl = getOriginalImageUrlFromBadfon(detailUrl)
        imageUrls.append(imageUrl)
        count += 1
        if count == totalCount:
            break

    return imageUrls



def getPageInfo(url):
    page= requests.session().get(url, headers=HTTP_HEADER, timeout=TIME_OUT)
    content = page.content#.decode(Coding).encode('utf-8')
    contentSoup = BeautifulSoup(content, 'html.parser')
    pageInfoDiv = contentSoup.find('div',{'class':'pageinfo'})
    if not pageInfoDiv:
        return (0, 0)
    divs = pageInfoDiv.findAll('div');
    if len(divs) is 0:
        return (0, 0)
    page = int(divs[0].string)
    total = int(divs[1].string)
    return (page, total)

def isHttpUrl(url):
    return url.startswith("http");

def stopHandler(signum, frame):
    global STOP
    STOP= True
    print("等待工作完成后退出......")
if __name__ == '__main__':
    signal.signal(signal.SIGTERM, stopHandler)
    signal.signal(signal.SIGINT, stopHandler)
    keyword = raw_input("输入关键字:")
    SEARCH_URL = "http://www.goodfon.su/search/?q=" + keyword
    print "正在计算有多少图片......"
    (page, total) = getPageInfo(SEARCH_URL)
    if total is 0:
        print "这个关键字没有图片"
        sys.exit()
    print "总共有%d页，%d张图片" % (page, total)
    onePageCount = math.ceil(total / float(page))
    totalNeed = raw_input("输入需要下载多少张(直接回车代表下载所有):")
    if not totalNeed:
        totalNeed = total
    try:
        totalNeed = int(totalNeed)
        totalNeed = totalNeed if totalNeed > total else totalNeed
    except Exception,e:
        print "输入了错误的数字"
    needPage = int(math.ceil(totalNeed / float(onePageCount)))
    pages = [i + 1 for i in range(needPage)]

    for pageIndex in range(needPage):
        if STOP:
            break
        fetchCount = int(onePageCount if pageIndex < needPage - 1 else totalNeed - pageIndex * onePageCount)
        imageUrls = getPageImageUrls(pageIndex + 1, fetchCount)
#        imageUrls = [u'https://img4.badfon.ru/original/1920x1200/7/6c/kang-ye-bin-actress-asian.jpg', u'https://img4.goodfon.su/original/2560x1600/2/98/cara-delevigne-woman-babe-girl-gorgeous-model.jpg', u'https://img4.goodfon.su/original/3000x2014/b/ff/alexandra-daddario-woman-babe-girl-gorgeous-actress-american.jpg', u'https://img4.badfon.ru/original/1920x1200/2/fa/girl-girl-armed-gun-girl.jpg']
        threadImageUrls = []
        #for j in range(fetchCount):
        #    imageUrls.append('https://img4.badfon.ru/original/1920x1200/7/6c/kang-ye-bin-actress-asian.jpg')
        for i in range(len(imageUrls)):
            index = i % 4
            tempImageUrls = threadImageUrls[index] if len(threadImageUrls) > index else None
            if tempImageUrls is not None:
                tempImageUrls.append(imageUrls[i])
            else :
                tempImageUrls = [imageUrls[i]]
                threadImageUrls.append(tempImageUrls)

        threads = []
        for threadImage in threadImageUrls:
            thread = WorkThread(threadImage)
            thread.setDaemon(True)
            thread.start()
            threads.append(thread)
        while True:
            alive = False
            for thread in threads:
                alive = alive or thread.isAlive()
                if thread.isAlive() is not True:
                    thread.join()
            if not alive:
                break
            time.sleep(0.5)
print("下载了%d张高清无码大图" % DOWNLOAD_COUNT)
raw_input("按回车键结束....")
