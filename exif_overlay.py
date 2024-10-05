import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageOps
import exifread
import os
import platform
import glob

FONT_PATH = "fonts/NunitoSans-VariableFont_YTLC,opsz,wdth,wght.ttf"


def extract_exif(image_path):
    with open(image_path, 'rb') as f:
        tags = exifread.process_file(f)

    return {
        "f_stop": tags.get('EXIF FNumber', '-'),
        "shutter_speed": tags.get('EXIF ExposureTime', '-'),
        "iso": tags.get('EXIF ISOSpeedRatings', '-'),
        "focal_length": tags.get('EXIF FocalLength', '-'),
        "focal_length_in_35mm_film": tags.get('EXIF FocalLengthIn35mmFilm', '-'),
        "flash": tags.get('EXIF Flash', '-'),
        "date_time": tags.get('EXIF DateTimeOriginal', '-'),
        "camera_make": tags.get('Image Make', '-'),
        "camera_model": tags.get('Image Model', '-'),
        "lens_make": tags.get('EXIF LensMake', '-'),
        "lens_model": tags.get('EXIF LensModel', '-'),
    }


def get_user_full_name():
    try:
        if platform.system() == "Windows":
            import ctypes
            # Use Windows API to get the full name of the user
            GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
            NameDisplay = 3
            size = ctypes.pointer(ctypes.c_ulong(0))
            GetUserNameEx(NameDisplay, None, size)
            name_buffer = ctypes.create_unicode_buffer(size.contents.value)
            if GetUserNameEx(NameDisplay, name_buffer, size):
                return name_buffer.value
        else:
            import pwd
            # Use pwd module to get the full name on Unix-like systems
            full_name = pwd.getpwuid(os.getuid()).pw_gecos.split(',')[0]
            return full_name
    except:
        return os.getlogin()  # Fallback to the login name if the full name is not available


def interpret_flash_exif(flash_value):
    flash_mode = (flash_value & 0b00011000) >> 3
    flash_fired = flash_value & 0b00000001

    if flash_mode in [0b00, 0b10]:
        return "Flash off"
    elif flash_mode == 0b01:
        mode_status = "on"
    elif flash_mode == 0b11:
        mode_status = "auto"
    else:
        return "Flash unknown"

    if flash_fired == 1:
        return f"Flash {mode_status}, fired"
    else:
        return f"Flash {mode_status}, did not fire"


def format_exif_text(exif_data, args):
    # Format f-stop
    f_stop_text = f"{exif_data['f_stop']}"
    if isinstance(exif_data['f_stop'], str) and f_stop_text != '-' and f_stop_text is not any(x in f_stop_text for x in ['f', 'F', 'ƒ']):
        f_stop_text = f"ƒ/{f_stop_text}"
    elif isinstance(exif_data['f_stop'], exifread.classes.IfdTag):
        f_stop_value = exif_data['f_stop'].values[0].num / exif_data['f_stop'].values[0].den
        f_stop_text = f"ƒ/{'{:.2f}'.format(f_stop_value).rstrip('0').rstrip('.')}"

    # Format shutter speed
    shutter_speed_text = f"{exif_data['shutter_speed']}"
    if shutter_speed_text != '-':
        shutter_speed_text = f"{shutter_speed_text} sec"
    if '/' in shutter_speed_text and not shutter_speed_text.startswith('1/'):
        shutter_speed_text = f"1/{round(exif_data['shutter_speed'].values[0].den / exif_data['shutter_speed'].values[0].num)} sec"

    # Format ISO
    iso_text = f"{exif_data['iso']}"
    if iso_text != '-':
        iso_text = f"ISO {iso_text}"

    # Format focal length
    focal_length_text = f"{exif_data['focal_length']}"
    if isinstance(exif_data['focal_length'], str) and focal_length_text != '-' and 'mm' not in focal_length_text:
        focal_length_text = f"{focal_length_text}mm"
    elif isinstance(exif_data['focal_length'], exifread.classes.IfdTag):
        focal_length_value = exif_data['focal_length'].values[0].num / exif_data['focal_length'].values[0].den
        focal_length_text = f"{'{:.2f}'.format(focal_length_value).rstrip('0').rstrip('.')}mm"
        if exif_data['focal_length_in_35mm_film'] != '-':
            focal_length_text = f"{focal_length_text} ({exif_data['focal_length_in_35mm_film']}mm FF)"

    # Format flash
    flash_text = f"{exif_data['flash']}"
    if isinstance(exif_data['flash'], exifread.classes.IfdTag):
        flash_text = interpret_flash_exif(exif_data['flash'].values[0])

    # Format date and time
    date_time_text = f"{exif_data['date_time']}"
    if isinstance(exif_data['date_time'], exifread.classes.IfdTag):
        date_time_text = datetime.strptime(date_time_text, '%Y:%m:%d %H:%M:%S').strftime('%d %B %Y, %I:%M %p').lstrip('0').replace(', 0', ', ')

    # Format camera
    camera_text = f"{exif_data['camera_model']}"
    if str(exif_data['camera_make']).lower() not in camera_text.lower() and exif_data['camera_make'] != '-':
        camera_text = f"{exif_data['camera_make']} {camera_text}"

    # Format lens
    lens_text = f"{exif_data['lens_model']}"
    if str(exif_data['lens_make']).lower() not in lens_text.lower() and exif_data['lens_make'] != '-':
        lens_text = f"{exif_data['lens_make']} {lens_text}"

    # Format copyright
    copy_right = f"{get_user_full_name()}"

    # Override EXIF data with the command-line arguments if provided
    if args.f_stop:
        f_stop_text = args.f_stop
    if args.shutter_speed:
        shutter_speed_text = args.shutter_speed
    if args.iso is not None:
        iso_text = args.iso
    if args.focal_length:
        focal_length_text = args.focal_length
    if args.flash:
        flash_text = args.flash
    if args.date_time:
        date_time_text = args.date_time
    if args.camera:
        camera_text = args.camera
    if args.lens:
        lens_text = args.lens
    if args.author:
        copy_right = args.author

    top_section_text = ""
    if not args.no_f_stop:
        top_section_text += f"{f_stop_text}\n"
    if not args.no_shutter_speed:
        top_section_text += f"{shutter_speed_text}\n"
    if not args.no_iso:
        top_section_text += f"{iso_text}\n"
    if not args.no_focal_length:
        top_section_text += f"{focal_length_text}\n"
    if not args.no_flash:
        top_section_text += f"{flash_text}\n"
    top_section_text = top_section_text.rstrip('\n')

    bottom_section_text = ""
    if not args.no_date_time:
        bottom_section_text += f"{date_time_text}\n"
    if not args.no_camera:
        bottom_section_text += f"{camera_text}\n"
    if not args.no_lens:
        bottom_section_text += f"{lens_text}\n"
    if not args.no_copyright:
        bottom_section_text += f"{copy_right}\n"
    bottom_section_text = bottom_section_text.rstrip('\n')

    return top_section_text, bottom_section_text


