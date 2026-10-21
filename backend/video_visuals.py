"""Science-video illustrations, including the restored dark split layout."""
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
    im=Image.new('RGB',(1280,720),'#0c2039'); d=ImageDraw.Draw(im)
    small=ImageFont.truetype(fontpath,18)
    d.text((46,28),'ResearchLens · 科普',font=small,fill='#74d7cf')
    title=str(scene.get('title','科普解读'))
    for size in range(32,19,-1):
        heading=ImageFont.truetype(fontpath,size)
        title_lines=_wrap(d,title,heading,1170)
        if len(title_lines)<=2:break
    for j,line in enumerate(title_lines[:2]):
        d.text((46,70+j*38),line,font=heading,fill='#f3f7ff')

    # Restore the four-node concept diagram and moving evidence markers.
    labels=list((scene.get('visual') or {}).get('labels') or ['研究问题','研究方法','主要发现','证据局限'])[:4]
    positions={1:[(395,350)],2:[(240,350),(570,350)],
               3:[(230,245),(570,350),(230,490)],
               4:[(230,245),(570,245),(230,490),(570,490)]}[len(labels)]
    edges=[(0,1),(1,2),(2,3)] if len(labels)==4 else [(i,i+1) for i in range(len(labels)-1)]
    for i,(a,b) in enumerate(edges):
        x1,y1=positions[a];x2,y2=positions[b]
        d.line((x1,y1,x2,y2),fill='#6686a8',width=4)
        t=(progress+i/max(1,len(edges)))%1
        x=x1+(x2-x1)*t;y=y1+(y2-y1)*t
        d.ellipse((x-7,y-7,x+7,y+7),fill='#74ddd1')
    for (x,y),label in zip(positions,labels):
        radius=67
        d.ellipse((x-radius,y-radius,x+radius,y+radius),fill='#234263',outline='#74d7cf',width=3)
        for size in range(24,11,-1):
            font=ImageFont.truetype(fontpath,size)
            lines=_wrap(d,str(label),font,112)
            if len(lines)*(size+4)<=100:break
        height=len(lines)*(size+4)
        for j,line in enumerate(lines):
            d.text((x-d.textlength(line,font=font)/2,y-height/2+j*(size+4)),line,font=font,fill='#e5effc')

    d.rounded_rectangle((800,145,1232,555),radius=24,fill='#1c3856')
    narration=str(scene.get('narration',''))
    for size in range(24,13,-1):
        font=ImageFont.truetype(fontpath,size)
        lines=_wrap(d,narration,font,380)
        if len(lines)*(size+10)<=354:break
    # Very long narration uses the current timed subtitle instead of clipping evidence.
    if len(lines)*(size+10)>354:
        font=ImageFont.truetype(fontpath,24);size=24
        lines=_wrap(d,subtitle or narration,font,380)
    for j,line in enumerate(lines[:354//(size+10)]):
        d.text((826,169+j*(size+10)),line,font=font,fill='#e2ecfb')
    d.text((65,575),'概念示意 · 非实验图片或定量结果',font=small,fill='#829cb6')
    source_lines=_wrap(d,str(source),small,1170)
    d.text((46,645),source_lines[0] if source_lines else '',font=small,fill='#829cb6')
    d.text((46,688),f'{index+1} / {total}',font=small,fill='#74d7cf')
    d.rounded_rectangle((160,695,1230,701),radius=3,fill='#243e59')
    end=160+int(1070*(index+1)/max(1,total))
    d.rounded_rectangle((160,695,end,701),radius=3,fill='#74d7cf')
    return im
