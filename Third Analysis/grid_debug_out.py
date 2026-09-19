import numpy as np
from PIL import Image
import cv2

img = np.array(Image.open(r'20260917_175649_masked.png').convert('RGB'))
R,G,B = img[:,:,0], img[:,:,1], img[:,:,2]
# Candidate grid mask: slightly blue/gray lines on near-white background.
grid = ((B > G+2) & (B > R+2) & (B < 240) & (G > 120) & (R < 220))
# Remove very short noise
kernel = np.ones((3,3), np.uint8)
grid = cv2.morphologyEx(grid.astype(np.uint8), cv2.MORPH_OPEN, kernel)
# path is darker gray
path = ((R < 200) & (G < 200) & (B < 200)) & (~grid)
path = cv2.morphologyEx(path.astype(np.uint8), cv2.MORPH_OPEN, kernel)

# save masks as images
out1 = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
out1[:,:,0] = grid.astype(np.uint8) * 255
out1[:,:,1] = grid.astype(np.uint8) * 255
out1[:,:,2] = grid.astype(np.uint8) * 255
Image.fromarray(out1).save('grid_mask_debug.png')

out2 = np.zeros((img.shape[0], img.shape[1], 3), dtype=np.uint8)
out2[:,:,0] = path.astype(np.uint8) * 255
out2[:,:,1] = path.astype(np.uint8) * 255
out2[:,:,2] = path.astype(np.uint8) * 255
Image.fromarray(out2).save('path_mask_debug.png')

print('grid pixels', grid.sum(), 'path pixels', path.sum())
