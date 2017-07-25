from __future__ import print_function
import csv
import PIL.Image
import base64
import cv2
from scipy.misc import imsave
from numpy import *
from itertools import groupby

import keras
from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D
from keras import backend as K
import numpy as np
import csv
from keras.models import load_model
import json


def mysplit(array):
	return [list(j) for i, j in groupby(array)]

def myround(array):
	return array.astype('int').tolist()

letter_saves = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]

# load json and create model
model = load_model("trained_model.hdf5")
# load weights into new model
model.load_weights("trained_weights.hdf5")
print("Loaded model from disk")

# initiate RMSprop optimizer
opt = keras.optimizers.rmsprop(lr=0.0001, decay=1e-6)

# Let's train the model using RMSprop
model.compile(loss='categorical_crossentropy',
              optimizer=opt,
              metrics=['accuracy'])

f = open('solved_0.7.json', 'w')
beginning = '{"solutions": [\n'
f.write(beginning)

with open('cdata.csv', 'r') as csvfile:
	spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
	count_15000 = 0
	for row in spamreader:
		if count_15000 == 15000:
			break
		if count_15000 % 100 == 0:
			print(count_15000)
		captcha_name = row[0]
		img_data = bytes(row[1], 'utf-8')

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

		# Read in the position of the line pixels
		lines = []
		with open('clines.csv', 'r') as csvfile:
			spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
			for row in spamreader:
				x, y = row[0].split(',')
				x = int(x)
				y = int(y)
				lines.append((x, y))

		for (x, y) in lines:
			if (x < width - 1) and (data[x+1, y] != 0) and ((x+1, y) not in lines):
				continue
			if (x > 0) and (data[x-1, y] != 0) and ((x-1, y) not in lines):
				continue
			if (y < height - 1) and (data[x, y+1] != 0) and ((x, y+1) not in lines): 
				continue
			if (y > 0) and (data[x, y-1] != 0) and ((x, y-1) not in lines):
				continue
			#version 2 includes below 4 if statements
			if (x < width - 1) and (y < height - 1) and (data[x+1, y+1] != 0) and ((x+1, y+1) not in lines):
				continue
			if (x > 0) and (y > 0) and (data[x-1, y-1] != 0) and ((x-1, y-1) not in lines):
				continue
			if (x > 0) and (y < height - 1) and (data[x-1, y+1] != 0) and ((x-1, y+1) not in lines):
				continue
			if (x < width - 1) and (y > 0) and (data[x+1, y-1] != 0) and ((x+1, y-1) not in lines):
				continue
			# Set pixel to black
			data[x, y] = 0

		image.save('cleaned.png')

		cols, rows = image.size
		#data = image.load()
		letters = [[[0] * 32] * 32] * 4

		a1 = [0] * cols
		for x in range(rows):
			for y in range(cols):
				if data[y, x] != 0:
					a1[y] = 1
		a1 = [0] + a1 + [0]
		a1 = mysplit(concatenate([[0] if i == [1] else ([0, 0] if i == [1, 1] else (
			[0, 0, 0] if i == [1, 1, 1] else i)) for i in mysplit(a1)]).tolist())

		while len(a1) > 9:
			k = a1
			a2 = []
			for i in range(len(k)):
				if k[i][0] == 0:
					a2 += [i]
			a2 = a2[1 : -1]
			mini = -1
			val = 1734516885
			for i in a2:
				if len(k[i - 1]) + len(k[i + 1]) < val:
					mini = i
					val = len(k[i - 1]) + len(k[i + 1])
			for i in range(len(k[mini])):
				k[mini][i] = 1
			a1 = mysplit(concatenate(k))

		while len(a1) < 9:
			k = a1
			a2 = []
			for i in range(len(k)):
				if k[i][0] == 1:
					a2 += [i]
			maxi = -1
			val = -1
			for i in a2:
				if k[i][0] == 1 and len(k[i]) > val:
					val = len(k[i])
					maxi = i
			a1 = (k[: maxi]
				+ [myround(ones(int(floor((len(k[maxi]) - 1) / 2))))] + [[0]]
				+ [myround(ones(int(ceil((len(k[maxi]) - 1) / 2))))]
				+ k[maxi + 1 :])

		a1 = add.accumulate([len(a1[i]) for i in range(len(a1))]).tolist()
		a1 = [i.tolist() for i in split(
			array(a1[: 2 * (len(a1) // 2)]), len(a1) // 2)]

		captcha_result = ""
		found_result = True

		for letter, j in enumerate(a1):
			a2 = [[0 if data[i, j] == 0 else 1 for j in range(
				rows)] for i in range(j[0] - 1, j[1] - 1)]
			a3 = [0] * len(a2[0])
			for i in range(len(a2)):
				for k in range(len(a2[0])):
					if a2[i][k] == 1:
						a3[k] = 1
			b = add.accumulate(
				[len(j) for j in mysplit([0] + a3 + [0])]).tolist()
			a4 = [[0] * (b[-2] - b[0])] * (j[1] - j[0] + 60)
			rowindex = 0
			for tojoin in [myround(zeros((30, b[-2] - b[0]))),
				transpose(transpose(a2)[b[0] - 1 : b[-2] - 1]).tolist(),
				myround(zeros((30, b[-2] - b[0])))]:
				for row in tojoin:
					a4[rowindex] = row
					rowindex += 1
			k = [[0] * (j[1] - j[0] + 60)] * (b[-2] - b[0] + 60)
			rowindex = 0
			for tojoin in [myround(zeros((30, j[1] - j[0] + 60))),
				transpose(a4).tolist(),
				myround(zeros((30, j[1] - j[0] + 60)))]:
				for row in tojoin:
					k[rowindex] = row
					rowindex += 1
			l = [0, 0, 0]
			for i in range(len(k)):
				for m in range(len(k[0])):
					if k[i][m] != 0:
						l[0] += i
						l[1] += m
						l[2] += 1
			l = [round(l[i] / l[2] - 15.5) for i in range(2)]
			#imsave('letter' + str(letter) + '.png', 
			output = reshape([[k[i][w] for w in range(
				l[1], l[1] + 32)] for i in range(
				l[0], l[0] + 32)], (1, 32, 32, 1))

			classes = model.predict(output)[0]
			val = -1
			index = -1
			for enum, element in enumerate(classes):
				if val < element:
					val = element
					index = enum
			if val < 0.70:
				found_result = False
				break
			captcha_result += letter_saves[index]
		
		if found_result:
			count_15000 += 1
			result = {'name': captcha_name, 'solution': captcha_result}
			f.write(str(result).replace("'", '"') + (", \n" if count_15000 < 15000 else ""))

f.write(']}')
f.close()
