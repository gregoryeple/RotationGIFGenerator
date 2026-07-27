from PIL import Image, ImageOps, ImageSequence
from enum import Enum
import math
import os

# ENUM
class RESIZE(Enum):
    NONE = "NONE"
    SCALE = "SCALE"
    COVER = "COVER"
    FILL = "FILL"

class ALIGN(Enum):
    TOP = "TOP"
    CENTER = "CENTER"
    BOTTOM = "BOTTOM"

class SIZE(Enum):
    MAIN = "MAIN"
    BACKGROUND = "BACKGROUND"
    ROTATION = "ROTATION"

# CONFIGURATION
IMAGE_BACKGROUND = None
IMAGE_MAIN = "main.png"
IMAGE_ROTATION = ["walk.gif"] # Ex: "orb.png", ["front.png"], ["back.png", "front.png"], ["back_left.png","back_right.png","front_right.png","front_left.png"]
IMAGE_OUTPUT = "animation.gif"

SCALE_BACKGROUND = 1.0
SCALE_MAIN = 0.5
SCALE_ROTATION = 10.0

ROTATION_HEIGHT = 0.75
ROTATION_ANGLE = 90
ROTATION_DURATION = 2.5
ROTATION_NUMBER = 4
ROTATION_RADIUS = 0.1

IMAGE_RESIZE = RESIZE.NONE
IMAGE_ALIGNMENT = ALIGN.CENTER
IMAGE_SIZE = SIZE.BACKGROUND

FPS = 30

# IMAGE OBJECT
class AnimatedImage:

    def __init__(self, frames, durations):
        self.frames = frames
        self.durations = durations
        self.total_duration = sum(durations)
        self.width = frames[0].width
        self.height = frames[0].height

    def frame_at_time(self, t_ms):
        if len(self.frames) == 1:
            return self.frames[0]
        t = t_ms % self.total_duration
        acc = 0
        for frame, duration in zip(self.frames, self.durations):
            acc += duration
            if t < acc:
                return frame
        return self.frames[-1]

# HELPERS
def ensure_rgba(image):
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    return image

def resize_image(img, scale):
    if scale == 1:
        return img
    w = max(1, int(img.width * scale))
    h = max(1, int(img.height * scale))
    return img.resize((w, h), Image.LANCZOS)

def load_image(path):
    img = Image.open(path)
    frames = []
    durations = []
    try:
        for frame in ImageSequence.Iterator(img):
            frame = ensure_rgba(frame.copy())
            duration = frame.info.get("duration", img.info.get("duration", 100))
            if duration <= 0:
                duration = 100
            frames.append(frame)
            durations.append(duration)
    except EOFError:
        pass
    if not frames:
        frames = [ensure_rgba(img)]
        durations = [100]
    return AnimatedImage(frames, durations)


# ROTATING SPRITE
class RotationSprite:

    def __init__(self, definition):
        if isinstance(definition, str):
            definition = [definition]
        self.images = []
        for path in definition:
            self.images.append(load_image(path))

    def get_image(self, orbit_angle):
        a = orbit_angle % 360
        count = len(self.images)
        if count == 1:
            return self.images[0]
        if count == 2:
            if 180 <= a < 360:
                return self.images[1]
            return self.images[0]
        if count == 4:
            if 0 <= a < 90:
                return self.images[0]
            if 90 <= a < 180:
                return self.images[1]
            if 180 <= a < 270:
                return self.images[2]
            return self.images[3]
        raise ValueError("Rotation image must contain 1, 2 or 4 images.")

# LOAD CONFIGURED IMAGES
BACKGROUND = (load_image(IMAGE_BACKGROUND) if IMAGE_BACKGROUND else None)
MAIN = (load_image(IMAGE_MAIN) if IMAGE_MAIN else None)
ROTATION = []

for item in IMAGE_ROTATION:
    ROTATION.append(RotationSprite(item))
ROTATION *= ROTATION_NUMBER
if len(ROTATION) == 0:
    raise ValueError("IMAGE_ROTATION must contain at least one image.")

# RESIZE UTILITIES
def apply_background_resize(img, target_size):
    if IMAGE_RESIZE == RESIZE.NONE:
        return img
    if IMAGE_RESIZE == RESIZE.SCALE:
        return ImageOps.contain(img, target_size, Image.LANCZOS)
    if IMAGE_RESIZE == RESIZE.COVER:
        return ImageOps.fit(img, target_size, Image.LANCZOS)
    if IMAGE_RESIZE == RESIZE.FILL:
        return img.resize(target_size, Image.LANCZOS)
    raise ValueError("Unknown IMAGE_RESIZE mode")

