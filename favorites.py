from sys import argv
from service import favfile
from os.path import isfile
from json import load, dump
from xbmc import executebuiltin

if isfile(favfile):
    try:
        with open(favfile, "r") as read_file:
            favdata = load(read_file)
    except:
        favdata = []
else:
    favdata = []

if __name__ == '__main__':
    if len(argv) == 3:
        title = argv[1]
        action = argv[2]
        if action == "add":
            if title not in favdata:
                favdata.append(title)
        elif action == "remove":
            if title in favdata:
                favdata.remove(title)
                executebuiltin("Container.Refresh")
        with open(favfile, "w") as outfile:
            dump(favdata, outfile)
