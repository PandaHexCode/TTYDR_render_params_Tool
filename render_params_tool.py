import json, sys, struct
from pathlib import Path

try:
    import zstandard as zstd
except ImportError:
    print("Error: zstandard is not installed.")
    print("Install it with:  pip install zstandard")
    print("Or in a venv:     python -m venv venv && venv/bin/pip install zstandard")
    sys.exit(1)


def crc32(text):
    poly = 0xedb88320
    table = []
    for i in range(256):
        temp = i
        for _ in range(8):
            temp = (temp >> 1) ^ poly if temp & 1 else temp >> 1
        table.append(temp)
    crc = 0xffffffff
    for b in text.encode('utf-8'):
        crc = (crc >> 8) ^ table[(crc ^ b) & 0xff]
    return (~crc) & 0xffffffff


def build_hash_table(hash_strings_path=None):
    names = []
    if hash_strings_path and Path(hash_strings_path).exists():
        names = Path(hash_strings_path).read_text(encoding='utf-8').splitlines()
    return {crc32(n): n for n in names if n.strip()}


HASH_TABLE = {}

def resolve(hash_int):
    return HASH_TABLE.get(hash_int, f'{hash_int:08x}')

def to_hash_str(key):
    try:
        return f'{int(key, 16):08x}'
    except ValueError:
        return f'{crc32(key):08x}'


def read_single(hex_str):
    return struct.unpack('<f', struct.pack('<I', int(hex_str, 16)))[0]

def write_single(f):
    if f == 0.0:
        return '0x0'
    b = struct.pack('<f', f)
    return '0x' + b[::-1].hex().lstrip('0').rjust(1, '0')


def read_value(value):
    v = value.strip()
    if v.startswith('0x'):
        return read_single(v)
    if ',' in v:
        parts = [float(x) for x in v.split(',')]
        return parts
    try:
        return int(v)
    except ValueError:
        return v

def write_value(value):
    if isinstance(value, list):
        return ','.join(f'{x:.6f}' for x in value)
    if isinstance(value, float):
        return write_single(value)
    if isinstance(value, int):
        return str(value)
    return str(value)


def parse_data(raw_bytes):
    if raw_bytes[:3] == b'\xef\xbb\xbf':
        raw_bytes = raw_bytes[3:]
    text = raw_bytes.decode('utf-8')
    lines = text.split('\n')

    count = int(lines[0], 16)

    index = []
    for i in range(1, count + 1):
        line = lines[i].strip()
        if ':' in line:
            h, size = line.split(':', 1)
            index.append((int(h, 16), int(size, 16)))

    sections = []
    pos = 0
    raw_no_bom = raw_bytes
    # find start of data section by byte offset
    # count+1 lines consumed = header + index
    header_text = '\n'.join(lines[:count + 1]) + '\n'
    byte_pos = len(header_text.encode('utf-8'))

    for entry_hash, size in index:
        chunk = raw_no_bom[byte_pos: byte_pos + size]
        chunk_text = chunk.decode('utf-8')
        chunk_lines = chunk_text.split('\n')

        section_name_hash = int(chunk_lines[0].strip(), 16)
        fields = {}
        for line in chunk_lines[1:]:
            line = line.strip()
            if not line or ':' not in line:
                continue
            fh, fv = line.split(':', 1)
            fields[int(fh.strip(), 16)] = read_value(fv.strip())

        sections.append({
            'entry_hash': entry_hash,
            'name_hash': section_name_hash,
            'size': size,
            'fields': fields,
        })
        byte_pos += size

    return sections


def serialize_data(sections):
    # Build each section's bytes first to get sizes
    section_bytes = []
    for sec in sections:
        name_h = f'{sec["name_hash"]:08x}'
        lines = [name_h]
        for fh, fv in sec['fields'].items():
            ph = f'{fh:08x}' if isinstance(fh, int) else to_hash_str(fh)
            lines.append(f'{ph}:{write_value(fv)}')
        chunk = '\n'.join(lines) + '\n'
        section_bytes.append(chunk.encode('utf-8'))

    # Build index
    index_lines = [f'{len(sections):08x}']
    for sec, chunk in zip(sections, section_bytes):
        index_lines.append(f'{sec["entry_hash"]:08x}:{len(chunk):08x}')
    index_text = '\n'.join(index_lines) + '\n'

    result = b'\xef\xbb\xbf' + index_text.encode('utf-8')
    for chunk in section_bytes:
        result += chunk
    return result


def load_file(path):
    p = Path(path)
    raw = p.read_bytes()
    if p.suffix == '.zst':
        raw = zstd.ZstdDecompressor().decompress(raw)
    return raw


def extract(path, out_path=None):
    p = Path(path)
    if out_path is None:
        name = p.name
        if name.endswith('.zst'): name = name[:-4]
        out_path = str(p.parent / (name + '.json'))

    print(f"[extract] {p.name}")
    raw = load_file(path)
    sections = parse_data(raw)
    print(f"  {len(sections)} sections")

    result = {'_meta': {'source': p.name, 'tool': 'render_params_tool.py v2.0'}, 'sections': []}
    for sec in sections:
        entry_name = resolve(sec['entry_hash'])
        fields_out = {}
        for fh, fv in sec['fields'].items():
            field_name = resolve(fh)
            fields_out[field_name] = fv
        result['sections'].append({'name': entry_name, 'fields': fields_out})

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  -> {out_path}")