# FRAME ACCESS
def get_background_frame(time_ms):
    if BACKGROUND is None:
        return None
    return resize_image(BACKGROUND.frame_at_time(time_ms), SCALE_BACKGROUND)

def get_main_frame(time_ms):
    if MAIN is None:
        return None
    return resize_image(MAIN.frame_at_time(time_ms), SCALE_MAIN)

# CANVAS SIZE
def rotation_radius_pixels(base_size):
    if isinstance(ROTATION_RADIUS, (list, tuple)):
        return (base_size[0] * 0.5 * ROTATION_RADIUS[0]), (base_size[1] * 0.5 * ROTATION_RADIUS[1])
    else:
        return (base_size[0] * 0.5 * ROTATION_RADIUS), (base_size[1] * 0.5 * ROTATION_RADIUS)

def get_base_size():
    if IMAGE_SIZE == SIZE.BACKGROUND and BACKGROUND:
        return BACKGROUND.width, BACKGROUND.height
    if IMAGE_SIZE == SIZE.MAIN and MAIN:
        return MAIN.width, MAIN.height
    if MAIN:
        return MAIN.width, MAIN.height
    if BACKGROUND:
        return BACKGROUND.width, BACKGROUND.height
    return ROTATION[0].images[0].width, ROTATION[0].images[0].height


def compute_canvas_size():
    base_w, base_h = get_base_size()
    if IMAGE_SIZE != SIZE.ROTATION:
        return int(base_w), int(base_h)
    rx, _ = rotation_radius_pixels((base_w, base_h))
    sprite_w = 0
    sprite_h = 0
    for sprite in ROTATION:
        for anim in sprite.images:
            sprite_w = max(sprite_w, anim.width)
            sprite_h = max(sprite_h, anim.height)
    width = int(base_w + rx * 2 + sprite_w)
    height = int(max(base_h, base_h + sprite_h))
    return width, height

CANVAS_WIDTH, CANVAS_HEIGHT = compute_canvas_size()

# MAIN IMAGE POSITION
def get_main_position(main_img):
    x = (CANVAS_WIDTH - main_img.width) // 2
    if IMAGE_ALIGNMENT == ALIGN.TOP:
        y = 0
    elif IMAGE_ALIGNMENT == ALIGN.BOTTOM:
        y = CANVAS_HEIGHT - main_img.height
    else:
        y = (CANVAS_HEIGHT - main_img.height) // 2
    return x, y

def get_rotation_center(main_img):
    x, y = get_main_position(main_img)
    return (x + main_img.width / 2), (y + main_img.height * ROTATION_HEIGHT)


