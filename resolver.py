# -*- coding: utf-8 -*-
import sys
import xbmc
from service import LANG, addonname, encode, decode, stations_url, codec
from service import PY3, jsonrequest, log, notify
from bs4 import BeautifulSoup

base_url = "https://api.mujrozhlas.cz/"
merid = xbmc.getRegion('meridiem')

def okdialog(message):
    if PY3:
        return Dialog().ok(heading=addonname, message = message)
    return Dialog().ok(heading=addonname, line1 = message)

def getNumbers(txt):
    newstr = ''.join((ch if ch in '0123456789' else ' ') for ch in txt)
    return [int(i) for i in newstr.split()]

# The date obtained must be independent of the date format set by the user !
def parsedate(_short, _long):
    ix = _short.find(' ')
    lnums = getNumbers(_long)
    snums = getNumbers(_short[:ix])
    year = max(lnums)
    day = min(lnums)
    snums.remove(day)
    month = min(snums)
    return '%i-%02d-%02d' % (year, month, day)

# The time stamp obtained must be independent of the time format set by the user !
def parsetime(txt):
    h, m = getNumbers(txt)
    if merid.__len__() > 2:
        AM, PM = merid.split('/')
        if txt.endswith(AM) and h == 12:
            h = 0
        elif txt.endswith(PM) and h < 12:
            h += 12
    return '%02d:%02d' % (h, m)

def getepisodes(showid, offset, limit = 1):
    url = base_url+'shows/%s/episodes?page[limit]=%i&page[offset]=%i' % (showid, limit, offset)
    return jsonrequest(url)

def getcount(showid):
    ep = getepisodes(showid, 0)
    if ep:
        if 'meta' in ep and 'count' in ep['meta']:
            return ep['meta']['count']
    return 0

def getep(showid, since):
    count = getcount(showid)
    if count:
        res = []
        resb = []
#        resc = []
        limit = 30
        since = since[:-3]
        sinceb = since[:-3]
        for i in range(0, count, limit):
            epdata = getepisodes(showid, i, limit)
            if 'data' in epdata:
                data = epdata['data']
                for itm in data:
                    _since = itm['attributes']['since'][:-12]
                    if _since == since:
                        res.append(itm)
                    if _since[:-3] == sinceb:
                        resb.append(itm)
#                    if _since[:-6] == sincec:
#                        resc.append(itm)
        if res:
            log("res = " + repr(res))
            return res
        if resb:
            log("resb =" + repr(resb))
            return resb
#        if resc:
#            log("resc =" + repr(resc))
#            return resc
        return ''

    else:
        log("Count is none or 0")

def getshows(statid, limit, offset):
    url = base_url+'stations/%s/shows?page[limit]=%i&page[offset]=%i' % (statid, limit, offset)
    return jsonrequest(url)

def findshowid(statid, title):
    count = 0
    first = getshows(statid, 1, 0)
    if first is not None:
        if 'meta' in first and 'count' in first['meta']:
            count = first['meta']['count']
    if count:
        limit = 30
        for i in range(0, count, limit):
            showdata = getshows(statid, limit, i)
            if showdata is not None and 'data' in showdata:
                data = showdata['data']
                for itm in data:
                    if 'attributes' in itm and 'title' in itm['attributes'] and 'id' in itm:
                        _title = itm['attributes']['title']
                        if _title == title:
                            return itm['id']
    return ''

def selal(als):
    if 'ondemand' in [al['linkType'] for al in als]:
        als2 = [al for al in als if al['linkType'] == 'ondemand' and al['variant'] == 'hls']
        if len(als2):
            return als[0]
    if 'download' in [al['linkType'] for al in als]:
        als2 = [al for al in als if al['linkType']=='download' and al['variant'] == ('aac', 'mp3')[codec]]
        if len(als2):
            return als[0]
        als2 = [al for al in als if al['linkType']=='download']
        if len(als2):
            return als[0]

