from base64 import b64decode, b64encode
from binascii import Error
from io import BytesIO
from typing import Annotated

from PIL import Image
from pydantic import AfterValidator, StringConstraints

MAX_BYTES = 512 * 1024
MAX_SIDE = 1200
PREFIXES = {"data:image/jpeg;base64": "JPEG", "data:image/png;base64": "PNG", "data:image/webp;base64": "WEBP"}


def validate_image(value: str) -> str:
    prefix, separator, data = value.partition(",")
    expected = PREFIXES.get(prefix)
    if not separator or not expected:
        raise ValueError("Attach a JPEG, PNG, or WebP image.")
    try:
        raw = b64decode(data, validate=True)
        if len(raw) > MAX_BYTES:
            raise ValueError("The attachment must be at most 512 KB.")
        with Image.open(BytesIO(raw), formats=[expected]) as image:
            if max(image.size) > MAX_SIDE or getattr(image, "n_frames", 1) != 1:
                raise ValueError("Use a still image no larger than 1200 pixels per side.")
            pixels = image.convert("RGBA")
            pixels.info.clear()
            clean = BytesIO()
            pixels.save(clean, format="WEBP", quality=76)
    except (Error, OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise ValueError("The attachment could not be read as an image.") from error
    if clean.tell() > MAX_BYTES:
        raise ValueError("The processed attachment must be at most 512 KB.")
    return "data:image/webp;base64," + b64encode(clean.getvalue()).decode("ascii")


PostImage = Annotated[str, StringConstraints(max_length=4 * ((MAX_BYTES + 2) // 3) + 24), AfterValidator(validate_image)]
