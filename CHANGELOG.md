# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

### Changed

* `set_rhproj_icons.py` no longer flattens the SVG `<style>` block into presentation attributes before storing an icon in `COMPAS-Masonry.rhproj`. Flattening cannot preserve `mix-blend-mode`, `isolation` or `clip-path` — those have no presentation-attribute form — and dropping them changes what the artwork means: an element that is invisible by design under a blend mode becomes an opaque block over everything behind it. Measured over the 22 icons with only the flattening changed: **8 render differently, worst 25.0%**, independently reproducing the finding made for the sprite sheet on 2026-08-28 (8 icons, worst 23.5%). `make_icons.py` stopped flattening then; this is the same fix on the rhproj path.

### Fixed

* `CM_Problem_displacements` has its icon back. It is the only icon using `clip-path`, `isolation` and `mix-blend-mode` together, which made it the one the flattening step mangled worst, and it was unbound in 0.5.2 to get a build through. With the flattening removed it binds and renders, and `verify_icons.py` — which fails on an SVG that is present but not bound, and so aborts a build at the icon-verification step — passes again.

### Removed


## [0.4.0] 2026-09-01

* Added 3DEC to `CM_Problem_setsolver`, with automatic executable discovery, optional executable and workspace overrides, convergence and timeout settings, implicit gravity setup, and an optional `threedec` dependency group.
* Added interactive ordering and grouping of 3DEC load and displacement stages, with concise solve progress in Rhino.
* Added selective solver-result export when saving a portable session.
* Improved result visualisation performance with batched Rhino drawing, compact result storage, hidden interface geometry, and geometry-relative load and displacement arrows.
* Corrected 3DEC tension reporting to use native normal subcontact forces.

### Changed — 2026-08-31

* **Every dependency now resolves from PyPI, so the environment can be rebuilt off the developer's machine.** `compas_dem` 0.6.0 and `compas_3dec` 0.2.0 reached PyPI, and `compas_cra` 0.8.0 ships wheels for CPython 3.9-3.13 on macOS (arm64 and x86_64), manylinux and Windows. A clean install on Rhino 8's own python3.9 resolves 49 distributions and passes the full suite, with no `--ignore-requires-python` and no local checkouts. `compas_cra` 0.5.0-0.7.0 have been withdrawn from PyPI, so the pin cannot go backwards; 0.4.0 breaks under NumPy 2.

* **`ipopt` is no longer an install step, and the machinery that hunted for it is gone.** compas_cra 0.8.0 dropped pyomo and runs IPOPT in-process through a bundled native binding, so no executable is looked up and `PATH` is never read. Removed `MasonrySession.ensure_solver_path()`, the `solver_bin` setting — whose default was a developer's own conda prefix, shipped to every user as a path that exists on one machine — and the pre-solve check that warned *"ipopt was not found … this will fail"*, which after 0.8.0 said that to installations that solve perfectly. Verified by solving the 20-block test arch with `ipopt` absent from `PATH`: identical reactions.

* `pyomo` became an explicit requirement rather than an inherited one. compas_cra no longer pulls it, but `compas_dem.analysis.cra` still imports `pyomo.environ` to inject `DEFAULT_IPOPT_OPTIONS`, so a CRA solve without it dies with `ModuleNotFoundError`. Against compas_cra 0.8.0 that injection is a no-op; the measured cost on the 20-block arch is 1.8e-07 relative, with IPOPT reporting `acceptable` where 0.5.0 reported `optimal`.

* `compas_3dec` moved from the optional `threedec` extra into the base requirements, and the extra was removed. At 324 KB of pure Python it costs little, and it lets a 3DEC solver be configured — and correctly refused — on every machine rather than only where someone installed an extra.

### Added — 2026-08-31

* **A 3DEC solve is refused up front on a machine that cannot run one.** `solvers.threedec_blocker()` reports why, and is consulted both when the solver is selected (a warning; the solver is still set, because its parameters are portable and belong to the problem) and by `check_ready()` before any stage prompt. Availability is asked of compas_3dec rather than inferred from `sys.platform`: an explicit executable path is honoured everywhere, so a macOS machine with a reachable licensed install is allowed, and a Windows machine *without* 3DEC is correctly refused — both of which a platform check gets wrong. Replaces `threedec_available()`, which tested only whether the adapter imported.

* **Every report is in kN, and every column says so.** The Rhino reaction tags divided by 1000 and appended " kN" while `Results_print`, `Results_block` and the CSV export all emitted raw newtons, so a label and the table row for the same contact disagreed by a factor of 1000 with nothing on screen saying which was which. The conversion now lives once in `compas_masonry.results` — the module both the reports and the drawing derive their numbers from — and the units are in the column headings rather than in a legend. Stress follows as kPa, which is kN/m2, so it is the same conversion rather than a second one that happens to match. Stored values are unchanged: everything on a `Results` stays in newtons, and only what a person reads is converted. CSV columns are renamed accordingly (`F_magnitude_kN`, `Fx_kN`, `stress_kPa`); displacements are lengths and are left in model units. Note this assumes a model in metres — nothing can detect the document unit, so a model drawn in millimetres reports correct forces over incorrect areas, which shows as stress wrong by 10^6.

* **Reactions, horizontal and vertical forces are drawn as arrows from their point of application**, instead of as lines centred on it. A centred line spans +/-v/2 with no head, so `v` and `-v` draw identically — an abutment pushing up and one pulling down were the same picture, and thrust could not be told from pull. Contact resultants stay centred deliberately: their sign is a matter of which of the two blocks you read them from. The head is set through `ObjectDecoration` on the attributes rather than with `rs.CurveArrows` afterwards, so a result arrow still commits in one document modification with its layer, colour and User Text.

* **A support reaction also draws its world X, Y and Z components**, as arrows in the reaction colour sharing the resultant's point of application, on `Forces::Reactions::X | Y | Z`. Together they answer how much of a reaction is horizontal thrust and how much is vertical load — what an abutment is sized on, and not something the eye recovers from the resultant. They are kept off the `Interface` layer on purpose: they share its colour, so on one layer neither could be switched off without the other. A zero component draws nothing, so a planar arch gives two arrows rather than a degenerate third.

* **Every drawn force view has its own Rhino layer.** Contact resultants, interface reactions, the normal and friction components, the per-corner forces and the value tags all landed on one `Forces` layer, so no view could be switched off without the others. `Results::<key>::Forces` now splits into `Reactions::Interface | Normal | Friction`, `Resultants::Horizontal | Vertical`, `Corners` and `Values` — normal and friction under Reactions because they are the interface force resolved in the joint's own frame, horizontal and vertical under Resultants because they are the same force resolved in world axes.

* **Horizontal and vertical force components can be drawn** (`show_horizontalforces`, `show_verticalforces`), separating thrust from weight. This is not recoverable from the normal/friction pair: on an inclined springing joint a large normal force is mostly horizontal thrust and the frame-relative split cannot say so. Computed from `resultant_global` — compas_dem stores no horizontal/vertical quantity — and available on CRA and RBE results, which carry no contact frame and therefore cannot show the normal/friction split at all.

* `Session_save` can include **all** solver results in one step, instead of only "none" or a hand-picked selection.

* **Results now record what produced them.** A `Results` carried `model_id`, `problem_id` and the per-node/edge data and nothing about the configuration behind them — and `problem_id` does not help, because editing a problem in place leaves its guid unchanged while the configuration differs. Solving stamps the solver name and parameters, the problem name, the contact model and the boundary-condition group names into `results.metadata`, which is part of `Results.__data__` and so survives a session save and re-import. Everything stamped is a primitive: `contact_model.__data__` is a plain dict — also the only way to read `mu`, which is a property rather than a public attribute — and storing live Data objects would make an old result unloadable the day compas_dem renames a class.

### Fixed — 2026-08-31

* **BUG 2: reactions were drawn per CONTACT, not per SUPPORT.** One red arrow and one kN tag per support contact. Correct on an arch, where each abutment touches the model once — which is why it looked right for so long — and wrong on a dome or a vault, where a support springs across several contacts and the reaction is their vector SUM. Measured on a 40-block barrel vault: all 8 supports span 3 or 4 force-carrying contacts, so the drawing showed 3-4 arrows and 3-4 overlapping tags per support, not one of which was the reaction, while `Results_print` printed the correct 36.349 kN total. The picture and the report disagreed, and the picture was wrong. Reactions are now drawn in a pass of their own from `support_reactions`, one arrow per support, at the force-weighted mean of that support's contact points — where the compas_dem viewer puts it, and far enough from a near-zero contact that it is not dragged off the loaded part of the abutment. The reference arch is unchanged at 28.049 kN per support.

