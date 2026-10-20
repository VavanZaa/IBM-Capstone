"""Populate the IBM template with editable Open XML text and tables.

Uses only the Python standard library and Pillow. The original template stays
unchanged. Export the generated PPTX to PDF with Keynote or PowerPoint.
"""
from pathlib import Path
import copy
import json
import re
import zipfile
import xml.etree.ElementTree as E
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "presentation"
OUT = WORK / "output"
NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
for key, value in NS.items():
    E.register_namespace(key, value)
def q(s):
    prefix, name = s.split(":")
    return f"{{{NS[prefix]}}}{name}"
def add(parent, tag, **attrs):
    return E.SubElement(parent, q(tag), {k: str(v) for k,v in attrs.items()})
def emu(pt):
    return str(round(pt*12700))
def xml(root):
    return E.tostring(root, encoding="utf-8", xml_declaration=True)

source = ROOT / "ds-capstone-template-coursera.pptx"
with zipfile.ZipFile(source) as z:
    package = {n: z.read(n) for n in z.namelist()}
records = {}
all_sources = {
    "API": "jupyter-labs-spacex-data-collection-api-v2.ipynb; dataset_part_1.csv; data/spacex_lab_metadata.json",
    "Scraping": "jupyter-labs-webscraping.ipynb; spacex_web_scraped.csv; https://en.wikipedia.org/wiki/Special:PermanentLink/1027686922",
    "Wrangling": "labs-jupyter-spacex-Data wrangling-v2.ipynb; dataset_part_2.csv",
    "EDA": "jupyter-labs-eda-dataviz-v2.ipynb; dataset_part_2.csv; dataviz_outputs/",
    "SQL": "jupyter-labs-eda-sql-coursera_sqllite.ipynb; my_data1.db, SPACEXTABLE; data/Spacex.csv",
    "Folium": "lab-jupyter-launch-site-location-v2.ipynb; location_outputs/; data/spacex_launch_geo.csv; data/launch_site_osm_features.json; https://www.openstreetmap.org/copyright",
    "Dash": "spacex_dash_app.py; data/spacex_launch_dash.csv; DASHBOARD_INSIGHTS.txt",
    "ML": "SpaceX-Machine-Learning-Prediction-Part-5-v1.ipynb; ml_outputs/course_model_comparison.csv; ml_outputs/fold_scaled_model_comparison.csv; ml_outputs/course_test_predictions.csv",
}

