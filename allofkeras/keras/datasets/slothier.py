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
    return loaded_model.predict(
        numpy.array(array).reshape((1, 32, 32, 3)))[0][1]

# load json and create model
json_file = open("model.json", "r")
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
# load weights into new model
loaded_model.load_weights("model.hdf5")
print("Loaded model from disk")

# initiate RMSprop optimizer
#opt = keras.optimizers.rmsprop(lr=0.0001, decay=1e-6)

# Let's train the model using RMSprop
#loaded_model.compile(loss='categorical_crossentropy',
#              optimizer=opt,
#              metrics=['accuracy'])

tolerance = 0.999999
mutation_rate = 0.001
num_children = 50
generation = 0
with open('outfile', 'rb') as fp:
    best = pickle.load(fp)
current_best = go(best)

print("The current best is " + str(100 * current_best) + "%.")

while current_best < tolerance:
    for i in range(3072):
        if i % 64 == 0:
            print("Done " + str(i // 64) + " out of 48 in generation "
                + str(generation) + ".\nCurrent best is "
                + str(100 * current_best) + "%.")
            with open('outfile', 'wb') as fp:
                pickle.dump(best, fp)
        val = best[i]
        child = best[:]
        child[i] = max(val - 1, 0)
        result = go(child)
        if result > current_best:
            current_best = result
            best = child[:]
        child[i] = min(val + 1, 255)
        result = go(child)
        if result > current_best:
            current_best = result
            best = child[:]

    generation += 1
    if generation == 1:
        print("After " + str(generation) + " generation, best is "
            + str(100 * current_best) + "%.")
    else:
        print("After " + str(generation) + " generations, best is "
            + str(100 * current_best) + "%.")
    with open('outfile', 'wb') as fp:
        pickle.dump(best, fp)