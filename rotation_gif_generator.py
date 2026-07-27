from PIL import Image, ImageOps, ImageSequence
import math
import os

# ============================================================
# CONFIGURATION
# ============================================================

IMAGE_BACKGROUND = None
IMAGE_MAIN = "main.png" # None

# Examples:
#
# IMAGE_ROTATION = [
#     "orb.png",
#     ["front.png"],
#     ["back.png", "front.png"],
#     ["back_left.png","back_right.png","front_right.png","front_left.png"]
# ]
#
IMAGE_ROTATION = ["walk.gif"
]

IMAGE_OUTPUT = "animation.gif"

SCALE_BACKGROUND = 1.0
SCALE_MAIN = 1.0
SCALE_ROTATION = 25.0

ROTATION_HEIGHT = 0.75
ROTATION_ANGLE = 0

ROTATION_DURATION = 5.0
ROTATION_NUMBER = 4

ROTATION_RADIUS = 0.75

IMAGE_RESIZE = "NONE"       # NONE SCALE COVER FILL
IMAGE_ALIGNMENT = "CENTER"  # TOP CENTER BOTTOM
IMAGE_SIZE = "BACKGROUND"   # MAIN BACKGROUND ROTATION

FPS = 30

# ============================================================
# ENUMS
# ============================================================

RESIZE_NONE = "NONE"
RESIZE_SCALE = "SCALE"
RESIZE_COVER = "COVER"
RESIZE_FILL = "FILL"

ALIGN_TOP = "TOP"
ALIGN_CENTER = "CENTER"
ALIGN_BOTTOM = "BOTTOM"

SIZE_MAIN = "MAIN"
SIZE_BACKGROUND = "BACKGROUND"
SIZE_ROTATION = "ROTATION"

# ============================================================
# IMAGE OBJECT
# ============================================================

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

# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# ROTATING SPRITE
# ============================================================

class RotationSprite:

    def __init__(self, definition):

        if isinstance(definition, str):

            definition = [definition]

        self.images = []

        for path in definition:

            self.images.append(load_image(path))

    def get_image(self, orbit_angle):

        """
        Returns the AnimatedImage according
        to the current orbit angle.

        1 image:
            always

        2 images:
            back / front

        4 images:
            back-left
            back-right
            front-right
            front-left
        """

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

        raise ValueError(
            "Rotation image must contain 1, 2 or 4 images."
        )

# ============================================================
# LOAD CONFIGURED IMAGES
# ============================================================

BACKGROUND = (
    load_image(IMAGE_BACKGROUND)
    if IMAGE_BACKGROUND
    else None
)

MAIN = (
    load_image(IMAGE_MAIN)
    if IMAGE_MAIN
    else None
)

ROTATION = []

for item in IMAGE_ROTATION:
    ROTATION.append(RotationSprite(item))

if len(ROTATION) == 0:
    raise ValueError(
        "IMAGE_ROTATION must contain at least one image."
    )

# ============================================================
# RESIZE UTILITIES
# ============================================================

def fit_inside(img, size):

    return ImageOps.contain(img, size, Image.LANCZOS)


def cover(img, size):

    return ImageOps.fit(img, size, Image.LANCZOS)


def stretch(img, size):

    return img.resize(size, Image.LANCZOS)


def apply_background_resize(img, target_size):

    if IMAGE_RESIZE == RESIZE_NONE:
        return img

    if IMAGE_RESIZE == RESIZE_SCALE:
        return fit_inside(img, target_size)

    if IMAGE_RESIZE == RESIZE_COVER:
        return cover(img, target_size)

    if IMAGE_RESIZE == RESIZE_FILL:
        return stretch(img, target_size)

    raise ValueError("Unknown IMAGE_RESIZE mode")

# ============================================================
# FRAME ACCESS
# ============================================================

def get_background_frame(time_ms):

    if BACKGROUND is None:
        return None

    img = BACKGROUND.frame_at_time(time_ms)

    return resize_image(img, SCALE_BACKGROUND)


def get_main_frame(time_ms):

    if MAIN is None:
        return None

    img = MAIN.frame_at_time(time_ms)

    return resize_image(img, SCALE_MAIN)


