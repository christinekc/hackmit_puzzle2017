import base64
import cv2
import numpy as np

import json
from pprint import pprint

import PIL.Image
import csv

# Read from json file
with open('5000images1.json') as data_file:    
    data = json.load(data_file)

# name = data["images"][0]["name"]
# img_data = data["images"][0]["jpg_base64"]
# img_data = bytes(img_data, 'utf-8')

#img_data = b'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'
#img_data = b'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'
#img_data = b'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'

counter = 0
for input_dict in data["images"]:

	#img_data = data["images"][i]["jpg_base64"]
	img_data = bytes(input_dict["jpg_base64"], 'utf-8')

	# Convert base 64 to png image
	with open("temp.png", "wb") as fp:
	    fp.write(base64.decodebytes(img_data))

	# Convert to gray scale
	img = cv2.imread('temp.png')
	img_g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	cv2.imwrite('temp_g.png', img_g)
	# Convert image to Binary
	thresh = 200
	img_bw = cv2.threshold(img_g, thresh, 255, cv2.THRESH_BINARY)[1]
	# Save
	cv2.imwrite('temp_bw.png', img_bw)


	image = PIL.Image.open('temp_bw.png')
	width, height = image.size
	data = image.load()

	# for x in range(width):
	# 	for y in range(height):

	# 		# Only look at white pixels
	# 		if data[x, y] != 0:

	# 			count = 0

	# 			# box of size 2
	# 			if (x < width - 2) and (data[x+1, y] != 0) and (data[x+2, y] != 0):
	# 				count += 1
	# 			if (x > 1) and (data[x-1, y] != 0) and (data[x-2, y] != 0):
	# 				count += 1
	# 			if (y < height - 2) and (data[x, y+1] != 0) and (data[x, y+2] != 0): 
	# 				count += 1
	# 			if (y > 1) and (data[x, y-1] != 0) and (data[x, y-2] != 0):
	# 				count += 1
	# 			if (x < width - 1) and (y < height - 1) and (data[x+1, y+1] != 0):
	# 				count += 1
	# 			if (x > 0) and (y > 0) and (data[x-1, y-1] != 0):
	# 				count += 1
	# 			if (x > 0) and (y < height - 1) and (data[x-1, y+1] != 0):
	# 				count += 1
	# 			if (x < width - 1) and (y > 0) and (data[x+1, y-1] != 0):
	# 				count += 1
	# 			# set (x, y) as black
	# 			if count < 4:
	# 				data[x, y] = 0

	for i in range(35):
		for x in range(width):
			for y in range(height):

				# Only look at white pixels
				if data[x, y] != 0:
					count = 0
					# box of size 1
					if (x < width - 1) and (data[x+1, y] != 0):
						count += 1
					if (x > 0) and (data[x-1, y] != 0):
						count += 1
					if (y < height - 1) and (data[x, y+1] != 0): 
						count += 1
					if (y > 0) and (data[x, y-1] != 0):
						count += 1
					if (x < width - 1) and (y < height - 1) and (data[x+1, y+1] != 0):
						count += 1
					if (x > 0) and (y > 0) and (data[x-1, y-1] != 0):
						count += 1
					if (x > 0) and (y < height - 1) and (data[x-1, y+1] != 0):
						count += 1
					if (x < width - 1) and (y > 0) and (data[x+1, y-1] != 0):
						count += 1
					# set (x, y) as black
					if count < 4:
						data[x, y] = 0

	image.save('tmp_cleaned.png')

	solution = input('Solve captcha #' + str(counter) + ': ')
	# skip if input is s
	if solution != "s":
		new = {"name": input_dict["name"], \
			   "solution": solution, \
			   "jpg_base64": input_dict["jpg_base64"]}

		# Write to csv file
		with open('solved.csv', 'a') as output_file:
		    writer = csv.writer(output_file)
		    for key, value in new.items():
    			writer.writerow([value])

	counter += 1
