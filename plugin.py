import sys

import xbmcplugin, xbmcgui
from service import stations_url, api_url, pastdays, futudays, LANG, addonname, PY3
from service import jsonrequest, get_date_range, create_m3u,  get_stations, convert


if PY3:
    #Python3
    from urllib.parse import parse_qsl, quote
else:
    #Python2
    from urlparse import parse_qsl
    from urllib import quote

params = dict(parse_qsl(sys.argv[2].lstrip('?'), keep_blank_values=True))
method = params.get('method')
handle = int(sys.argv[1])


def write_playlist(filepath):
    jsondata = jsonrequest(stations_url)
    if jsondata and 'data' in jsondata:
        stations = get_stations(jsondata['data'])
        if not stations:
            return "ERROR 1"
        create_m3u(stations, filepath)
        return "1"


def write_epg(filepath):
    jsondata = jsonrequest(stations_url)
    if jsondata and 'data' in jsondata:
        stations = get_stations(jsondata['data'])
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
    xbmcplugin.endOfDirectory(handle, succeeded=True)

else:
    xbmcgui.Dialog().ok(addonname, LANG(30500))