def get_rotation_frame(sprite, angle, time_ms):

    anim = sprite.get_image(angle)

    img = anim.frame_at_time(time_ms)

    return resize_image(img, SCALE_ROTATION)

# ============================================================
# CANVAS SIZE
# ============================================================

def rotation_radius_pixels(base_size):
    """
    Converts ROTATION_RADIUS to pixel radii.

    A single value means:
        width = height = depth

    A list/tuple means:
        [horizontal, depth]
    """

    if isinstance(ROTATION_RADIUS, (list, tuple)):
        rx_ratio = ROTATION_RADIUS[0]
        rz_ratio = ROTATION_RADIUS[1]
    else:
        rx_ratio = ROTATION_RADIUS
        rz_ratio = ROTATION_RADIUS

    rx = base_size[0] * 0.5 * rx_ratio
    rz = base_size[1] * 0.5 * rz_ratio

    return rx, rz


def get_base_size():

    if IMAGE_SIZE == SIZE_BACKGROUND and BACKGROUND:
        return BACKGROUND.width, BACKGROUND.height

    if IMAGE_SIZE == SIZE_MAIN and MAIN:
        return MAIN.width, MAIN.height

    if MAIN:
        return MAIN.width, MAIN.height

    if BACKGROUND:
        return BACKGROUND.width, BACKGROUND.height

    img = ROTATION[0].images[0]

    return img.width, img.height


def compute_canvas_size():

    """
    Computes the exported image size.

    IMAGE_SIZE:

        MAIN
        BACKGROUND
        ROTATION
    """

    base_w, base_h = get_base_size()

    if IMAGE_SIZE != SIZE_ROTATION:
        return (
            int(base_w),
            int(base_h)
        )

    rx, _ = rotation_radius_pixels((base_w, base_h))

    sprite_w = 0
    sprite_h = 0

    for sprite in ROTATION:

        for anim in sprite.images:

            sprite_w = max(sprite_w, anim.width)
            sprite_h = max(sprite_h, anim.height)

    width = int(base_w + rx * 2 + sprite_w)

    height = int(max(
        base_h,
        base_h + sprite_h
    ))

    return width, height


CANVAS_WIDTH, CANVAS_HEIGHT = compute_canvas_size()

# ============================================================
# MAIN IMAGE POSITION
# ============================================================

def get_main_position(main_img):

    x = (CANVAS_WIDTH - main_img.width) // 2

    if IMAGE_ALIGNMENT == ALIGN_TOP:
        y = 0

    elif IMAGE_ALIGNMENT == ALIGN_BOTTOM:
        y = CANVAS_HEIGHT - main_img.height

    else:
        y = (CANVAS_HEIGHT - main_img.height) // 2

    return x, y


def get_rotation_center(main_img):

    x, y = get_main_position(main_img)

    cx = x + main_img.width / 2

    cy = y + main_img.height * ROTATION_HEIGHT

    return cx, cy


# ============================================================
# BACKGROUND POSITION
# ============================================================

def prepare_background(img):

    target = (CANVAS_WIDTH, CANVAS_HEIGHT)

    bg = apply_background_resize(img, target)

    canvas = Image.new(
        "RGBA",
        target,
        (0, 0, 0, 0)
    )

    px = (target[0] - bg.width) // 2
    py = (target[1] - bg.height) // 2

    canvas.alpha_composite(bg, (px, py))

    return canvas


# ============================================================
# SCALE HELPERS
# ============================================================

def depth_scale(depth):

    """
    depth

    -1 = back

     0 = side

     1 = front

    Returns a multiplicative scale.
    """

    return 0.75 + (depth + 1) * 0.125


def resize_for_depth(img, depth):

    scale = depth_scale(depth)

    w = max(1, int(img.width * scale))
    h = max(1, int(img.height * scale))

    return img.resize(
        (w, h),
        Image.LANCZOS
    )


# ============================================================
# DRAW HELPERS
# ============================================================

def paste_center(canvas, img, x, y):

    canvas.alpha_composite(
        img,
        (
            int(x - img.width / 2),
            int(y - img.height / 2)
        )
    )


