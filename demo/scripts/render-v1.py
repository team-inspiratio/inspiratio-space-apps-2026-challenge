from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import math, subprocess, json, sys
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'assets'; O=ROOT/'output'; O.mkdir(exist_ok=True)
W,H,FPS=1920,1080,30
BG='#0b2029'; PANEL='#12303b'; WHITE='#f3f2e9'; MUTED='#adc2c6'; TEAL='#70d4c2'; ORANGE='#ff8866'; GRID='#1b3943'
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'; BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'; SERIF='/System/Library/Fonts/Supplemental/Georgia.ttf'
fonts={}
def ft(n,b=False,serif=False):
 k=(n,b,serif)
 if k not in fonts: fonts[k]=ImageFont.truetype(SERIF if serif else BOLD if b else FONT,n)
 return fonts[k]
def text(d,xy,s,n=32,c=WHITE,b=False,serif=False): d.text(xy,s,font=ft(n,b,serif),fill=c)
def ease(v): v=max(0,min(1,v)); return 1-(1-v)**3
def base(t,section):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
 for x in range(0,W,80): d.line((x,0,x,H),fill=GRID)
 for y in range(0,H,80): d.line((0,y,W,y),fill=GRID)
 d.rectangle((0,0,W,112),fill=BG);d.rectangle((0,980,W,H),fill=BG)
 text(d,(72,42),'INSPIRATIO  /  FIRE ATLAS',24,TEAL,True)
 text(d,(1320,42),section,23,MUTED)
 d.rectangle((72,1046,1848,1050),fill=GRID);d.rectangle((72,1046,72+1776*t/30,1050),fill=TEAL)
 return im,d
site=Image.open(A/'site-full.png').convert('RGB')
mapim=site.crop((32,922,1070,1402))
calim=site.crop((32,2034,1390,2925))
chartim=site.crop((32,3030,1390,3745))
for name,img in [('map-crop',mapim),('calendar-crop',calim),('history-crop',chartim)]: img.save(A/(name+'.png'))
def panel(im,img,box,zoom=1):
 x,y,w,h=box
 # Preserve source content; zoom is a camera crop, never a change to data.
 r=ImageOps.fit(img,(int(w*zoom),int(h*zoom)),method=Image.Resampling.LANCZOS)
 left=(r.width-w)//2;top=(r.height-h)//2;r=r.crop((left,top,left+w,top+h))
 im.paste(r,(x,y));ImageDraw.Draw(im).rectangle((x,y,x+w,y+h),outline='#52707a',width=2)