class Slide:
    def __init__(self, number, title=None, source_key=None, template_number=None):
        self.n = number
        original = template_number or number
        self.root = E.fromstring(package[f"ppt/slides/slide{original}.xml"])
        self.rels = E.fromstring(package[f"ppt/slides/_rels/slide{original}.xml.rels"])
        # Keep original masters, layouts, full-slide images and section artwork.
        self.tree = self.root.find("p:cSld/p:spTree", NS)
        for node in list(self.tree):
            if node.tag in {q("p:sp"), q("p:graphicFrame"), q("p:cxnSp")}:
                self.tree.remove(node)
        if number not in [1, 5, 17, 34, 38, 42, 47]:
            for node in list(self.tree):
                if node.tag == q("p:pic"):
                    self.tree.remove(node)
        self.id = 100
        self.notes = ""
        self.manifest = {"title":title or "Template artwork", "texts":[], "images":[], "tables":[]}
        if title:
            self.text(title, 66, 41, 825, 52, size=28, color="0B49CB")
            display_number = number - 1 if number in [48, 49, 50] else number
            self.text(str(display_number), 891, 494, 30, 15, size=10, color="397CAC")
        if source_key:
            self.notes = "Sources: " + all_sources[source_key] + "\n"
            self.text("Source: " + source_key + " lab. Detailed references in speaker notes.",
                      67, 502, 780, 17, size=10, color="536274")
    def text(self, text, x, y, w, h, size=19, color="25354B", bold=False, font="Abadi", hyperlink=None):
        self.id += 1
        s = add(self.tree, "p:sp")
        nv=add(s,"p:nvSpPr");add(nv,"p:cNvPr",id=self.id,name=f"Text {self.id}")
        add(nv,"p:cNvSpPr",txBox="1");add(nv,"p:nvPr")
        pr=add(s,"p:spPr");tr=add(pr,"a:xfrm")
        add(tr,"a:off",x=emu(x),y=emu(y));add(tr,"a:ext",cx=emu(w),cy=emu(h))
        add(add(pr,"a:prstGeom",prst="rect"),"a:avLst");add(pr,"a:noFill")
        tx=add(s,"p:txBody");add(tx,"a:bodyPr",wrap="square",lIns="0",tIns="0",rIns="0",bIns="0",anchor="t");add(tx,"a:lstStyle")
        for line in text.split("\n"):
            p=add(tx,"a:p");pp=add(p,"a:pPr")
            add(add(pp,"a:lnSpc"),"a:spcPct",val="112000")
            add(add(pp,"a:spcAft"),"a:spcPts",val="600")
            add(pp,"a:buNone")
            r=add(p,"a:r");rp=add(r,"a:rPr",lang="en-US",sz=round(size*100),b=int(bold))
            add(add(rp,"a:solidFill"),"a:srgbClr",val=color);add(rp,"a:latin",typeface=font)
            if hyperlink:
                rid=f"rIdLink{self.id}"
                if not any(node.get("Id")==rid for node in self.rels):
                    E.SubElement(self.rels,f"{{{REL}}}Relationship",{
                        "Id":rid,"Type":NS["r"]+"/hyperlink",
                        "Target":hyperlink,"TargetMode":"External"})
                add(rp,"a:hlinkClick",**{q("r:id"):rid})
            add(r,"a:t").text=line
            add(p,"a:endParaRPr",lang="en-US",sz=round(size*100))
        self.manifest["texts"].append({"text":text,"box":[x,y,w,h],"size":size})
    def bullets(self, items, x=68,y=135,w=820,size=21,gap=77):
        for i,item in enumerate(items):
            self.text(item,x,y+i*gap,w,gap-8,size=size)
    def picture(self, path, x,y,w,h):
        path=Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        with Image.open(path) as im:
            iw,ih=im.size
        scale=min(w/iw,h/ih); pw=iw*scale;ph=ih*scale
        x+=(w-pw)/2;y+=(h-ph)/2
        self.id+=1
        name=f"presentation_{self.n}_{self.id}.png"
        package["ppt/media/"+name]=path.read_bytes()
        rid=f"rIdAsset{self.id}"
        E.SubElement(self.rels,f"{{{REL}}}Relationship",{
            "Id":rid,"Type":NS["r"]+"/image","Target":"../media/"+name})
        pic=add(self.tree,"p:pic");nv=add(pic,"p:nvPicPr")
        add(nv,"p:cNvPr",id=self.id,name=path.name,descr=path.stem)
        add(add(nv,"p:cNvPicPr"),"a:picLocks",noChangeAspect="1");add(nv,"p:nvPr")
        fill=add(pic,"p:blipFill");add(fill,"a:blip",**{q("r:embed"):rid})
        add(add(fill,"a:stretch"),"a:fillRect")
        pr=add(pic,"p:spPr");tr=add(pr,"a:xfrm")
        add(tr,"a:off",x=emu(x),y=emu(y));add(tr,"a:ext",cx=emu(pw),cy=emu(ph))
        add(add(pr,"a:prstGeom",prst="rect"),"a:avLst")
        self.manifest["images"].append(str(path.relative_to(ROOT)))
    def table(self, headers, rows, x=68,y=180,w=820,row_h=34,widths=None,size=17):
        self.id+=1
        gf=add(self.tree,"p:graphicFrame");nv=add(gf,"p:nvGraphicFramePr")
        add(nv,"p:cNvPr",id=self.id,name=f"Results table {self.n}")
        add(nv,"p:cNvGraphicFramePr");add(nv,"p:nvPr")
        tr=add(gf,"p:xfrm");add(tr,"a:off",x=emu(x),y=emu(y))
        add(tr,"a:ext",cx=emu(w),cy=emu(row_h*(len(rows)+1)))
        gd=add(add(gf,"a:graphic"),"a:graphicData",uri=NS["a"]+"/table")
        tbl=add(gd,"a:tbl");add(tbl,"a:tblPr",firstRow="1",bandRow="0")
        grid=add(tbl,"a:tblGrid")
        widths=widths or [1/len(headers)]*len(headers)
        for width in widths:add(grid,"a:gridCol",w=emu(w*width))
        for i,row in enumerate([headers]+rows):
            tr=add(tbl,"a:tr",h=emu(row_h))
            for val in row:
                tc=add(tr,"a:tc");tx=add(tc,"a:txBody")
                add(tx,"a:bodyPr");add(tx,"a:lstStyle")
                p=add(tx,"a:p");add(add(p,"a:pPr"),"a:buNone")
                r=add(p,"a:r");rp=add(r,"a:rPr",lang="en-US",sz=round(size*100),b=int(i==0))
                add(add(rp,"a:solidFill"),"a:srgbClr",val="FFFFFF" if i==0 else "25354B")
                add(rp,"a:latin",typeface="Abadi");add(r,"a:t").text=str(val)
                pr=add(tc,"a:tcPr",marL=emu(8),marR=emu(6),marT=emu(5),marB=emu(4),anchor="ctr")
                add(add(pr,"a:solidFill"),"a:srgbClr",val="0B49CB" if i==0 else ("E7EDF6" if i%2 else "FFFFFF"))
        self.manifest["tables"].append({"headers":headers,"rows":rows})
    def finish(self):
        notes=E.Element(q("p:notes"))
        cs=add(notes,"p:cSld");st=add(cs,"p:spTree")
        nv=add(st,"p:nvGrpSpPr");add(nv,"p:cNvPr",id="1",name="");add(nv,"p:cNvGrpSpPr");add(nv,"p:nvPr")
        add(st,"p:grpSpPr")
        sp=add(st,"p:sp");nv=add(sp,"p:nvSpPr");add(nv,"p:cNvPr",id="2",name="Notes")
        add(nv,"p:cNvSpPr");add(add(nv,"p:nvPr"),"p:ph",type="body",idx="1");add(sp,"p:spPr")
        tx=add(sp,"p:txBody");add(tx,"a:bodyPr");add(tx,"a:lstStyle")
        for line in self.notes.split("\n"):
            add(add(add(tx,"a:p"),"a:r"),"a:t").text=line
        package[f"ppt/notesSlides/notesSlide{self.n}.xml"]=xml(notes)
        notesrels=E.Element(f"{{{REL}}}Relationships")
        E.SubElement(notesrels,f"{{{REL}}}Relationship",Id="rId1",Type=NS["r"]+"/slide",Target=f"../slides/slide{self.n}.xml")
        package[f"ppt/notesSlides/_rels/notesSlide{self.n}.xml.rels"]=xml(notesrels)
        for node in list(self.rels):
            if node.get("Type","").endswith("/notesSlide"):self.rels.remove(node)
        E.SubElement(self.rels,f"{{{REL}}}Relationship",Id="rIdNotes",Type=NS["r"]+"/notesSlide",Target=f"../notesSlides/notesSlide{self.n}.xml")
        package[f"ppt/slides/slide{self.n}.xml"]=xml(self.root)
        package[f"ppt/slides/_rels/slide{self.n}.xml.rels"]=xml(self.rels)
        records[self.n]=self.manifest

