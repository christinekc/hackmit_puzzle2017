import pickle
import numpy
from PIL import Image

with open('outfile', 'rb') as fp:
	array = pickle.load(fp)

array = numpy.reshape(array, (32, 32, 3))
array = 1.0 * array
array /= 256
r = array[:, :, 0]
g = array[:, :, 1]
b = array[:, :, 2]
rgb = numpy.zeros((32, 32, 3), 'uint8')
rgb[..., 0] = r * 256
rgb[..., 1] = g * 256
rgb[..., 2] = b * 256
img = Image.fromarray(rgb)
img.save('output.png')