def frame(t):
 if t<5:
  im,d=base(t,'01  /  THE SENSOR GAP')
  text(d,(90,145),'Same region. Same years.',68,b=True)
  text(d,(92,239),'Southern Africa  /  2014–2021',29,MUTED)
  p=ease(t/1.5)
  for y,lab,v,col in [(420,'Aqua MODIS',1,TEAL),(590,'S-NPP VIIRS',5,ORANGE)]:
   text(d,(95,y-48),lab,32,b=True);d.rounded_rectangle((95,y,95+int(205*v*p)+1,y+70),radius=8,fill=col)
  text(d,(1240,395),'~5×',150,ORANGE,True)
  text(d,(1248,570),'as many detections',32)
  text(d,(95,760),'What changed?' if t<3.1 else 'The sensor.',76,b=True)
  text(d,(95,887),'Different sensitivity can look like a change in fire activity.',32,MUTED)
  text(d,(75,995),'NASA FIRMS · Annual VIIRS / Aqua ratios: 4.8–5.6 · Bars illustrate the approximate ratio',22,MUTED)
 elif t<10:
  u=t-5;im,d=base(t,'02  /  ONE COMMON SCALE')
  text(d,(90,140),'Fire Atlas',108,WHITE,serif=True)
  text(d,(95,280),'26 years. One common scale.',55,TEAL,b=True)
  xs=[95,705,1315];labels=[('NASA FIRMS','Terra + Aqua MODIS'),('LEARN THE OVERLAP','Two-stage LightGBM'),('VIIRS SCALE','Observed + estimated')]
  for i,(title,sub) in enumerate(labels):
   x=xs[i]; y=440+int(35*(1-ease((u-i*.35)/.65)))
   d.rounded_rectangle((x,y,x+510,y+200),radius=18,fill=PANEL,outline=TEAL if i==1 else '#3c5963',width=2)
   text(d,(x+28,y+38),title,28,TEAL,True);text(d,(x+28,y+99),sub,32,b=True)
   if i<2:
    d.line((x+530,y+100,x+590,y+100),fill=ORANGE,width=4);d.polygon([(x+590,y+100),(x+578,y+92),(x+578,y+108)],fill=ORANGE)
  d.line((95,794,1825,794),fill='#42636d',width=4);q=ease(u/2)
  d.line((95,794,95+1730*q,794),fill=TEAL,width=7)
  for start in [605,1215]:
   phase=(u*.8)%1;cx=int(start+100*phase)
   d.ellipse((cx-5,535,cx+5,545),fill=ORANGE)
  text(d,(95,830),'2000-11',34);text(d,(1640,830),'2026-10',34)
  text(d,(640,830),'312 months  ·  0.25° grid',34,TEAL)
  text(d,(75,995),'Reference: S-NPP VIIRS · NOAA-20 supports eligible continuation months',23,MUTED)
 elif t<15:
  u=t-10;im,d=base(t,'03  /  EXPLORE A PLACE')
  text(d,(75,130),'Choose a place. Select a month.',62,b=True)
  panel(im,mapim,(75,265,1240,575),1+0.025*ease(u/5));d=ImageDraw.Draw(im)
  text(d,(1370,285),'CHONGQING',29,TEAL,True);text(d,(1370,340),'STUDY AREA',29,TEAL,True)
  text(d,(1370,430),'August 2022',37,b=True)
  text(d,(1370,515),'≈420',94,ORANGE,True)
  text(d,(1370,630),'VIIRS-equivalent',28);text(d,(1370,669),'detections',28)
  d.rounded_rectangle((1370,735,1825,798),radius=8,fill=PANEL);text(d,(1390,751),'Source: scaled NOAA-20',25,TEAL)
  # Draw an editorial outline around the actual selected study area in the captured map.
  p=ease(u/1.5);x0,y0,x1,y1=477,302,912,680
  # Editorial scan line moves across the actual map, not a new selection.
  scan=75+int(1240*min(1,u/1.8))
  if u<1.8:d.line((scan,265,scan,840),fill=TEAL,width=3)
  text(d,(75,890),'106–108° E  /  29–30.5° N  ·  48 intersecting grid cells',29,MUTED)
  text(d,(75,995),'Actual Fire Atlas interface · NASA FIRMS · © OpenStreetMap contributors · Natural Earth · Leaflet',22,MUTED)
 elif t<21:
  u=t-15;im,d=base(t,'04  /  COMPARE THE SAME MONTH')
  text(d,(75,133),'Is this August unusual?',65,b=True)
  # Fit the complete calendar so no years are omitted.
  r=ImageOps.contain(calim,(1090,715),Image.Resampling.LANCZOS);im.paste(r,(75,255));d=ImageDraw.Draw(im)
  text(d,(1240,286),'6.8×',145,ORANGE,True)
  text(d,(1245,475),'the historical',38);text(d,(1245,527),'August median',38)
  text(d,(1245,635),'420  /  62 detections',32,TEAL,True)
  text(d,(1245,696),'21 earlier Augusts',30,MUTED)
  text(d,(1245,801),'Compare seasons.',32,b=True);text(d,(1245,849),'Check sources. Export.',32,b=True)
  # Scan the August column in the real calendar, retaining all underlying cells.
  x=75+int(760/1358*r.width)
  d.rounded_rectangle((x,268,x+int(100/1358*r.width),255+r.height-20),radius=5,outline=ORANGE,width=3)
  text(d,(75,995),'Actual released calendar · Historical comparison, not a forecast or fire-severity measure',23,MUTED)
 elif t<25.5:
  u=t-21;im,d=base(t,'05  /  MEASURED IMPROVEMENT')
  text(d,(90,145),'Test the conversion.',68,b=True)
  text(d,(95,246),'Global-model validation  ·  MALE ↓ lower is better',33,MUTED)
  p=ease(u/1.1)
  for y,label,value,color in [(450,'Simple ratio',.619,MUTED),(660,'Fire Atlas',.534,TEAL)]:
   text(d,(95,y-62),label,37,b=True)
   d.rounded_rectangle((95,y,95+int(value*1500*p)+1,y+80),radius=8,fill=color)
   text(d,(1070,y+11),str(value),45,color,True)
  text(d,(1350,402),'14%',132,TEAL,True);text(d,(1350,575),'lower error',39,b=True)
  text(d,(95,840),'Separate regional blind tests: 22% / 25% lower MALE.',31)
  text(d,(95,901),'Geographic transfer remains harder; global refit was not blind-tested.',27,MUTED)
  text(d,(75,995),'vs. shrinkage-ratio baseline · Two global validation windows · See Project Details for full results',22,MUTED)
 else:
  im,d=base(t,'06  /  EXPLORE FIRE HISTORY')
  text(d,(90,136),'Fire Atlas',100,serif=True)
  text(d,(95,275),'Find unusual months.',55,TEAL,True)
  text(d,(95,345),'Know where to investigate next.',50,b=True)
  text(d,(95,453),'For researchers and land managers · Historical records, not forecasts',29,MUTED)
  d.line((95,530,1825,530),fill='#42636d',width=2)
  text(d,(95,574),'TEAM INSPIRATIO',26,TEAL,True)
  text(d,(95,626),'Xie Qinqi  ·  Yinuo Zhang  ·  Tianyi Han',32)
  text(d,(95,676),'Xinrui Zhou  ·  Jiuyan Lyu',32)
  text(d,(95,759),'Challenge: Harmonization of MODIS and VIIRS Hot Spots',26,MUTED)
  text(d,(95,823),'Music: “Xi Jian” — MoFeansy / Warsic · Album: Jing Yu Ni',25,MUTED)
  text(d,(95,870),'Data: NASA FIRMS · Map: © OpenStreetMap contributors / Natural Earth',24,MUTED)
  text(d,(75,995),'Open the interactive atlas through the Project link · NASA Space Apps 2026',23,TEAL)
 # short continuous dissolve at scene boundaries
 return im

