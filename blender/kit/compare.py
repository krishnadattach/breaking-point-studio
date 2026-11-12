# Compares a render with a reference image, pixel by pixel.
#   blender.exe -b -P blender/kit/compare.py -- <render.png> [reference.png] [diff.png]
# Reference defaults to blender/kit/reference.png. Writes a diff image where
# differences are boosted 10x (black = identical). Prints a PASS/FAIL verdict.
import os
import sys
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("-P") + 1]))
args = sys.argv[sys.argv.index("--") + 1:]
render_path = args[0]
ref_path = args[1] if len(args) > 1 else os.path.join(HERE, "reference.png")
diff_path = args[2] if len(args) > 2 else os.path.splitext(render_path)[0] + "_diff.png"

# Tolerances: tiny render noise is fine, a visible change is not
MEAN_LIMIT = 0.005   # average difference per channel (0..1)
PIXEL_STEP = 0.05    # a pixel "differs" if any channel moves more than this (~13/255)
SHARE_LIMIT = 0.002  # ...and at most 0.2 % of pixels may differ


def load(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    return np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3], (w, h)


a, size_a = load(render_path)
b, size_b = load(ref_path)
print(f"COMPARE render    {render_path}  {size_a}")
print(f"COMPARE reference {ref_path}  {size_b}")
if size_a != size_b:
    print("COMPARE FAIL: sizes differ")
    sys.exit(0)
d = np.abs(a - b)
mean = float(d.mean())
worst = float(d.max())
share = float((d.max(axis=2) > PIXEL_STEP).mean())
print(f"COMPARE mean difference {mean:.5f} (limit {MEAN_LIMIT})")
print(f"COMPARE largest single difference {worst:.3f}")
print(f"COMPARE pixels that visibly differ {share * 100:.3f} % (limit {SHARE_LIMIT * 100:.1f} %)")
print("COMPARE identical:", bool(worst == 0.0))
ok = mean <= MEAN_LIMIT and share <= SHARE_LIMIT
print("COMPARE", "PASS" if ok else "FAIL")

boost = np.clip(d * 10, 0, 1)
out = bpy.data.images.new("diff", size_a[0], size_a[1])
out.pixels = np.dstack([boost, np.ones(boost.shape[:2])]).ravel().tolist()
out.filepath_raw = diff_path
out.file_format = "PNG"
out.save()
print("COMPARE diff image:", diff_path)