def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(maximum, value)
    )


# ============================================================
# CACHE
# ============================================================

_resize_cache = {}


def cached_resize(img, scale):

    key = (
        id(img),
        round(scale, 4)
    )

    if key in _resize_cache:
        return _resize_cache[key]

    w = max(1, int(img.width * scale))
    h = max(1, int(img.height * scale))

    out = img.resize(
        (w, h),
        Image.LANCZOS
    )

    _resize_cache[key] = out

    return out


def cached_depth_resize(img, depth):

    return cached_resize(
        img,
        depth_scale(depth)
    )


# ============================================================
# ORBIT PARAMETERS
# ============================================================

def orbit_parameters():

    """
    Returns the radii used by the renderer.
    """

    if MAIN:
        size = (
            MAIN.width,
            MAIN.height
        )

    elif BACKGROUND:
        size = (
            BACKGROUND.width,
            BACKGROUND.height
        )

    else:
        img = ROTATION[0].images[0]

        size = (
            img.width,
            img.height
        )

    return rotation_radius_pixels(size)

# ============================================================
# ROTATION MATH
# ============================================================

def orbit_position(progress, index, count):
    """
    Returns the orbit information for one sprite.

    progress : 0..1
    index    : sprite index
    count    : total sprites

    Returns:
        x
        depth
        angle
    """

    angle = (
        progress * 360.0
        + index * (360.0 / count)
        + ROTATION_ANGLE
    ) % 360.0

    r = math.radians(angle)

    rx, rz = orbit_parameters()

    x = math.sin(r) * rx

    depth = -math.cos(r)

    return x, depth, angle


def project_orbit(cx, cy, x, depth):

    _, rz = orbit_parameters()

    y = cy + depth * rz

    return cx + x, y


# ============================================================
# DIRECTIONAL SPRITE SELECTION
# ============================================================

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


# ============================================================
# SPRITE RENDER LIST
# ============================================================

def build_rotation_list(progress, time_ms, main_img):

    cx, cy = get_rotation_center(main_img)

    render = []

    total = len(ROTATION)

    for i, sprite in enumerate(ROTATION):

        x, depth, angle = orbit_position(
            progress,
            i,
            total
        )

        img = sprite_frame(
            sprite,
            angle,
            time_ms
        )

        img = cached_depth_resize(
            img,
            depth
        )

        px, py = project_orbit(
            cx,
            cy,
            x,
            depth
        )

        render.append({
            "depth": depth,
            "image": img,
            "x": px,
            "y": py
        })

    render.sort(
        key=lambda e: e["depth"]
    )

    return render


# ============================================================
# RENDER FRAME
# ============================================================

def render_frame(progress, time_ms):

    main = get_main_frame(time_ms)

    if main is None:

        # Invisible anchor if no main image.
        main = Image.new(
            "RGBA",
            (1, 1),
            (0, 0, 0, 0)
        )

    background = get_background_frame(time_ms)

    if background is None:

        canvas = Image.new(
            "RGBA",
            (
                CANVAS_WIDTH,
                CANVAS_HEIGHT
            ),
            (0, 0, 0, 0)
        )

    else:

        canvas = prepare_background(background)

    sprites = build_rotation_list(
        progress,
        time_ms,
        main
    )

    main_x, main_y = get_main_position(main)

    # Draw everything behind the main image.
    for sprite in sprites:

        if sprite["depth"] < 0:

            paste_center(
                canvas,
                sprite["image"],
                sprite["x"],
                sprite["y"]
            )

    # Main image.
    if MAIN is not None:

        canvas.alpha_composite(
            main,
            (
                int(main_x),
                int(main_y)
            )
        )

    # Draw everything in front.
    for sprite in sprites:

        if sprite["depth"] >= 0:

            paste_center(
                canvas,
                sprite["image"],
                sprite["x"],
                sprite["y"]
            )

    return canvas


# ============================================================
# FRAME GENERATION
# ============================================================

