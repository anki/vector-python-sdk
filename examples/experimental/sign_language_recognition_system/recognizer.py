# Copyright (c) 2019 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sign language recognition system using the camera feed from Vector."""

import asyncio
from concurrent.futures import CancelledError
import os
import sys

try:
    import keras
    from keras.layers import Conv2D, Dense, Dropout, Flatten, MaxPooling2D
    from keras.models import Sequential, model_from_json
    from keras.preprocessing.image import img_to_array
except ImportError as exc:
    sys.exit("Cannot import keras: Do `pip3 install --user keras` to install")

try:
    import numpy as np
except ImportError as exc:
    sys.exit("Cannot import numpy: Do `pip3 install --user numpy` to install")

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

try:
    from sklearn.model_selection import train_test_split
except ImportError as exc:
    sys.exit("Cannot import scikit: Do `pip3 install --user scikit-learn` to install")

try:
    import tensorflow as tf
except ImportError:
    sys.exit("Cannot import from tensorflow: Do `pip3 install --user tensorflow` to install")

import anki_vector
import util


class SignLanguageRecognizer():
    """Recognize sign language hand signals using Vector's camera feed.

    A convolutional neural network is used to predict the hand signs.
    The network is built with a Keras Sequential model with a TensorFlow backend.
    """

    def __init__(self):
        self.training_images: np.ndarray = None
        self.training_labels: np.ndarray = None
        self.test_images: np.ndarray = None
        self.test_labels: np.ndarray = None
        self.model: keras.engine.sequential.Sequential = None
        self.graph: tf.python.framework.ops.Graph = tf.get_default_graph()

    def load_datasets(self, dataset_root_folder: str) -> None:
        """Load the training and test datasets required to train the model.
        A sample dataset is included in the project ("dataset.zip"). Unzip the
        folder to use it to train the model.

        .. code-block:: python

            recognizer = SignLanguageRecognizer()
            recognizer.load_datasets("/path/to/dataset_root_folder")
        """

        if not dataset_root_folder:
            sys.exit("Cannot load dataset. Provide valid path with `--dataset_root_folder`")

        images = []
        labels = []

        for filename in os.listdir(dataset_root_folder):
            if filename.endswith(".png"):
                # Read black and white image
                image = Image.open(os.path.join(dataset_root_folder, filename))
                # Convert image to an array with shape (image_width, image_height, 1)
                image_data = img_to_array(image)
                images.append(image_data)

                label = filename[0]
                if filename.startswith("background"):
                    # Use the last class to denote an unknown/background image
                    label = util.NetworkConstants.NUM_CLASSES - 1
                else:
                    # Use ordinal value offsets to denote labels for all alphabets
                    label = ord(label) - 97
                labels.append(label)

        # Normalize the image data
        images = np.array(images, dtype="float") / 255.0
        # Convert labels to a numpy array
        labels = np.array(labels)

        # Split data read in to training and test segments
        self.training_images, self.test_images, self.training_labels, self.test_labels = train_test_split(images, labels, test_size=util.NetworkConstants.TEST_SPLIT)

        # Convert array of labels in to binary classs matrix
        self.training_labels = keras.utils.to_categorical(self.training_labels, num_classes=util.NetworkConstants.NUM_CLASSES)
        self.test_labels = keras.utils.to_categorical(self.test_labels, num_classes=util.NetworkConstants.NUM_CLASSES)

    def create_model(self) -> None:
        """Creates a convolutional neural network model with the following architecture:

        ConvLayer -> MaxPoolLayer -> ConvLayer -> MaxPoolLayer -> ConvLayer ->
        Dropout -> Flatten -> Dense -> Dropout -> Dense

        .. code-block:: python

            recognizer = SignLanguageRecognizer()
            recognizer.load_datasets("/path/to/dataset_root_folder")
            recognizer.create_model()
        """
        self.model = Sequential()
        self.model.add(Conv2D(32, kernel_size=(3, 3), activation="relu", input_shape=(util.NetworkConstants.IMAGE_WIDTH, util.NetworkConstants.IMAGE_HEIGHT, 1)))
        self.model.add(MaxPooling2D(pool_size=(2, 2)))
        self.model.add(Conv2D(64, kernel_size=(3, 3), activation="relu"))
        self.model.add(MaxPooling2D(pool_size=(2, 2)))
        self.model.add(Conv2D(64, kernel_size=(3, 3), activation="relu"))

        self.model.add(Dropout(0.25))
        self.model.add(Flatten())

        self.model.add(Dense(128, activation="relu"))
        self.model.add(Dropout(0.5))
        self.model.add(Dense(util.NetworkConstants.NUM_CLASSES, activation="softmax"))

        self.model.compile(loss=keras.losses.categorical_crossentropy,
                           optimizer=keras.optimizers.Adadelta(),
                           metrics=['accuracy'])

    def train_model(self, epochs: int = util.NetworkConstants.EPOCHS, verbosity: int = 1) -> None:
        """Trains the model off of the training and test data provided

        .. code-block:: python

            recognizer = SignLanguageRecognizer()
            recognizer.load_datasets("/path/to/dataset_root_folder")
            recognizer.create_model()
            recognizer.train_model()
        """
        if self.training_images.size == 0 or self.training_labels.size == 0:
            sys.exit("Training dataset is empty. Build a dataset with `data_gen.py` before training the model.")
        self.model.fit(self.training_images,
                       self.training_labels,
                       epochs=epochs,
                       verbose=verbosity,
                       validation_split=util.NetworkConstants.VALIDATION_SPLIT)

    def load_model(self, model_config_filename: str, model_weights_filename: str) -> None:
        """Loads a saved model's config and weights to rebuild the model rather than create
        a new model and re-train.

        .. code-block:: python

            recognizer = SignLanguageRecognizer()
            recognizer.load_model("/path/to/model_config_filename", "/path/to/model_weights_filename")
        """
        if not model_config_filename or not model_weights_filename:
            sys.exit("Cannot load model. Provide valid paths with --model_config and --model_weights.")
        json_model = None
        with open(model_config_filename, "r") as file:
            json_model = file.read()
        # Load the network architecture
        self.model = model_from_json(json_model)
        # Load the weight information and apply it to the model
        self.model.load_weights(model_weights_filename)

        self.model.compile(loss=keras.losses.categorical_crossentropy,
                           optimizer=keras.optimizers.Adadelta(),
                           metrics=['accuracy'])

    def save_model(self, model_config_filename: str, model_weights_filename: str) -> None:
        """Saves a model's config and weights for latter use.

        .. code-block:: python

            recognizer = SignLanguageRecognizer()
            recognizer.load_datasets(args.dataset_root_folder)
            recognizer.create_model()
            recognizer.train_model()
            recognizer.save_model("/path/to/model_config_filename", "/path/to/model_weights_filename")
        """
        json_model = self.model.to_json()
        # Save the network architecture
        with open(model_config_filename, "w") as file:
            file.write(json_model)
        # Save the model's assigned weights
        self.model.save_weights(model_weights_filename)

    async def predict_with_camera_feed(self, robot: anki_vector.Robot) -> None:
        """Use the camera feed from Vector to detect sign language hand signs by applying a trained
        convolutional neural network on to images received from the camera feed.

        .. code-block:: python

            recognizer = SignLanguageRecognizer()
            recognizer.load_model("/path/to/model_config_filename",
                                "/path/to/model_weights_filename")
            with anki_vector.Robot(show_viewer=True) as robot:
                print("------ predicting hand signs, press ctrl+c to exit early ------")
                try:
                    robot.conn.run_coroutine(recognizer.predict_with_camera_feed(robot))
                except KeyboardInterrupt:
                    print("------ predicting done ------")
        """
        with self.graph.as_default():
            while True:
                await asyncio.sleep(2)

                # Get the latest image from the robot's camera feed
                camera_image = robot.camera.latest_image.raw_image
                
                # - Image pre-processing -
                # Convert the image into black and white using Pillow
                black_white_image = camera_image.convert("L")
                # Crop the image to reduce the complexity of the network
                cropped_image = util.crop_image(black_white_image, util.NetworkConstants.IMAGE_WIDTH, util.NetworkConstants.IMAGE_HEIGHT)
                # Convert image to an array with shape (image_width, image_height, 1)
                image = img_to_array(cropped_image)
                # Normalize the image data
                image = image.astype("float") / 255.0
                # Expand array shape to add an axis to denote the number of images fed as input
                image = np.expand_dims(image, axis=0)

                prediction = self.model.predict(image)[0]
                prediction = enumerate(prediction)
                prediction = sorted(prediction, key=lambda x: x[1], reverse=True)[0]
                label = prediction[0]
                if label == (util.NetworkConstants.NUM_CLASSES - 1):
                    label = "No Sign Displayed"
                else:
                    label = chr(label + 97)
                prediction = (label, prediction[1] * 100)
                print(f"Prediction: {prediction[0]} Confidence: {prediction[1]:.2f}%")
                if prediction[0] != "No Sign Displayed":
                    # If valid prediction is available, use Vector's text-to-speech system to say the
                    # recognized alphabet out loud
                    await robot.behavior.say_text(prediction[0])


