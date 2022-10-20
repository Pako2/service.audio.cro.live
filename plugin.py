import sys

import xbmcplugin, xbmcgui
from service import api_url, pastdays, futudays, LANG, addon, addonname, PY3, fanart, dictfile, favfile, favscript
from service import jsonrequest, xmlrequest, get_date_range, create_m3u,  get_stations, convert
from service import log
from json import load, dump
from datetime import datetime as dt
from datetime import timedelta as td
from os.path import isfile, getmtime, join
from xml.etree import ElementTree
from itertools import groupby
import czech_sort


if PY3:
    #Python3
    from urllib.parse import parse_qsl, quote, urlencode
else:
    #Python2
    from urlparse import parse_qsl
    from urllib import quote, urlencode

params = dict(parse_qsl(sys.argv[2].lstrip('?'), keep_blank_values = True))
method = params.get('method')
handle = int(sys.argv[1])
__url__ = sys.argv[0]


def write_playlist(filepath):
    stations = get_stations()
    if not stations:
        return "ERROR 1"
    create_m3u(stations, filepath)
    return "1"

def write_epg(filepath):
    stations = get_stations()
    if not stations:
        return "ERROR 1"
    epg = []
    for d in get_date_range(pastdays, futudays):
        url = api_url + "schedule/day/" + d + ".json"
        jsondata = jsonrequest(url)
        if jsondata and 'data' in jsondata:
            epg.append(jsondata['data'])
    if epg:
        stats = [(i[0],i[1]) for i in stations]
        convert(stats, epg, filepath)
        return "1"
    return "ERROR 2"

def timestr(t):
    T = t.index('T')
    return t[T + 1:T + 6]

def get_poddata():
    data = xmlrequest("https://api.mujrozhlas.cz/rss/podcasts.rss")
    tree = ElementTree.fromstring(data)
    if isfile(dictfile):
        with open(dictfile, "r") as read_file:
            imagedata = load(read_file)
            log(imagedata)
    else:
        imagedata = None
    poddata = []
    for item in tree.iter('item'):
        link = item.find('link').text
        if link is not None:
            poditem = {}
            poditem['link'] = link
            poditem['title'] = item.find('title').text if item.find('title').text is not None else "???"
            poditem['description'] = item.find('description').text if item.find('description').text is not None else "???"
            if imagedata is not None and link in imagedata:
                poditem['image'] = imagedata[link]
            poddata.append(poditem)
    poddata.sort(key = lambda x: czech_sort.key(x['title'][0]))
    return poddata

def addContext(li, title):
    if isfile(favfile):
        try:
            with open(favfile, "r") as read_file:
                favdata = load(read_file)
        except:
            favdata = []
    else:
        favdata = []
    if title in favdata:
        label = LANG(30209)
        action = "remove"
    else:
        label = LANG(30208)
        action = "add"
    cm = [(label, "RunScript({},{},{})".format(favscript, title, action)),]
    li.addContextMenuItems(cm)


if method in ('epg', 'playlist'):
    message = 'ERROR 0'
    try:
        if method == 'epg':
            message = write_epg(params.get('output'))
        elif method == 'playlist':
            message = write_playlist(params.get('output'))
    except Exception as e:
        message = str(e)
    xbmcplugin.addDirectoryItem(handle, quote(message), xbmcgui.ListItem())
    xbmcplugin.endOfDirectory(handle, succeeded = True)

elif method == 'groups':
    poddata = get_poddata()
    key = params.get('key')
    grps = [list(ele) for i, ele in groupby(poddata, lambda x: x['title'][0])]
    grp = [i for i in grps if i[0]['title'][0]==key][0]
    for i in grp:
        title = i['title']
        li = xbmcgui.ListItem(title, path = i['link'], offscreen=True)
        li.setArt({'fanart':fanart, 'icon':i['image'] if 'image' in i else 'DefaultFolder.png'})
        li.setInfo('video', {'path':i['link'], 'plot':i['description']})
        li.setInfo('music', {'title': i['title']})
        addContext(li, title)
        xbmcplugin.addDirectoryItem(handle, i['link'], li, False)
    xbmcplugin.endOfDirectory(handle, succeeded = True)