def simple(n,title,items,source=None,size=21,gap=77):
    s=Slide(n,title,source);s.bullets(items,size=size,gap=gap);s.finish()
def figure(n,title,img,items,source="EDA"):
    s=Slide(n,title,source)
    s.picture(ROOT/img,325,125,585,340)
    s.bullets(items,x=68,y=145,w=240,size=18,gap=100);s.finish()
def sql(n,title,query,headers,rows,note="",widths=None,size=17,row_h=34):
    s=Slide(n,title,"SQL");s.text(query,68,117,820,84,size=14,font="Courier New")
    s.table(headers,rows,y=210,row_h=row_h,widths=widths,size=size)
    s.text(note,68,450,820,42,size=16)
    s.notes+="SQL query:\n"+query+"\n"+note;s.finish()

s=Slide(1);s.text("Vavan Farizzaman\n20 October 2026",77,368,380,70,size=20,color="FFFFFF")
s.notes="IBM Applied Data Science Capstone. Original IBM template imagery retained. Historical course datasets, not a statement about current launch prices.";s.finish()
simple(2,"Outline",[
    "Project question and executive summary",
    "Data collection, preparation and analytical methods",
    "Visualization and SQL findings",
    "Folium maps and the Plotly Dash dashboard",
    "Classification results, conclusions and technical appendix",
],size=21,gap=62)
simple(3,"Executive Summary",[
    "90 Falcon 9 launches support the main analysis. The course label marks 60 successful outcomes (66.7%).",
    "Collection combines an API snapshot with documented enrichment. Scraping and the SQL/dashboard labs use separate datasets.",
    "KSC LC-39A leads the dashboard sample: 10 successes from 13 launches (76.9%).",
    "SVM, logistic regression and KNN each classify 15 of 18 test launches correctly. Training CV selects SVM.",
],source="ML",size=21,gap=80)
simple(4,"Introduction",[
    "Business context: first-stage recovery can support reuse and influence launch economics.",
    "Question: which observed launch characteristics are associated with successful first-stage outcomes?",
    "Approach: inspect payload, orbit, launch site and time, then compare four binary classifiers.",
    "Scope: a historical learning exercise. Landing classification alone does not estimate launch cost or guarantee future recovery.",
],source="Wrangling",size=21,gap=80)
for n in [5,17,34,38,42,47]:
    s=Slide(n)
    s.text(str(50 if n == 47 else n),900,505,24,18,size=10,color="FFFFFF")
    s.notes="Original IBM Skills Network template section artwork retained.";s.finish()
simple(6,"Methodology",[
    "1. Collect and reconcile launch data, resource IDs and source provenance.",
    "2. Clean fields, label outcomes and encode 80 numerical features.",
    "3. Explore patterns through Python charts, SQL queries and interactive maps.",
    "4. Filter dashboard views by site and payload mass.",
    "5. Tune four classifiers with 10-fold CV and evaluate a fixed 18-row test sample.",
],size=20,gap=63)
s=Slide(7,"Data Collection","API")
s.table(["Source","Records","Use"],[
    ["API-derived Falcon 9 sample","90","Wrangling, EDA and classification"],
    ["Wikipedia historical revision","121","Independent scraping exercise"],
    ["Course SQL dataset","101","SQL aggregation and filters"],
    ["Course map/dashboard datasets","56 each","Interactive analytics"],
],y=145,row_h=51,widths=[.38,.14,.48],size=19)
s.text("Different scopes and labels produce different totals. These datasets are not pooled.",68,430,820,42,size=20)
s.notes+="Source paths: data/API_call_spacex_api.json; spacex_web_scraped.csv; data/Spacex.csv; data/spacex_launch_geo.csv; data/spacex_launch_dash.csv.";s.finish()
s=Slide(8,"Data Collection: SpaceX API","API")
s.bullets(["Launch JSON supplies resource IDs, not all enrichment fields.",
           "Archived API records and course reference data supply documented historical metadata.",
           "Timeouts and caching keep requests explicit and repeatable."],x=68,y=145,w=340,size=19,gap=97)
