# Overview:

The sign language recognition system passes Vector's camera feed images through a Convolutional Neural Network built to recognize sign language hand signs. The network is built using Keras with a TensorFlow Backend.

>Network Architecture:
>ConvLayer -> MaxPoolLayer -> ConvLayer -> MaxPoolLayer -> ConvLayer -> Dropout -> Flatten -> Dense -> Dropout -> Dense

The `data_gen.py` script can be used to build a dataset to train and test the model. Each image captured is used to generate a multiplier number of other images to expand the dataset. The images are translated to 200\*200 black and white images to reduce the complexity of the network. Therefore, ensure while capturing images from the feed, that your hand is positioned within the blue rectangle which represents the cropped image dimensions.

# Generating Data:

### Generate Dataset:

```
python3 data_gen.py --serial <robot_serial> --dataset_root_folder <path_to_folder>
```

>Note: In order to capture an image, display the hand sign within the blue frame on the camera feed displayed and press the key corresponding to the label representing the hand sign. Dimensions of images in the dataset are 200\*200. Use the images captured that are displayed, to position your hand within the cropped frame.


# Run Project:

### Training:

```
python3 recognizer.py --serial <robot_serial> --train --dataset_root_folder <path_to_folder> [--model_config <path_to_config_file>] [--model_weights <path_to_weights_file>]
```

>Note: Use the `model_config` and `model_weights` flags to save the model's configurations after it has been trained.

### Prediction:

```
python3 recognizer.py --serial <robot_serial> --predict --model_config <path_to_config_file> --model_weights <path_to_weights_file>
```

>Note: Use the `model_config` and `model_weights` flags to load an existing model's configuration. If not using an existing model's configuration, train the model first.

### Train and Predict:

```
python3 recognizer.py --serial <robot_serial> --train --predict --dataset_root_folder <path_to_folder>
```