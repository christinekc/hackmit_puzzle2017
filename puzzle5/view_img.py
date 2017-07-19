import base64

img_data = b'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'

# Convert base 64 to png image
with open("temp.png", "wb") as fp:
    fp.write(base64.decodebytes(img_data))