s.table(["Step","Output"],[["1. Read launch snapshot","94 retained launch rows"],
    ["2. Resolve resource IDs","Rockets, payloads, cores, pads"],
    ["3. Keep Falcon 9","90 rows, excluding 4 Falcon 1"],
    ["4. Export","dataset_part_1.csv"]],x=440,y=140,w=450,row_h=59,widths=[.45,.55],size=17)
s.notes+="Live API retrieval timed out. No fabricated enrichment values were used. Resource-level provenance is retained in data/spacex_lab_metadata.json.";s.finish()
s=Slide(9,"Data Collection: Web Scraping","Scraping")
s.table(["Step","Method"],[
    ["1. Retrieve","Read the 9 June 2021 Wikipedia revision"],
    ["2. Parse","BeautifulSoup extracts Falcon 9 launch tables"],
    ["3. Normalize","Clean dates, payloads, sites and outcomes"],
    ["4. Filter and export","121 numeric-flight rows in spacex_web_scraped.csv"],
],y=145,row_h=55,widths=[.25,.75],size=20)
s.text("The lab's numeric flight-number rule excludes Falcon Heavy rows labelled FH. Unknown payload masses remain missing.",68,430,820,52,size=18);s.finish()
s=Slide(10,"Data Wrangling","Wrangling")
s.table(["Stage","Implementation"],[
    ["Clean","Keep Falcon 9, normalize fields and impute missing payload mass with the mean"],
    ["Label","Class 1: True ASDS, True RTLS or True Ocean. Other listed outcomes: class 0"],
    ["Check","90 launches: 60 class 1 and 30 class 0. True ASDS contributes 41"],
    ["Encode","One-hot encode orbit, site, landing pad and serial. Produce 80 float64 features"],
],y=135,row_h=56,widths=[.17,.83],size=19)
s.text("Outcome and Class are excluded from the feature matrix. Successful ocean outcomes remain included in the course target.",68,430,820,55,size=18);s.finish()
s=Slide(11,"EDA with Data Visualization","EDA")
s.table(["Plot","Analytical purpose"],[
    ["Flight number vs. site and orbit","Inspect historical progression and category coverage"],
    ["Payload vs. site and orbit","Compare operating ranges and overlapping outcomes"],
    ["Success rate by orbit","Compare outcome proportions with sample counts"],
    ["Yearly average success rate","Describe change over time without assuming causality"],
],y=145,row_h=58,widths=[.44,.56],size=20)
s.text("Color encodes Class. Counts accompany rates so small categories do not look as reliable as large samples.",68,443,820,47,size=18);s.finish()
simple(12,"EDA with SQL",[
    "SQLite stores 101 rows in a cleaned SPACEXTABLE, with dates and labels trimmed.",
    "DISTINCT and LIKE identify sites. SUM and AVG aggregate payload mass.",
    "MIN and MAX locate milestones and payload extremes. A subquery retains all maximum-payload boosters.",
    "CASE separates mission outcomes. GROUP BY counts landing outcomes within an inclusive date window.",
],source="SQL",size=21,gap=82)
simple(13,"Interactive Map Methodology",[
    "Folium markers and circles identify launch sites. Popups preserve site names and counts.",
    "Green/red markers show class 1/0. MarkerCluster groups overlapping launch coordinates.",
    "Mouse coordinates, click popups and distance lines support proximity inspection.",
    "OpenStreetMap features provide coastline, internal rail spur, major road and town-centre reference points.",
],source="Folium",size=21,gap=82)
simple(14,"Plotly Dash Methodology",[
    "A searchable launch-site dropdown filters both charts.",
    "All Sites shows successful outcome counts by site. A selected site shows its success/failure split.",
    "A 0-10,000 kg range slider filters the scatter plot, including both endpoints.",
    "Scatter points use payload mass and class, with a consistent color for each booster category.",
],source="Dash",size=21,gap=82)
s=Slide(15,"Predictive Analysis Methodology","ML")
s.table(["Stage","Specification"],[
    ["Inputs","90 rows, 80 numerical features and binary Class labels"],
    ["Holdout","72 train / 18 test. test_size=0.2, random_state=2"],
    ["Models","Logistic regression, SVM, decision tree and KNN"],
    ["Tuning","GridSearchCV, 10 folds, accuracy scoring"],
    ["Scaling check","Repeat with StandardScaler inside each training-fold pipeline"],
],y=135,row_h=48,widths=[.22,.78],size=19)
s.text("The course sequence scales before splitting. The extra comparison addresses this scaling leakage while retaining the same test rows.",68,442,820,47,size=18)
s.notes+="Hyperparameter grids and exact split indices are in the notebook and ml_outputs/run_summary.json. Upstream imputation and category generation still precede the split.";s.finish()
s=Slide(16,"Results Overview")
s.table(["Analysis","Finding"],[
    ["Python EDA, 90 launches","60 successful course labels. Orbit and year patterns differ"],
    ["SQL, 101 launches","100 mission successes and 1 mission failure"],
    ["Dashboard, 56 launches","KSC LC-39A leads in count and success rate"],
    ["Classification, 18 test rows","Three methods tie at 83.3% accuracy"],
],y=145,row_h=54,widths=[.33,.67],size=18)
s.text("The following sections preserve each dataset's denominator and outcome definition.",68,440,820,46,size=20);s.finish()
figure(18,"Flight Number vs. Launch Site","dataviz_outputs/01_flight_number_vs_launch_site.png",[
    "CCAFS SLC 40 contributes 55 of 90 launches.",
    "KSC: 17/22 successes. VAFB: 10/13. CCAFS: 33/55.",
    "Sites operate over different periods. A site effect is not isolated."
])
figure(19,"Payload vs. Launch Site","dataviz_outputs/02_payload_vs_launch_site.png",[
    "Payload ranges overlap across launch sites.",
    "Both classes occur at similar masses. Mass alone does not separate outcomes.",
    "Site comparisons should account for orbit and booster generation."
])
figure(20,"Success Rate by Orbit","dataviz_outputs/03_success_rate_by_orbit.png",[
    "VLEO: 12/14 successes (85.7%). GTO: 14/27 (51.9%).",
    "SSO: 5/5. GEO, HEO and ES-L1 each have only one launch.",
    "A 100% rate from one launch has very little supporting evidence."
])
figure(21,"Flight Number vs. Orbit","dataviz_outputs/04_flight_number_vs_orbit.png",[
    "Orbit categories occur at different stages of the launch history.",
    "Later VLEO missions coincide with a more mature launch program.",
    "Time and mission mix can confound an apparent orbit effect."
])
figure(22,"Payload vs. Orbit","dataviz_outputs/05_payload_vs_orbit.png",[
    "Orbit constrains the payload range represented in the data.",
    "GTO has 27 launches with mixed outcomes.",
    "The scatter plot supports joint analysis of payload and orbit."
])
figure(23,"Yearly Success Trend","dataviz_outputs/06_yearly_success_rate.png",[
    "2013: 0/3. 2017: 15/18. 2020: 16/19 successful labels.",
    "The rate generally improves but drops to 11/18 in 2018.",
    "No 2011 record appears in this sample. Missing years are not zero rates."
])
sql(24,"Unique Launch Sites",
    "SELECT DISTINCT Launch_Site\nFROM SPACEXTABLE ORDER BY Launch_Site;",
    ["Launch site"],[["CCAFS LC-40"],["CCAFS SLC-40"],["KSC LC-39A"],["VAFB SLC-4E"]],
    "Four labels appear in the SQL source. This spelling differs from the 90-row API-derived sample.")
