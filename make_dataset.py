# splits an RGB image into L, U, V image
import cv2
import os
import random
path = 'Opencountry'
path_o = 'Opencountry_outputs'
path1, path2, path3 = 'L', 'U', 'V'
train, val = 'train', 'val'
dataset = 'dataset'
val_files = random.sample(os.listdir(path), 50)
for file in os.listdir(path):
	try:
		img = cv2.imread(os.path.join(path, file))
		luv = cv2.cvtColor(img, cv2.COLOR_BGR2Luv)
		if file in val_files:
			cv2.imwrite(os.path.join(dataset, val, path1, file), luv[:,:,0])
			cv2.imwrite(os.path.join(dataset, val, path2, file), luv[:,:,1])
			cv2.imwrite(os.path.join(dataset, val, path3, file), luv[:,:,2])
			cv2.imwrite(os.path.join(dataset, val, 'orig', file), img)
		else:
			cv2.imwrite(os.path.join(dataset, train, path1, file), luv[:,:,0])
			cv2.imwrite(os.path.join(dataset, train, path2, file), luv[:,:,1])
			cv2.imwrite(os.path.join(dataset, train, path3, file), luv[:,:,2])
			cv2.imwrite(os.path.join(dataset, train, 'orig', file), img)
	except:
		pass
# cv2.imshow('image', img)
# cv2.waitKey()