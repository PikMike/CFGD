# -*- coding: utf-8 -*-
import os
import urllib.request as re
import urllib.error as err
import json
import time
import sys

def byte(num, size):  # Transforming integer to m-sized array of bytes
    mod = 8*(size-1)
    curByte = hex((num >> mod) % 256)[2:]  # First byte
    res = bytearray.fromhex((2-len(curByte))*'0'+curByte)
    for i in range(size-1):
        mod -= 8
        curByte = hex((num >> mod) % 256)[2:]
        res += bytearray.fromhex((2-len(curByte))*'0'+curByte)  # Counting each byte
    return res

def packXYPosition(n):
    return (n << 16) >> 3  # Some magic from Gravity Defied forum
                           # Not sure what does it mean

def clearify(s):  # Deleting all non-ASCII symbols from JSON
    pos = s.find('\\x')  # Mostly russian names for rounds
    while pos != -1:
        s = s[:pos]+'0'+s[pos+4:]
        pos = s.find('\\x')
    return s

def createGDLVL(arr, name):
    global i
    output = open('levels/'+'0'*(4-len(str(i+1)))+str(i+1)+'.gdlvl', 'w')
    output.write('{"name":"' + name +
                 '","author":"PikMike","scheme":"Green",' +  # Printing some headers
                 '"1-star":"00:02:00","2-star":"00:01:55","3-star":"00:01:50",' +  # Level record time
                 '"start":[-30,'+str(arr[1]-50)+'],' +
                 '"goal":[1499,'+str(arr[-1])+'],"points":[')  # Starting and finishing points for driver
    output.write(','.join(map(str, arr)))  # Printing points
    output.write(','+str(arr[-2]+200)+','+str(arr[-1])+']}')  # Finishing plate
    output.close()