sql(25,"First Five Records Matching CCA",
    "SELECT Date, Booster_Version, Launch_Site\nFROM SPACEXTABLE WHERE Launch_Site LIKE 'CCA%'\nORDER BY Date, \"Time (UTC)\" LIMIT 5;",
    ["Date","Booster","Launch site"],[
        ["2010-06-04","F9 v1.0 B0003","CCAFS LC-40"],
        ["2010-12-08","F9 v1.0 B0004","CCAFS LC-40"],
        ["2012-05-22","F9 v1.0 B0005","CCAFS LC-40"],
        ["2012-10-08","F9 v1.0 B0006","CCAFS LC-40"],
        ["2013-03-01","F9 v1.0 B0007","CCAFS LC-40"]],
    "An explicit chronological order makes LIMIT 5 reproducible.",widths=[.25,.4,.35])
sql(26,"Total Payload for NASA (CRS)",
    "SELECT SUM(PAYLOAD_MASS__KG_) AS Total_Payload_Mass_KG\nFROM SPACEXTABLE WHERE Customer = 'NASA (CRS)';",
    ["Customer filter","Total payload mass"],[["NASA (CRS), exact label","45,596 kg"]],
    "This total covers the NASA (CRS) category only. It does not combine other NASA customer labels.",
    widths=[.55,.45],size=23,row_h=64)
sql(27,"Average Payload for F9 v1.1",
    "SELECT AVG(PAYLOAD_MASS__KG_) AS Average_Payload_Mass_KG\nFROM SPACEXTABLE WHERE Booster_Version = 'F9 v1.1';",
    ["Booster filter","Average payload mass"],[["F9 v1.1, exact label","2,928.4 kg"]],
    "Serial-number variants are separate strings and do not match this exact filter.",
    widths=[.55,.45],size=23,row_h=64)