def main():

    recognizer = SignLanguageRecognizer()
    args = util.parse_command_args()

    if not args.train and not args.predict:
        sys.exit("Use flags `--train` or `--predict` to enable the corresponding actions")

    if args.train:
        recognizer.load_datasets(args.dataset_root_folder)
        recognizer.create_model()
        recognizer.train_model()

        # Save the model's configs and weights if the corresponding paths are given
        if args.model_config and args.model_weights:
            recognizer.save_model(args.model_config, args.model_weights)

        test_score = recognizer.model.evaluate(recognizer.test_images, recognizer.test_labels, verbose=1)
        print(f"{recognizer.model.metrics_names[1].capitalize()}: {test_score[1] * 100}%")

    if args.predict:
        if not recognizer.model:
            # Load the model's configs and weights if the corresponding paths are given
            recognizer.load_model(args.model_config, args.model_weights)

        with anki_vector.Robot(args.serial) as robot:
            print("------ predicting hand signs, press ctrl+c to exit early ------")
            try:
                # Add a rectangular overlay describing the portion of image that is used after cropping.
                # @TODO: The rectangle overlay should feed in a full rect, not just a size
                frame_of_interest = anki_vector.util.RectangleOverlay(util.NetworkConstants.IMAGE_WIDTH, util.NetworkConstants.IMAGE_HEIGHT)
                robot.viewer.overlays.append(frame_of_interest)
                robot.camera.init_camera_feed()
                robot.viewer.show()

                future = robot.conn.run_coroutine(recognizer.predict_with_camera_feed(robot))
                future.result()
            except KeyboardInterrupt:
                future.cancel()
                print("------ predicting done ------")
            except CancelledError:
                print("------ predicting task cancelled ------")


if __name__ == '__main__':
    main()
