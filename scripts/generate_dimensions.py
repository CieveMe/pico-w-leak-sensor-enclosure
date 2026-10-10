"""Generate a revision-matched SVG from CAD parameters and manifest data."""
import argparse
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cad.build import source_revision
from cad.config import load_parameters


def esc(value):
    return html.escape(str(value))


def number(value):
    return f"{float(value):g}"


def line(x1, y1, x2, y2, **attrs):
    rest = " ".join(f'{key.replace("_", "-")}="{esc(value)}"' for key, value in attrs.items())
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" {rest}/>'


def text(x, y, value, cls="label", anchor="middle", rotate=None):
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    return f'<text class="{cls}" x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}"{transform}>{esc(value)}</text>'


def dim_h(x1, x2, y, offset, label):
    y2 = y + offset
    return "".join((line(x1,y,x1,y2,stroke="#778078"), line(x2,y,x2,y2,stroke="#778078"),
                    line(x1,y2,x2,y2,stroke="#52695b",marker_start="url(#arrow)",marker_end="url(#arrow)"),
                    text((x1+x2)/2,y2-4,label,"dim")))


def dim_v(x, y1, y2, offset, label):
    x2 = x + offset
    return "".join((line(x,y1,x2,y1,stroke="#778078"), line(x,y2,x2,y2,stroke="#778078"),
                    line(x2,y1,x2,y2,stroke="#52695b",marker_start="url(#arrow)",marker_end="url(#arrow)"),
                    text(x2-4,(y1+y2)/2,label,"dim",rotate=-90)))


def axis_values(points, index):
    values = sorted({round(float(point[index]), 6) for point in points})
    if len(values) == 2 and math.isclose(values[0], -values[1], abs_tol=1e-6):
        return f"±{number(abs(values[1]))}"
    return ", ".join(number(value) for value in values) or "—"


def part_dimensions(parts, part_id):
    box = parts[part_id]["bbox"]
    return [float(box["max"][i]) - float(box["min"][i]) for i in range(3)]


