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

# NAM AMP (NAM Extended): AmpCab, the class behind every amplifier block ("82 LEAD 800 Bright" is the one the
# hook acts on). Found through the RTTI of the MX5 2.7 Evil (same method that reproduces the two pedal vtables
# above); process() sits in slot 7 and uses the object offsets the Gigboard hook expects (0x94ec, 0x9548, 0x95a5, 0x9500...).
MX5.update({
    "amp_engine_vtable_vaddr": 0x15E737C,
    "amp_orig_process_fn": 0x139538,
    "amp_process_slot": 7,
})
