"""
Simple tool for automatically retrieving and merging .m files

Retrieves the files from autohost, merges them, and creates
an html index with newest file and index. 

I place the output in a (password protected) public html folder.
If you and your ally both run the tool you can also keep ik local.
"""


import requests, re, sys, os, shutil, subprocess

MERGE_TOOL = "/home/wva/stars/StarsFileMerger.jar"

tmpdir = "/tmp/merge"
if not os.path.exists(tmpdir):
    os.mkdir(tmpdir)
    
outdir = "/home/wva/stars/GAME"


force = "-f" in sys.argv # ieuw!

def get_year():
    p = requests.get("https://starsautohost.org/games/GAME.htm")
    p.raise_for_status()

    m = re.search(r"Playing&nbsp;Year: (\d{4})", p.text)
    if not m:
        print(p.text)
        raise Exception("Could not get year")
    year = int(m.group(1))
    if year < 2400 or year > 3000:
        raise Exception("Year not right (or game went on far too long :) ): {year}".format(**locals()))
    return year


def download_m(fn, password, outfile):
    #if os.path.exists(outfile):
    #    print(outfile, "exists")
    #    return
    
    url = "https://starsautohost.org/cgi-bin/downloadturn.php?file={fn}".format(**locals())
    print("Downloading", url)
    r = requests.post(url, data=dict(password=password), stream=True)
    r.raise_for_status()

    with open(outfile, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)        

def cp(inf, outf):
    inf = os.path.join(tmpdir, inf)
    outf = os.path.join(outdir, outf)
    print("  ", inf, "->", outf)
    shutil.copyfile(inf, outf)
        
year = get_year()
print("Current year:", year)
fn_orig = os.path.join(outdir, "GAME_{year}.m1".format(**locals()))
if os.path.exists(fn_orig) and not force:
    print("{fn_orig} exists, nothing to do!".format(**locals()))
    sys.exit()


# You need to edit the .m* and passwords here!
    
download_m("GAME.m1", PASSWORD1, os.path.join(tmpdir, "GAME.m1"))
download_m("GAME.m4", PASSWORD4, os.path.join(tmpdir, "GAME.m4"))

cp("GAME.m1", "GAME_orig.m1")
cp("GAME.m1", "GAME_{year}_orig.m1".format(**locals()))
cp("GAME.m4", "GAME_orig.m4")
cp("GAME.m4", "GAME_{year}_orig.m4".format(**locals()))

print("Merging .m files")
cmd = ["java", "-jar", MERGE_TOOL, "-m", "GAME.m1", "GAME.m4"]
print(cmd)
subprocess.check_call(cmd, cwd=tmpdir)


cp("GAME.m1", "GAME.m1")
cp("GAME.m1", "GAME_{year}.m1".format(**locals()))
cp("GAME.m4", "GAME.m4")
cp("GAME.m4", "GAME_{year}.m4".format(**locals()))

years = [int(m.group(1)) for m in [re.match(r"GAME_(\d+).m1", f) for f in os.listdir(outdir)] if m]
print(years)

def row(year):
    fns = ["GAME_{year}{suffix}.m{p}".format(year=year, p=p, suffix=suffix)
           for suffix in ["", "_orig"] for p in [1,4]]
    row = "".join('  <td><a href="{fn}">{fn}</a></td>\n'.format(fn=fn) for fn in fns)
    return "<tr>\n{row}</tr>\n".format(**locals())
                           

archive = "\n".join(row(year) for year in years)

html = """
<html>
<body>
<h1>GAME year {year}</h1>
<h2>Current files:</h2>
<ul>
  <li><a href='GAME.m1'>GAME.m1</a> (merged file)
  <li><a href='GAME.m4'>GAME.m4</a> (merged file)
  <li><a href='GAME_orig.m1'>GAME_orig.m1</a> (original)
  <li><a href='GAME_orig.m4'>GAME_org.m4</a> (original)
</ul>
<h2>Archive:</h2>
<table border=1>
<tr>
  <th>Merged m1</th>
  <th>Merged m4</th>
  <th>Original m1</th>
  <th>Original m4</th>
</tr>
{archive}
</body>
</html>""".format(**locals())

print("Writing index.html")
open(os.path.join(outdir, "index.html"), "w").write(html)