* **BUG 1: the force-scale yardstick was orientation-dependent.** `_max_block_size` measured the AXIS-ALIGNED bounding box diagonal, which grows as a block is tilted relative to world XYZ even though the block is unchanged — so rotating a model silently rescaled every force arrow in it. Measured on the reference arch: 1.2771 upright, 1.4934 at 30 degrees, 1.5684 at 45 degrees, a 23% drift for a model that had not otherwise changed. It is now the block's own diameter, invariant under placement, which also brings the picture back in line with the compas_dem viewer: half the diameter is 0.4896 against the viewer's 0.500, where the old yardstick's half was 0.6386 and made every arrow 1.28x too long. The viewer's own measure, a single mesh edge, is not used because it depends on which edge the mesh happens to store first. This also fixes the load and displacement arrows, which share the yardstick.

* **Result geometry could land in whatever layer the user had active.** `_result_attributes` looked the destination layer up and, when it did not exist yet, left `LayerIndex` unset — and an object added with no `LayerIndex` goes to the CURRENT Rhino layer, silently. Running a command with `Default` active therefore scattered result geometry into it, untracked by the session and removable only by hand. The layer is now created when missing, and a layer that can neither be found nor created raises rather than falling back. The three `rs.Add*` boundary-condition paths are guarded the same way: they add to the current layer and then move the object, and the move only works if the destination already exists.

* **Horizontal and vertical force components are drawn only on support reactions**, not on every contact — thrust against weight is a question about an abutment, and drawing it on all 14 contacts of an arch buried the two being asked about. Every reaction component (X, Y, Z, horizontal, vertical) now carries its own magnitude as Rhino User Text, in newtons and kN, so a component selected on its own can answer for itself instead of sending the reader back to the parent reaction.

* **LMGC90 reactions were drawn on a corner of the contact.** `support_reaction_points` resolved its position with `contact_point()`, which answers a different question — "a representative point ON the contact" — and puts the contact frame origin first. compas_dem stores LMGC90's frame as `contact_frames[0]`, the FIRST subcontact, which sits at a corner of the interface. Measured on a real LMGC90 solve: the frame origin was `[3.1534, 0.0, 1.5186]`, exactly polygon corner `[3.153, 0.0, 1.519]`, while the force acts at `[2.8374, 0.2471, 1.3664]`. Both the resultants and the reactions now resolve through one `application_point()` — force_point, then the force-weighted `resultantpoint`, then the frame, then the centroid — because two orders is precisely how a reaction ends up drawn somewhere the resultant it sums is not.

* **Corner forces were never visible in Rhino.** The per-corner data is written on every `FrictionContact` — verified on a 3-block CRA solve: four `compressiondata` rows per contact, 8486.47 N each, summing to the 33945.86 N resultant — but they were drawn onto the same `Forces` layer as the resultants and buried underneath them. They now have their own `Forces::Corners` layer.

* **`Session_redraw` rebuilt only the blocks, not the layers.** It called `redraw()`, which refreshes the scene objects and re-tags their guids and nothing else, so reopening Rhino after closing without saving came back with the session data intact and every problem, boundary-condition and results layer missing — and only `Session_undo`, which routes through `_restore_state`, brought them back. It now calls `redraw_document()`, the same full rebuild, without moving through history.

* **`Results_show` could re-enable force views the user had deliberately switched off.** It decides "all force views are disabled" from a hand-written tuple, and the horizontal/vertical views added above were not in it — so asking for Forces with only those enabled would switch resultants and reactions back on over an explicit choice, and persist it, because the command records. All eight force views are now counted, and a test pins the tuple against the settings model so adding a view without adding it there fails.

* **An imported session showed no results.** `Session_import` restored the results into the data and drew the model and the boundary conditions, but never the result geometry — so results were present and invisible until `Results_show` was re-run by hand. Three things were missing, not one: `Session_save` never exported `shown_results`, `Session_import` never restored it, and `clear_model` deletes it on the way in, so there was nothing left to replay. The view is now exported (filtered to the results actually included, so a file never claims a view onto data it omits), restored on import (filtered again to the problems and keys that arrived), and drawn.

* **Session settings did not survive a restart.** `Session_settings` mutated the in-memory pydantic model and wrote nothing: the settings file is only produced by `dump()`, which `record()` calls, and this was the one state-changing command that never recorded. It now records, which also puts settings under undo/redo like the rest of the session.

* **3DEC tension reporting was never actually using native subcontact forces.** `tension_contacts` guards against reading the affine, sometimes-negative vertex weights of a 3DEC-to-DEM conversion as tension — but the guard keyed off `results.metadata["solver"]`, and no backend has ever written it, so the branch never ran and 3DEC results silently took the path it exists to prevent. `Problem_solve` now stamps the solver name onto the results, which also persists through a saved session. Not yet exercised on a real 3DEC run.

* Corrected the stale claim, in three places, that `compas_lmgc90` is built only for cp312 and is therefore unavailable inside Rhino. It has shipped a cp39 wheel since 0.1.10 and is installed.

### Fixed — 2026-08-28

* **Toolbar rework: five tabs collapsed to one flat `COMPAS Masonry` bar** of 22 buttons with separators at the old group boundaries, and 22 redrawn icons. The six `CM_TNA_*` commands came off the bar but remain in `commands/` and typeable, pending a decision on retiring them.

* **`make_icons.py` no longer flattens CSS into presentation attributes.** `mix-blend-mode`, `isolation` and `clip-path` have no attribute form, so flattening silently dropped them and produced wrong z-order — `CM_Model_supports` painted an opaque white block over its own artwork. Eight of 22 icons were affected, the worst by 23.5% of pixels. `rsvg-convert` honours the `<style>` block natively, so reading the source verbatim is pixel-exact across all 22.

* **`make_icons.py --color` now defaults to shipping the artwork as drawn.** The old `#E6E6E6` default was chosen for a black icon set on a dark toolbar and made the redrawn light-toolbar set invisible. Measured over the real 22-tile sheet rather than a single swatch, which reversed the conclusion a swatch suggested.

* `verify_icons.py` and `test_registration.py` now assert that every toolbar *button* has an icon and pin the parked command set by name, instead of asserting that every command has a button — an assertion the parking made false. The rhproj ↔ `resources/icons/` check became two-directional, which caught six icons whose SVGs had been deleted.

### Fixed — 2026-08-27

* **Contact resultants are drawn where the force acts, not at the joint centroid.** The application point in `results.contact_resultants` resolved as `force_point` → contact frame origin → polygon centroid, and **CRA and RBE write neither of the first two** — `_post_processing_cra` stores the contact data, points, polygon, resultants and magnitude, and nothing else. So every CRA resultant landed on the middle of its joint, which discards the eccentricity: the drawn thrust line became a function of the geometry rather than of the solve, and an arch reported its own joint midpoints back.

  The value was never missing, only unread. `contact_data.resultantpoint` is the normal-force-weighted point, and it is now preferred ahead of the frame fallback. Measured on a 15-block arch, the correction is up to **0.22 m on a 0.5 m joint — 44% of the joint thickness** — and afterwards all 14 contacts match `compas_dem.viewer.DEMViewer.add_solution` to within 0.0000.

  The fix reaches every backend, because `contact_resultants` is solver-agnostic and all three compas_dem contact classes answer `resultantpoint`. LMGC90, PRD and BLA were also drawing at an arbitrary point — `contact_frames[0].point`, the *first* stored contact point — and are corrected too. 3DEC is unchanged: it is the one backend that writes `force_point`, and that still takes precedence.

  Magnitudes and directions were never affected. Reactions were and remain correct: 28.049 kN per support on that arch, exactly half the non-support weight in Z, matching the viewer to the digit.

* **`results.application_point_report()` warns when a contact's application point had to be guessed.** Reported by `Results_show` as it draws and by `Results_print` as it tabulates — worded once in `results.py` for the same reason as `tension_report`, since the same finding phrased two ways reads as two findings. It separates contacts that fell back to a joint centroid (eccentricity lost) from contacts dropped entirely for having no application point at all, which is what a 3DEC edge carrying more than one subcontact produces — those are silently absent from both the drawing and every report.

### Added — 2026-08-20

* **Loads are placed by picking the geometry, across any number of blocks.** The old flow selected ONE block, drew a temporary `TextDot` on every face or vertex, and asked the user to type the index back — a number they had no way to check, on a single block per command call. `inputs.pick_block_components` picks the faces or vertices themselves, on as many blocks as are selected in one go, and every anchor gets the same load.

  Two things worth not rediscovering. **`rs.GetMeshFaces` / `rs.GetMeshVertices` cannot do this**: they do exactly the right thing but pin themselves to one object via `SetCustomGeometryFilter(FilterById)`. `pick_mesh_components` is that function with that line removed, on `Rhino.Input.Custom.GetObject`. And **components are matched by POSITION, never by index** — blocks are drawn with `mesh_to_rhino(..., disjoint=True)`, which gives every face its own vertex copies and fans ngons into triangles, so a Rhino component index only accidentally equals the COMPAS key while every face is a tri or quad, and for vertices it is never right (a box has 8 COMPAS vertices and 24 Rhino ones). Matching uses `compas.geometry.closest_point_in_cloud`.