def createMRG(coords, names):
    global lvls, ratioX
    fileMRG = open("levels.mrg", 'wb')  # Opening in byte mode
    pos = 12
    for i in names:
        pos += len(i) + 5  # Counting address of first track

    tracks = []
    for i in range(len(names)):
        tracks.append(pos)
        pos += 25 + len(coords[i])  # All tracks' addresses

    for i in range(3):
        fileMRG.write(byte(lvls[i], 4))  # Writing number of tracks of current difficulty
        for j in range(sum(lvls[:i]), sum(lvls[:i])+lvls[i]):
            fileMRG.write(byte(tracks[j], 4))  # Writing track's addresses
            fileMRG.write(bytearray(names[j], encoding="utf-8"))  # Track's name
            fileMRG.write(byte(0, 1))  # Zero byte

    for i in range(len(names)):
        fileMRG.write(byte(0x33, 1))  # Byte for track's beginning
        fileMRG.write(byte(packXYPosition(-30), 4) +
                      byte(packXYPosition(coords[i][1] + 50), 4))  # Starting point for driver
        fileMRG.write(byte(packXYPosition(ratioX-1), 4) +
                      byte(packXYPosition(coords[i][-1]), 4))  # Finishing point
        fileMRG.write(byte(len(coords[i]) // 2, 2))  # Number of points in track
        fileMRG.write(byte(coords[i][0], 4) +
                      byte(coords[i][1], 4))  # First point
        for j in range(1, len(coords[i]) // 2):
            diffX = coords[i][j*2] - coords[i][j*2-2]
            diffY = coords[i][j*2-1] - coords[i][j*2+1]
            fileMRG.write(byte(diffX, 1) +
                          byte(diffY, 1))  # Difference in x, y for each point
    fileMRG.close()

def div(x1, y1, x2, y2):  # Dividing segment between two points to smaller ones
    partCnt = max(x2 - x1, abs(y2 - y1)) // 127 + 1  # .mrg files type is limiting Y coord difference to [-128..127]
    stepX = (x2 - x1) // partCnt                                             # and X coord difference to [1..127]
    stepY = (y2 - y1) // partCnt
    res = []
    for i in range(partCnt):
        res += [x1 + stepX*(i+1), y1 + stepY*(i+1)]  # Dividing segment into equal parts
    res += [x2, y2]
    return res

def getOpts(args):  # Recognizing console app arguments and options
    res = {}
    for i in range(len(args)):
        if args[i][0] == '-':  # Short options
            if args[i][1] == '-':  # And long ones
                if args[i][2:] in ["help", "list", "file"]:
                    res[args[i][2]] = i
            else:
                if args[i][1:] in ['h', 'l', 'f']:
                    res[args[i][1]] = i
    return res

def printHelp():
    print()
    print("Usage:", os.path.basename(__file__), '[options]')
    print()
    print("Options:")
    print()
    print("  -l, --list <handles>" + ' '*7 + "read handles from command line")
    print(' '*29 + "(divided by space)")
    print("  -f, --file <path>" + ' '*10 + "read handles from file")
    print(' '*29 + "(one per line)")
    print("  -h, --help" + ' '*17 + "display this message")

def parse(args):
    opts = getOpts(args)  # Getting options positions
    handles = []
    if 'h' in opts:  # Help message
        printHelp()
    else:
        if ('l' in opts) and ('f' in opts):  # Taking handles from arguments
            if (min(opts['f'], len(args))) - (opts['l']+1) < 1:
                print("No arguments given for option -l")
            else:
                handles += args[opts['l'] + 1:min(opts['f'], len(args))]
        elif 'l' in opts:
            if (len(args)) - (opts['l'] + 1) < 1:
                print("No arguments given for option -l")
            else:
                handles += args[opts['l']+1:len(args)]
        if 'f' in opts:  # And from input file
            if (opts['f'] < len(args)-1) and (os.path.isfile(args[opts['f'] + 1])):
                file = open(args[opts['f']+1])
                for i in file:
                    handles.append(i.split()[0])
            elif (opts['f'] == len(args) - 1) or (('l' in opts) and (opts['l'] == opts['f'] + 1)):
                print("No arguments given for option -f")
            else:
                print("File not found")
    if ('l' not in opts) and ('f' not in opts) and ('h' not in opts):
        print("Options not found, run script with -h to view help")
    return handles

def getJSON(i):
    global handles, cur
    site = "http://codeforces.com/api/user.rating?handle="+handles[i]
    try:  # Requesting Codeforces API page with JSON of user's contests
        req = re.urlopen(site)
    except err.URLError:
        print('User', handles[i], 'not found')
        handles = handles[:i]+handles[i+1:]
        cur += 1
        return False
    res = str(req.read())[26:-3]+']'  # Deleting info about 'successful request'
    res = clearify(res)  # Deleting non-ASCII symbols
    res = json.loads(res)  # Parsing JSON to list
    return res

args = sys.argv[1:]
handles = parse(args)  # Creating handles list

if len(handles) < 3:
    print("You entered less than 3 handles, levels.mrg file will not be generated")
    # Should be at least 1 track per level of difficulty in levels.mrg file

if os.path.isdir("levels"):  # Creating directory for .gdlvl tracks
    for i in os.listdir('levels'):
        os.remove('levels/'+i)
else:
    os.mkdir("levels")

fileDef = open("levels/pack.def", 'w')  # main file for .gdlvl track system
fileDef.write('{ "packName": "CFRatingGraph" }')
fileDef.close()

secs = "ratingUpdateTimeSeconds"
coords = []
cur = 0  # Requests number
i = 0
ratioX, ratioY = 1500, 300
while i < len(handles):
    if (cur+1) % 5 == 0:  # CF's requests per second limit is 5
        time.sleep(1)
    res = getJSON(i)  # parsing JSON page of user's contests
    if not res:
        continue
    if len(res) < 2:
        print(handles[i]+"'s contests list is too small")  # Can't create graph with 0 or 1 point
        handles = handles[:i]+handles[i+1:]
        i -= 1
    else:
        minRes, maxRes = 1000000, -1000000
        for j in range(len(res)):
            minRes = min(minRes, res[j]["oldRating"])
            maxRes = max(maxRes, res[j]["newRating"])
        diffX = int(res[-1][secs])-int(res[0][secs])  # Defining difference between min and max
        diffY = maxRes - minRes                       # to normalize coordinates
        coords.append([-200, round((diffY - res[0]["newRating"])/diffY*ratioY),  # Adding starting plate
                       -100, round((diffY - res[0]["newRating"])/diffY*ratioY),
                       -1, round((diffY - res[0]["newRating"])/diffY*ratioY)])
        for j in range(len(res)):
            # Adding pairs of x, y for each point
            coords[-1] += div(coords[i][-2], coords[i][-1], round(int(res[j][secs]-int(res[0][secs]))/diffX*ratioX),
                                  round((diffY - res[j]["newRating"])/diffY*ratioY))
        coords[i] += ([coords[i][-2]+100, coords[i][-1], coords[i][-2]+200, coords[i][-1]])  # Adding finishing plate
        createGDLVL(coords[i], handles[i])
        print("Added", handles[i])
    cur += 1
    i += 1
hCnt = len(handles)
lvls = [hCnt // 3, hCnt // 3, hCnt - (hCnt // 3)*2]  # Dividing levels into easy, medium and hard difficulties
if len(handles) > 2:
    createMRG(coords, handles)
