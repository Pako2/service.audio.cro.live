# -*- coding: utf-8 -*-

import xbmc
import xbmcgui
import xbmcaddon
from xml.dom import minidom as miniDom
from codecs import open as codecs_open
from xbmc import Monitor
from datetime import datetime as dt
from datetime import timedelta as td
from json import loads
from os.path import isfile, getmtime, join
from sys import version_info

PY3 = version_info[0] == 3

if PY3:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
else:
    from urllib2 import Request, urlopen, HTTPError

addon       = xbmcaddon.Addon(id = 'service.audio.cro.live')
addonname   = addon.getAddonInfo('name')
headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0", "Content-Type":"application/json"}
api_url = "https://api.rozhlas.cz/data/v2/"
stations_url = "https://api.mujrozhlas.cz/stations"
bitrate = 128 * (1 + int(addon.getSetting('bitrate')))
pastdays = int(addon.getSetting('pastdays'))
futudays = int(addon.getSetting('futudays'))
val = int(addon.getSetting('period'))
period = 12 * (1 + val) if val < 6 else 0
m3ufile  = join(addon.getSetting('folder'), addon.getSetting('playlist'))
epgfile  = join(addon.getSetting('folder'), addon.getSetting('epg'))


def LANG(id):
    return addon.getLocalizedString(id)

def decode(txt):
    return txt if PY3 or isinstance(txt, unicode) else txt.decode('utf-8')

def encode(txt):
    return txt if PY3 else txt.encode('utf-8')

def convertTime(t):
    return t.replace('-', '').replace(':', '').replace('T', '').replace('+', ' +')

def get_date_range(pds, fds):
    base = dt.today()
    return [str((base + td(days = x)).date()).replace('-','/') for x in range(-pds, fds)]

def get_links(links, br):
    res = []
    for l in links:
        if 'quality' in l and 'linkType' in l and 'variant' in l and 'url' in l:
            if l['url'] and l['quality'] == 'normal' and l['linkType'] == 'directstream' and l['variant'] == 'mp3':
               res.append(l)
    select = [i for i in res if i['bitrate'] == br]
    res = select if select else res
    return res[0]['url']


def get_stations(data):
    lst = []
    for i in data:
        if 'type' in i and 'attributes' in i and 'id' in i and i['type'] == 'station':
            attrs = i['attributes']
            icon = attrs['asset']['url'] if 'asset' in attrs and 'url' in attrs['asset'] else 'special://home/addons/service.audio.cro.live/resources/logos/%s.jpg' % attrs['code']
            if 'code' in attrs and 'shortTitle' in attrs and 'stationType' in attrs and 'audioLinks' in attrs:
                tmp = (attrs['code'], attrs['shortTitle'], attrs['stationType'], get_links(attrs['audioLinks'], bitrate), icon)
                lst.append(tmp)
    return lst


def create_m3u(lst, outfl = m3ufile):
    num = 1
    txt = '#EXTM3U\n'
    for i in lst:
        group = LANG(30203) if i[2] == 'regional' else LANG(30204)
        txt += '#EXTINF:-1, tvg-chno="%i" tvg-name="%s" tvg-id="%s" tvg-logo="%s" group-title="%s" radio="true", %s\n%s\n' % (num,i[1],i[0],i[4],group,i[1],i[3])
        num += 1
    f = codecs_open(outfl, 'w', encoding = "utf-8")
    f.write(txt)
    f.close()