sql(28,"First Successful Ground-Pad Landing",
    "SELECT MIN(Date) AS First_Successful_Ground_Pad_Landing\nFROM SPACEXTABLE\nWHERE Landing_Outcome = 'Success (ground pad)';",
    ["Landing outcome","Earliest date in dataset"],[["Success (ground pad)","22 December 2015"]],
    "The result follows the SQL dataset's date field.",widths=[.55,.45],size=23,row_h=64)
sql(29,"Drone-Ship Successes at 4,000-6,000 kg",
    "SELECT DISTINCT Booster_Version FROM SPACEXTABLE\nWHERE Landing_Outcome = 'Success (drone ship)'\nAND PAYLOAD_MASS__KG_ > 4000 AND PAYLOAD_MASS__KG_ < 6000;",
    ["Matching booster versions"],[["F9 FT B1021.2"],["F9 FT B1031.2"],["F9 FT B1022"],["F9 FT B1026"]],
    "Strict bounds exclude payloads equal to 4,000 or 6,000 kg.")
sql(30,"Mission Outcomes in the SQL Dataset",
    "SELECT CASE WHEN Mission_Outcome LIKE 'Success%' THEN 'Success'\nWHEN Mission_Outcome LIKE 'Failure%' THEN 'Failure' END AS Result,\nCOUNT(*) FROM SPACEXTABLE GROUP BY Result;",
    ["Mission outcome","Count","Share"],[["Success","100","99.0%"],["Failure","1","1.0%"]],
    "Mission success concerns the mission objective. Booster landing outcomes are a different field.",
    widths=[.5,.25,.25],size=22,row_h=54)
s=Slide(31,"Boosters Carrying the Maximum Payload","SQL")
s.text("SELECT DISTINCT Booster_Version FROM SPACEXTABLE\nWHERE PAYLOAD_MASS__KG_ = (SELECT MAX(PAYLOAD_MASS__KG_) FROM SPACEXTABLE);",
       68,116,820,60,size=13,font="Courier New")
s.text("Maximum payload mass: 15,600 kg. Twelve distinct booster-version records match.",68,181,820,43,size=20)
s.table(["Booster version","Booster version"],[
    ["F9 B5 B1048.4","F9 B5 B1051.4"],["F9 B5 B1048.5","F9 B5 B1051.6"],
    ["F9 B5 B1049.4","F9 B5 B1056.4"],["F9 B5 B1049.5","F9 B5 B1058.3"],
    ["F9 B5 B1049.7","F9 B5 B1060.2"],["F9 B5 B1051.3","F9 B5 B1060.3"]],
    y=235,row_h=31,size=17)
s.notes+="Rows are displayed in two columns for compactness. All 12 result records are included.";s.finish()
sql(32,"Drone-Ship Landing Failures in 2015",
    "SELECT Date, Booster_Version, Launch_Site FROM SPACEXTABLE\nWHERE SUBSTR(Date, 1, 4) = '2015'\nAND Landing_Outcome = 'Failure (drone ship)' ORDER BY Date;",
    ["Month","Booster","Launch site"],[
        ["January","F9 v1.1 B1012","CCAFS LC-40"],
        ["April","F9 v1.1 B1015","CCAFS LC-40"]],
    "Both records have Landing_Outcome = Failure (drone ship).",
    widths=[.22,.43,.35],size=22,row_h=55)
s=Slide(33,"Landing Outcomes: June 2010 to March 2017","SQL")
s.text("SELECT Landing_Outcome, COUNT(*) FROM SPACEXTABLE\nWHERE Date BETWEEN '2010-06-04' AND '2017-03-20'\nGROUP BY Landing_Outcome ORDER BY COUNT(*) DESC;",
       68,116,820,70,size=14,font="Courier New")
s.table(["Landing outcome","Count"],[
    ["No attempt",10],["Failure (drone ship)",5],["Success (drone ship)",5],
    ["Controlled (ocean)",3],["Success (ground pad)",3],["Failure (parachute)",2],
    ["Uncontrolled (ocean)",2],["Precluded (drone ship)",1]],
    y=200,row_h=30,widths=[.8,.2],size=16)
s.text("31 launches match the inclusive date window. Counts are in descending order.",68,475,820,22,size=14);s.finish()
figure(35,"Launch Sites on the US Coasts","presentation/assets/folium_sites.png",[
    "The course data identifies four labels at coastal launch facilities.",
    "VAFB is in California. The other three labels are in Florida.",
    "Nearby Florida sites overlap at this map scale."
],source="Folium")
s=Slide(36,"Launch Outcomes Behind the Folium Markers","Folium")
s.table(["Launch site","Launches","Successes","Success rate"],[
    ["CCAFS LC-40",26,7,"26.9%"],["CCAFS SLC-40",7,3,"42.9%"],
    ["KSC LC-39A",13,10,"76.9%"],["VAFB SLC-4E",10,4,"40.0%"]],
    y=145,row_h=52,widths=[.4,.2,.2,.2],size=21)
