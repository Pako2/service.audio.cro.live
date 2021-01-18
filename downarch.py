# -*- coding: utf-8 -*-
from resolver import get_audio

#plist.item : (link, title, since, descr, part, total)
res = get_audio("down")
plist = []
if res is not None:
    _label, channel, icon, plist = res

if plist:
    from service import PY3, addon, notify, log, LANG, decode
    from os.path import splitext, basename, join
    if PY3:
        from urllib.parse import urlparse
        from urllib.request import urlopen, Request
        from urllib.error import HTTPError
    else:
        from urlparse import urlparse
        from urllib2 import urlopen, Request, HTTPError
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0"}

    i = 0
    for itm in plist:
        i += 1
        disassembled = urlparse(itm[0])
        file_ext = splitext(basename(disassembled.path))[1]

        if len(plist) > 1:
            filename = '%s_%s_%s[%i]%s' % (channel, itm[2], decode(_label), i, file_ext)
        else:
            filename = '%s_%s_%s%s' % (channel, itm[2], decode(_label), file_ext)
        localfile  = join(addon.getSetting('downfolder'), filename).encode('utf-8')

        req = Request(itm[0], headers = headers)
        code = 0
        try:
            resp = urlopen(req)
            notify(LANG(30406) % filename)
            code = resp.getcode()
            if code == 200:
                datatowrite = resp.read()
                with open(localfile, 'wb') as f:
                    f.write(datatowrite)
        except HTTPError as e:
            log(repr(e.read))

        if code == 200:
            notify(LANG(30407) % filename)
        else:
            notify(LANG(30408) % filename, False, True)

