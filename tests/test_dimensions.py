from pathlib import Path
import xml.etree.ElementTree as ET
from cad.build import generate as build_variant
from scripts.generate_dimensions import generate as generate_dimensions

ROOT = Path(__file__).resolve().parents[1]
SVG_NS = '{http://www.w3.org/2000/svg}'

def test_dimensions_follow_variant_parameters_and_manifest(tmp_path):
    variant_dir = tmp_path / 'dimension-probe'
    report, _ = build_variant(variant_dir, {
        'lid_hole_diameter': 4.2,
        'lid_screw_x': 16.0,
        'lid_screw_y': 28.0,
        'shell_width': 46.0,
    }, 'dimension-probe')
    assert report['digital_checks_pass'], [r for r in report['checks'] if r['status'] == 'failed']

    svg_path = generate_dimensions(
        parameters_path=variant_dir / 'parameters.json',
        manifest_path=variant_dir / 'manifest.json',
        output_path=tmp_path / 'dimension-probe.svg',
    )
    drawing = ET.parse(svg_path).getroot()
    labels = [node.text or '' for node in drawing.findall(f'.//{SVG_NS}text')]

    assert '盖板 · 4 × Ø4.2 通孔' in labels
    assert '盖板孔中心 X ±16 / Y ±28' in labels
    assert '主机下壳 46 × 74' in labels
    assert any(node.attrib.get('r') == '5.88' for node in drawing.findall(f'.//{SVG_NS}circle'))

def test_dimensions_reject_parameters_with_stale_manifest(tmp_path):
    from cad.config import load_parameters
    import json
    data, _ = load_parameters()
    data['design_assumptions']['lid_hole_diameter']['value'] = 4.2
    changed = tmp_path / 'changed-parameters.json'
    changed.write_text(json.dumps(data), encoding='utf-8')
    with __import__('pytest').raises(ValueError, match='does not match'):
        generate_dimensions(parameters_path=changed, manifest_path=ROOT / 'artifacts/baseline/manifest.json',
                            output_path=tmp_path / 'should-not-exist.svg')
    assert not (tmp_path / 'should-not-exist.svg').exists()
