import numpy as np
from PIL import Image

img = np.array(Image.open(r'20260917_175649.png').convert('RGB'))
R,G,B = img[:,:,0], img[:,:,1], img[:,:,2]
# strong blue dominance signal
sig = (B.astype(np.int32) - np.maximum(R.astype(np.int32), G.astype(np.int32)))
# keep positive blue-leaning pixels, else 0
sig2 = np.clip(sig, 0, None)

col = sig2.sum(axis=0)
row = sig2.sum(axis=1)

# print top 50 local maxima positions and their values in selected bands only
for name, arr in [('col', col), ('row', row)]:
    print('---', name)
    # rough local maxima by comparing neighbors
    maxima = []
    for i in range(1, len(arr)-1):
        if arr[i] >= arr[i-1] and arr[i] >= arr[i+1] and arr[i] > 200:
            maxima.append((i, int(arr[i])))
    print('num maxima >200', len(maxima))
    # show first 50 maxima sorted by position
    for m in maxima[:50]:
        print(m)
    # print average spacing among signals > threshold over top maxima
    if maxima:
        pos = np.array([m[0] for m in maxima])
        diffs = np.diff(pos)
        print('avg spacing among maxima', float(np.median(diffs)), 'min', float(diffs.min()), 'max', float(diffs.max()))

print('image size', img.shape)
