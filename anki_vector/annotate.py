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

"""Camera image annotation.

.. image:: ../images/annotate.png

This module defines an :class:`ImageAnnotator` class used by
:class:`anki_vector.camera.CameraImage` and
:class:`anki_vector.camera.CameraComponent` to add annotations
to camera images received by the robot.

This can include the location of cubes and faces that the robot currently sees,
along with user-defined custom annotations.

The ImageAnnotator instance can be accessed as
:attr:`anki_vector.camera.CameraComponent.image_annotator`.
"""

# __all__ should order by constants, event classes, other classes, functions.
__all__ = ['DEFAULT_OBJECT_COLORS',
           'RESAMPLE_MODE_NEAREST', 'RESAMPLE_MODE_BILINEAR',
           'AnnotationPosition', 'ImageText', 'Annotator',
           'ObjectAnnotator', 'FaceAnnotator', 'TextAnnotator', 'ImageAnnotator',
           'add_img_box_to_image', 'add_polygon_to_image', 'annotator']


from enum import Enum
import collections
import functools
import sys
from typing import Callable, Iterable, Tuple, Union

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")
except SyntaxError:
    sys.exit("SyntaxError: possible if accidentally importing old Python 2 version of PIL")

from . import faces
from . import objects
from . import util


DEFAULT_OBJECT_COLORS = {
    objects.LightCube: 'yellow',
    objects.CustomObject: 'purple',
    'default': 'red'
}

#: Fastest resampling mode, use nearest pixel
RESAMPLE_MODE_NEAREST = Image.NEAREST
#: Slower, but smoother, resampling mode - linear interpolation from 2x2 grid of pixels
RESAMPLE_MODE_BILINEAR = Image.BILINEAR


class AnnotationPosition(Enum):
    """Specifies where the annotation must be rendered."""
    LEFT = 1
    RIGHT = 2
    TOP = 4
    BOTTOM = 8

    #: Top left position
    TOP_LEFT = TOP | LEFT

    #: Bottom left position
    BOTTOM_LEFT = BOTTOM | LEFT

    #: Top right position
    TOP_RIGHT = TOP | RIGHT

    #: Bottom right position
    BOTTOM_RIGHT = BOTTOM | RIGHT


