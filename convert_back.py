# converts LUV image into RGB
import numpy as np
import cv2
import os
path = 'Opencountry_outputs'
path1, path2, path3 = 'opencountry_L', 'opencountry_U', 'opencountry_V'
for file in os.listdir(path1):
	x = cv2.imread(os.path.join(path1, file), 0)
	y = cv2.imread(os.path.join(path2, file), 0)
	z = cv2.imread(os.path.join(path3, file), 0)
	out = np.zeros((x.shape[0], x.shape[1], 3))
	out[:, :, 0] = x
	out[:, :, 1] = y
	out[:, :, 2] = z
	out = out.astype('uint8')
	out = cv2.cvtColor(out, cv2.COLOR_Luv2BGR)
	cv2.imwrite(os.path.join(path, file), out)