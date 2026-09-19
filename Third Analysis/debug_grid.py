import numpy as np
from PIL import Image

img = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
R,G,B = img[:,:,0], img[:,:,1], img[:,:,2]

# Show broad stats for candidate grid vs path masks.
for name, mask in {
    'blueish': ((B > G) & (B > R) & (B > 120)),
    'blueish_strong': ((B > G+20) & (B > R+20) & (B > 180)),
    'grayish': ((abs(B-G) < 20) & (abs(B-R) < 20) & (B < 220)),
    'dark': ((R < 120) & (G < 120) & (B < 120)),
    'light_lineish': ((B > 150) & (G > 140) & (R < 220)),
}.items():
    pix = img[mask]
    print(name, 'count', pix.shape[0])
    if pix.size:
        print(' min', pix.min(axis=0), 'max', pix.max(axis=0))
        uniq, counts = np.unique(pix.reshape(-1,3), axis=0, return_counts=True)
        idx = np.argsort(counts)[::-1][:10]
        print(' top', [(tuple(map(int,u)), int(c)) for u,c in zip(uniq[idx], counts[idx])])

# Row/column counts for candidate masks.
for name, mask in {
    'blueish': ((B > G) & (B > R) & (B > 120)),
    'light_lineish': ((B > 150) & (G > 140) & (R < 220)),
}.items():
    row = mask.sum(axis=1)
    col = mask.sum(axis=0)
    print('---', name)
    print('row max', row.max(), 'row mean', row.mean(), 'nonzero rows', np.count_nonzero(row))
    print('col max', col.max(), 'col mean', col.mean(), 'nonzero cols', np.count_nonzero(col))
    print('top rows', np.argsort(row)[-10:])
    print('top cols', np.argsort(col)[-10:])