# BACKGROUND POSITION
def prepare_background(img):
    target = (CANVAS_WIDTH, CANVAS_HEIGHT)
    bg = apply_background_resize(img, target)
    canvas = Image.new("RGBA", target, (0, 0, 0, 0))
    canvas.alpha_composite(bg, ((target[0] - bg.width) // 2, (target[1] - bg.height) // 2))
    return canvas

# SCALE HELPERS
def depth_scale(depth): # -1 = back / 0 = side / 1 = front
    return 0.75 + (depth + 1) * 0.125

def resize_for_depth(img, depth):
    scale = depth_scale(depth)
    return img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)

# DRAW HELPERS
def paste_center(canvas, img, x, y):
    canvas.alpha_composite(img, (int(x - img.width / 2), int(y - img.height / 2)))

# CACHE
_resize_cache = {}

def cached_resize(img, scale):
    key = (id(img), round(scale, 4))
    if key in _resize_cache:
        return _resize_cache[key]
    out = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    _resize_cache[key] = out
    return out

def cached_depth_resize(img, depth):
    return cached_resize(img, depth_scale(depth))

# ORBIT PARAMETERS
def orbit_parameters():
    if MAIN:
        size = (MAIN.width, MAIN.height)
    elif BACKGROUND:
        size = (BACKGROUND.width, BACKGROUND.height)
    else:
        size = (ROTATION[0].images[0].width, ROTATION[0].images[0].height)
    return rotation_radius_pixels(size)

# ROTATION MATH
def orbit_position(progress, index, count):
    angle = (progress * 360.0 + index * (360.0 / count) + ROTATION_ANGLE) % 360.0
    r = math.radians(angle)
    rx, rz = orbit_parameters()
    return math.sin(r) * rx, -math.cos(r), angle

def project_orbit(cx, cy, x, depth):
    _, rz = orbit_parameters()
    return (cx + x), (cy + depth * rz)

# DIRECTIONAL SPRITE SELECTION
def sprite_frame(sprite, angle, time_ms):
    count = len(sprite.images)
    if count == 1:
        return sprite.images[0].frame_at_time(time_ms)
    angle %= 360
    if count == 2:
        # front
        if 90 <= angle < 270:
            return sprite.images[1].frame_at_time(time_ms)
        # back
        return sprite.images[0].frame_at_time(time_ms)
    if count == 4:
        if angle < 90:
            i = 0
        elif angle < 180:
            i = 1
        elif angle < 270:
            i = 2
        else:
            i = 3
        return sprite.images[i].frame_at_time(time_ms)
    raise ValueError("Rotation sprite must contain 1, 2 or 4 images.")

# SPRITE RENDER LIST
def build_rotation_list(progress, time_ms, main_img):
    cx, cy = get_rotation_center(main_img)
    render = []
    total = len(ROTATION)
    for i, sprite in enumerate(ROTATION):
        x, depth, angle = orbit_position(progress, i, total)
        img = cached_depth_resize(sprite_frame(sprite, angle, time_ms), depth)
        px, py = project_orbit(cx, cy, x, depth)
        render.append({"depth": depth, "image": img, "x": px, "y": py})
    render.sort(key=lambda e: e["depth"])
    return render

# RENDER FRAME
def render_frame(progress, time_ms):
    main_frame = get_main_frame(time_ms)
    if main_frame is None:
        # Invisible anchor if no main image.
        main_frame = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    background = get_background_frame(time_ms)
    if background is None:
        canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    else:
        canvas = prepare_background(background)
    sprites = build_rotation_list(progress, time_ms, main_frame)
    main_x, main_y = get_main_position(main_frame)
    # Draw everything behind the main image.
    for sprite in sprites:
        if sprite["depth"] < 0:
            paste_center(canvas, sprite["image"], sprite["x"], sprite["y"])
    # Main image.
    if MAIN is not None:
        canvas.alpha_composite(main_frame, (int(main_x), int(main_y)))
    # Draw everything in front.
    for sprite in sprites:
        if sprite["depth"] >= 0:
            paste_center(canvas, sprite["image"], sprite["x"], sprite["y"])
    return canvas

# TIMELINE
def animation_frame_count():
    return max(1, round(ROTATION_DURATION * FPS))

def frame_duration_ms():
    return round(1000 / FPS)

def frame_time_ms(frame_index):
    return frame_index * frame_duration_ms()

# GENERATE ANIMATION
def generate_animation():
    frames = []
    count = animation_frame_count()
    for frame in range(count):
        frames.append(render_frame(frame / count, frame_time_ms(frame)))
    return frames

# GIF EXPORT
def export_gif(frames):
    if len(frames) == 0:
        raise RuntimeError("No frames generated.")
    output = IMAGE_OUTPUT
    if not output.lower().endswith(".gif"):
        output += ".gif"
    frames[0].save(
        output,
        save_all = True,
        append_images = frames[1:],
        loop = 0,
        duration = round(1000 / FPS),
        disposal = 2,
        optimize = True,
    )
    print(f"Saved GIF: {output}")
    print(f"Frames: {len(frames)}")
    print(f"FPS: {FPS}")
    print(f"Duration: {ROTATION_DURATION:.2f}s")


# VALIDATION
def validate_configuration():
    if len(ROTATION) == 0:
        raise ValueError("IMAGE_ROTATION must contain at least one image.")
    if ROTATION_DURATION <= 0:
        raise ValueError("ROTATION_DURATION must be > 0.")
    if FPS <= 0:
        raise ValueError("FPS must be > 0.")
    if SCALE_BACKGROUND <= 0:
        raise ValueError("SCALE_BACKGROUND must be > 0.")
    if SCALE_MAIN <= 0:
        raise ValueError("SCALE_MAIN must be > 0.")
    if SCALE_ROTATION <= 0:
        raise ValueError("SCALE_ROTATION must be > 0.")
    if not (0 <= ROTATION_HEIGHT <= 1):
        raise ValueError("ROTATION_HEIGHT must be between 0 and 1.")

# MAIN
def main():
    print("=" * 60)
    print("Rotation GIF Generator")
    print("=" * 60)
    validate_configuration()
    print("Rendering animation...")
    frames = generate_animation()
    print(f"Generated {len(frames)} frames.")
    print("Exporting GIF...")
    export_gif(frames)
    print("Done.")

if __name__ == "__main__":
    main()