class ImageText:  # pylint: disable=too-few-public-methods
    """ImageText represents some text that can be applied to an image.

    The class allows the text to be placed at various positions inside a
    bounding box within the image itself.

    .. testcode::

        import time

        try:
            from PIL import ImageDraw
        except ImportError:
            sys.exit("run `pip3 install --user Pillow numpy` to run this example")

        import anki_vector
        from anki_vector import annotate


        # Define an annotator using the annotator decorator
        @annotate.annotator
        def clock(image, scale, annotator=None, world=None, **kw):
            d = ImageDraw.Draw(image)
            bounds = (0, 0, image.width, image.height)
            text = annotate.ImageText(time.strftime("%H:%m:%S"),
                                      position=annotate.AnnotationPosition.TOP_LEFT,
                                      outline_color="black")
            text.render(d, bounds)

        with anki_vector.Robot(show_viewer=True, enable_face_detection=True, enable_custom_object_detection=True) as robot:
            robot.camera.image_annotator.add_static_text("text", "Vec-Cam", position=annotate.AnnotationPosition.TOP_RIGHT)
            robot.camera.image_annotator.add_annotator("clock", clock)

            time.sleep(3)


    :param text: The text to display; may contain newlines
    :param position: Where on the screen to render the text
        - such as AnnotationPosition.TOP_LEFT or AnnotationPosition.BOTTOM_RIGHT
    :param align: Text alignment for multi-line strings
    :param color: Color to use for the text - see :mod:`PIL.ImageColor`
    :param font: ImageFont to use (None for a default font)
    :param line_spacing: The vertical spacing for multi-line strings
    :param outline_color: Color to use for the outline - see
        :mod:`PIL.ImageColor` - use None for no outline.
    :param full_outline: True if the outline should surround the text,
        otherwise a cheaper drop-shadow is displayed. Only relevant if
        outline_color is specified.
    """

    def __init__(self, text: str, position: int = AnnotationPosition.BOTTOM_RIGHT, align: str = "left", color: str = "white",
                 font = None, line_spacing: int = 3, outline_color: str = None, full_outline: bool = True):
        self.text = text
        self.position = position
        self.align = align
        self.color = color
        self.font = font
        self.line_spacing = line_spacing
        self.outline_color = outline_color
        self.full_outline = full_outline

    def render(self, draw: ImageDraw.ImageDraw, bounds: tuple) -> ImageDraw.ImageDraw:
        """Renders the text onto an image within the specified bounding box.

        :param draw: The drawable surface to write on
        :param bounds(top_left_x, top_left_y, bottom_right_x, bottom_right_y): bounding box
        """
        (bx1, by1, bx2, by2) = bounds
        text_width, text_height = draw.textsize(self.text, font=self.font)

        if self.position.value & AnnotationPosition.TOP.value:
            y = by1
        else:
            y = by2 - text_height

        if self.position.value & AnnotationPosition.LEFT.value:
            x = bx1
        else:
            x = bx2 - text_width

        # helper method for each draw call below
        def _draw_text(pos, color):
            draw.text(pos, self.text, font=self.font, fill=color,
                      align=self.align, spacing=self.line_spacing)

        if self.outline_color is not None:
            # Pillow doesn't support outlined or shadowed text directly.
            # We manually draw the text multiple times to achieve the effect.
            if self.full_outline:
                _draw_text((x - 1, y), self.outline_color)
                _draw_text((x + 1, y), self.outline_color)
                _draw_text((x, y - 1), self.outline_color)
                _draw_text((x, y + 1), self.outline_color)
            else:
                # just draw a drop shadow (cheaper)
                _draw_text((x + 1, y + 1), self.outline_color)

        _draw_text((x, y), self.color)

        return draw


def add_img_box_to_image(draw: ImageDraw.ImageDraw, box: util.ImageRect, color: str, text: Union[ImageText, Iterable[ImageText]] = None) -> None:
    """Draw a box on an image and optionally add text.

    This will draw the outline of a rectangle to the passed in image
    in the specified color and optionally add one or more pieces of text
    along the inside edge of the rectangle.

    :param draw: The drawable surface to write on
    :param box: The ImageBox defining the rectangle to draw
    :param color: A color string suitable for use with PIL - see :mod:`PIL.ImageColor`
    :param text: The text to display - may be a single ImageText instance,
        or any iterable (eg a list of ImageText instances) to display multiple pieces of text.
    """
    x1, y1 = box.x_top_left, box.y_top_left
    x2, y2 = (box.x_top_left + box.width), (box.y_top_left + box.height)
    draw.rectangle([x1, y1, x2, y2], outline=color)
    if text is not None:
        if isinstance(text, collections.Iterable):
            for t in text:
                t.render(draw, (x1, y1, x2, y2))
        else:
            text.render(draw, (x1, y1, x2, y2))


def add_polygon_to_image(draw: ImageDraw.ImageDraw, poly_points: list, scale: float, line_color: str, fill_color: str = None) -> None:
    """Draw a polygon on an image

    This will draw a polygon on the passed-in image in the specified
    colors and scale.

    :param draw: The drawable surface to write on
    :param poly_points: A sequence of points representing the polygon,
        where each point has float members (x, y)
    :param scale: Scale to multiply each point to match the image scaling
    :param line_color: The color for the outline of the polygon. The string value
        must be a color string suitable for use with PIL - see :mod:`PIL.ImageColor`
    :param fill_color: The color for the inside of the polygon. The string value
        must be a color string suitable for use with PIL - see :mod:`PIL.ImageColor`
    """
    if len(poly_points) < 2:
        # Need at least 2 points to draw any lines
        return

    # Convert poly_points to the PIL format and scale them to the image
    pil_poly_points = []
    for pt in poly_points:
        pil_poly_points.append((pt.x * scale, pt.y * scale))

    draw.polygon(pil_poly_points, fill=fill_color, outline=line_color)


