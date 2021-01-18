from resolver import get_audio
import xbmc
import xbmcgui
from service import decode, log

#plist.item : (link, title, since, descr, part, total)
res = get_audio("play")
plist = []
if res is not None:
    _label, channel, icon, plist = res
if plist:
    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()
    for itm in plist:
        title = '%s %s' % (decode(channel), itm[2])
        label = decode(itm[1])
        label += '' if itm[4] == 0 else ' %i/%i' % (itm[4], itm[5])
        listItem = xbmcgui.ListItem(label = title)
        listItem.setInfo(
            type        = 'Music',
            infoLabels  = {'Artist' : label, 'Album' : decode(itm[3]), 'Title' : title}
        )
        listItem.setArt({'thumb' : icon})
        listItem.setMimeType('audio/mpeg')
        playlist.add(itm[0], listitem = listItem)
        del listItem
    pl = xbmc.Player()
    pl.play(playlist)
    del playlist
    del pl
