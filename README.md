# Solving the admission puzzles for Hack MIT 2017

Below is a rough write-up of our attempt at the admission puzzles for Hack MIT
2017. 

## Puzzle 4

### Problem
URL: https://hotsinglebots.delorean.codes/u/USERNAME <br />
Need to get the puzzler bot to like you. From the console, we know that puzzler
bots only like automobiles. Our goal is to upload a profile pic that the 
neural network thinks is an automobile. In [username] file, it says, 
"Make /api/USERNAME/model/model.json, and model.hdf5 files private." When
we add these to the base url, a model.json file and a model.hdf5 file are
downloaded. The former contains a model of the neural network, 
whereas the latter contains the weights of the neural network. We will generate 
an image sych that the neural network thinks it is a car.

### To-do
Install keras and tensorflow <br />
Files are in allofkeras > keras > datasets <br />
Start with a mutation rate of 0.1 and then slow decreases the number <br />
```
python3 big_genetic.py
python3 image_converter.py
```
Upload output.png as profile pic <br />
Like a puzzler bot and the date for the time machine will appear!

## Puzzle 5
### Problem
URL: https://captcha.delorean.codes/u/USERNAME/ <br />
The goal for the puzzle is to solve 10,000 out of 15,000 CAPTCHAs successfully.
I solved 1000 captchas manually to be used as training and test data 
(manual_solver.py).

### To-do
The lines are at the exact same position and angle for all the captchas for 
the same user. We can easily clean the captchas if we find the positions of 
the pixels of the lines (overlap of images). <br />
Install opencv <br />
```
python3 cleaner.py
```