def _find_key_for_cls(d, cls):
    for c in cls.__mro__:
        result = d.get(c, None)
        if result:
            return result
    return d['default']


class Annotator:
    """Annotation base class

    Subclasses of Annotator handle applying a single annotation to an image.
    """
    #: int: The priority of the annotator - Annotators with higher numbered
    #: priorities are applied first.
    priority = 100

    def __init__(self, img_annotator, priority=None):
        #: :class:`ImageAnnotator`: The object managing camera annotations
        self.img_annotator = img_annotator

        #: :class:`~anki_vector.world.World`: The world object for the robot who owns the camera
        self.world = img_annotator.world

        #: bool: Set enabled to false to prevent the annotator being called
        self.enabled = True

        if priority is not None:
            self.priority = priority

    def apply(self, image: Image.Image, scale: float):
        """Applies the annotation to the image."""
        # should be overriden by a subclass
        raise NotImplementedError()

    def __hash__(self):
        return id(self)


class ObjectAnnotator(Annotator):  # pylint: disable=too-few-public-methods
    """Adds object annotations to an Image.

    This handles :class:`anki_vector.objects.LightCube`,
    :class:`anki_vector.objects.Charger` and
    :class:`anki_vector.objects.CustomObject`.
    """
    priority = 100
    object_colors = DEFAULT_OBJECT_COLORS

    def __init__(self, img_annotator, object_colors=None):
        super().__init__(img_annotator)
        if object_colors is not None:
            self.object_colors = object_colors

    def apply(self, image: Image.Image, scale: float) -> None:
        draw = ImageDraw.Draw(image)
        for obj in self.world.visible_objects:
            color = _find_key_for_cls(self.object_colors, obj.__class__)
            text = self._label_for_obj(obj)
            box = obj.last_observed_image_rect
            if scale != 1:
                box.scale_by(scale)
            add_img_box_to_image(draw, box, color, text=text)

    def _label_for_obj(self, obj):  # pylint: disable=no-self-use
        """Fetch a label to display for the object.

        Override or replace to customize.
        """
        return ImageText(obj.descriptive_name)


class FaceAnnotator(Annotator):  # pylint: disable=too-few-public-methods
    """Adds annotations of currently detected faces to a camera image.

    This handles the display of :class:`anki_vector.faces.Face` objects.
    """
    priority = 100
    box_color = 'green'

    def __init__(self, img_annotator, box_color=None):
        super().__init__(img_annotator)
        if box_color is not None:
            self.box_color = box_color

    def apply(self, image: Image.Image, scale: float) -> None:
        draw = ImageDraw.Draw(image)
        for obj in self.world.visible_faces:
            text = self._label_for_face(obj)
            box = obj.last_observed_image_rect
            if scale != 1:
                box.scale_by(scale)
            add_img_box_to_image(draw, box, self.box_color, text=text)
            add_polygon_to_image(draw, obj.left_eye, scale, self.box_color)
            add_polygon_to_image(draw, obj.right_eye, scale, self.box_color)
            add_polygon_to_image(draw, obj.nose, scale, self.box_color)
            add_polygon_to_image(draw, obj.mouth, scale, self.box_color)

    def _label_for_face(self, obj):  # pylint: disable=no-self-use
        """Fetch a label to display for the face.

        Override or replace to customize.
        """
        label_text = ""
        expression = faces.Expression(obj.expression).name

        if obj.name:
            label_text = f"Name:{obj.name}"
        if expression != "UNKNOWN":
            label_text += f"\nExpression:{expression}"
        if obj.expression_score:
            # if there is a specific known expression, then also show the score
            # (display a % to make it clear the value is out of 100)
            label_text += f"\nScore:{sum(obj.expression_score)}"

        return ImageText(label_text + "\n" + f"Face Id:{obj.face_id}")


