# MLP for Pima Indians Dataset Serialize to JSON and HDF5
from keras.models import Sequential
from keras.layers import Dense
from keras.models import model_from_json

from keras.callbacks import LearningRateScheduler, ModelCheckpoint

#import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
from sklearn.metrics import confusion_matrix
import time
from datetime import timedelta
import math
import os

import cifar10

def lr_schedule(epoch):
    return lr * (0.1 ** int(epoch / 10))

cifar10.maybe_download_and_extract()
class_names = cifar10.load_class_names()
# Load training data
images_train, cls_train, labels_train = cifar10.load_training_data()
# Load test data 
images_test, cls_test, labels_test = cifar10.load_test_data()

print("Size of:")
print("- Training-set:\t\t{}".format(len(images_train)))
print("- Test-set:\t\t{}".format(len(images_test)))

# Load json and create model
json_file = open("model.json", "r")
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
# Load weights into new model
loaded_model.load_weights("model.hdf5")
print("Loaded model from disk")

# batch_size = 32
# epochs = 30

# model.fit(X, Y,
#           batch_size=batch_size,
#           epochs=epochs,
#           validation_split=0.2,
#           callbacks=[LearningRateScheduler(lr_schedule),
#                      ModelCheckpoint('model.h5', save_best_only=True)]
#           )