s.text("The map encodes each launch as green (class 1) or red (class 0). Clusters group repeated site coordinates. This table makes the underlying rates explicit.",
       68,425,820,65,size=19)
s.notes+="Counts from location_outputs/launch_site_summary.csv. This slide reports the map's underlying records as an editable table.";s.finish()
figure(37,"CCAFS LC-40 Proximity Analysis","presentation/assets/folium_proximity.png",[
    "Coastline: 0.922 km. Major road: 6.385 km.",
    "Cape Canaveral centre: 19.568 km. Internal rail spur: about 3 m.",
    "Distances use mapped reference points. Rail is a local spur, not the external network."
],source="Folium")
figure(39,"Successful Outcomes Across All Sites","presentation/assets/dash_all.png",[
    "The 56-row dashboard sample contains 24 successful outcomes.",
    "KSC LC-39A contributes 10, or 41.7% of all successes.",
    "A pie share is different from a site's success rate."
],source="Dash")
figure(40,"KSC LC-39A Has the Highest Site Rate","presentation/assets/dash_ksc.png",[
    "10 successful and 3 unsuccessful outcomes.",
    "Success rate: 10/13 = 76.9%, the highest in this sample.",
    "The selected-site pie changes the denominator to that site's launches."
],source="Dash")
s=Slide(41,"Payload Filters Reveal Different Outcome Mixes","Dash")
s.picture(WORK/"assets/dash_payload_full.png",64,118,406,235)
s.picture(WORK/"assets/dash_payload_filtered.png",490,118,406,235)
s.text("Full payload range",68,360,390,25,size=17,bold=True)
s.text("Filtered payload range",494,360,390,25,size=17,bold=True)
s.text("Using fixed 1,000 kg bins: 3,000 to under 4,000 kg has 8/11 successes (72.7%). The 6,000 to under 7,000 kg bin has 0/4.",
       68,395,820,62,size=18)
s.text("B5 has 1/1 success. FT has 16/24, providing more evidence than a single B5 observation.",68,462,820,33,size=16)
s.notes+="The charts are exported directly from dashboard callbacks. Left: ALL sites, 0-10,000 kg. Right: ALL sites, 3,000-4,000 kg, inclusive. Bin endpoints differ from the dashboard's inclusive slider endpoints. See DASHBOARD_INSIGHTS.txt for the complete bin table.";s.finish()
figure(43,"Classification Accuracy","ml_outputs/05_model_comparison.png",[
    "Logistic regression, SVM and KNN tie: 15/18 correct (83.3%).",
    "Decision tree: 13/18 (72.2%). Majority baseline: 12/18 (66.7%).",
    "Fold-fitted scaling selects SVM by CV: 83.6% CV, 83.3% test."
],source="ML")
figure(44,"SVM Confusion Matrix","ml_outputs/02_svm_confusion.png",[
    "True negatives: 3. False positives: 3. False negatives: 0. True positives: 12.",
    "Success recall: 100%. Success precision: 80%. Specificity: 50%.",
    "All three errors predict success for an unsuccessful launch."
],source="ML")
simple(45,"Conclusions",[
    "Historical outcome rates differ by orbit, year and site. Their effects overlap and are not causal estimates.",
    "The dashboard's strongest site is KSC LC-39A at 10/13 successful outcomes.",
    "Three classifiers achieve 83.3% test accuracy. Training cross-validation favors SVM.",
    "Next steps: use a future-time holdout, rebuild preprocessing on training data, and audit feature availability before launch.",
],source="ML",size=21,gap=82)
s=Slide(46,"Appendix: Dataset and Label Register")
s.table(["Analysis","Rows","Positive outcome definition"],[
    ["API / EDA / ML","90","True ASDS, True RTLS or True Ocean"],
    ["SQL","101","Mission success and landing outcome are separate fields"],
    ["Folium / Dash","56 each","Supplied binary class in each course file"],
    ["Wikipedia scraping","121","Source outcome text, not merged into ML labels"],
],y=145,row_h=54,widths=[.25,.12,.63],size=19)
s.text("The main 90-row sample has 41 successful drone-ship outcomes. Including 14 ground and 5 ocean successes produces 60 positive labels.",68,435,820,55,size=19);s.finish()
s=Slide(48,"Additional Insights and Evaluation Limits","ML",template_number=46)
s.table(["Observation","Implication"],[
    ["15 correct predictions out of 18","Approximate 95% Wilson interval: 60.8%-94.2%"],
    ["3 of 6 class-0 launches predicted as class 1","Accuracy conceals a 50% false-positive rate for this class"],
    ["Five True Ocean outcomes count as positive","Excluding ocean outcomes gives 55/90 = 61.1%, not 66.7%"],
    ["Scaling inside CV changes model tuning","KNN chooses k=5 instead of k=6, despite the same test accuracy"],
],y=145,row_h=56,widths=[.45,.55],size=18)
s.text("These checks sharpen the interpretation. They do not justify claiming deployment readiness.",68,445,820,42,size=18)
s.notes+="Wilson interval uses 15 successes / 18 trials, z=1.96. This binomial interval does not account for model selection, temporal dependence or upstream preprocessing.";s.finish()
s=Slide(49,"Code and Reproducibility",template_number=46)
s.text("GitHub project repository",68,125,820,32,size=23,bold=True)
s.text("https://github.com/VavanZaa/IBM-Capstone",68,163,820,32,size=23,color="0B49CB",
       hyperlink="https://github.com/VavanZaa/IBM-Capstone")