class TextAnnotator(Annotator):  # pylint: disable=too-few-public-methods
    """Adds simple text annotations to a camera image.
    """
    priority = 50

    def __init__(self, img_annotator, text):
        super().__init__(img_annotator)
        self.text = text

    def apply(self, image: Image.Image, scale: int) -> None:
        d = ImageDraw.Draw(image)
        self.text.render(d, (0, 0, image.width, image.height))


class _AnnotatorHelper(Annotator):  # pylint: disable=too-few-public-methods
    def __init__(self, img_annotator, wrapped):
        super().__init__(img_annotator)
        self._wrapped = wrapped

    def apply(self, image: Image.Image, scale: int) -> None:
        self._wrapped(image, scale, world=self.world, img_annotator=self.img_annotator)


def annotator(f):
    """A decorator for converting a regular function/method into an Annotator.

    The wrapped function should have a signature of
    ``(image, scale, img_annotator=None, world=None, **kw)``
    """
    @functools.wraps(f)
    def wrapper(img_annotator):
        return _AnnotatorHelper(img_annotator, f)
    return wrapper


class ImageAnnotator:
    """ImageAnnotator applies annotations to the camera image received from the robot.

    This is instantiated by :class:`anki_vector.world.World` and is accessible as
    :class:`anki_vector.camera.CameraComponent.image_annotator`.

    By default it defines two active annotators named ``objects`` and ``faces``.

    The ``objects`` annotator adds a box around each object (such as light cubes)
    that the robot can see.  The ``faces`` annotator adds a box around each person's
    face that the robot can recognize.

    Custom annotations can be defined by calling :meth:`add_annotator` with
    a name of your choosing and an instance of a :class:`Annotator` subclass,
    or use a regular function wrapped with the :func:`annotator` decorator.

    Individual annotations can be disabled and re-enabled using the
    :meth:`disable_annotator` and :meth:`enable_annotator` methods.

    All annotations can be disabled by setting the
    :attr:`annotation_enabled` property to False.

    E.g. to disable face annotations, call
    ``robot.camera.image_annotator.disable_annotator('faces')``

    Annotators each have a priority number associated with them. Annotators
    with a larger priority number are rendered first and may be overdrawn by those
    with a lower/smaller priority number.


    .. testcode::

        from PIL import ImageDraw

        import anki_vector
        from anki_vector import annotate
        import time

        @annotate.annotator
        def clock(image, scale, annotator=None, world=None, **kw):
            d = ImageDraw.Draw(image)
            bounds = (0, 0, image.width, image.height)
            text = annotate.ImageText(time.strftime("%H:%m:%S"),
                                      position=annotate.AnnotationPosition.TOP_LEFT,
                                      outline_color="black")
            text.render(d, bounds)

        with anki_vector.Robot(show_viewer=True) as robot:
            # Add a custom annotator to the camera feed
            robot.camera.image_annotator.add_annotator("custom-annotator", clock)
            time.sleep(5)
            # Disable the custom annotator
            robot.camera.image_annotator.disable_annotator("custom-annotator")
            time.sleep(5)
    """

    def __init__(self, world, **kw):
        super().__init__(**kw)
        #: :class:`anki_vector.world.World`: World object that created the annotator.
        self.world = world

        self._annotators = {}
        self._sorted_annotators = []
        self.add_annotator('objects', ObjectAnnotator(self))
        self.add_annotator('faces', FaceAnnotator(self))

        #: If this attribute is set to false, the :meth:`annotate_image` method
        #: will continue to provide a scaled image, but will not apply any annotations.
        self.annotation_enabled = True

    def _sort_annotators(self):
        self._sorted_annotators = sorted(self._annotators.values(),
                                         key=lambda an: an.priority, reverse=True)

    def add_annotator(self, name: str, new_annotator: Union[Annotator, Callable[..., Annotator]]) -> None:
        """Adds a new annotator for display.

        Annotators are enabled by default.

        :param name: An arbitrary name for the annotator; must not
                already be defined
        :param new_annotator: The annotator to add may either by an instance of Annotator,
            or a factory callable that will return an instance of Annotator.
            The callable will be called with an ImageAnnotator instance as its first argument.

        Raises:
            :class:`ValueError` if the annotator is already defined.
        """
        if name in self._annotators:
            raise ValueError('Annotator "%s" is already defined' % (name))
        if not isinstance(new_annotator, Annotator):
            new_annotator = new_annotator(self)
        self._annotators[name] = new_annotator
        self._sort_annotators()

    def remove_annotator(self, name: str) -> None:
        """Remove an annotator.

        :param name: The name of the annotator to remove as passed to :meth:`add_annotator`.

        Raises:
            KeyError if the annotator isn't registered
        """
        del self._annotators[name]
        self._sort_annotators()

    def get_annotator(self, name: str) -> None:
        """Return a named annotator.

        :param name: The name of the annotator to return

        Raises:
            KeyError if the annotator isn't registered
        """
        return self._annotators[name]

    def disable_annotator(self, name: str) -> None:
        """Disable a named annotator.

        Leaves the annotator as registered, but does not include its output
        in the annotated image.

        :param name: The name of the annotator to disable
        """
        if name in self._annotators:
            self._annotators[name].enabled = False

    def enable_annotator(self, name: str) -> None:
        """Enabled a named annotator.

        (re)enable an annotator if it was previously disabled.

        :param name: The name of the annotator to enable
        """
        self._annotators[name].enabled = True

    def add_static_text(self, name: str, text: Union[str, ImageText], color: str = 'white', position: int = AnnotationPosition.TOP_LEFT) -> None:
        """Add some static text to annotated images.

        This is a convenience method to create a :class:`TextAnnnotator`
        and add it to the image.

        :param name: An arbitrary name for the annotator; must not
            already be defined
        :param text: The text to display
            may be a plain string, or an ImageText instance
        :param color: Used if text is a string; defaults to white
        :param position: Used if text is a string; defaults to TOP_LEFT
        """
        if isinstance(text, str):
            text = ImageText(text, position=position, color=color)
        self.add_annotator(name, TextAnnotator(self, text))

    def annotate_image(self, image: Image.Image, scale: float = None, fit_size: Tuple[int, int] = None, resample_mode: int = RESAMPLE_MODE_NEAREST) -> Image.Image:
        """Called by :class:`~anki_vector.camera.CameraComponent` to annotate camera images.

        :param image: The image to annotate
        :param scale: If set then the base image will be scaled by the
            supplied multiplier.  Cannot be combined with fit_size
        :param fit_size:  If set, then scale the image to fit inside
            the supplied (width, height) dimensions. The original aspect
            ratio will be preserved.  Cannot be combined with scale.
        :param resample_mode: The resampling mode to use when scaling the
            image. Should be either :attr:`RESAMPLE_MODE_NEAREST` (fast) or
            :attr:`RESAMPLE_MODE_BILINEAR` (slower, but smoother).
        """
        if scale is not None and scale != 1:
            image = image.resize((int(image.width * scale), int(image.height * scale)),
                                 resample=resample_mode)

        elif fit_size is not None and fit_size != (image.width, image.height):
            img_ratio = image.width / image.height
            fit_width, fit_height = fit_size
            fit_ratio = fit_width / fit_height
            if img_ratio > fit_ratio:
                fit_height = int(fit_width / img_ratio)
            elif img_ratio < fit_ratio:
                fit_width = int(fit_height * img_ratio)
            scale = fit_width / image.width
            image = image.resize((fit_width, fit_height))

        else:
            scale = 1
            image = image.copy()

        if not self.annotation_enabled:
            return image

        for an in self._sorted_annotators:
            if an.enabled:
                an.apply(image, scale)

        return image
