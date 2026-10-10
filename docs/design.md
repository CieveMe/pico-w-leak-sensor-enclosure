# Pico W leak sensor enclosure design

Status: P0–P3 digital implementation and browser review are complete. The current baseline has 176 digital checks passed and 1 independent desktop-CAD reopening check unverified. Physical fit, print, strength, RF, alarm, and waterproof tests remain unperformed. P4 clean reproduction and publication preparation are in progress; no public upload has occurred.

## Purpose

Create a reproducible mechanical learning prototype around a Raspberry Pi Pico W and an external DFRobot SEN0121 water sensor. The deliverable is editable CAD, derived engineering files, digital checks and a browser assembly review. The structure and documentation are suitable for public reuse. This is a mechanical prototype, not a tested electronic alarm or certified waterproof product.

## Inputs and scope

- Raspberry Pi Pico W without pre-soldered headers: nominal PCB footprint 51 × 21 mm; use manufacturer mechanical documentation for hole locations and an explicitly identified conservative component envelope.
- DFRobot SEN0121: nominal overall envelope 30 × 20 × 6 mm; analog water/steam sensing board with a connector that is not waterproof.
- Indoor learning scenario: controller mounted above the wet area, external removable sensor holder near the inspection location. Avoid direct contact with hot pipes.
- Four custom printable parts: lower shell, removable lid, wall mounting bracket and sensor holder.
- Screw assembly, USB access, separate sensor cable exit, maintainable sensor mounting. Component, connector, solder and cable-bend envelopes are explicit inputs, not inferred from rendered appearance.
- No battery pack, custom PCB, cloud service, firmware or online CAD editor in the first version.

## Engineering and data flow

Python parameters → build123d/OCP solids → STEP/STL/GLB and drawings → digital validation report → browser review.

Use the pinned build123d/OCP dependencies directly; no external CAD plugin or cadgen installation is required. Preserve the Python source as the editable design; STEP is the engineering exchange format and GLB is for viewing. The viewer cannot modify engineering dimensions. Exploded presentation offsets never enter geometry validation.

The baseline manifest uses part IDs `lower_shell`, `lid`, `wall_bracket`, `probe_holder`; reference components use `pico_w` and `water_sensor`. Each part entry has `id`, `name`, `role` (`custom` or `reference`), `files` (relative to manifest), `color`, `explode` (millimetres), `bbox` (`min`, `max`) and `volume_mm3`. The manifest carries `schema_version`, `units` (`mm`), `cad_up_axis` (`Z`), `glb_units` (`m`), `up_axis` (GLB `Y`), `variant`, `parts`, `parameters`, `limitations` and `validation`. P0 generated specimens now establish this conversion for the tested simple shapes, including an asymmetric, off-origin export. See the observed export contract below; arbitrary orientations and assemblies still require their own validation.

## Review page

Chinese-first, accessible controls for orbiting, fitting, exploded assembly, shell transparency and selecting parts. Show part names, dimensions, material assumptions and checks. Link downloads to the same generated revision. The sensor holder is an external subassembly; explain its installation context. A static page works without accounts or live telemetry.

## Acceptance

1. All four custom parts are valid positive-volume solids and export successfully.
2. Re-import STEP and compare bounding boxes and volumes against the source solids with stated numerical tolerances.
3. Assert controller keep-out clearance and absence of unintended overlap in the assembled geometry; classify intentional fastener/contact interfaces separately.
4. Verify parameter-driven regeneration for at least two meaningful dimensional variants; test an invalid configuration that must be rejected.
5. Review USB insertion access, screw access, antenna space and external sensor connector exposure against recorded envelopes. Record incomplete component dimensions as explicit assumptions.
6. Browser review loads every model, switches modes without console errors, and downloads the associated files.
7. A clean rebuild follows the documented commands. CI recreates and validates geometry; a report must identify what it measured.

Digital clearances and nominal dimensions do not establish print tolerances, radio performance, waterproofing or physical fit. Print trials, sensor calibration and electronics testing are separate future steps.

## Delivery and publication

Publish a dedicated repository with source, derived artifacts, source references, license, reproducible commands, CI and a concise contribution guide. Prepare Chinese/English resume text, a technical blog draft and a short X post using only observed results. GitHub publication is authorized; blog/social publishing and purchases are not part of this implementation.


## P0 observed export contract (2026-10-10)

The off-origin 12 x 7 x 5 mm solid establishes the mm/Z-up to m/Y-up contract. In build123d 0.11.1, default GLB export post-multiplies the shape location by Rx(-90), which leaves translation in its original basis. P0 retains the raw file and failure evidence, and corrects root translation (x,y,z) -> (x,z,-y) for its translation-only test. Three.js GLTFLoader independently restores bbox [11,-17,4] to [23,-10,9] mm with a single scale=1000, Rx(+90) parent. A production export adapter must also handle arbitrary source orientation; every generated GLB will be measured in scene world coordinates against CAD bbox. No per-part viewer correction or centering is allowed.