s.table(["Artifact","Local location"],[
    ["Completed notebooks and Python files","capstone/"],
    ["Dataset snapshots and provenance","capstone/data/"],
    ["Charts, maps and model predictions","dataviz_outputs/, location_outputs/, ml_outputs/"],
    ["Dashboard entry point","spacex_dash_app.py"],
    ["Run instructions and dependencies","RUN_INSTRUCTIONS.txt and requirements.txt"],
],y=210,row_h=40,widths=[.42,.58],size=18)
s.text("Reproduce the dashboard with Python and rerun notebooks from top to bottom. This report uses the saved historical inputs.",68,457,820,42,size=16)
s.notes+="Project repository supplied by the author: https://github.com/VavanZaa/IBM-Capstone. The artifact table lists the local project locations.";s.finish()
s=Slide(50,"Sources and Technical References",template_number=46)
s.bullets([
    "IBM Skills Network course datasets: API_call_spacex_api.json, dataset_part_1.csv, Spacex.csv, spacex_launch_geo.csv and spacex_launch_dash.csv.",
    "Wikipedia historical launch tables: revision 1027686922, dated 9 June 2021.",
    "Archived SpaceX API metadata: resource URLs and field provenance in data/spacex_lab_metadata.json.",
    "OpenStreetMap contributors: extracted features dated 20 October 2026. ODbL attribution applies to the map data.",
    "scikit-learn: model selection and preprocessing guidance. Plotly Dash and Folium: interactive visualization libraries.",
],size=18,gap=65)
s.notes="""Dataset base: https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBM-DS0321EN-SkillsNetwork/
API snapshot: datasets/API_call_spacex_api.json
SQL: labs/module_2/data/Spacex.csv
Geo: datasets/spacex_launch_geo.csv
Dashboard: datasets/spacex_launch_dash.csv
Wikipedia: https://en.wikipedia.org/wiki/Special:PermanentLink/1027686922
OpenStreetMap: https://www.openstreetmap.org/copyright
scikit-learn: https://scikit-learn.org/1.6/common_pitfalls.html#data-leakage
Dash: https://dash.plotly.com/basic-callbacks
Folium: https://python-visualization.github.io/folium/
All numerical findings derive from local executed notebooks and associated CSV exports.
Template and template imagery: supplied IBM Skills Network ds-capstone-template-coursera.pptx."""
s.finish()

# Append technical slides before the original closing artwork.
order=list(range(1,47))+[48,49,50,47]
pres=E.fromstring(package["ppt/presentation.xml"])
ids=pres.find("p:sldIdLst",NS)
original_ids={i:copy.deepcopy(node) for i,node in enumerate(ids,1)}
for node in list(ids):ids.remove(node)
presrels=E.fromstring(package["ppt/_rels/presentation.xml.rels"])
for n in [48,49,50]:
    E.SubElement(presrels,f"{{{REL}}}Relationship",Id=f"rIdAdded{n}",
                 Type=NS["r"]+"/slide",Target=f"slides/slide{n}.xml")
for n in order:
    if n<=47:ids.append(original_ids[n])
    else:add(ids,"p:sldId",id=str(500+n),**{q("r:id"):f"rIdAdded{n}"})
package["ppt/presentation.xml"]=xml(pres)
package["ppt/_rels/presentation.xml.rels"]=xml(presrels)
content=E.fromstring(package["[Content_Types].xml"])
existing={x.get("PartName") for x in content}
for n in records:
    for path,ctype in [
        (f"/ppt/slides/slide{n}.xml","application/vnd.openxmlformats-officedocument.presentationml.slide+xml"),
        (f"/ppt/notesSlides/notesSlide{n}.xml","application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml")]:
        if path not in existing:E.SubElement(content,f"{{{CT}}}Override",PartName=path,ContentType=ctype)
E.register_namespace("", CT)
package["[Content_Types].xml"]=xml(content)
OUT.mkdir(exist_ok=True)
target=OUT/"SpaceX_Capstone_Final_Presentation.pptx"
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as z:
    for name,body in package.items():z.writestr(name,body)
(WORK/".build/slide_manifest.json").write_text(json.dumps(
    {"order":order,"slides":records},indent=2))
print(target)
print(f"{len(order)} slides, source masters and backgrounds preserved")