def resolve_path(value, default):
    if value is None:
        return default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def generate(copy_to_viewer=False, parameters_path=None, manifest_path=None, output_path=None):
    parameters_path = resolve_path(parameters_path, ROOT / "cad/parameters.json")
    manifest_path = resolve_path(manifest_path, ROOT / "artifacts/baseline/manifest.json")
    data, p = load_parameters(parameters_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    revision = source_revision(data)
    if manifest.get("source_revision") != revision:
        raise ValueError("CAD manifest revision does not match the supplied parameters and sources")
    parts = {item["id"]: item for item in manifest["parts"]}
    interfaces = manifest["interfaces"]
    ids = ["lower_shell", "lid", "wall_bracket", "probe_holder"]
    width, height = 1200, 840
    out = [f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">Pico W 漏水监测结构尺寸图</title><desc id="description">由参数文件和CAD manifest {revision} 生成，包含PCB孔位、壳体盖板和背板安装接口、四件包围尺寸。</desc>
<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto-start-reverse"><path d="M6 0 0 3 6 6" fill="none" stroke="#52695b" stroke-width="1"/></marker></defs>
<style>text{{font-family:"Microsoft YaHei","Segoe UI",sans-serif;fill:#283230}}.mono{{font-family:Consolas,monospace;letter-spacing:.08em}}.title{{font-size:26px;font-weight:600}}.sub{{font-size:11px;fill:#717b73}}.section{{font-size:15px;font-weight:600}}.label{{font-size:11px}}.small{{font-size:9px;fill:#69746d}}.dim{{font:10px Consolas,monospace;fill:#52695b}}.outline{{fill:#f7f6f0;stroke:#40554b;stroke-width:1.6}}.board{{fill:#e6eee5;stroke:#52735d;stroke-width:1.3}}.interface{{fill:none;stroke:#d57242;stroke-width:1.5}}.hole{{fill:#f4f1ea;stroke:#52735d;stroke-width:1.2}}.panel{{fill:#fbfaf6;stroke:#e0e2db}}.rule{{stroke:#d9ddd5;stroke-width:1}}</style>
<rect width="1200" height="840" fill="#f4f1ea"/><text x="54" y="57" class="sub mono">PICO W / STRUCTURAL STUDY</text><text x="54" y="96" class="title">尺寸与装配接口</text><text x="1146" y="60" class="small mono" text-anchor="end">REV {esc(revision[:19])}</text>
<text x="54" y="124" class="sub">名义尺寸，单位 mm。板上元件、插头与制造公差按参数文件中的假设处理。</text>
<rect x="40" y="148" width="530" height="405" rx="2" class="panel"/><rect x="588" y="148" width="572" height="405" rx="2" class="panel"/><rect x="40" y="572" width="1120" height="225" rx="2" class="panel"/>
<text x="64" y="182" class="section">01 · 主机与 PCB 定位</text><text x="64" y="201" class="small">Pico W PCB / 厂家 Figure 3；USB 端朝 +Y</text>"""]
    shell = part_dimensions(parts, "lower_shell")
    scale, cx, cy = 4.2, 300, 388
    sw, sl = shell[0] * scale, shell[1] * scale
    out.append(f'<rect x="{cx-sw/2}" y="{cy-sl/2}" width="{sw}" height="{sl}" rx="5" class="outline"/>')
    out.append(text(cx, cy-sl/2+17, f'主机下壳 {number(shell[0])} × {number(shell[1])}', "small"))
    bw, bl = p["pcb_width"]*scale, p["pcb_length"]*scale
    out.append(f'<rect x="{cx-bw/2}" y="{cy-bl/2}" width="{bw}" height="{bl}" rx="2" class="board"/>')
    pcb_holes = interfaces["pcb_holes"]
    for x, y in pcb_holes:
        radius = p["pcb_hole_diameter"]*scale/2
        out.append(f'<circle cx="{cx+x*scale:.2f}" cy="{cy-y*scale:.2f}" r="{radius:g}" class="hole"/>')
    out.append(dim_h(cx-p["pcb_hole_pitch_x"]/2*scale,cx+p["pcb_hole_pitch_x"]/2*scale,cy-p["pcb_hole_pitch_y"]/2*scale,-19,number(p["pcb_hole_pitch_x"])))
    out.append(dim_v(cx+bw/2,cy-p["pcb_hole_pitch_y"]/2*scale,cy+p["pcb_hole_pitch_y"]/2*scale,24,number(p["pcb_hole_pitch_y"])))
    out.append(text(cx,cy+bl/2+31,f'PCB {number(p["pcb_width"])} × {number(p["pcb_length"])} · 孔 Ø{number(p["pcb_hole_diameter"])}',"small"))
    out.append(text(64,519,f'孔中心：X {axis_values(pcb_holes,0)}，Y {axis_values(pcb_holes,1)}；孔径 {number(p["pcb_hole_diameter"])}（厂家公差 ±0.05）。',"small","start"))
    out.append(text(64,537,'壳体安装孔与板孔分开；这里只画俯视定位关系，不代表元件级净空。',"small","start"))
    out.append(text(cx,cy+bl/2+48,'两颗前侧固定；天线侧孔位留空','small'))
    out.append(text(cx,cy-sl/2-10,'USB / +Y','small'))
    out.append(dim_h(cx-sw/2,cx+sw/2,cy+sl/2,23,number(shell[0])))
    out.append(dim_v(cx+sw/2,cy-sl/2,cy+sl/2,39,number(shell[1])))
    first_hole = pcb_holes[0]
    radius = p["pcb_hole_diameter"]*scale/2
    out.append(f'<circle cx="{cx+first_hole[0]*scale:.2f}" cy="{cy-first_hole[1]*scale:.2f}" r="{radius:g}" class="interface"/>')

    out.append('<text x="612" y="182" class="section">02 · 盖板与壁挂接口</text><text x="612" y="201" class="small">孔坐标使用manifest实际装配位置</text>')
    plan_scale, left, right = 2.8, (690,370), (965,370)
    def plate(center, part_id, holes, label, hole_diameter):
        d = part_dimensions(parts, part_id)
        x0, y0 = center[0]-d[0]*plan_scale/2, center[1]-d[1]*plan_scale/2
        out.append(f'<rect x="{x0}" y="{y0}" width="{d[0]*plan_scale}" height="{d[1]*plan_scale}" rx="3" class="outline"/>')
        for x, y in holes:
            radius = hole_diameter*plan_scale/2
            out.append(f'<circle cx="{center[0]+x*plan_scale:.2f}" cy="{center[1]-y*plan_scale:.2f}" r="{radius:g}" class="hole"/>')
        out.append(text(center[0],y0-13,label,"label"))
        out.append(text(center[0],y0+d[1]*plan_scale+19,f'{number(d[0])} × {number(d[1])}',"dim"))
    lid_holes = interfaces["lid_holes"]
    wall_holes = interfaces["wall_holes"]
    plate(left,"lid",lid_holes,f'盖板 · {len(lid_holes)} × Ø{number(p["lid_hole_diameter"])} 通孔',p["lid_hole_diameter"])
    plate(right,"wall_bracket",wall_holes,f'背板 · {len(wall_holes)} × Ø{number(p["wall_hole_diameter"])} 墙孔',p["wall_hole_diameter"])
    out.append(text(612,516,f'盖板孔中心 X {axis_values(lid_holes,0)} / Y {axis_values(lid_holes,1)}',"small","start"))
    bracket_holes = interfaces["bracket_holes"]
    for x,y in bracket_holes:
        out.append(f'<circle cx="{right[0]+x*plan_scale:.2f}" cy="{right[1]-y*plan_scale:.2f}" r="2.5" class="interface"/>')
    out.append(text(right[0],516,f'橙色圆：壳体—背板连接点 {len(bracket_holes)} 个（X {axis_values(bracket_holes,0)} / Y {axis_values(bracket_holes,1)}）',"small"))
    out.append(text(612,537,f'背板墙孔中心 X {axis_values(wall_holes,0)} / Y {axis_values(wall_holes,1)}；M3 塑料自攻螺钉及间隙为未试装假设。',"small","start"))

    out.append('<text x="64" y="607" class="section">03 · 四件外包尺寸</text><text x="1140" y="607" class="small" text-anchor="end">尺寸取自同版manifest包围盒</text>')
    names={"lower_shell":"主机下壳","lid":"螺钉上盖","wall_bracket":"壁挂背板","probe_holder":"外接探头托架"}
    cols, heady = [64,320,598,875], 640
    for x,label in zip(cols,["零件","X / 宽","Y / 长","Z / 高"]):
        out.append(text(x,heady,label,"small","start"))
    out.append(line(64,650,1138,650,stroke="#d9ddd5"))
    for row,key in enumerate(ids):
        d=part_dimensions(parts,key);y=679+row*27
        out.append(text(cols[0],y,names[key],"label","start"))
        for i in range(3):
            out.append(text(cols[i+1],y,number(d[i]),"dim","start"))
        if row<3:
            out.append(line(64,y+9,1138,y+9,stroke="#ecece6"))
    out.append(f'<text x="64" y="777" class="small">来源：Pico W datasheet Figure 3；SEN0121 官方整体包络。未包含打印公差、螺纹强度或实物校准。 · {esc(revision)}</text></svg>')
    svg="\n".join(out)+"\n"
    target=resolve_path(output_path,ROOT/"artifacts/drawings/pico-w-dimensions.svg")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(svg,encoding="utf-8",newline="\n")
    if copy_to_viewer:
        public=ROOT/"viewer/public/drawings";public.mkdir(parents=True,exist_ok=True)
        (public/target.name).write_text(svg,encoding="utf-8",newline="\n")
    return target


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--parameters",help="parameter JSON (default: cad/parameters.json)")
    parser.add_argument("--manifest",help="matching CAD manifest (default: artifacts/baseline/manifest.json)")
    parser.add_argument("--output",help="SVG output path (default: artifacts/drawings/pico-w-dimensions.svg)")
    parser.add_argument("--copy-to-viewer",action="store_true")
    args=parser.parse_args()
    print(generate(args.copy_to_viewer,args.parameters,args.manifest,args.output).relative_to(ROOT))
