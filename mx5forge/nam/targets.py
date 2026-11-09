"""Per-firmware constants of the NAM hijack (values from headrush-nam-mod core/model_targets.c).

Only the MX5 (FIT compatible "inmusic,hg04", firmware 2.7) is supported by this project."""

MX5 = {
    "name": "mx5",
    "compatible": "inmusic,hg04",
    # Anxiety OD (v1) engine vtable and its real process() function
    "engine_vtable_vaddr": 0x17EE460,
    "orig_process_fn": 0x302ED0,
    # Anxiety OD V2 ("AnxietyV2"); same compiled process() function as v1
    "v2_engine_vtable_vaddr": 0x17EE4DC,
    "v2_orig_process_fn": 0x302ED0,
}