def render_animation():

    frame_count = max(
        1,
        int(ROTATION_DURATION * FPS)
    )

    frames = []

    duration = int(
        1000 / FPS
    )

    for i in range(frame_count):

        progress = i / frame_count

        time_ms = int(
            progress * ROTATION_DURATION * 1000
        )

        frame = render_frame(
            progress,
            time_ms
        )

        frames.append(frame)

    return frames, duration

# ============================================================
# TIMELINE
# ============================================================

def animation_frame_count():
    """
    Number of exported frames.

    Rounded to avoid accumulating timing errors.
    """

    return max(
        1,
        round(ROTATION_DURATION * FPS)
    )


def frame_duration_ms():

    return round(
        1000 / FPS
    )


def frame_time_ms(frame_index):

    return frame_index * frame_duration_ms()


# ============================================================
# GENERATE ANIMATION
# ============================================================

def generate_animation():

    frames = []

    count = animation_frame_count()

    for frame in range(count):

        progress = frame / count

        time_ms = frame_time_ms(frame)

        image = render_frame(
            progress,
            time_ms
        )

        frames.append(image)

    return frames


# ============================================================
# GIF OPTIMIZATION
# ============================================================

def optimize_frame(frame):
    """
    Pillow exports GIFs much smaller if frames are palettized.

    Transparency is preserved.
    """

    alpha = frame.getchannel("A")

    palette = frame.convert(
        "P",
        palette=Image.ADAPTIVE,
        colors=255
    )

    mask = alpha.point(
        lambda p: 255 if p == 0 else 0
    )

    palette.paste(
        255,
        mask
    )

    palette.info["transparency"] = 255

    return palette


def optimize_frames(frames):

    return [
        optimize_frame(frame)
        for frame in frames
    ]


# ============================================================
# SAVE GIF
# ============================================================

def save_animation(frames):

    if not IMAGE_OUTPUT.lower().endswith(".gif"):
        output = IMAGE_OUTPUT + ".gif"
    else:
        output = IMAGE_OUTPUT

    duration = frame_duration_ms()

    optimized = optimize_frames(frames)

    optimized[0].save(
        output,
        save_all=True,
        append_images=optimized[1:],
        duration=duration,
        loop=0,
        disposal=2,
        optimize=False,
        transparency=255
    )

    print()

    print("Saved:", output)

    print("Frames :", len(frames))

    print("FPS :", FPS)

    print("Duration :", ROTATION_DURATION, "seconds")


# ============================================================
# ENTRY POINT
# ============================================================

def build_animation():

    print("Rendering...")

    frames = generate_animation()

    print("Encoding GIF...")

    save_animation(frames)

    print("Done.")

    return frames

# ============================================================
# GIF EXPORT
# ============================================================

def export_gif(frames):
    """
    Exports the generated frames as a looping GIF.
    """

    if len(frames) == 0:
        raise RuntimeError("No frames generated.")

    output = IMAGE_OUTPUT

    if not output.lower().endswith(".gif"):
        output += ".gif"

    duration = round(1000 / FPS)

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=duration,
        disposal=2,
        optimize=True,
    )

    print(f"Saved GIF: {output}")
    print(f"Frames: {len(frames)}")
    print(f"FPS: {FPS}")
    print(f"Duration: {ROTATION_DURATION:.2f}s")


# ============================================================
# VALIDATION
# ============================================================

def validate_configuration():

    if len(ROTATION) == 0:
        raise ValueError(
            "IMAGE_ROTATION must contain at least one image."
        )

    if ROTATION_DURATION <= 0:
        raise ValueError(
            "ROTATION_DURATION must be > 0."
        )

    if FPS <= 0:
        raise ValueError(
            "FPS must be > 0."
        )

    if SCALE_BACKGROUND <= 0:
        raise ValueError(
            "SCALE_BACKGROUND must be > 0."
        )

    if SCALE_MAIN <= 0:
        raise ValueError(
            "SCALE_MAIN must be > 0."
        )

    if SCALE_ROTATION <= 0:
        raise ValueError(
            "SCALE_ROTATION must be > 0."
        )

    if not (0 <= ROTATION_HEIGHT <= 1):
        raise ValueError(
            "ROTATION_HEIGHT must be between 0 and 1."
        )


# ============================================================
# MAIN
# ============================================================

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