def main():
 samples=[1.8,4.2,7.5,12.5,18,23.2,27.5]
 thumbs=[]
 for t in samples:
  im=frame(t);im.save(O/f'frame-{t:04.1f}.jpg',quality=93);thumb=im.resize((640,360));thumbs.append(thumb)
 sheet=Image.new('RGB',(1280,360*4),BG)
 for i,im in enumerate(thumbs):sheet.paste(im,((i%2)*640,(i//2)*360))
 sheet.save(O/'storyboard.jpg',quality=92)
 if '--stills' in sys.argv:return
 cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(A/'music-original.mp3'),'-map','0:v','-map','1:a','-t','30','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-af','afade=t=in:st=0:d=0.25,afade=t=out:st=28.5:d=1.5','-movflags','+faststart',str(O/'fire-atlas-demo-v1.mp4')]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 edges=[5,10,15,21,25.5]
 for i in range(900):
  t=i/FPS;im=frame(t)
  for edge in edges:
   if edge<=t<edge+.22:im=Image.blend(frame(edge-1/FPS),im,(t-edge)/.22)
  p.stdin.write(im.tobytes())
  if i%150==0:print(f'Rendered {i}/900 frames',flush=True)
 p.stdin.close();code=p.wait();assert code==0
 print('Finished',flush=True)
if __name__=='__main__':main()
