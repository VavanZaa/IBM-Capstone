"""Render this report's PPTX text, tables, pictures and template backgrounds to PDF.

This scoped Open XML renderer preserves the original 960 x 540 pt canvas.
Abadi falls back to Helvetica, as in the inspected native template PDF.
"""
from pathlib import Path
import posixpath
import zipfile
import xml.etree.ElementTree as E
import fitz

ROOT = Path(__file__).resolve().parents[1]
PPTX = ROOT / "output/SpaceX_Capstone_Final_Presentation.pptx"
PDF = PPTX.with_suffix(".pdf")
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
def pt(value): return int(value) / 12700
def color(value): return tuple(int(value[i:i+2],16)/255 for i in [0,2,4])

with zipfile.ZipFile(PPTX) as z:
    package={name:z.read(name) for name in z.namelist()}
def rels(part):
    folder,name=posixpath.split(part)
    rp=f"{folder}/_rels/{name}.rels"
    return {r.get("Id"):posixpath.normpath(posixpath.join(folder,r.get("Target")))
            for r in E.fromstring(package[rp]) if r.get("TargetMode")!="External"}
def rect(xfrm):
    off=xfrm.find("a:off",NS);ext=xfrm.find("a:ext",NS)
    x,y,w,h=pt(off.get("x")),pt(off.get("y")),pt(ext.get("cx")),pt(ext.get("cy"))
    return fitz.Rect(x,y,x+w,y+h)

overflow=[]
def text(page,tx,box,slide_no,table=False):
    cursor=box.y0
    for para in tx.findall("a:p",NS):
        runs=para.findall("a:r",NS)
        value="".join((r.findtext("a:t","",NS)) for r in runs)
        if not value:
            cursor+=8
            continue
        rp=runs[0].find("a:rPr",NS)
        size=float(rp.get("sz","1800"))/100 if rp is not None else 18
        bold=rp is not None and rp.get("b")=="1"
        face=rp.find("a:latin",NS) if rp is not None else None
        family=face.get("typeface","") if face is not None else ""
        font="cour" if family=="Courier New" else ("hebo" if bold else "helv")
        rgb=rp.find("a:solidFill/a:srgbClr",NS) if rp is not None else None
        ink=color(rgb.get("val")) if rgb is not None else color("25354B")
        f=fitz.Font(font)
        words=value.split()
        lines=[];line=""
        for word in words:
            candidate=(line+" "+word).strip()
            if line and f.text_length(candidate,fontsize=size)>box.width:
                lines.append(line);line=word
            else:line=candidate
        if line:lines.append(line)
        # Baseline and line height use the renderer's actual font metrics.
        line_height=size*1.12
        needed=(len(lines)-1)*line_height+size*(f.ascender-f.descender)
        if cursor+needed>box.y1+2:
            overflow.append((slide_no,value,round(needed,1),round(box.y1-cursor,1)))
        baseline=cursor+size*f.ascender
        for line in lines:
            page.insert_text((box.x0,baseline),line,fontname=font,fontsize=size,color=ink)
            baseline+=line_height
        cursor+=needed+(0 if table else 6)

presentation=E.fromstring(package["ppt/presentation.xml"])
pr=rels("ppt/presentation.xml")
size=presentation.find("p:sldSz",NS)
doc=fitz.open()
for index,entry in enumerate(presentation.find("p:sldIdLst",NS),1):
    part=pr[entry.get("{"+NS["r"]+"}id")]
    slide=E.fromstring(package[part]);sr=rels(part)
    page=doc.new_page(width=pt(size.get("cx")),height=pt(size.get("cy")))
    bg=slide.find("p:cSld/p:bg/p:bgPr/a:blipFill/a:blip",NS)
    if bg is not None:
        page.insert_image(page.rect,stream=package[sr[bg.get("{"+NS["r"]+"}embed")]])
    tree=slide.find("p:cSld/p:spTree",NS)
    for shape in tree:
        tag=shape.tag.split("}")[-1]
        if tag=="sp":
            xf=shape.find("p:spPr/a:xfrm",NS)
            tx=shape.find("p:txBody",NS)
            if xf is not None and tx is not None:
                text(page,tx,rect(xf),index)
                links=tx.findall(".//a:hlinkClick",NS)
                if links:
                    folder,name=posixpath.split(part)
                    relationships=E.fromstring(package[f"{folder}/_rels/{name}.rels"])
                    for link in links:
                        rid=link.get("{"+NS["r"]+"}id")
                        target=next((r.get("Target") for r in relationships
                                     if r.get("Id")==rid and r.get("TargetMode")=="External"),None)
                        if target:
                            page.insert_link({"kind":fitz.LINK_URI,"from":rect(xf),"uri":target})
        elif tag=="pic":
            xf=shape.find("p:spPr/a:xfrm",NS)
            blip=shape.find("p:blipFill/a:blip",NS)
            if xf is not None and blip is not None:
                page.insert_image(rect(xf),stream=package[sr[blip.get("{"+NS["r"]+"}embed")]])
        elif tag=="graphicFrame":
            tbl=shape.find("a:graphic/a:graphicData/a:tbl",NS)
            if tbl is None:continue
            box=rect(shape.find("p:xfrm",NS))
            widths=[pt(c.get("w")) for c in tbl.find("a:tblGrid",NS)]
            y=box.y0
            for row in tbl.findall("a:tr",NS):
                height=pt(row.get("h"));x=box.x0
                for cell,width in zip(row.findall("a:tc",NS),widths):
                    tcpr=cell.find("a:tcPr",NS)
                    fill=tcpr.find("a:solidFill/a:srgbClr",NS)
                    page.draw_rect(fitz.Rect(x,y,x+width,y+height),color=None,fill=color(fill.get("val")))
                    text(page,cell.find("a:txBody",NS),
                         fitz.Rect(x+8,y+5,x+width-6,y+height-4),index,table=True)
                    x+=width
                y+=height
    print(f"Rendered slide {index}",flush=True)
doc.set_metadata({
    "title":"SpaceX Capstone: Winning Space Race with Data Science",
    "author":"Vavan Farizzaman",
    "subject":"IBM Applied Data Science Capstone final report",
    "creator":"Python Open XML presentation renderer",
})
if overflow:
    print("TEXT FIT ISSUES")
    for issue in overflow: print(issue)
    raise RuntimeError("Resolve text fit before exporting the final PDF.")
doc.save(PDF,garbage=4,deflate=True)
print("Saved",PDF)
render=ROOT/".build/rendered"
render.mkdir(exist_ok=True)
for i,page in enumerate(doc,1):
    page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(render/f"slide_{i:02d}.png")
print(f"Rendered {len(doc)} slide previews")
