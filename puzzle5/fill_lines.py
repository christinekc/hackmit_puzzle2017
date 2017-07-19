# Check if the positions of the pixels from the csv file are correct.

import csv
import PIL.Image

image = PIL.Image.open('temp.png')
width, height = image.size
data = image.load()

with open('clines.csv', 'r') as csvfile:
	spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
	for row in spamreader:
		x, y = row[0].split(',')
		data[int(x), int(y)] = 0

image.save('filled.png')
	  