* **A load direction can be drawn in the viewport** — `Direction = Type|Draw` on Point and Surface loads. `inputs.pick_direction` rubber-bands a line and keeps only the **unit** vector; the magnitude is typed separately. The length is discarded deliberately: a force is in newtons and the document is in metres, so a 1 kN load would need a line a thousand units long. Displacements are dimensionally legal but are millimetres on a model metres across, so they are excluded too, and Moment and BodyForce stay components-only because a moment's vector is a rotation axis and drawing one reads as a movement. Direction is picked AFTER the anchors, so the geometry it acts on is on screen; emptiness is checked BEFORE any selection, so nobody picks a block, an anchor and a direction only to be told the force was zero.

* **Per-corner contact forces, and a tension report.** A solver does not solve for the contact resultant — it solves for a force at every vertex of the contact polygon, and the resultant is their sum. Drawing only the sum hides the thing that matters: a contact whose resultant is net compressive can still be in **tension** at some of its corners, and masonry takes no tension. The new `show_cornerforces` setting (off by default — a quad contact adds four lines) draws one line per corner along the contact normal, compression in `COLOR_NORMAL` and tension in the new `COLOR_TENSION`. Magenta rather than red, because reactions are already red and both appear in the same view.

  Nothing is recomputed: `FrictionContact.compressiondata` / `.tensiondata` already return `[x, y, z, nx, ny, nz, 0.5 * force]` per corner. Guarded with `getattr`, because LMGC90 stores an `EdgeContact` or `VertexContact` for degenerate contacts and neither carries per-corner forces.

  `results.tension_report()` builds ONE worded finding, used by `Problem_solve` at the moment the result is produced and by `Results_show` whenever it is drawn — worded differently in the two places it would read as two different findings. It warns normally, but only *prints* when `metadata["penalty"]` is set: a CRA penalty solve permits tension by design, so the same numbers are a result there and a fault everywhere else. That is also all a penalty solve needed to become visible — compas_dem already stored the flag, and the tension it allows is what the corner view now shows.

* **`CM_Results_block` exports CSV, and can isolate a block for a screenshot.** The output prompt became four toggles asked at once — Print, Tag, Csv, View — rather than one choice, so any combination is legal. Rows come from `results.block_result_rows`, built from the very same report the table prints, so the file and the screen cannot disagree about a number: one row per (block, contact), with the block's displacement repeated on every row so it pivots without carrying a value down a merged cell. Missing values are blank cells and never `0` — a stress of 0 and a stress the solver never produced are different answers — and a block with no force-carrying contact still gets a row, because dropping it would make a block that WAS reported on vanish from the export.

  Isolate hides every other block and every result force that does not touch a selected one, so a contact BETWEEN two selected blocks survives while their contacts with hidden neighbours do not. Objects carrying neither an `element_guid` nor an `edge` tag are left alone, so a construction line the user put in the document is not swept up. **Boundary-condition arrows are not filtered** — they carry a `load_kind` but no block index, so there is nothing to match on. `Session_redraw` restores the view; nothing else does.

* **`MasonrySession.summary()` and a `Status` option on `CM_Session_redraw`.** Nothing in the plugin ever reported its own state. It returns text — elements, contacts, materials, problems with their solver and boundary-condition groups, stored results, what is on screen, history position and the current record's name — printed and shown in `compas_rui.forms.InfoForm`, which already existed; no custom Eto was written.

* **`MasonrySession.save_problems()`**, the counterpart to `save_model()`, writing only the problems half of the analysis folder. See the storage note under Changed for why it matters.

### Changed — 2026-08-20

* **The session stores the analysis as a FOLDER of separate JSONs.** `LazyLoadSession` writes one `data/<key>.json` per key, so the whole model and every problem were rewritten on any edit to anything inside them. On a real 1025-block model:

  ```
  analysis/model.json                6.4 MB   0.430s
  analysis/problems/Problem_1.json   8 KB     0.001s
  ```

  Every `Problem_*` command paid the model write for nothing — a **430×** overhead, landing exactly on the 0.45s the `SESSION_KEYS` comment had predicted. `save_problems()` / `save_model()` now write only their own half; `save_analysis()` remains the both-changed case, and `test_every_problem_editing_command_uses_the_narrow_write` fails if a `CM_Problem_*` command regresses to it.

  **`analysis` deliberately stays ONE key.** Splitting it back into `blockmodel` + `problems` is what the 2026-08-07 migration undid: a `Problem` serializes as a guid REFERENCE to its model and `Analysis.__from_data__` is what rebinds them, so two keys hand that rebinding back to every load path. Only the STORAGE was split, and `_load_analysis` passes the parts straight to `Analysis.__from_data__` so the binding stays compas_dem's code. Implemented as four `LazyLoadSession` overrides — `get`, `set`, `delete`, `dump` — each dispatching on the key name and delegating everything else to the parent, which is why **no command changed for the format itself**. `analysis` and `results` remain two INDEPENDENT keys that merely share a parent directory, because `CM_TNA_envelope` deletes the analysis and keeps the results.

  The manifests are authoritative and the filenames are sanitized handles that nothing parses back. Problems are rewritten as a set rather than file by file, so a state with fewer problems than the last one cannot leave files behind for a later load to resurrect. **Legacy monolithic `analysis.json` / `results.json` are still read, permanently rather than as a one-shot migration**: every `__records/` snapshot taken before the folder existed holds one, and `undo()` copies those directories back verbatim, so a legacy file can reappear long after the first upgrade. A narrow write upgrades itself to a full one when the manifest is missing, otherwise the load would fall back to a stale monolith and silently discard the save.

* **Load arrows push into the geometry instead of hanging off it.** `rs.CurveArrows(guid, 2)` heads the END of a curve, so `_draw_bc_vector` gained `at="tip"|"tail"`: "tip" walks the start back along the vector and lands the head on the point of application. A −1000 N force at z=10 now draws from z=12 down to z=10. Two callers keep `at="tail"` — the **body force**, which has no point of application (it acts on every block by its mass, and the world-origin arrow is a legend), and the **prescribed displacement**, which is the block travelling rather than something pushing it.

* **Appearance is a Rhino viewport display mode; blocks are always meshes.** `show_wireframe` used to make `RhinoBlockObject.draw` emit one line per edge instead of a mesh. That is a display mode's job, and doing it by swapping the geometry gave the same picture while emptying the document of the faces and vertices that sub-object picking and the per-block guid tagging both need. Three settings now go through one validated `inputs.set_display_mode`: `pickmode_face` (`Shaded`) and `pickmode_vertex` (`Wireframe`) are restored afterwards by a context manager; `results_display_mode` (`Wireframe`) is set and **left** set, because the point is to leave you looking at the result.

* **The contact law and the joint model are one command.** `CM_Problem_contactlaw` was a ContactLaw/JointModel branch, so setting both meant running it twice. Every field is now seeded from what the problem already carries, because accept writes BOTH halves — fixed defaults would have silently reset `kn`/`kt` for anyone who came in only to change the friction angle.

* **The BlockModel settings section was audited: 12 of its 21 fields were read by nothing.** The dialog offered them and the drawing ignored them. Worst of it, `tol_contacts` / `amin_contacts` were a duplicate pair sitting two rows from `contact_tolerance` / `contact_minimum_area` — so "Tolerance Contacts" did nothing while "Contact Tolerance" was what `Model_contacts` actually used. The duplicates were merged away; `show_blocks` / `show_supports` / `show_contacts` / `show_interactions` were wired into `draw_model`, gated at the `scene.add` rather than by hiding afterwards, since an object never added has no guid to go stale; and `show_resultants` / `show_reactions` / `show_normalforces` / `show_frictionforces` / `show_selfweight` were wired into `draw_result_forces`.

  Resultants and reactions default **on**, because that is exactly what the command drew before the flags existed. Normal and friction are not new computations — `resultant_local` is the same stored force in the contact frame, so normal is `local[2]·zaxis` and friction is `local[0]·xaxis + local[1]·yaxis`, and the two sum back to the resultant. Self-weight uses compas_dem's own `_element_mass` rather than re-deriving density × volume, so the picture cannot disagree with what the solver applied. `BlockModelSettings` is now pinned by `test_every_show_setting_is_read_somewhere`, which walks `model_fields` and fails if a field is added without a consumer.

