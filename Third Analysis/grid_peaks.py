import numpy as np
from PIL import Image

img = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]
blue = (B > G + 15) & (B > R + 15) & (B > 120)
col = blue.sum(axis=0)
row = blue.sum(axis=1)
kernel = np.ones(5)
smooth = {
    'col': np.convolve(col, kernel, mode='same') / 5,
    'row': np.convolve(row, kernel, mode='same') / 5,
}

for name, s in smooth.items():
    idx = []
    for i in range(2, len(s)-2):
        if s[i] >= s[i-1] and s[i] >= s[i+1] and s[i] > 30:
            idx.append(i)
    print('---', name)
    print('candidate maxima', len(idx))
    print('first 30', idx[:30])
    print('last 30', idx[-30:])
    if len(idx) > 2:
        diffs = np.diff(idx)
        print('diff median', float(np.median(diffs)))
        print('diff p10/p90', float(np.percentile(diffs,10)), float(np.percentile(diffs,90)))
        print('diff min/max', float(diffs.min()), float(diffs.max()))
