# hackmit_puzzle2017

## Puzzle 4

##### Problem
URL: https://hotsinglebots.delorean.codes/u/[USERNAME]
Need to get the puzzler bot to like you. From the console, we know that puzzler
bots only like automobiles. Our goal is to upload a profile pic that the 
neural network thinks is an automobile. In [username] file, it says, 
"Make /api/[USERNAME]/model/model.json, and model.hdf5 files private." When
we add these to the base url, a model.json file and a model.hdf5 file are
downloaded. The former contains a model of the neural network, 
whereas the latter contains the weights of the neural network. We will use 
this model to generate an image that the neural network thinks it is a car.

##### To-do
Install keras and tensorflow
Files are in allofkeras > keras > datasets
```python3 big_genetic.py
python3 image_converter.py
```
Upload output.png as profile pic
Like a puzzler bot and the date for the time machine will appear!