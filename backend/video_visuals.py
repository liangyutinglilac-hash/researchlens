"""Content-led light illustrations for the science video."""
import math
from PIL import Image, ImageDraw, ImageFont


def _wrap(draw, text, font, width):
    lines=[];line=''
    for char in text:
        if draw.textlength(line+char,font=font)>width:
            lines.append(line);line=char
        else: line+=char
    if line:lines.append(line)
    return lines


def _label(draw, x, y, label, font, color='#284d73'):
    lines=[label[i:i+5] for i in range(0,len(label),5)]
    for i,line in enumerate(lines):
        draw.text((x-draw.textlength(line,font=font)/2,y-(len(lines)-1)*13+i*27),line,font=font,fill=color)


def _visual(draw, scene, progress, font):
    v=scene.get('visual') or {'kind':'network','labels':['研究问题','研究方法','证据局限']}
    kind=v.get('kind','network'); labels=v.get('labels',[])[:4]
    labels=labels or ['研究问题','证据','局限']
    left,right,top,bottom=65,805,155,530
    blue='#6399d9'; line='#abc2dd'; orange='#ee9561'; pale='#edf5ff'
    if kind in ('flow','experiment'):
        xs=[left+80+i*(right-left-160)/max(1,len(labels)-1) for i in range(len(labels))]
        for i,x in enumerate(xs):
            if i: draw.line((xs[i-1]+72,345,x-72,345),fill=line,width=6)
            draw.rounded_rectangle((x-70,295,x+70,395),radius=22,fill=pale,outline=blue,width=3)
            _label(draw,x,347,labels[i],font)
            if i<len(xs)-1:
                t=(progress+i/len(xs))%1;px=xs[i]+72+(xs[i+1]-xs[i]-144)*t
                draw.ellipse((px-8,337,px+8,353),fill=orange)
        if kind=='experiment':
            draw.ellipse((135,190,205,260),fill='#d6edf2',outline=blue,width=3);draw.line((170,260,170,295),fill=blue,width=5)
            draw.polygon([(155,190),(185,190),(180,170),(160,170)],fill='#d6edf2',outline=blue)
    elif kind=='timeline':
        y=345;draw.line((left,y,right,y),fill=line,width=7)
        for i,label in enumerate(labels):
            x=left+70+i*(right-left-140)/max(1,len(labels)-1);draw.ellipse((x-20,y-20,x+20,y+20),fill=orange if i==int(progress*len(labels))%len(labels) else blue,outline='white',width=3)
            draw.rounded_rectangle((x-68,210 if i%2==0 else 395,x+68,275 if i%2==0 else 460),radius=16,fill='white',outline='#c8dcef',width=2);_label(draw,x,245 if i%2==0 else 430,label,font)
    elif kind in ('cell','microbes'):
        draw.ellipse((300,190,565,480),fill='#e4f6ef' if kind=='cell' else '#fff1dd',outline=blue,width=5)
        if kind=='cell':
            draw.ellipse((382,270,482,375),fill='#c8d7ff',outline='#6979c9',width=4)
            for i in range(5):
                x=330+(i*47)%190+8*math.sin(progress*6+i);y=225+((i*73)%210)+6*math.cos(progress*6+i);draw.ellipse((x,y,x+22,y+18),fill='#f2a77d',outline='#c56f5b')
        else:
            for i in range(10):
                x=335+(i*53)%190;y=235+((i*67)%210);r=12+5*((i+int(progress*10))%3);draw.ellipse((x-r,y-r,x+r,y+r),fill=['#f28b67','#8fcf9b','#76a7e8'][i%3],outline='white',width=2)
        for i,label in enumerate(labels):
            x=145+(i%2)*510;y=220+(i//2)*210;draw.rounded_rectangle((x-90,y-30,x+90,y+30),radius=14,fill=pale,outline=blue);_label(draw,x,y,label,font)
    elif kind=='ecosystem':
        draw.ellipse((105,175,175,245),fill='#ffd77e');draw.arc((105,175,175,245),20,320,fill='#e1a84f',width=3)
        draw.polygon([(100,470),(760,470),(700,390),(170,390)],fill='#c69162',outline='#9a6b46');draw.line((100,470,760,470),fill='#7c9b68',width=8)
        for i in range(4):
            x=190+i*130+7*math.sin(progress*6+i);draw.line((x,410,x,315),fill='#4a9c71',width=7);draw.ellipse((x-45,320,x,370),fill='#74c589');draw.ellipse((x,300,x+45,370),fill='#67b77f')
        for i,label in enumerate(labels):
            x=155+(i%2)*490;y=220+(i//2)*145;draw.rounded_rectangle((x-92,y-28,x+92,y+28),radius=14,fill='white',outline='#bfd7cb');_label(draw,x,y,label,font)
    elif kind=='compare':
        for i,label in enumerate(labels[:4]):
            x=215+(i%2)*385;y=250+(i//2)*190;draw.rounded_rectangle((x-135,y-65,x+135,y+65),radius=22,fill=pale if i%2==0 else '#fff1e7',outline=blue if i%2==0 else orange,width=4);_label(draw,x,y,label,font)
    else:
        center=(430,345);pts=[]
        for i in range(len(labels)):
            pts.append((center[0]+235*math.cos(i*2*math.pi/len(labels)-math.pi/2),center[1]+145*math.sin(i*2*math.pi/len(labels)-math.pi/2)))
        for i in range(len(pts)-1):
            draw.line((pts[i],pts[i+1]),fill=line,width=6);t=(progress+i/len(pts))%1;x=pts[i][0]+(pts[i+1][0]-pts[i][0])*t;y=pts[i][1]+(pts[i+1][1]-pts[i][1])*t;draw.ellipse((x-9,y-9,x+9,y+9),fill=orange)
        for (x,y),label in zip(pts,labels):draw.ellipse((x-68,y-68,x+68,y+68),fill=pale,outline=blue,width=4);_label(draw,x,y,label,font)


def scene_image(scene,index,total,fontpath,source,progress=0.5,mouth_open=False,subtitle=None):
    im=Image.new('RGB',(1280,720),'#f3f8ff'); d=ImageDraw.Draw(im)
    h=ImageFont.truetype(fontpath,32); f=ImageFont.truetype(fontpath,24); small=ImageFont.truetype(fontpath,18)
    d.ellipse((-100,450,300,850),fill='#dbf5eb'); d.ellipse((1050,-160,1420,210),fill='#ffecd3')
    d.text((42,22),'ResearchLens · 科普动画',font=small,fill='#277d80'); d.text((42,57),scene['title'],font=h,fill='#234569')
    d.rounded_rectangle((35,125,1245,570),radius=28,fill='white',outline='#cddff3',width=3)
    diagram=Image.new('RGB',(850,580),'white'); _visual(ImageDraw.Draw(diagram),scene,progress,f)
    im.paste(diagram.crop((0,150,850,530)).resize((1120,380),Image.Resampling.LANCZOS),(80,160))
    d.rounded_rectangle((42,615,1238,693),radius=18,fill='#e3eefb')
    text=subtitle if subtitle is not None else scene['narration']; lines=[]; line=''
    for char in text:
        if d.textlength(line+char,font=f)>1120: lines.append(line); line=char
        else: line+=char
    if line: lines.append(line)
    for j,line in enumerate(lines[:2]): d.text((65,624+j*29),line,font=f,fill='#234569')
    d.text((45,587),f'{index+1}/{total} · '+source[:60],font=small,fill='#758ca7')
    return im
