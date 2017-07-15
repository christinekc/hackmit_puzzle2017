from __future__ import print_function

from keras.models import Sequential
from keras.layers import Dense
from keras.models import model_from_json
from keras.utils import np_utils, generic_utils
import numpy
import os
import pickle
import random

import keras
from keras.preprocessing.image import ImageDataGenerator
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers import Conv2D, MaxPooling2D

import cifar10

def go(array):
    arg = array[:]
    #for i in range(len(arg)):
    #    arg[i] = 1.0 * array[i] / 255
    return loaded_model.predict(
        numpy.array(arg).reshape((1, 32, 32, 3)))[0]

# load json and create model
json_file = open("model.json", "r")
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
# load weights into new model
loaded_model.load_weights("model.hdf5")
print("Loaded model from disk")

# initiate RMSprop optimizer
opt = keras.optimizers.rmsprop(lr=0.0001, decay=1e-6)

# Let's train the model using RMSprop
loaded_model.compile(loss='categorical_crossentropy',
              optimizer=opt,
              metrics=['accuracy'])

tolerance = 0.999999
mutation_rate = 0.0003
generation = 0
with open('rng', 'rb') as fp:
    parent = pickle.load(fp)
best_child = parent[:]
current_best = go(parent)

print("The current best is " + str(current_best) + ".")