def convert(stats, epg, epgfl = epgfile):
    impl = miniDom.getDOMImplementation()
    dcmnt = impl.createDocument(None, u'tv', None)
    root = dcmnt.documentElement
    # create channels
    for stat in stats:
        if stats[0] == "webik":
            continue
        channNode = dcmnt.createElement(u'channel')
        displNode = dcmnt.createElement(u'display-name')
        displText = dcmnt.createTextNode(stat[1])
        displNode.appendChild(displText)
        displNode.setAttribute('lang', 'cs')
        channNode.appendChild(displNode)
        channNode.setAttribute('id', stat[0])
        root.appendChild(channNode)
    # create programms
    for stat in stats:
        if stat[0] == "webik":
            continue
        # load data of one channel to temporary list
        tmpday = []
        for day in epg:
            if stat[0] in day:
                for item in day[stat[0]]:
                    tmpprog = {}
                    tmpprog['title'] = item['title']
                    tmpprog['description'] = item['description']
                    if 'edition' in item and 'asset' in item['edition']:
                        tmpprog['icon'] = item['edition']['asset']
                    tmpprog['start'] = item['since']
                    tmpprog['stop'] = item['till']
                    tmpday.append(tmpprog)
        # check and repair time continuity
        tmpday2 = []
        flag = False
        for i in range(len(tmpday)):
            if flag:
                flag = False
                continue
            if i < len(tmpday) - 2:
                if tmpday[i]['start'] <= tmpday[i + 1]['start']:
                    if tmpday[i]['stop'] > tmpday[i + 1]['stop']:
                        flag = True
                        tmpday2.append(tmpday[i])
                        continue
                    if tmpday[i]['stop'] > tmpday[i + 1]['start']:
                        flag = True
                        tmpday2.append(tmpday[i])
                        continue
                elif tmpday[i]['start'] >= tmpday[i + 1]['start']:
                    if tmpday[i]['stop'] < tmpday[i + 1]['stop']:
                        flag = True
                        tmpday2.append(tmpday[i+1])
                        continue
                    if tmpday[i]['start'] < tmpday[i + 1]['stop']:
                        flag = True
                        tmpday2.append(tmpday[i + 1])
                        continue

                if tmpday2 and tmpday[i]['start']>=tmpday2[-1]['start'] and tmpday[i]['stop']<=tmpday2[-1]['stop']:
                    continue
            tmpday2.append(tmpday[i])
        for item in tmpday2:
            prgNode = dcmnt.createElement(u'programme')
            titleNode = dcmnt.createElement(u'title')
            titleText = dcmnt.createTextNode(item['title'])
            titleNode.appendChild(titleText)
            titleNode.setAttribute('lang', 'cs')
            prgNode.appendChild(titleNode)
            descNode = dcmnt.createElement(u'desc')
            descText = dcmnt.createTextNode(item['description'])
            descNode.appendChild(descText)
            descNode.setAttribute('lang', 'cs')
            prgNode.appendChild(descNode)
            if 'icon' in item:
                iconNode = dcmnt.createElement(u'icon')
                iconNode.setAttribute('src', item['icon'])
                prgNode.appendChild(iconNode)
            prgNode.setAttribute('start', convertTime(item['start']))
            prgNode.setAttribute('stop', convertTime(item['stop']))
            prgNode.setAttribute('channel', stat[0])
            root.appendChild(prgNode)
    with codecs_open(epgfl, "w", "utf-8") as out:
        dcmnt.writexml(out, addindent = '    ', newl = '\n', encoding = "utf-8")
        out.close()
    if epgfl != epgfile and tmpday2:
        notify(LANG(30201), True, False)

def log(message, debug = True):
    if debug:
        if addon.getSetting('debug') in (True, 'true'):
            level = xbmc.LOGDEBUG
        else:
            return
    else:
        level = xbmc.LOGINFO if PY3 else xbmc.LOGNOTICE
    message = message if PY3 or not isinstance(message, unicode) else message.encode('utf-8')
    xbmc.log("%s: %s" % (addonname, message), level = level)


def notify(text, backgr = False, error = False):
    if backgr and addon.getSetting('notif') not in (True, 'true'):
        return
    text = encode(text)
    icon = xbmcgui.NOTIFICATION_ERROR  if error else addon.getAddonInfo('icon')
    xbmcgui.Dialog().notification(addonname, text, icon, 4500)


def jsonrequest(url):
    log(url)
    req = Request(url, headers = headers)
    try:
        resp = urlopen(req)
        if resp.getcode() == 200:
            html = resp.read()
            log(html)
            return loads(html)
    except HTTPError as e:
        log(repr(e.read()))
    except Exception as e:
        log(repr(e))

def run():
    url = stations_url
    jsondata = jsonrequest(url)
    if jsondata and 'data' in jsondata:
        stations = get_stations(jsondata['data'])
        if not stations:
            return 1
        create_m3u(stations)
        epg = []
        for d in get_date_range(pastdays, futudays):
            url = api_url + "schedule/day/" + d + ".json"
            jsondata = jsonrequest(url)
            if jsondata and 'data' in jsondata:
                epg.append(jsondata['data'])
        if epg:
            stats = [(i[0],i[1]) for i in stations]
            convert(stats, epg)
            return 0
    return 2


class BackgroundService(Monitor):

    def __init__(self):
        log('service started', False)


    def update(self):
        res = run()
        note, error = (LANG(30201), False) if not res else (LANG(30202), True)
        notify(note, True, error)


    def tick(self):
        if isfile(epgfile) and isfile(m3ufile):
            tdiff = dt.now() - dt.fromtimestamp(getmtime(epgfile))
            tlimit = td(hours = period)
            #tlimit = td(minutes = 5)
            if tdiff >= tlimit:
                self.update()
        else:
            self.update()


if __name__ == '__main__':
    if period:
        monitor = BackgroundService()
        while not monitor.abortRequested():
            if monitor.waitForAbort(60):
                break
            monitor.tick()
        log('service stopped', False)
        del monitor
        del addon
        sys.exit()
