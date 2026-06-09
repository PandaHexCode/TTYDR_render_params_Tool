import json, random, sys, copy
from pathlib import Path


FIELDS = {
    "/env/globalLightColor"           : ("hdr_color",   None),
    "/env/globalLightAmbient"         : ("color",       None),
    "/env/globalLightSpecAmbient"     : ("color",       None),
    "/env/effectLightColor"           : ("hdr_color",   None),
    "/env/effectLightAmbient"         : ("color",       None),
    "/env/clearColor"                 : ("color",       None),
    "/env/altitude"                   : ("float",       (-90.0,  90.0)),
    "/env/azimuth"                    : ("float",       (0.0,   360.0)),
    "/env/effectLight_altitude"       : ("float",       (-90.0,  90.0)),
    "/env/effectLight_azimuth"        : ("float",       (0.0,   360.0)),
    "/env/exposure/bias"              : ("float",       (0.5,    1.8)),
    "/env/indirectIntensity"          : ("float",       (0.0,    2.0)),
    "/env/indirectSaturation"         : ("float",       (0.0,    2.0)),
    "/env/iblRotateH"                 : ("float",       (0.0,   360.0)),
    "/env/iblRotateV"                 : ("float",       (-90.0,  90.0)),
    "/env/probeShadowIntensity"       : ("float",       (0.0,    2.0)),
    "/env/probeShadow_EnhanceHigh"    : ("float",       (0.0,    5.0)),
    "/env/probeShadow_EnhanceLow"     : ("float",       (0.0,    5.0)),
    "/env/diffIblExposure"            : ("float",       (0.0,    1.5)),
    "/env/specIblExposure"            : ("float",       (0.0,    1.5)),
    "/env/aoMixAlbedo"                : ("float",       (0.0,    1.0)),
    "/env/highLuminance_Intensity"    : ("float",       (0.0,    1.0)),
    "/env/manualSunEnable"            : ("bool",        None),
    "/env/sunShadowEnable"            : ("bool",        None),
    "/env/dynamicShadowEnable"        : ("bool",        None),
    "/event/shadowLightColor"         : ("color",       None),
    "/event/shadowLightAltitude"      : ("float",       (-90.0,  90.0)),
    "/event/shadowLightAzimuth"       : ("float",       (0.0,   360.0)),
    "/event/shadowLightEnable"        : ("bool",        None),
    "/bloom/visible"                  : ("bool",        None),
    "/bloom/power"                    : ("float",       (0.0,    1.5)),
    "/bloom/threshold"                : ("float",       (0.5,    2.0)),
    "/expfog/visible"                 : ("bool",        None),
    "/tonemap/triple/exponent"        : ("float",       (0.8,    2.0)),
    "/tonemap/triple/maxBrightness"   : ("float",       (0.8,    2.5)),
    "/tonemap/triple/contrast"        : ("float",       (0.5,    2.0)),
    "/tonemap/triple/blackTightness"  : ("float",       (0.0,    1.0)),
    "/tonemap/triple/blackPedestal"   : ("float",       (0.0,    0.5)),
    "/ssao/visible"                   : ("bool",        None),
    "/ssao/radius"                    : ("float",       (0.1,    5.0)),
    "/ssao/bias"                      : ("float",       (0.0,    0.5)),
    "/ssao/power_exponent"            : ("float",       (0.5,    4.0)),
    "/dof/visible"                    : ("bool",        None),
    "/vignette/visible"               : ("bool",        None),
    "/vignette/radius"                : ("float",       (0.0,    1.5)),
    "/vignette/softness"              : ("float",       (0.0,    1.0)),
    "/pera_shadow/visible"            : ("bool",        None),
    "/pera_shadow/peraShadowDarkness" : ("int",         (0,      200)),
    "/pera_shadow/altitude"           : ("float",       (-90.0,  90.0)),
    "/pera_shadow/azimuth"            : ("float",       (0.0,   360.0)),
    "/drop_shadow/enableShadow"       : ("bool",        None),
    "/drop_shadow/dropShadowDarkness" : ("float",       (0.0,    1.0)),
    "/drop_shadow/dropShadowAmount"   : ("float",       (0.0,    1.0)),
    "/drop_shadow/shadowColor"        : ("color",       None),
    "/drop_shadow/m_altitude"         : ("float",       (0.0,   90.0)),
    "/drop_shadow/m_azimuth"          : ("float",       (0.0,  360.0)),
    "/depthShadow/altitude"           : ("float",       (0.0,   90.0)),
    "/depthShadow/azimuth"            : ("float",       (0.0,  360.0)),
    "/offscreen_scene/dirLightColor"  : ("color",       None),
    "/offscreen_scene/edgeColor"      : ("color",       None),
    "/occlusiondecal/opacity"         : ("float",       (0.0,    1.0)),
    "/layerLighting/visible"          : ("bool",        None),
    "/aurora_film/visible"            : ("bool",        None),
    "/darkness_filter/visible"        : ("bool",        None),
    "/caustics/applyCaustics"         : ("bool",        None),
}


def rand_float(lo, hi):
    return round(random.uniform(lo, hi), 4)

def rand_color():
    return [round(random.uniform(0.0, 1.0), 4) for _ in range(3)]

def rand_hdr_color():
    return [round(random.uniform(0.0, 2.0), 4) for _ in range(3)]

def rand_value(ftype, frange):
    if ftype == "bool":
        return random.choice([0, 1])
    if ftype == "float":
        return rand_float(*frange)
    if ftype == "int":
        return random.randint(*frange)
    if ftype == "color":
        return rand_color()
    if ftype == "hdr_color":
        return rand_hdr_color()
    return None


def randomize(json_path, out_path=None, seed=None):
    if seed is not None:
        random.seed(seed)

    p = Path(json_path)
    if out_path is None:
        out_path = str(p.parent / (p.stem + "_randomized.json"))

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if seed is not None:
        print(f"Seed: {seed}")
    print(f"Randomizing {len(data['sections'])} sections...")

    for sec in data["sections"]:
        count = 0
        for field, (ftype, frange) in FIELDS.items():
            if field not in sec["fields"]:
                continue
            sec["fields"][field] = rand_value(ftype, frange)
            count += 1
        print(f"  {sec['name']}: {count} fields randomized")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"-> {out_path}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage:")
        print("  randomizer.py <file.json> [-o out.json] [-seed 42]")
        print()
        print("  Randomizes all visual light/color/effect fields in ALL sections.")
        print("  Bools stay bools, floats stay in valid ranges, colors stay colors.")
        print()
        print("Example:")
        print("  randomizer.py render_params.data.json")
        print("  randomizer.py render_params.data.json -seed 1234")
        sys.exit(0)

    json_path = args[0]
    out_path = None
    seed = None

    if "-o" in args:
        idx = args.index("-o")
        out_path = args[idx + 1]

    if "-seed" in args:
        idx = args.index("-seed")
        seed = int(args[idx + 1])

    randomize(json_path, out_path, seed)


if __name__ == "__main__":
    main()