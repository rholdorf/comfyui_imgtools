# ROADMAP: ComfyUI Image Tools v1.0

## Milestone: v1.0 - Image Dimension Fitter

### Phase 1: Project Setup ✓
**Goal:** Establish ComfyUI custom node structure and verify integration

- [x] Create `__init__.py` with node registration
- [x] Create main node file structure
- [ ] Test node appears in ComfyUI (pending user verification)

**Plans:** 1 | **Status:** completed

---

### Phase 2: Core Node Implementation
**Goal:** Implement the ImageDimensionFitter node with model selection and dimension logic

- [ ] Define dimension tables for each model (SD, Flux, Z-Turbo)
- [ ] Implement dimension matching algorithm (find closest standard size)
- [ ] Create node class with INPUT_TYPES and RETURN_TYPES
- [ ] Add model dropdown widget

**Research:** Confirm Z-Image Turbo optimal dimensions

---

### Phase 3: Crop Logic
**Goal:** Implement centered crop functionality

- [ ] Implement center crop algorithm
- [ ] Handle edge cases (image smaller than target)
- [ ] Support batch processing
- [ ] Test with various aspect ratios

**Research:** None required

---

### Phase 4: Testing & Polish
**Goal:** Validate the node works correctly in real workflows

- [ ] Test with SD workflows
- [ ] Test with Flux workflows
- [ ] Verify no KSampler artifacts
- [ ] Add any missing error handling

**Research:** None required

---

## Notes

- Simple single-node project
- Focus on correctness over features
- v1 only does crop (no scale)