def overlay_exif(image_path, output_path, exif_data, args):
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)

    # Darken and blur the image
    image = ImageEnhance.Brightness(image).enhance(0.7)
    image = image.filter(ImageFilter.GaussianBlur(radius=min(image.size) * 0.01))

    top_section_text, bottom_section_text = format_exif_text(exif_data, args)

    font_size = int(min(image.size) * 0.08)
    font = ImageFont.truetype(FONT_PATH, font_size)
    font.set_variation_by_name('Light')
    line_spacing = int(font_size * 0.3)

    icons = {
        "f_stop": Image.open("icons/aperture.png"),
        "shutter_speed": Image.open("icons/shutter_speed.png"),
        "iso": Image.open("icons/iso.png"),
        "focal_length": Image.open("icons/focal_length.png"),
        "flash_off": Image.open("icons/flash_off.png"),
        "flash_on": Image.open("icons/flash_on.png"),
        "flash_auto": Image.open("icons/flash_auto.png"),
        "date_time": Image.open("icons/date_time.png"),
        "camera": Image.open("icons/camera.png"),
        "lens": Image.open("icons/lens.png"),
        "copyright": Image.open("icons/copyright.png"),
    }

    exif_overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(exif_overlay)

    image_width, image_height = image.size
    margin_x = int(image_width * 0.05)

    top_text_height = (font_size + line_spacing) * len(top_section_text.split('\n'))

    bottom_font_size = int(font_size * 0.6)
    bottom_font = ImageFont.truetype(FONT_PATH, bottom_font_size)
    bottom_font.set_variation_by_name('Light')
    bottom_line_spacing = int(bottom_font_size * 0.5)
    bottom_text_height = (bottom_font_size + bottom_line_spacing) * len(bottom_section_text.split('\n'))

    separator_thickness = int(font_size * 0.02)
    separator_padding_height = int(line_spacing * 1.5)
    total_text_height = top_text_height + bottom_text_height + separator_thickness + 2 * separator_padding_height

    start_y = (image_height - total_text_height) // 2

    current_y = start_y

    #
    # Draw the top section text
    #

    icon_keys = []

    if not args.no_f_stop:
        icon_keys.append('f_stop')
    if not args.no_shutter_speed:
        icon_keys.append('shutter_speed')
    if not args.no_iso:
        icon_keys.append('iso')
    if not args.no_focal_length:
        icon_keys.append('focal_length')
    if not args.no_flash:
        icon_keys.append('flash')

    for line, icon_key in zip(top_section_text.split('\n'), icon_keys):
        # Special handling for the flash icon
        if icon_key == 'flash':
            if line.startswith('Flash auto'):
                icon_key = 'flash_auto'
            elif line.startswith('Flash off'):
                icon_key = 'flash_off'
            else:
                icon_key = 'flash_on'

        # Draw icon next to text on the EXIF overlay
        icon_size = int(font_size * 0.8)
        icon = icons[icon_key].resize((icon_size, icon_size), Image.LANCZOS)
        r, g, b = Image.new('RGB', icon.size, 'white').split()
        icon = Image.merge('RGBA', (r, g, b, icon.split()[3])).resize((icon_size, icon_size), Image.LANCZOS)
        exif_overlay.paste(icon, (margin_x, current_y + (font_size + line_spacing - icon_size) // 2), icon)

        # Draw text on the EXIF overlay
        text_x = margin_x + icon_size + int(font_size * 0.5)
        draw_overlay.text((text_x, current_y), line, fill="white", font=font)
        current_y += font_size + line_spacing

    # Draw a separator between the top and bottom sections
    current_y += separator_padding_height
    draw_overlay.line([(margin_x, current_y), (image_width - margin_x, current_y)], fill=(255, 255, 255, 96), width=separator_thickness)
    current_y += separator_thickness + separator_padding_height

    #
    # Draw the bottom section text
    #

    bottom_icon_keys = []

    if not args.no_date_time:
        bottom_icon_keys.append('date_time')
    if not args.no_camera:
        bottom_icon_keys.append('camera')
    if not args.no_lens:
        bottom_icon_keys.append('lens')
    if not args.no_copyright:
        bottom_icon_keys.append('copyright')

    for line, icon_key in zip(bottom_section_text.split('\n'), bottom_icon_keys):
        # Draw icon next to text on the EXIF overlay
        bottom_icon_size = int(bottom_font_size * 0.8)
        icon = icons[icon_key].resize((bottom_icon_size, bottom_icon_size), Image.LANCZOS)
        r, g, b = Image.new('RGB', icon.size, 'white').split()
        icon = Image.merge('RGBA', (r, g, b, icon.split()[3])).resize((bottom_icon_size, bottom_icon_size), Image.LANCZOS)
        exif_overlay.paste(icon, (margin_x, current_y + (bottom_font_size + bottom_line_spacing - bottom_icon_size) // 2), icon)

        # Draw text on the EXIF overlay
        text_x = margin_x + bottom_icon_size + int(bottom_font_size * 0.7)
        draw_overlay.text((text_x, current_y), line, fill="white", font=bottom_font)
        current_y += bottom_font_size + bottom_line_spacing

    # Create a shadow by duplicating the EXIF overlay and converting to black
    shadow = exif_overlay.copy()
    r, g, b = Image.new('RGB', shadow.size, 'black').split()
    shadow = Image.merge('RGBA', (r, g, b, shadow.split()[3]))

    # Apply Gaussian blur to create the shadow effect
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=min(image.size) * 0.005))

    # Composite the shadow and the EXIF overlay on the original image
    image_with_shadow = image.convert("RGBA")
    image_with_shadow = Image.alpha_composite(image_with_shadow, shadow)
    image_with_shadow = Image.alpha_composite(image_with_shadow, exif_overlay)

    # Save the final image
    image_with_shadow = image_with_shadow.convert("RGB")
    image_with_shadow.save(output_path, quality=95)


def main():
    parser = argparse.ArgumentParser(description="Add EXIF data overlay to multiple images.")

    parser.add_argument("--f-stop", help='Override f-stop value (e.g., "ƒ/2.8")', default=None)
    parser.add_argument("--shutter-speed", help='Override shutter speed (e.g., "60 sec")', default=None)
    parser.add_argument("--iso", help='Override ISO value (e.g., "ISO 100")', default=None)
    parser.add_argument("--focal-length", help='Override focal length (e.g., "50mm")', default=None)
    parser.add_argument("--flash", help='Override flash status (e.g., "Flash auto, fired")', default=None)
    parser.add_argument("--date-time", help='Override date and time (e.g., "1 January 2006, 3:04 PM")', default=None)
    parser.add_argument("--camera", help='Override camera (e.g., "Sony a6000")', default=None)
    parser.add_argument("--lens", help='Override lens (e.g., "Pentax Super-Takumar 50mm f/1.4")', default=None)
    parser.add_argument("--author", help='Override author name (e.g., "John Doe")', default=None)

    parser.add_argument("--no-f-stop", action="store_true", help="Hide f-stop value")
    parser.add_argument("--no-shutter-speed", action="store_true", help="Hide shutter speed")
    parser.add_argument("--no-iso", action="store_true", help="Hide ISO value")
    parser.add_argument("--no-focal-length", action="store_true", help="Hide focal length")
    parser.add_argument("--no-flash", action="store_true", help="Hide flash status")
    parser.add_argument("--no-date-time", action="store_true", help="Hide date and time")
    parser.add_argument("--no-camera", action="store_true", help="Hide camera")
    parser.add_argument("--no-lens", action="store_true", help="Hide lens")
    parser.add_argument("--no-copyright", action="store_true", help="Hide copyright notice")

    parser.add_argument("--output-dir", help="Path to the output directory", default="images_with_exif_overlay")

    parser.add_argument("input_images", nargs='+', help="Path to the input image(s) (supports glob patterns like DSC*.jpg)")

    args = parser.parse_args()

    image_files = []
    for pattern in args.input_images:
        image_files.extend(glob.glob(pattern))

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    for image_path in image_files:
        exif_data = extract_exif(image_path)
        output_path = os.path.join(output_dir, os.path.basename(image_path))
        overlay_exif(image_path, output_path, exif_data, args)
        print(f"Image with EXIF overlay saved to {output_path}")


if __name__ == "__main__":
    main()