* **The results view reads against the model.** Displaced blocks are drawn in their own colour (`COLOR_DISPLACED`), because at a small displacement scale the displaced copy sits almost exactly on the model and in one colour reads as a no-op. Reaction magnitudes are drawn as `TextDot`s on their own `Forces::Values` sublayer, so the numbers toggle off without losing the arrows; only reactions are labelled, since one dot per contact resultant buries the model. The format is `%.4g`, matching `Results_print`, so the number on screen is the number in the report.

* `compas_dem`'s `Load` and `Displacement` are imported here as `AppliedLoad` and `PrescribedDisplacement`. `compas_dem.problem` also exports `Translation` and `Rotation`, which collide with `compas.geometry.Translation` / `Rotation`; the clash is latent rather than live — nothing here bound those bare names — but the plugin no longer binds any of them. The kind **strings** cannot follow: they are compas_dem class names read back through `_classname(bc)` and the stored discriminator at once, so renaming what the user sees needs a display-name map and renaming the classes means changing compas_dem and every serialized session's `dtype`.

### Fixed — 2026-08-20

* **A point load placed on a FACE crashed the redraw, and looked like it had only applied to one block.** compas_dem resolves the two anchors differently — `Problem.add_point_load_at_vertex` uses `vertex_coordinates()` and returns a **list**, `add_point_load_at_face` uses `face_center()` and returns a **`Point`** — and `session.set_user_params` did a bare `json.dumps`, which takes the list and raises `TypeError: Object of type Point is not JSON serializable` on the Point. So vertex loads always worked and face loads never could.

  The visible symptom was worse than the traceback: `draw_problem_conditions` tags each arrow as it draws it, in one loop, so the first face load raised and every load after it got no arrow. **The loads were always added and saved** — only the drawing died, which is why "Added point load … on 3 face(s)" still printed alongside the error. Fixed with `default=list` at the shared function every tagging caller routes through; it fires only for types `json` cannot take but that iterate as a sequence, and a type that is neither JSON-native nor iterable still raises. Not `compas.json_dumps`, which writes `{"dtype": ...}` wrappers that every reader here — plain `json.loads` expecting `[x, y, z]` — would fail on.

* **`CM_Masonry_Start.py` was tracked under two names.** The file had been capital-S in git since `7b161bb` while `ui.json` and `COMPAS-Masonry.rhproj` both said `CM_Masonry_start`; macOS is case-insensitive so the checked-out file was lowercase and `glob()` matched, but a `main` → branch checkout rewrote it and two registration tests began failing. The file was renamed to lowercase, matching the other 27 commands and both registries — and then the stale capital-S **index entry** was removed as well, which the rename alone had left behind: 29 tracked paths against 28 files on disk, invisible on macOS but producing a duplicate command on Windows or Linux. `test_every_rhproj_uri_exists` had only ever passed because of the case-insensitive filesystem.

### Removed — 2026-08-20

* **The `Output: Quiet|Verbose` toggle on `CM_Problem_setsolver`.** It only ever fed the CRA/RBE `verbose` argument, whose backends print solver iterations into the Rhino command line — noise in a plugin — and both `Solver.CRA` and `Solver.RBE` already default it to `False`, so neither is passed `verbose` at all now. LMGC90 is untouched: there `verbose` is a print INTERVAL rather than a flag (`lmgc90_solve` does `step % verbose`), which is why it is never passed there either.
* **The results fade** — the Fade/Keep prompt, `fade_model`, its `_blend` helper, `COLOR_FADED_BLOCK` and the `results_model_transparency` setting. Drawing the blocks as wireframe keeps result geometry readable without repainting every block object.
* From `BlockModelSettings`: `show_wireframe`, `scale_reactions`, and the duplicated `tol_contacts` / `amin_contacts` (see the settings audit above). Reactions are contact resultants and share `scale_forces`; a second independent scale desynchronises the one picture they exist to be compared in. **`FormDiagramSettings.scale_reactions` is a different field on the TNA side and is untouched.** The section is 20 fields now, all of them read by something.
* `label_faces`, `label_vertices`, `parse_faces` and `pick_indices`, with their 14 tests — replaced by picking the geometry. Also `delete_bc_group_layer` and `delete_bc_layers` (zero callers; `prune_bc_group_layers` and `delete_problem` cover them), `get_user_params` (zero callers; the two readers want one known key and call `rs.GetUserText` directly), and two unused arguments on `block_report`.

### Added — 2026-08-06

* **`CM_Session_undo` and `CM_Session_redo` do something.** Both were `warn("Not available yet.")`, and nothing in the repo had ever called `session.record()`, so there was no history to walk either. Thirteen state-changing commands now record a named state, `Session_clear` clears the history along with everything else, and history keeps the last 10 states on disk (`~/.compas_session/COMPAS-Masonry.session/__records/`), surviving a Rhino restart.

  `LazyLoadSession` implements only half of undo: `record()` works, but `undo()`/`redo()` move the FILES back and stop — they never touch `_data` or `_scene`, and `get()` only reads from disk when a key is *missing* from `_data`, so every already-loaded key kept returning the pre-undo object and an undo changed nothing observable. The module's own header comment lists the missing steps ("clear data dict", "load scene ... link items by guid"); neither was ever written. `MasonrySession` now overrides `undo`/`redo` to call the parent and then restore.

  **The restore deliberately does not load `_scene.json`.** `Scene.__data__` re-serializes the *items*, so a reloaded scene object's `.item` would be a copy of the model's block rather than the block itself — `Model_supports` would set `is_support` on one object while the scene coloured from another, silently — and `SceneObject.settings` carries no `layer` or `group` either. The scene is rebuilt from the restored data instead, via `draw_model()` and `draw_problem_conditions()`, the same path `Session_import` already takes. Documented in `temp/wiki_session_primer.md` §8.4.

  Two limits, stated in the commands' own docstrings: **TNA is not covered** (its envelope and form diagram are drawn inline by the TNA commands, not through the session, so a restore has nothing to call), and **history is global rather than per-document** (every command roots the session at `~/.compas_session`).

* `MasonrySession.record()` overrides the parent to fix three things, all found on the first real run and all measured or reproduced before fixing.

  **Dropped records leaked their snapshot folders.** Both places the parent shortens the history — the branch discard and the depth trim — do it with a slice assignment and never delete the folders, and `clear_history()` cannot reach them afterwards because it iterates the *list*. The depth trim runs on every record past `_depth`, so orphans grew without bound: one full copy of the session per command, ~6.5 MB each on a real model. Verified: 15 records at depth 10 left 15 folders on disk with 10 in history. The override sweeps whatever the parent dropped.

  **Recording serialized the data a second time.** `dump()` re-serializes every key in `_data` to the paths `set()` has already autosynced, producing byte-identical files. Measured at **0.45s per command** on a 6.5 MB BlockModel, against 3ms for the copy that follows — so undo roughly doubled the cost of every command, which was visible in Rhino. Emptying the cache around the parent call skips that loop; the snapshot comes from the autosynced working copy instead. `record()` on the same model: **0.42s → 0.00s**. Skipped when `autosync` is off, where the full dump is the only thing writing the working copy.

  **A snapshot now carries an empty scene, deliberately.** `dump()` also serialized `session.scene` on every record — `_scene.json` measured **12.7 MB against the model's 6.5 MB**, because `Scene.__data__` re-serializes the same block items — for a file that has no reader: the `scene` property only loads it when `_scene` is falsy, an empty `Scene` is truthy, and `__new__` always assigns one, so that branch cannot fire; and the restore rebuilds the scene from the data on purpose (see the Added note above). An empty scene keeps the path present so `undo()`'s copy of it cannot raise, and costs nothing. **The reversal is written out as a comment in `record()`**, along with what else it would take — a scene reloaded from a snapshot needs its items relinked to the data by guid and its `layer`/`group` reassigned before it is usable at all.

  **The persisted cursor was one behind** — `LazyLoadSession.record` writes `_history.json` through `dump()` **before** it updates `_current`, so the cursor on disk is always one behind the records beside it. Invisible in one process; fatal across commands, because each Rhino command is a fresh `Session(...)` whose `__init__` calls `load_history()` and reads that stale cursor back. `record()` then discards the forward branch against a cursor stuck at 0, on every single command — history never exceeded two entries and undo answered "Nothing more to undo!" no matter how much work had been done. Found on the first real run, reproduced headless, and pinned by `test_history_survives_a_session_rebuilt_between_commands`.
