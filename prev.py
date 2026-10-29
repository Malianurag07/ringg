import render as R
from PIL import Image, ImageDraw
import os
auds=[os.path.join(R.NAR,f"scene{i+1:02d}.m4a") for i in range(11)]
durs=[R.dur(a)+1 for a in auds]
sheet=Image.new("RGB",(1280*2,720*2))
import sys
pick=[(0,.9),(1,.85),(2,.85),(3,.8)] if len(sys.argv)<2 else [(int(a.split(':')[0]),float(a.split(':')[1])) for a in sys.argv[1:]]
for k,(si,fr) in enumerate(pick[:4]):
    img=Image.new("RGB",(R.W,R.H),R.BG); d=ImageDraw.Draw(img); R.SCENES[si](d,durs[si]*fr,durs[si]); sheet.paste(img,((k%2)*1280,(k//2)*720))
sheet.resize((1600,900)).save("prev.png")
