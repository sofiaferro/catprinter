import cv2
from math import ceil
import numpy as np


def floyd_steinberg_dither(img):
    '''Applies the Floyd-Steinberf dithering to img, in place.
    img is expected to be a 8-bit grayscale image.

    Algorithm borrowed from wikipedia.org/wiki/Floyd%E2%80%93Steinberg_dithering.
    '''
    h, w = img.shape

    def adjust_pixel(y, x, delta):
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        img[y][x] = min(255, max(0, img[y][x] + delta))

    for y in range(h):
        for x in range(w):
            new_val = 255 if img[y][x] > 127 else 0
            err = img[y][x] - new_val
            img[y][x] = new_val
            adjust_pixel(y, x + 1, err * 7/16)
            adjust_pixel(y + 1, x - 1, err * 3/16)
            adjust_pixel(y + 1, x, err * 5/16)
            adjust_pixel(y + 1, x + 1, err * 1/16)
    return img


def halftone_dither(img):
    '''Applies Haltone dithering using different sized circles

    Algorithm is borrowed from https://github.com/GravO8/halftone
    '''

    def square_avg_value(square):
        '''
        Calculates the average grayscale value of the pixels in a square of the
        original image
        Argument:
            square: List of N lists, each with N integers whose value is between 0
            and 255
        '''
        sum = 0
        n = 0
        for row in square:
            for pixel in row:
                sum += pixel
                n += 1
        return sum/n

    side = 4
    jump = 4  # Todo: make this configurable
    alpha = 3
    height, width = img.shape

    if not jump:
        jump = ceil(min(height, height)*0.007)
    assert jump > 0, "jump must be greater than 0"

    height_output, width_output = side*ceil(height/jump), side*ceil(width/jump)
    canvas = np.zeros((height_output, width_output), np.uint8)
    output_square = np.zeros((side, side), np.uint8)
    x_output, y_output = 0, 0
    for y in range(0, height, jump):
        for x in range(0, width, jump):
            output_square[:] = 255
            intensity = 1 - square_avg_value(img[y:y+jump, x:x+jump])/255
            radius = int(alpha*intensity*side/2)
            if radius > 0:
                # draw a circle
                cv2.circle(
                    output_square,
                    center=(side//2, side//2),
                    radius=radius,
                    color=(0, 0, 0),
                    thickness=-1,
                    lineType=cv2.FILLED
                )
            # place the square on the canvas
            canvas[y_output:y_output+side,
                   x_output:x_output+side] = output_square
            x_output += side
        y_output += side
        x_output = 0
    return canvas


def read_img(
        filename,
        print_width,
        logger,
        img_binarization_algo,
        show_preview):
    im = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
    height = im.shape[0]
    width = im.shape[1]
    factor = print_width / width
    resized = cv2.resize(
        im,
        (
            int(width * factor),
            int(height * factor)
        ),
        interpolation=cv2.INTER_AREA)

    if img_binarization_algo.startswith('f'):
        logger.info('⏳ Applying Floyd-Steinberg dithering to image...')
        resized = floyd_steinberg_dither(resized)
        logger.info('✅ Done.')
        resized = resized > 127
    elif img_binarization_algo.startswith('h'):
        logger.info('⏳ Applying halftone dithering to image...')
        resized = halftone_dither(resized)
        logger.info('✅ Done.')
        resized = resized > 127
    elif img_binarization_algo.startswith('m'):
        resized = resized > resized.mean()
    elif img_binarization_algo.startswith('n'):
        if width == print_width:
            resized = im > 127
        else:
            logger.error(
            f'🛑 Wrong width of {width} px. An image with a width of {print_width} px is required for "none" binarization')
            raise RuntimeError(
            f'Wrong width of {width} px. An image with a width of {print_width} px is required for "none" binarization')

    else:
        logger.error(
            f'🛑 Unknown image binarization algorithm: {img_binarization_algo}')
        raise RuntimeError(
            f'unknown image binarization algorithm: {img_binarization_algo}')

    if show_preview:
        # Convert from our boolean representation to float.
        preview_img = resized.astype(float)
        cv2.imshow('Preview', preview_img)
        logger.info('ℹ️  Displaying preview.')
        # Calling waitKey(1) tells OpenCV to process its GUI events and actually display our image.
        cv2.waitKey(1)
        if input('🤔 Go ahead with print? [Y/n]? ').lower() == 'n':
            logger.info('🛑 Aborted print.')
            return None

    # Invert the image before returning it.
    return ~resized