* **`shown_results`, a new session key** — `{problem_name: {"keys": [...], "mode": ...}}`, written by `CM_Results_show` and replayed by `MasonrySession.draw_shown_results()` during a restore. Result geometry is the one thing a restore cannot infer from the data: solving draws nothing, `Results_show` draws and takes choices that existed nowhere but in the document, and a restore clears the document — so the first version of undo silently destroyed the result view while `session["results"]` sat there intact. Being a session key it is snapshotted, so **undo now restores what was on screen, not only what was in the session**. Deleted by both `clear_results()` and `clear_model()`, so it cannot outlive the results it names. The fade is deliberately not recorded — `fade_model()` already defaults to `settings.blockmodel.results_model_transparency`.
* `MasonrySession.ensure_baseline()`, called at the top of each recording command. `undo()` refuses at `current == 0`, so history's oldest entry is a floor rather than a destination — without a snapshot taken *before* the first change, the first command of a session could never be undone.
* `MasonrySession.count_results()` / `clear_results()`, and `_clear_document()` split out of `clear_all()` so a restore can empty the document without deleting the session keys it has just restored.
* `tests/test_session_history.py` — 12 headless tests over the restore path, including one that pins the trap below.

### Fixed — 2026-08-06

* **Recomputing contacts silently invalidated stored results.** A `Results` is keyed by graph **node index** and `"u,v"` edge strings, so rebuilding the interaction graph voids every result derived from the old one — while `model_id` still matches, because it *is* the same model. `draw_results` looks up `results.transformation(block.graphnode)` by the block's *current* index, so shifted numbering drew another block's transformation as if it were correct, with no error. `CM_Model_contacts` now counts the stored results, asks for confirmation naming the count, and deletes them (and their Rhino geometry) before touching anything. The confirmation is at the top of the command deliberately: the existing teardown removes every interaction *before* the tolerance prompt, so a later prompt would leave the model with no contacts on a "no".
* **`CM_Session_import` produced problems that could not be solved.** A `Problem` serializes as a guid *reference* to its model and comes back unbound, so `problem.model` raised `ValueError` and every imported session failed at `Problem_solve`. It now calls `problem._bind_model(model)`.
* `src/compas_masonry/scene/__init__.py` records what the `# this clashes with TNA and/or RV` comment actually means: `compas_tna` registers the same `FormDiagram` key under the same `"Rhino"` context, registration is a plain dict assignment (last writer wins, silently), and compas_tna is a hard dependency — so it fires with no other plugin installed. RhinoVAULT does *not* collide directly; it registers its own subclasses. Options in `temp/status_open_decisions.md` §7.9. Not yet resolved.

### Fixed — 2026-08-05 (first run through the installed plugin)

* **LMGC90 crashed on its own default settings.** `Output = Quiet` sent `verbose=0` into `lmgc90_solve`, which used it as a modulus — `step % verbose` — so the very first step raised `ZeroDivisionError: integer division or modulo by zero` before anything was solved. Fixed upstream in compas_dem `ff128c0`: the progress print is guarded, and the force history is decoupled from it. `verbose` was gating `force_time` as well as printing, which meant a *logging* setting silently decided how much **result data** was recorded — the `Solver.LMGC90` default of `1000` kept a single sample for a 100-step run. It is now sampled every step. **The plugin needed no change**: `Solver.LMGC90(verbose=int(verbose))` in `CM_Problem_setsolver` became correct once `0` stopped being fatal.
* `CM_Session_settings` calls `session.redraw()` instead of `session.scene.redraw()`, matching every other non-TNA command.

### Added — 2026-08-05

* **The plugin is built and installed again** — `0.1.54-beta+24784`, the first build since Sep 2025 and the first ever to register the `CM_` command set. Typing a command name or pressing a toolbar button now runs something; before this, only the Script Editor did. Three things about the build are worth knowing and are documented in `temp/wiki_plugin_guide.md` §1.5: the `.rhp` **embeds a snapshot of `commands/`**, so a command edit needs a rebuild; the package **ships no Python library**, so `compas_masonry` is still resolved from the site-env through each command's `# r:` header, and a rebuild therefore does *not* pick up `src/` changes; and the build stamps its own `+<build>` number, so the version `yak install` expects comes from `manifest.yml`, not from `--buildversion`.

### Known issues — 2026-08-05

* **`CM_Masonry_start` fails unreadably when the plugin is not installed.** It resolves the splash through `Rhino.PlugIns.PlugIn.PathFromId`, which returns nothing in that case, so `System.Uri` is handed the literal relative path `None/shared/index.html` and throws `UriFormatException: Invalid URI: The format of the URI could not be determined` — naming neither the plugin nor the cause. Both `commands/CM_Masonry_start.py` and `src/compas_masonry/splash.py` compute it the same way and both want a guard. Every other command is genuinely independent of the install.

### Changed — 2026-08-04 (migrated onto the restructured compas_dem)

* **A Problem IS the load case.** compas_dem's restructure (`restructure/bc-hierarchy`) replaced the `BoundaryCondition` container with typed objects — `Load` (`PointLoad`, `Moment`, `SurfaceLoad`, `BodyForce`) and `Displacement` (`Translation`, `Rotation`) — registered directly on a Problem. `CM_Problem_createbc` is **deleted**, `CM_Problem_solve` no longer asks which boundary conditions to solve (every one is solved; a different set means a different problem), and the private-list swap that worked around `boundary_conditions` having no setter is gone with the property.
* **The session-side BC-kind map is deleted** — `BC_KINDS`, `bc_kind`, `set_bc_kind`, `reindex_bc_kinds`, `bc_allows` and the `bc_kinds` session key. It existed because a BC was an untyped bag constructed with `g=9.81`; the class is the kind now, and `g` is gone (self-weight is applied unconditionally from block density, so there is no Gravity load type and no gravity arrow).
* **Conditions are grouped for display by their own `name`.** compas_dem has no container to group them, but `name` rides in compas's `Data` envelope — verified to survive a JSON round trip despite being absent from `__data__` — so every condition called "Load_1" draws on `…::BoundaryConditions::Load_1`. `CM_Problem_loads` and `CM_Problem_displacements` offer New-or-existing as a field in the same window as the load itself, and a group's layer is deleted when its last condition goes.
* **Supports are model-level only.** `Model_supports` goes through `model.add_supports` / `remove_support` instead of setting `is_support` by hand. `session.refresh_problem_supports` and `Problem_create > RefreshSupports` are deleted, and the "Refresh the supports on them?" prompt with them — supports were copied onto every Problem and BC, which is the only reason they could go stale.
* **`BodyForce` is no longer expanded by hand.** The plugin used to write one centroid point load per block because `add_global_body_force` reached no solver; `resolve_centroidal_loads` now applies `BodyForce` natively and mass-weights it, so that expansion and the `AllPoint` removal it forced are deleted.
* **Point loads are offered at a vertex or a face centroid only.** compas_dem keeps all four anchors; restricting the Rhino UI to the two a user can see and click is the plugin's own decision (the summer-school one).
* Result keys are `<solver>_<timestamp>` (`RBE_2026-08-04T15-30-12`) instead of `<solver>_<bcs>`, so re-solving after a material or contact-law change keeps both runs side by side.
* `problem.solve()` replaces `model.solve(problem)`; `set_solver` / `set_contact_model` / `set_joint_model` replace `solver()` / `add_contact_model()` / `add_joint_model()`.
* **`CM_Problem_solve` checks the installed compas_cra up front.** compas_dem passes `loads=` into `cra_solve`/`rbe_solve` and no released compas_cra accepts it, so a stale site-env died mid-solve with `TypeError: cra_solve() got an unexpected keyword argument 'loads'` — naming neither package. It also refuses a CRA/RBE problem carrying prescribed movements, which those solvers structurally cannot apply (support blocks have no displacement degrees of freedom).

### Removed — 2026-08-04

* `CM_Problem_createbc` (a problem is the load case) and `CM_Results_export` (session save covers persistence; per-block numbers come from `CM_Results_block`). Renamed: `CM_Problem_addload` → **`CM_Problem_loads`**, `CM_Problem_solver` → **`CM_Problem_setsolver`**, `CM_Results_blockdata` → **`CM_Results_block`**. **30 commands → 28**, with the toolbars reordered to the agreed workflow order; renamed registry entries keep their `id` and icon.

### Changed — 2026-07-31 (first Rhino run: architecture and the fixes it decided)