elif method == 'podcastsub':
    poddata = get_poddata()
    subname = params.get('subname')
    if isfile(favfile):
        try:
            with open(favfile, "r") as read_file:
                favdata = load(read_file)
        except:
            favdata = []
    else:
        favdata = []
    if len(favdata) and subname == 'favorites':
        for i in poddata:
            title = i['title']
            if title in favdata:
                li = xbmcgui.ListItem(title, path = i['link'], offscreen=True)
                li.setArt({'fanart':fanart, 'icon':i['image'] if 'image' in i else 'DefaultFolder.png'})
                li.setInfo('video', {'path':i['link'], 'plot':i['description']})
                li.setInfo('music', {'title': title})
                addContext(li, title)
                xbmcplugin.addDirectoryItem(handle, i['link'], li, False)
    if subname == 'all':
        for i in poddata:
            title = i['title']
            li = xbmcgui.ListItem(title, path = i['link'], offscreen=True)
            li.setArt({'fanart':fanart, 'icon':i['image'] if 'image' in i else 'DefaultFolder.png'})
            li.setInfo('video', {'path':i['link'], 'plot':i['description']})
            li.setInfo('music', {'title': title})
            addContext(li, title)
            xbmcplugin.addDirectoryItem(handle, i['link'], li, False)

    elif subname == 'groups': # Grouping by first letter
        grps = [list(ele) for i, ele in groupby(poddata, lambda x: x['title'][0])]
        for gr in grps:
            key=gr[0]['title'][0]
            url = __url__ + '?' + urlencode({'method': 'groups', 'key': key})
            li = xbmcgui.ListItem(key, offscreen=True)
            li.setArt({'fanart':fanart})
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder = True)
    xbmcplugin.endOfDirectory(handle, cacheToDisc = False)