def get_audio(kind):
    chann_dict = {}
    jsondata = jsonrequest(stations_url)
    if jsondata and 'data' in jsondata:
        stations = jsondata['data']
        for i in stations:
            if 'type' in i and 'attributes' in i and 'id' in i and i['type'] == 'station':
                if 'shortTitle' in i['attributes']:
                    chann_dict[i['attributes']['shortTitle']]=i['id']
    else:
        notify(LANG(30405))
        return
    if sys.listitem.getPath() != xbmc.getInfoLabel('ListItem.FolderPath'):
        okdialog(LANG(30402))
        return
    label = xbmc.getInfoLabel('ListItem.Label')
    log("label = "+repr(label))
    plot = xbmc.getInfoLabel('ListItem.Plot')
    icon = xbmc.getInfoLabel('ListItem.Icon')
    channel = xbmc.getInfoLabel('ListItem.ChannelName')
    statid = None
    if decode(channel) in chann_dict:
        statid = decode(chann_dict[decode(channel)])
    if statid is not None:
        day = parsedate(xbmc.getInfoLabel('ListItem.Date'), xbmc.getInfoLabel('ListItem.StartDate'))
        starttime = parsetime(xbmc.getInfoLabel('ListItem.StartTime'))
        since = '%sT%s' % (day, starttime)
        log("since = " + repr(since))
        url = base_url + 'schedule-day?filter[day]=' + day + '&filter[stations.id]=' + statid
        data = jsonrequest(url)
        if data is not None and 'links' in data:
            links = data['links']
            if 'next' in links and links['next'] == None:
                if 'data' in data:
                    data = data['data']
                    ep1a = [i for i in data if i['attributes']['since'][:-9] == since and encode(i['attributes']['mirroredShow']['title']) == label]
                    ep2a = [i for i in data if i['attributes']['since'][:-12] == since[:-3] and encode(i['attributes']['mirroredShow']['title']) == label]
                    ep3a = [i for i in data if i['attributes']['since'][:-15] == since[:-6] and encode(i['attributes']['mirroredShow']['title']) == label]
                    ep1b = [i for i in data if i['attributes']['since'][:-9] == since and encode(i['attributes']['title']) == label]
                    ep2b = [i for i in data if i['attributes']['since'][:-12] == since[:-3] and encode(i['attributes']['title']) == label]
                    ep3b = [i for i in data if i['attributes']['since'][:-15] == since[:-6] and encode(i['attributes']['title']) == label]
                    ep1c = [i for i in data if i['attributes']['since'][:-9] == since]
                    ep = ep1a if ep1a else ep1b if ep1b else ep2a if ep2a else ep2b if ep2b else ep3a if ep3a else ep3b if ep3b else ep1c
                    if len(ep) > 1:
                        notify(LANG(30410))
                    ep = ep[0] if len(ep) else None
                    if isinstance(ep, dict):
                        log("scheduled episode  = " + repr(ep))
                        if 'attributes' in ep:
                            till = ep['attributes']['till'][:-6]
                            nowd = xbmc.getInfoLabel('System.Date(yyyy-mm-dd)')
                            nowt = xbmc.getInfoLabel('System.Time(hh:mm)')
                            now = '%sT%s' % (nowd, nowt)
                            if till >= now:
                                notify(LANG(30401))
                                return
                            #show = ep['relationships']['show']
                            show = ep['attributes']['mirroredShow']
                            if 'data' in show and 'id' in show['data']:
                                showid = show['data']['id']
                            else: # must be searched by aired show title
                                log("show id not in show['data'] or 'data' not in response")
                                showid = ''
                                title = ep['attributes']['mirroredShow']['title']
                                log("mirroredShow title  = " + title)
                                showid = findshowid(statid, title)
                                if not showid:
                                    title = ep['attributes']['title']
                                    log("title  = " + title)
                                    showid = findshowid(statid, title)
                                    if not showid:
                                        title = label
                                        showid = findshowid(statid, title)
                        else:
                            notify(LANG(30405))
                            return
                        if showid:
                            log("showid = " + showid)
                            epis = getep(showid, since)
                            if epis is None:
                                notify(LANG(30404))
                                return
                            if epis:
                                res = []
                                for epi in epis:
                                    log("epi = "+repr(epi))
                                    if 'attributes' in epi:
                                        part = total = 0
                                        attrs = epi['attributes']
                                        descr = BeautifulSoup(attrs['description'], "html.parser").text
                                        title = attrs['title']
                                        if 'part' in attrs and 'mirroredSerial' in attrs and 'totalParts' in attrs['mirroredSerial']:
                                            part = attrs['part']
                                            total = attrs['mirroredSerial']['totalParts']
                                        if 'asset' in attrs and 'url' in attrs['asset'] and attrs['asset']['url']:
                                            icon = attrs['asset']['url']
                                        if 'audioLinks' in attrs:
                                            al = selal(attrs['audioLinks'])
                                            if al is not None:
                                                if kind == 'down' and 'playableTill' in al:
                                                    notify(LANG(30409))
                                                    return
                                                link = al['url']
                                                res.append((link, title, attrs['since'][:-9].replace('T', ' '), descr, part, total))
                                res.sort(key = lambda x:(x[1], x[4]))
                                log("result = "+repr(res))
                                return [label, channel, icon, res]
                            else:
                                notify(LANG(30403))
                        else:
                            notify(LANG(30404))
                    else:
                        notify(LANG(30403))
            else:
                log("################  paging ? ################")
        else:
            log("############## 'links' not in data or data is None ##############")
    else:
        log("############ unknown id of station ############")
    return