* **Results moved out from under the boundary conditions.** They are drawn at problem level now — `Masonry::<i>_<problem>::Results::<key>::Forces|Displaced` — instead of `…::BC<n>_<bc>::Results::<key>`. A result set covers a *combination* of BCs (`RBE_BC1-BC2`), so filing it under one of them meant choosing which BC to blame, and the whole set was thrown away whenever that BC was renamed or deleted (`delete_all_bc_layers` regenerates the subtree from scratch). `draw_results` and `draw_result_forces` lost their `bc, index` arguments, `session.results_layer()` is new, and `Results_show.target_bc` — which existed only to pick that BC, with a fallback for when the stored names no longer matched — is gone.
* **Boundary conditions hang off a parent layer**: `Masonry::<i>_<problem>::BoundaryConditions::BC<n>_<bc>`, not directly off the problem. `delete_all_bc_layers` deletes the children of that parent rather than of the problem, so it can no longer take the results with it.
* **The block fade is a custom object colour, not a layer render material.** Render materials are only consulted by the modes that render, so the fade was invisible in stock Shaded — the mode most people work in. `set_model_transparency` is replaced by `fade_model(amount)`, which blends each block toward white and restores objects to "colour by layer" at 0. Rhino layers have no opacity, so faded means pale rather than see-through; the old setting only ever *looked* transparent in Rendered mode.
* **Everything the plugin draws now carries a custom object colour, set at creation.** Contact resultants and applied loads dark green (21, 128, 61), a resultant on a support contact red (214, 40, 40) since that reading is the support's reaction, prescribed displacements and rotations black, contact surfaces / edge lines / points `#0092d2`. A resultant on a support contact is also tagged `result_kind: support_reaction`.
* `Model_supports` no longer asks "Refresh the supports on them?" when the problems in question hold **no** supports yet — that fired on the very first run of the command, before any support existed. A problem with nothing to lose is refreshed silently; the prompt is kept for one whose support set would actually be replaced.
* `Results_show` offers **Displaced only for a solver that produces displacements** (LMGC90, 3DEC). The solver is read off the result key rather than off `problem.solver`, which may have been changed since the solve. For a CRA/RBE set there is nothing to choose, so it no longer asks at all.
* `Session_clear` parks the current layer on Default before tearing the tree down. Rhino refuses to delete the current layer and `delete_layers` only guards the path it is handed, so with a problem or BC layer current, `rs.PurgeLayer("Masonry")` left the whole branch containing it standing — which is how problem layers survived a clear. The empty `Masonry` root is recreated afterwards. `delete_problem` and `delete_all_bc_layers` take the same guard.
* Command line prompts use one separator style: `prompt | annotations | units | accept`, with units as `Keyword [unit]`. They mixed `[…]`, `(…)` and a non-ASCII em dash in a single line, which ran together and rendered inconsistently in the Rhino command line.
* The predefined-material table sizes its columns to their contents and prints floats to 4 significant digits. `str()` of a float runs to 18 characters (`0.19999999999999998`) — wider than the hardcoded 12-character column, which shifted every cell after it out of line.

### Removed — 2026-07-31

* **Import and save are session-level only**, as in RhinoVAULT: `CM_Masonry_import` → `CM_Session_import`, `CM_Masonry_export` → `CM_Session_save`, and `CM_Model_import`, `CM_Model_export` and `CM_Problem_export` are deleted. They wrote fragments that could not be opened back into a working session, and gave three answers to "how do I save my work". **33 commands → 30**, in `commands/`, `COMPAS-Masonry.rhproj` and `resources/rui/ui.json` alike; the two renamed entries keep their `id` and icon. `CM_Results_export` stays — it writes result data for analysis, not session state.

### Added — 2026-07-30 (a simulation runs end to end)

* A simulation now runs end to end in Rhino with **CRA or RBE**: model → contacts → supports → material → problem → contact law → solver → boundary condition → solve → results. Verified in Rhino and headless on Rhino's own python3.9.
* Added `MasonrySession.draw_result_forces`, which draws contact resultants and contact geometry under `…::Results::<key>::Forces`. CRA and RBE store an *identity* transformation per block and put the whole answer on the contact edges, so a displaced-geometry view of their results showed a duplicate of the model and looked like nothing had happened. Force lines are centred on the contact point, contacts are drawn by class (face → polygon, edge → line, point → point), and each carries its magnitudes as User Text.
* Added `settings.blockmodel.scale_forces`, a **dimensionless** result-force scale: at 1.0 the largest resultant in a result set is drawn half as long as the biggest block is wide, so forces are visible without per-model tuning whatever the units are.
* Added `MasonrySession.ensure_solver_path` and `settings.solver_bin`. compas_cra resolves `ipopt` as an *executable* on `PATH`, and Rhino launched from the Finder has no shell `PATH`, so a conda-installed ipopt was invisible and the solve died inside pyomo saying nothing about `PATH`.
* Added `MasonrySession.clear_all`, so `Session_clear` empties the document: the whole `Masonry` layer tree (children included, which also sweeps orphans from an earlier crash) plus every session key the plugin owns.
* Added `MasonrySession.refresh_problem_supports` and a `RefreshSupports` operation to `Problem_create`. Supports are copied onto a problem at creation and into each boundary condition at registration, so editing them afterwards silently left every problem holding the old set. `Model_supports` now detects that and offers to refresh. Prescribed displacements are preserved.
* Added **BC kinds** — `Gravity | Loads | Displacements | Mixed` — chosen with the name in `Problem_createbc` and enforced by `Problem_addload` and `Problem_displacements`. Held session-side (`session.bc_kinds`), keyed by index and reindexed when a BC is deleted, since compas_dem's `BoundaryCondition` has no such field.
* Added a **BodyForce** load type: an acceleration applied to every block by its mass, expanded into one centroid point load each (`mass * a * direction̂`). This is the tilted-table / static-seismic load, expressed so that every solver reading point loads honours it without a compas_dem change.
* Added `units=` to `compas_masonry.inputs`, shown as a legend of the currently visible fields on the command line and appended to the label in the Eto renderer. A Rhino option renders as `Keyword=Value` and nothing else, so units written into `prompt` were invisible until the option was picked.
* Added `settings.blockmodel.results_model_transparency` and `MasonrySession.set_model_transparency`, to fade the blocks while results are drawn on top. Transparency lives in a layer's render material, so it only shows in Rendered/Raytraced display modes.
* Added `tests/rhinostub.py` and `tests/test_command_helpers.py` — 35 headless tests covering face parsing, the BC-kind matrix and its reindexing, result keys, BC naming, body forces and the supports refresh. `compas_masonry.inputs` touches `Rhino.Input.Custom` at class-definition time, which had made every command module unimportable outside Rhino.

* Added `compas_masonry.results`, which derives everything a report or a drawing needs from a `Results` — contact resultants, face stresses, joint openings, per-body displacements, support reactions, and a tagged summary of the maxima — with no Rhino, so the reporting commands and the force drawing cannot disagree and both are testable headlessly.
* Implemented the three Results stubs on top of it: `Results_print` (Summary / Contacts / Blocks / Reactions), `Results_blockdata` (per selected block, printed or written back as User Text), and `Results_export` (Json round-trip of the Results, or Csv per contact).

### Changed — 2026-07-30

* **`LoadCase` → `BoundaryCondition`**, following the compas_dem rename (`a6454c6`, no compatibility alias): `compas_masonry/loadcases.py` → `boundaryconditions.py` (`bc_name`, `bc_labels`), the session's layer API (`bc_layer`, `ensure_/clear_/delete_bc_layers`, `choose_bc(s)`, `draw_bc`, `draw_problem_bcs`), and the layer prefix `LC<n>_` → `BC<n>_`. `CM_Problem_createloadcase.py` → `CM_Problem_createbc.py`, and `CM_Problem_boundaryconditions.py` → `CM_Problem_displacements.py`, whose old name now collided with the BC concept. Existing session JSON holding `LoadCase` dtypes no longer loads.
* Solving no longer offers PerLoadCase/Combined: **every selected BC solves together**, in list order, and the result is stored under a key naming the solver and the BCs (`RBE_BC1-BC2`). An identical key is reused rather than re-solved. There is no stepped solve.
* `Problem_solve` checks contacts, solver, contact law, supports and material densities before starting, and resolves `ipopt` first, so a failure names the command to run instead of surfacing a traceback.
* `Results_show` draws per stored result set, with a Forces / Displaced / Both mode that defaults to **Forces** when every transformation is an identity.
* The solver picker is now CRA / RBE / LMGC90 (PRD and BLA dropped), with LMGC90 guarded by an importability probe. `d_bnd`/`eps`, `mu` and `theta` are deliberately not exposed — see `REFACTOR_GUIDE.md` §6.
* BC sublayers are created **only when they have content**, so a gravity-only BC grows no `Displacements` layer and `Results` appears only once results are drawn.
* Surface loads accept **several faces** (`0,3,5` or `all`), one entry per face; invalid entries are reported rather than silently loading the wrong face.
* A new BC no longer arrives carrying a gravity load: `BoundaryCondition` is constructed with `g=9.81`, so only a Gravity or Mixed BC keeps it. (`bc.g` is a flag — CRA and RBE apply self-weight internally regardless.)
* `Problem_contactlaw` prints **both** phi and mu, read back from the stored contact model, since they are two views of the same thing and mu is what the solvers use.
* `Model_materialassign` now tags blocks with `material_name` as well as `material_guid`.
* `fc` → `fck` in `Model_material`, following compas_dem `c924950`; `Ecm` is labelled MPa (the predefined values are 20000/30000).