elif method == 'folder':
    foldername = params.get('foldername')
    if foldername == 'podcasts':
        url = __url__ + '?' + urlencode({'method': 'podcastsub', 'subname': 'all'})
        li = xbmcgui.ListItem(LANG(30211), offscreen=True)
        li.setArt({'fanart':fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder = True)
        url = __url__ + '?' + urlencode({'method': 'podcastsub', 'subname': 'groups'})
        li = xbmcgui.ListItem('A - Ž', offscreen=True)
        li.setArt({'fanart':fanart})
        xbmcplugin.addDirectoryItem(handle, url, li, isFolder = True)
        if isfile(favfile):
            try:
                with open(favfile, "r") as read_file:
                    favdata = load(read_file)
            except:
                favdata = []
        else:
            favdata = []
        if len(favdata):
            url = __url__ + '?' + urlencode({'method': 'podcastsub', 'subname': 'favorites'})
            li = xbmcgui.ListItem(LANG(30210), offscreen=True)
            li.setArt({'fanart':fanart})
            xbmcplugin.addDirectoryItem(handle, url, li, isFolder = True)
        xbmcplugin.endOfDirectory(handle, cacheToDisc = False)
    else:
        stations = get_stations()
        if not stations:
            exit
        jsondata = jsonrequest("https://api.rozhlas.cz/data/v2/schedule/now.json")
        if jsondata and 'data' in jsondata:
            data = jsondata['data']
            stnames = data.keys() 
            listing = []
            for st in stations:
                if st[2] == 'regional' and foldername == 'allover':
                    continue
                elif st[2] in ('allover', 'webradio') and foldername == 'regional':
                    continue
                if st[0] in stnames:
                    stdata = data[st[0]][0]
                    list_item = xbmcgui.ListItem("{} » [COLOR=FF00FFF0]{}[/COLOR] « {}-{}".format(st[1], stdata['title'], timestr(stdata['since']), timestr(stdata['till'])), path=st[3], offscreen=True)
                    plot = stdata['description'] if stdata['description'] else stdata['title']
                    list_item.setInfo('video', {'path':st[3], 'plot':plot})
                    list_item.setInfo('music', {'title': "{} » [COLOR=FF00FFF0]{}[/COLOR] « {}-{}".format(st[1], stdata['title'], timestr(stdata['since']), timestr(stdata['till']))})
                    thumb = stdata['edition']['asset'] if 'asset' in stdata['edition'] else st[4]
                    icon = st[4]
                    list_item.setArt({'icon' : icon, 'thumb' : thumb, 'fanart':fanart})
                    list_item.setProperties({'IsPlayable':'false'})
                    url = __url__ + '?' + urlencode({'method': 'play', 'path':st[3], 'station':st[1], 'title':stdata['title'], 'thumb':thumb, 'since':stdata['since'],'till':stdata['till'], 'desc':plot})
                    is_folder = False
                    listing.append((url, list_item, is_folder))
                else:
                    list_item = xbmcgui.ListItem(st[1], path=st[3])
                    list_item.setInfo('video', {'path':st[3], 'plot':st[1]})
                    list_item.setInfo('music', {'title': st[1]})
                    thumb = st[4]
                    list_item.setArt({'thumb' : thumb, 'fanart':fanart})
                    list_item.setProperties({'IsPlayable':'false'})
                    url = __url__ + '?' + urlencode({'method': 'play', 'path':st[3], 'station':st[1], 'thumb':thumb})
                    is_folder = False
                    listing.append((url, list_item, is_folder))
        xbmcplugin.addDirectoryItems(handle, listing, len(listing))
        xbmcplugin.endOfDirectory(handle, cacheToDisc = False)

elif method == 'play':
    path = params.get('path')
    station = params.get('station')
    thumb = params.get('thumb')
    li = xbmcgui.ListItem(path = path)
    if 'title' in params:
        title = params.get('title')
        since = params.get('since')
        till = params.get('till')
        description = params.get('desc')
        label = "{} » [COLOR=FF00FFF0]{}[/COLOR] « {}-{}".format(station, title, timestr(since), timestr(till))
        li.setLabel(label)
        duration = (dt.fromisoformat(till)-dt.fromisoformat(since)).total_seconds()
        li.setInfo('video',{'plot' : description, 'duration':duration, "starttime": since})
        li.setInfo('music',{'Artist' : title, 'Album' : description, 'Title' : station, 'duration':duration, 'mediatype':'music', "starttime": since})
    else:
        li.setLabel(station)
        li.setInfo('video', {})
        li.setInfo('music',{'Title' : station, 'mediatype':'music'})
    li.setArt({'thumb' : thumb, 'fanart':fanart})
    li.setIsFolder(False)
    xbmc.Player().play(path, li)
    del li

else: # Main menu
    url = __url__ + '?' + urlencode({'method': 'folder', 'foldername': 'podcasts'})
    li = xbmcgui.ListItem(LANG(30205), offscreen=True)
    li.setArt({'fanart':fanart})
    xbmcplugin.addDirectoryItem(handle, url, li, isFolder = True)

    url = __url__ + '?' + urlencode({'method': 'folder', 'foldername': 'allover'})
    li = xbmcgui.ListItem(LANG(30206), offscreen=True)
    li.setArt({'fanart':fanart})
    xbmcplugin.addDirectoryItem(handle, url, li, isFolder = True)

    url = __url__ + '?' + urlencode({'method': 'folder', 'foldername': 'regional'})
    li = xbmcgui.ListItem(LANG(30207), offscreen=True)
    li.setArt({'fanart':fanart})
    xbmcplugin.addDirectoryItem(handle, url, li, isFolder = True)

    xbmcplugin.endOfDirectory(handle, cacheToDisc = False)

#Image dict creating 
if not isfile(dictfile) or (dt.now() - dt.fromtimestamp(getmtime(dictfile))) > td(hours = 7 * 24):
    data = xmlrequest("https://api.mujrozhlas.cz/rss/podcasts.rss")
    tree = ElementTree.fromstring(data)
    imagedict = {}
    for item in tree.iter('item'):
        link = item.find('link').text
        if link is not None:
            tmpdata = xmlrequest(link)
            root = ElementTree.fromstring(tmpdata)
            image = None
            if root:
                channel=root.find('channel')
                if channel:
                    image=channel.find('image')
                    if image:
                        image=image.find('url').text
            if image is not None:
                imagedict[link] = image
    with open(dictfile, "w") as outfile:
        dump(imagedict, outfile)