def pack(json_path, out_path=None):
    p = Path(json_path)
    if out_path is None:
        stem = p.stem
        if not stem.endswith('.data'): stem += '.data'
        out_path = str(p.parent / stem)

    print(f"[pack] {p.name}")
    with open(json_path, 'r', encoding='utf-8') as f:
        d = json.load(f)

    src = d['_meta']['source']
    orig = next((c for c in [p.parent / src,
                              p.parent / (src[:-4] if src.endswith('.zst') else src)]
                 if c.exists()), None)
    if orig is None:
        found = list(p.parent.glob('*.data'))
        orig = found[0] if found else None
    if orig is None:
        print(f"ERROR: Original '{src}' not found.")
        sys.exit(1)
    print(f"  Base: {orig.name}")

    raw = load_file(str(orig))
    sections = parse_data(raw)

    json_sections = d['sections']
    if len(json_sections) != len(sections):
        print(f"  WARNING: section count mismatch ({len(json_sections)} vs {len(sections)})")

    for i, (sec, jsec) in enumerate(zip(sections, json_sections)):
        new_fields = {}
        for fname, fval in jsec['fields'].items():
            fh = crc32(fname) if not all(c in '0123456789abcdefABCDEF' for c in fname) or len(fname) != 8 else int(fname, 16)
            try:
                fh = int(fname, 16)
            except ValueError:
                fh = crc32(fname)
            new_fields[fh] = fval
        sec['fields'] = new_fields

    out_bytes = serialize_data(sections)

    if out_path.endswith('.zst'):
            out_bytes = zstd.ZstdCompressor(level=19).compress(out_bytes)

    Path(out_path).write_bytes(out_bytes)
    print(f"  {len(out_bytes):,} B")
    print(f"  -> {out_path}")


def info(path):
    p = Path(path)
    raw = load_file(path)
    sections = parse_data(raw)

    print(f"\n{'='*60}")
    print(f"  {p.name}")
    print(f"{'='*60}")
    print(f"  Sections: {len(sections)}")
    print()
    for i, sec in enumerate(sections[:30]):
        name = resolve(sec['entry_hash'])
        print(f"  [{i:3d}] {name}  ({len(sec['fields'])} fields)")
    if len(sections) > 30:
        print(f"  ... and {len(sections)-30} more")
    print()


def diff(path, key1, key2):
    raw = load_file(path)
    sections = parse_data(raw)

    name_map = {resolve(s['entry_hash']): s for s in sections}
    hash_map = {s['entry_hash']: s for s in sections}

    def find(k):
        if k in name_map: return name_map[k]
        try: return hash_map.get(int(k, 16))
        except: return None

    s1, s2 = find(key1), find(key2)
    if not s1: print(f"ERROR: '{key1}' not found"); sys.exit(1)
    if not s2: print(f"ERROR: '{key2}' not found"); sys.exit(1)

    f1 = {resolve(h): v for h, v in s1['fields'].items()}
    f2 = {resolve(h): v for h, v in s2['fields'].items()}
    all_keys = sorted(set(list(f1.keys()) + list(f2.keys())))
    diffs = [(k, f1.get(k, '<missing>'), f2.get(k, '<missing>'))
             for k in all_keys if f1.get(k) != f2.get(k)]

    n1, n2 = resolve(s1['entry_hash']), resolve(s2['entry_hash'])
    print(f"\nDiff: {n1}  vs  {n2}")
    print(f"  {len(diffs)} differences\n")
    print(f"  {'Field':<45}  {n1:<30}  {n2}")
    print(f"  {'-'*45}  {'-'*30}  {'-'*30}")
    for k, v1, v2 in diffs:
        v1s = str(v1)[:30]
        v2s = str(v2)[:30]
        print(f"  {k:<45}  {v1s:<30}  {v2s}")
    print()


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print("Usage:")
        print("  render_params_tool.py extract <file.data> [-hs hash_strings.txt]")
        print("  render_params_tool.py pack    <file.data.json> [-hs hash_strings.txt]")
        print("  render_params_tool.py info    <file.data> [-hs hash_strings.txt]")
        print("  render_params_tool.py diff    <file.data> <section1> <section2> [-hs hash_strings.txt]")
        print()
        print("  -hs  Path to hash_strings.txt (default: hash_strings.txt next to tool)")
        sys.exit(0)

    global HASH_TABLE

    hs_path = None
    if '-hs' in args:
        idx = args.index('-hs')
        hs_path = args[idx + 1]
        args = args[:idx] + args[idx+2:]
    else:
        default = Path(__file__).parent / 'hash_strings.txt'
        if default.exists():
            hs_path = str(default)

    HASH_TABLE = build_hash_table(hs_path)
    if HASH_TABLE:
        print(f"  Loaded {len(HASH_TABLE)} hash names")

    cmd = args[0]
    rest = args[1:]
    out = None
    if '-o' in rest:
        idx = rest.index('-o')
        out = rest[idx + 1]
        rest = rest[:idx] + rest[idx+2:]

    if not rest:
        print("Error: No input file specified.")
        sys.exit(1)

    if   cmd == 'extract': extract(rest[0], out)
    elif cmd == 'pack':    pack(rest[0], out)
    elif cmd == 'info':    info(rest[0])
    elif cmd == 'diff':
        if len(rest) < 3:
            print("Error: diff needs <file> <section1> <section2>")
            sys.exit(1)
        diff(rest[0], rest[1], rest[2])
    else:
        print(f"Unknown command '{cmd}'. Use: extract | pack | info | diff")
        sys.exit(1)


if __name__ == '__main__':
    main()