### Fixed — 2026-07-30
* `contact_frame` is absent from every CRA/RBE result — `_post_processing_cra` writes the polygon, points, resultants and magnitude and nothing else — so deriving the contact normal from the frame silently returned **no stress and no reactions** for them. The normal now falls back to the contact polygon's own normal; pinned by `tests/test_results.py`.

* `MasonrySession.clear_model` deleted the session key `"problem"`, but the key the plugin writes is **`"problems"`** — so stale problems and `active_problem` survived a model swap, pointing at a deleted model.
* `bc_name` returned `"BoundaryCondition"` for an unnamed BC, making the `BC<n>` fallback unreachable: compas's `Data.name` returns `self._name or self.__class__.__name__`. It now reads `_name`.
* `create_problem`'s duplicate path called `source.boundary_conditions.copy()`, which since the rename copies a *list* and shares the BC objects between problems. Each BC is now deep-copied.
* `session.draw_problem` (shared with the frozen original commands) assumed `problem.boundary_conditions` was a single object; it is now a list.
* `print_predefined` in `Model_material` still read the `fc` key and would have printed "-" for every material's strength.
* Fixed two pre-existing test failures from upstream API drift: `problem.contact_properties` became a property, and `Mesh.volume` a method.

* Registered all 33 commands in `COMPAS-Masonry.rhproj` and `resources/rui/ui.json`, and rebuilt the toolbars in workflow order. `Problem_solve` sits at the end of the **Problem** toolbar, not in Results: solving is the last step of setting a problem up, and Results holds what you do with the answer. Renamed entries in place so each keeps its `id` and icon; the four genuinely new commands (`Problem_createbc`, `Results_show`, `Masonry_export`, `Masonry_import`) borrow a sibling's icon.
* Fixed the toolbars pointing at commands that do not exist: the items still used un-prefixed names (`Masonry_Start`) after the `CM_` rename, so every button silently did nothing — the RUI loads fine either way.
* Removed five stale registry entries whose command files are gone (`Session_settings`, `Problem_loads`, `Problem_boundaryconditions`, `Problem_contactmodel`, `Solve`) by pointing them at the commands that replaced them.

* Brought every working doc in line with the code: `REFACTOR_GUIDE.md` gained §1.5 on the two ways to run a command and what a build actually changes, `IMPLEMENTATION_PLAN.md`'s next actions are now the build-and-release list, and `ARCHITECTURE_STUDY.md` / `RHINO_PRIMER.md` / `RHINO_DEV_GUIDE.md` no longer describe load cases, two command sets, or an unregistered `_options` set.
* Rewrote the user-facing `README.md`: all 33 commands by group (checked against the registry), a Solvers section stating that CRA/RBE work and need the unreleased compas_cra 0.5.0 plus pyomo >= 6.7.3, and that LMGC90 has no Rhino build. It had claimed the plugin shipped no solvers at all, and told users to "install RhinoVAULT with Yak".
* Extended `tests/rhino/README.md` with the whole-workflow manual checks and the after-a-build checks.

* Fixed `CM_Problem_addload` throwing `NameError: name 'bc_name' is not defined` partway through the command — it used the helper without importing it. A command body only runs inside Rhino, so this survived every headless test and `compileall`. `tests/test_lint.py` now runs ruff F821/F811 over `commands/`, `src/` and `tests/`, which catches the whole class statically.

### Environment — 2026-07-30

* CRA/RBE could not run in the Rhino site-env at all: it ships **numpy 2.0.2**, and **pyomo 6.4.2** registers `np.float_` (removed in NumPy 2) at import. Patching the alias makes the import succeed and then produces a corrupt `.nl` file (`np.float64(-0.0)` → ipopt `INVALID_TNLP`), so it is not a fix. pyomo ≥ 6.7.3 in turn breaks **compas_cra 0.4.0** (`MatrixConstraint`), and PyPI has nothing newer. Resolved with **pyomo 6.8.2 + the local compas_cra 0.5.0 fork** (`--no-deps --ignore-requires-python`), installed into the site-env. Full account in `temp/COMMANDS_REVIEW.md` §12.
* A stale `build/` tree makes setuptools package deleted modules, so a renamed file keeps reappearing in the site-env after every sync. `rm -rf build/` after any rename.

### Added

* Added `compas_masonry.inputs`: command line input built on `Rhino.Input.Custom.GetOption`, so a command shows every parameter at once instead of a chain of sequential `rs.GetString`/`rs.GetReal` prompts. `Options` (with `add_number`/`add_integer`/`add_toggle`/`add_list`/`add_text` and a `visible` predicate for dependent fields), `choose`, and the `BACK` sentinel for a "Back" option that steps to the previous window. COMPAS has no parameter-input layer for Rhino — `compas_rhino` covers object selection and file browsing only — which is what this fills.
* Added `Options.from_model` / `Options.apply`, which build the options from a pydantic model's fields (title, default, `ge`/`le`), so one settings model renders either as the Eto `SettingsForm` or on the command line. `field_ge`/`field_le` moved to `compas_masonry.inputs` and are re-exported from `compas_masonry.forms.settings`.
* Added a `keywords` mode to `MasonrySession.choose_problem`: problem names are offered as command line options with the active problem as the Enter default, instead of picking a printed index.
* Added `compas_masonry.loadcases`, the single bridge to the incoming compas_dem LoadCase API (`LoadCase`, `Problem.add_loadcase`, `BlockModel.solve(problem=, loadcases=)`). Commands are written against that API already; until it lands the helpers raise `LoadCaseUnavailable` with an explanatory message instead of an ImportError traceback.
* Added the load case layer hierarchy to `MasonrySession`: `indexed_problem_layer`, `renumber_problem_layers`, `loadcase_layer`, `ensure_loadcase_layers`, `clear_loadcase_layers`, `delete_loadcase_layers`, `delete_all_loadcase_layers`, `choose_loadcase`, `choose_loadcases`, `draw_loadcase`, `draw_problem_loadcases`, `draw_results`.
* Added `commands/*_options.py`, the RhinoCommon variant of every command that takes input, plus the new commands of the dev notes refactor: `Problem_createloadcase`, `Problem_addload`, `Problem_solve`, `Results_show`, `Masonry_export`, `Masonry_import`.
* Added a temporary face-index helper to `Problem_addload`: the faces of the selected block are labelled with their index while the surface load face is picked, and the labels are always removed afterwards.
* Added a session-level export/import pair (`Masonry_export` / `Masonry_import`) covering the model, every problem with its load cases, the active problem and the display settings in one JSON file.
* Added `compas_masonry.forms.options.OptionsForm`, an Eto renderer for the same `Options` declaration the command line uses. `Options.get()` dispatches on the new `settings.dialog_input` (Session_settings -> Input), so no command has to know which renderer is running; the form writes back into the same Rhino option objects, leaving `Options.values` identical either way. Useful on macOS, where Rhino's command options dialog always carries an empty text entry box that no `GetOption` API can remove.
* Added `temp/REFACTOR_GUIDE.md`, a full walkthrough of the refactor: how to get the repo running (sync scripts, engine reload, build), the data model and layer tree, every command, the backend modules, and the known gaps.

* Added `MasonrySession.set_model`, `MasonrySession.clear_model`, `MasonrySession.draw_model` as the shared install/clear/draw path for every model-creating command.
* Added `MasonrySession.redraw` to redraw the scene and keep Rhino guid tags in sync, since `Scene.redraw()` recreates every drawn object with new guids.
* Added `MasonrySession._tag_block_guids`, `MasonrySession.guid_element_map`, `MasonrySession.find_node` to resolve a Rhino object guid to its current graph node via a persistent `element_guid` Rhino User Text tag, robust to node renumbering and object renaming (replaces parsing the `"Block_N"` object name).
* Implemented `Add`/`Remove`/`Clear` support logic in `Model_supports.py`, syncing existing supports to the `Masonry::Model::Supports` layer on open.

### Changed

