# Sources and frozen assumptions

Reviewed 2026-10-10. Manufacturer files are linked, not redistributed. Values and attribution are in cad/parameters.json.

- [Pico W datasheet](https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf): local reference SHA256 BA8649BA98437301B9F1621504569A27F1D2BA6111795B4DF76783ADB08DE7C5. Printed page 6 / Figure 3: PCB 51 x 21 x 1 mm, four 2.1 mm holes (manufacturer tolerance +/-0.05), X pitch 11.4, Y pitch 47 mm. X short, Y long; USB at +Y, antenna at -Y. No pre-soldered headers.
- Printed page 10 / section 2.2.1: carrier-board antenna cutout 14 x 9 mm and nearby-material caution in any dimension. Our 20 mm wide open rear zone extends to Y=-16.5 across floor, lid and backplate. Rear two PCB holes are unfastened; front two M2 screws plus mid-edge supports are used. This project placement is an assumption, not RF clearance certification.
- [DFRobot SEN0121](https://wiki.dfrobot.com/sen0121): overall 30 x 20 x 6 mm, not PCB thickness; connector is not waterproof. No hole pattern is guessed. Inclined edge supports leave a central sensing aperture and raise the connector end. Vertical removal is checked using an actual swept envelope, not an oversized bounding box.
- Socket (8 mm wide), plug/straight insertion (14 x 6 mm), cable reserve, components (18 x 36 x 5 mm above PCB), solder (16 x 35 x 0.8 mm below), screw pilots and print clearances are project assumptions. No named cable brand or measured component-level accuracy is claimed.

## Assembly and installation

The open antenna zone prioritises a material-free rear region over sealing. Install the host in a dry elevated indoor position, external sensor separately. No IP rating.

Cover: four M3 x 12 plastic-thread screws, 2.5 mm printed pilots and 3.4 mm cover holes. PCB: two M2 x 6 plastic-thread screws, 1.6 mm pilots through 2.1 mm manufacturer holes. Host/backplate: four M3 x 8 plastic-thread screws, 3.4 mm shell holes and 2.5 mm bracket pilots. These are untested nominal choices, not modeled threads or proven pull-out strength.

Order: mount wall backplate first; attach empty shell; install PCB and external cable tie; install cover. Reverse for host removal. Wall-screw tools are checked with bracket alone; host-joint tools with empty shell/bracket; PCB tools with shell/board before cover; cover tools with full enclosure. These contexts are explicit, not global exclusions.

Two sidewall tunnels route a separate nylon tie to form an external cable loop. No cable pull test. Sensor is inclined 12 degrees and front raised 3 mm; physical sensing depth, actual trace locations, connector exposure and removal fit require trials. Sensing-region envelope is conservatively assumed in the front 20 mm, not a manufacturer-certified active area.

P2 review added two front edge stops because the original low bridge did not intercept downhill motion. Stop thickness is a project assumption of 1.2 mm, width 2.4 mm matching the support rails, and height is front height plus the overall sensor height. Their rear edge lies ahead of the tilted sensor's full front projection by `sensor_side_clearance` (baseline 0.6 mm). The virtual retention witness moves the sensor 3 mm downhill; it must hit the stops. The vertical removal check covers a 25 mm lift and extrudes all upward-facing faces of the convex envelope, including the inclined rear face. These are geometric service/retention checks, not strength or measured fit claims.

## Boundaries

No print trial, RF trial, firmware/alarm test, waterproof/immersion certification, guaranteed fastening strength or community adoption. Simplified envelopes cannot prove every component collision. build123d/OCP STEP reimport alone is not independent CAD-app reopening.


## P1/P2 implementation notes

The nominal M2x6 screw must have a compact head OD <=3 mm and a driver shaft <=2.4 mm beside the assumed 8 mm USB socket. These are selection constraints, not measured purchased hardware. Host M3 tool corridor diameter is 6 mm. PCB pilots extend to Z=floor-1.5 (baseline 1 mm); nominal M2x6 tip Z=1.5 mm leaves 0.5 mm. Bracket pilots extend to Z=-6 mm for M3x8 tip Z=-5.5 mm. Geometry checks measure actual core clearance over those insertion depths; plastic thread bite/strength remain unverified.

An initial assembly total-volume comparison failed because Compound.volume on that nested source hierarchy omitted the Pico reference, while recursive leaf-solid volumes agreed with STEP reimport. The check now compares leaf-solid sums and adds all six named component bbox/volume comparisons; the 1e-5 relative threshold is unchanged. See retained failure and diagnosis artifacts.

Production GLB export conjugates a deep copy's location before build123d's post-Rx(-90), instead of modifying translations in the viewer. It supports arbitrary source orientation and was exercised by an off-origin [17,31,23] degree rotation witness. Each derived GLB is independently parsed into scene world vertices and checked against CAD bbox. STL is a unitless mesh treated as CAD mm; it is not a solid engineering exchange format.

## Dependency attribution and publication scope

Original Python/JavaScript, parametric solids, dimension sheets and local viewer screenshots belong to this project. Reference boards are newly modeled simplified envelopes, not redistributed manufacturer CAD or artwork. The repository contains no manufacturer PDF, photograph, logo, external template, plugin code, or installed dependency directory.

Dependencies are installed separately from the pinned Python requirements and Node lockfile. Principal dependencies retain their upstream licenses: [build123d 0.11.1 (Apache-2.0)](https://github.com/gumyr/build123d/blob/v0.11.1/LICENSE), [Three.js r180 (MIT)](https://github.com/mrdoob/three.js/blob/r180/LICENSE), and [Vite 7.1.9 (MIT and bundled dependency notices)](https://github.com/vitejs/vite/blob/main/packages/vite/LICENSE.md). The project's MIT license applies to original project material, not these dependencies. The Three.js license is preserved in `viewer/public/licenses/third-party-notices.txt` and copied into the built site at `/licenses/third-party-notices.txt`; retain it when distributing the viewer build. Python/OCP and build-time packages are not vendored or republished here.

`p0_probe.py` and `p1_check.py` are historical stage witnesses, not production export adapters. `review_p2.py` is a local review utility that expects baseline plus `artifacts/variants/wall_thickness` and `artifacts/variants/pcb_support_height` generated by `cad/build.py --set wall_thickness=2.0` and `--set pcb_support_height=6.0` respectively (use matching `--output` directories and `--variant` names). Install viewer dependencies before using its independent Three.js reader. Generated stage evidence remains ignored; normal reproduction uses `scripts/prepare_viewer.py` and the test suite.
