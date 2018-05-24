"""
Simple tool for automatically retrieving and merging .m files

Retrieves the files from autohost, merges them, and creates
an html index with newest file and index. 

I place the output in a (password protected) public html folder.
If you and your ally both run the tool you can also keep ik local.
"""


import requests, re, sys, os, shutil, subprocess, json

tmpdir = "/tmp/merge"
if not os.path.exists(tmpdir):
    os.mkdir(tmpdir)
    
force = "-f" in sys.argv # ieuw!

def get_year(game):
    p = requests.get("https://starsautohost.org/games/{game}.htm".format(**locals()))
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

config_file = "merge_config.json"
config = json.load(open(config_file))
game = config["game"]
players = {p["id"]: p for p in config["players"]}
outdir = config["outdir"]
MERGE_TOOL = config["jarfile"]

player = list(players)[1]
year = get_year(game)
print("Current year:", year)
fn_orig = os.path.join(outdir, "{game}_{year}.m{player}".format(**locals()))
if os.path.exists(fn_orig) and not force:
    print("{fn_orig} exists, nothing to do!".format(**locals()))
    sys.exit()



for player in players:
    download_m("{game}.m{player}".format(**locals()), players[player]["pwd"], os.path.join(tmpdir, "{game}.m{player}".format(**locals())))
    cp("{game}.m{player}".format(**locals()), "{game}_orig.m{player}".format(**locals()))
    cp("{game}.m{player}".format(**locals()), "{game}_{year}_orig.m{player}".format(**locals()))

print("Merging .m files")
cmd = ["java", "-jar", MERGE_TOOL, "-m"] + ["{game}.m{player}".format(**locals()) for player in players]
print(cmd)
subprocess.check_call(cmd, cwd=tmpdir)

for player in players:
    cp("{game}.m{player}".format(**locals()), "{game}.m{player}".format(**locals()))
    cp("{game}.m{player}".format(**locals()), "{game}_{year}.m{player}".format(**locals()))

years = [int(m.group(1)) for m in [re.match(r"{game}_(\d+).m{player}".format(**locals()), f) for f in os.listdir(outdir)] if m]
print(years)

def row(year):
    fns = ["{game}_{year}{suffix}.m{p}".format(game=game, year=year, p=p, suffix=suffix)
           for suffix in ["", "_orig"] for p in players]
    row = "".join('  <td><a href="{fn}">{fn}</a></td>\n'.format(fn=fn) for fn in fns)
    return "<tr>\n{row}</tr>\n".format(**locals())
                           

archive = "\n".join(row(year) for year in years)

html = """
<html>
<body>
<h1>{game} year {year}</h1>
<h2>Current files:</h2>
<ul>""".format(**locals())
for player in players:
    html += "  <li><a href='{game}.m{player}'>{game}.m{player}</a> (merged file)".format(**locals())
for player in players:
    html += "  <li><a href='{game}.m{player}'>{game}_orig.m{player}</a> (original file)".format(**locals())
html += """
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