* Every file in `commands/` is now prefixed `CM_` (`Model_blocks.py` → `CM_Model_blocks.py`), so command files are recognizable at a glance. The filename **is** the Rhino command name, so the commands are now `CM_Model_blocks`, `CM_Problem_create`, and so on; `COMPAS-Masonry.rhproj` (`title` + `uri`) and `resources/rui/ui.json` (`name` + `! _<macro>`) were updated to match — 28 entries each. `commands/old/` was left alone.
* Load cases, not problems, now own the loads, the boundary conditions and the results (dev notes). A problem gets one layer, `Masonry::<index>_<name>`, with no Loads/Boundary conditions sublayers; each load case creates its own subtree on demand, `…::LC<n>_<name>::Loads|Displacements|Results`. Deleting a problem renumbers the remaining problem layers. `MasonrySession.create_problem` takes `sublayers=False` for the new hierarchy and `delete_problem` takes `indexed=True`; the defaults keep the pre-loadcase commands working unchanged.
* `Problem_create` asks for the problem name as a named option seeded with the next free `Problem_<n>` (no string prompt on the first window), and gained a `Delete` operation, which is where the layer renumbering happens.
* `Problem_boundaryconditions` now edits a load case, and draws a prescribed displacement as an arrow and a prescribed rotation as a circle around its axis — no displaced copy of the geometry (that is `Results_show`).
* `Model_material` prints every predefined material with its values as a table before the pick, offers a `Custom` entry in the same list that leads into the custom generation, and offers `Back` on the property window.
* `Problem_solve` draws nothing: it stores one result per solved load case on the session, and `Results_show` is what puts displaced geometry in the document.
* Restyled the splash screen (`resources/splash/`): light layout matched to the artwork with its coral as the only accent, a white scrim for legibility, real Yes/No buttons and hover states.
* Deduplicated the command helpers against upstream: list dialogs use `rs.ListBox`, yes/no uses `compas_rui.feedback.confirm`, problem picking uses `MasonrySession.choose_problem` — replacing the `pick_from_list`, `confirm` and `choose_problem` helpers that had been added to `compas_masonry.inputs`.
* `Model_blocks.py` now calls `session.clear_model()`/`session.set_model(model)` instead of duplicating scene setup/teardown inline.
* `Model_contacts.py` now calls `session.redraw()` instead of `session.scene.redraw()`, so Block guid tags survive.

### Fixed

* `MasonrySession.redraw` no longer dies with `AttributeError: 'NoneType' object has no attribute 'RuntimeSerialNumber'`. `Scene.redraw()` purges every guid its scene objects still hold, and `compas_rhino.objects.purge_objects` dereferences `find_object(guid)` without a None check — so one scene object holding a guid whose Rhino object is gone breaks the redraw of the whole scene. The new `MasonrySession.prune_stale_guids()` drops those guids first, and runs on every `session.redraw()`. A guid is dropped only when the lookup `purge_objects` uses reports it gone, so the redraw keeps deleting everything it should.
* Fixed the **duplicate geometry** that followed such a crash: two copies of every block. `Scene.clear()` nulls each scene object's `_guids` *before* purging them, so a crash mid-purge left the scene tracking nothing while every Rhino object stayed in the document — orphans invisible to all later redraws, with the next draw stacking a fresh set on top. Preventing the crash prevents the orphans; orphans already saved in a `.3dm` are swept by the next `clear_model()`.
* `MasonrySession.clear_model` now prunes stale guids first, clears each scene object (`obj.clear()`) before removing it, and matches `EdgeContact` / `VertexContact` alongside `FrictionContact` — the same three corrections applied to `Model_contacts`, so every teardown path behaves the same way.
* `Model_contacts` now clears contact/graph scene objects (`obj.clear()`) before removing them, and matches `EdgeContact` and `VertexContact` as well as `FrictionContact`. Those two are plain `Data` subclasses, **not** `FrictionContact` subclasses, so `find_all_by_itemtype(FrictionContact)` left their scene objects behind while `clear_layer` deleted the geometry under them — the exact way the redraw above got poisoned. The same pattern is still present in the frozen original `CM_Model_contacts.py`, which is now protected by the session-level prune rather than fixed in place.
* `session.draw_loadcase` now redraws the loaded face of a surface load, not only the load arrow — the face mesh was drawn by the old `draw_problem` and was lost in the load case rewrite.
* `compas_masonry.forms.settings.SettingsForm` no longer raises `TypeError` on non-class field annotations (`Optional[...]`, `Literal[...]`, `list[...]`): the `issubclass(field.annotation, BaseModel)` check is guarded with `isinstance(field.annotation, type)`.

### Removed

* Removed `Problem_contactmodel`, renamed to `Problem_contactlaw` (dev notes: a problem holds one solver and one contact law).
* Removed `Problem_loads`, superseded by `Problem_addload` (loads belong to a load case).
* Removed `pick_from_list` and `confirm` from `compas_masonry.inputs`, and the module-level `choose_problem` that forked `MasonrySession.choose_problem`.
* Removed name-string parsing (`"Block_N"` → `int`) as the mechanism for resolving Rhino objects to graph nodes.

### Adapted to the shipped compas_dem LoadCase API

The `LoadCase` / `Results` API landed in compas_dem, and differs from the dev notes in ways that changed the commands:

* `LoadCase.add_point_load(block_index=, force=, moment=, point=, loading_type=)` and `add_surface_load(block_index=, face_index=, load=, loading_type=)` — not the `add_pointload(block_idx=, forcevector=)` spelling of the notes. The commands call them directly and expose `loading_type` (ramp / instantaneous) as an option.
* `LoadCase.add_displacement(block_index, dx=, dy=, dz=)` is **per component**, where `None` means the DOF is unconstrained — which is not the same as prescribing 0.0. `Problem_boundaryconditions` mirrors that with a Prescribed/Free toggle per axis, and the value option for an axis only appears when that axis is constrained.
* `Problem.add_loadcase` returns the index to use and *replaces* the auto-created "default" load case at index 0 when one exists, so the return value is used rather than `len(loadcases) - 1`. Supports live on the Problem and are copied into each load case as it is registered.
* `BlockModel.solve(problem, loadcases=[...])` returns ONE `Results` for the whole call and solves the given load cases concurrently — not one result per load case. `Problem_solve` exposes the resulting choice: `PerLoadCase` (default, one solve each, matching the per-load-case Results layers) or `Combined` (one concurrent solve, stored under the first selected load case).
* `Results` is a compas Data, so it serializes onto the session as is, and `Results.displacement_scale` does the exaggeration inside `Results.transformation`. `session.draw_results` sets it from `settings.blockmodel.scale_displacement`.
* `Solver` now offers LMGC90 / CRA / PRD / **BLA** / RBE (no DPRD). `Problem_solver` follows, with the real parameters per solver; the dict-shaped `non_linear_params` / `non_associative_params` are left at their compas_dem defaults since they have no command line widget.
* `compas_masonry.loadcases` shrank from an availability/compat shim to display helpers only (`loadcase_name`, `loadcase_labels`, `is_support`, `entry_vector`, `describe_entry`); commands import `LoadCase` from `compas_dem.problem` directly.

### Known gaps

* Every command file is now prefixed `CM_` (see below), which renames the Rhino commands themselves.
* Nothing in the `*_options` set has been exercised inside Rhino yet.
* The `*_options` commands are not registered in `COMPAS-Masonry.rhproj` / `resources/rui/ui.json` — they run from the script editor only.

* Added `compas_masonry.algorithms.mesh_mesh_contacts`.
* Added `compas_masonry.elements.BlockElement`.
* Added `compas_masonry.interactions.ContactInterface`.
* Added `compas_masonry.models.BlockModel`.
* Added `compas_masonry.templates.Template`.
* Added `compas_masonry.templates.ArchTemplate`.
* Added `compas_masonry.viewers.BlockModelViewer`.
* Added `compas_masonry.materials.Material`.
* Added `compas.masonry.materials.Stone`.

### Changed

* Changed `compute_aabb and compute_obb in compas_masonry.elements.BlockElement`.

### Removed

* Removed `frame attribute from compas_masonry.elements.BlockElement`.

## [0.3.0] 2025-09-10

### Added

* Added `compas_masonry.viewer.MasonryViewer` for interactive visualization of masonry structures.

### Changed

### Removed


## [0.2.7] 2025-09-10

### Added

### Changed

### Removed


## [0.2.6] 2025-09-10

### Added

### Changed

### Removed


## [0.2.5] 2025-09-09

### Added

### Changed

### Removed


## [0.2.4] 2025-09-09

### Added

* Updated TNA_Loads and TNA_analysis

### Changed

### Removed

## [0.2.3] 2025-09-09

### Added

* Added MeshEnvelope options to TNA_Envelope

### Changed

### Removed


## [0.2.2] 2025-09-09

### Added

### Changed

### Removed


## [0.2.1] 2025-09-09

### Added

### Changed

### Removed


## [0.2.0] 2025-09-08

### Added

### Changed

### Removed


## [0.1.1] 2025-09-07

### Added
