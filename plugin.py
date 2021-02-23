import sys
#import codecs
#from xml.sax.saxutils import escape

import xbmc, xbmcplugin, xbmcgui, xbmcaddon
from os.path import isfile
#from codecs import open as codecs_open
from service import m3ufile, epgfile, LANG, addonname, PY3

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
    if isfile(m3ufile):
        with open(m3ufile, 'rb') as rf:
            data = rf.read()
            with open(filepath, 'wb') as f:
                f.write(data)

def write_epg(filepath):
    if isfile(epgfile):
        with open(epgfile, 'rb') as rf:
            data = rf.read()
            with open(filepath, 'wb') as f:
                f.write(data)


if method in ('epg', 'playlist'):
    try:
        if method == 'epg':
            write_epg(params.get('output'))
        elif method == 'playlist':
            write_playlist(params.get('output'))
    except Exception as e:
        message = str(e)
    else:
        message = 'ok'

    xbmcplugin.addDirectoryItem(handle, quote(message), xbmcgui.ListItem())
    xbmcplugin.endOfDirectory(handle, succeeded=True)

else:
    xbmcgui.Dialog().ok(addonname, LANG(30500))

