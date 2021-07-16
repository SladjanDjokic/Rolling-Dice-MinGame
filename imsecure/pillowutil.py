import argparse
from PIL import Image
from math import sqrt
import os

def sort_color_code(colortuple): # RGB, 3 byte hex
    return get_colorcode(colortuple)

def sort_color_count(colortuple):   # to sort on count of colors
    return colortuple[0]

def get_colorcode(colortuple):
    return (colortuple[0] << 16) + (colortuple[1] << 8) + colortuple[2]

def get_colortuple(colorcode):
    return ((colorcode >> 16, (colorcode & 0xffff) >> 8, colorcode & 0xff))

def pixel_from_index(nx, size):
    return int(nx/size[1]), nx%size[1]

def index_from_pixel(pixel, size):
    return pixel[0]*size[1] + pixel[1]


def color_from_index(nx, size):
    per_row= size[1] * 3
    row = int(nx/per_row)
    column = nx%per_row
    color = column%3
    column = int(column/3)
    return row, column, color

def image_uniquefile(imagefile, target="", verbose=False):
    im = Image.open(imagefile)
    imuniq = image_unique(im, verbose)
    if target == "":
        target = f'{os.path.splitext(tocheck)[0]}_uniq.jpg'

    imuniq.save(target)


def image_unique(im, verbose=False):
    pixels = im.load()
    size = im.size
    count = size[0]*size[1]

    # look for unique pixels, save them in list, original order
    unique = []
    map ={}
    for nx in range(count):
        row, column = pixel_from_index(nx, size)
        pixel = pixels[row, column]
        colorcode = get_colorcode(pixel)
        if colorcode not in map:
            map[colorcode] = nx
            unique.append(pixel)

    # figure out what size image, approximately square we need to create
    unique_count = len(unique)
    rows = sqrt(unique_count)
    columns = rows = int(rows)
    calc_size = rows*columns
    while calc_size < unique_count:
        columns += 1
        calc_size = rows * columns

    if verbose:
        print(f'unique {unique_count}, original {count} compression {(1 - unique_count/count)*100:0.3}%')
        print(f' rows {rows} columns {columns} calculated size {calc_size}')

    #create new PIL object, put in unique pixels and return it
    imuniq = Image.new('RGB', (rows, columns), color = (255, 255, 255))
    pixels = imuniq.load()
    for nx in range(unique_count):
        pixels[pixel_from_index(nx, (rows, columns))] = unique[nx]

    return imuniq

def image_extract_from_list(im, pixel_list, rows=0, savefile="", verbose=False):

    #this is from the source image
    pixels = im.load()
    size = im.size
    count = size[0]*size[1]

    pixel_count = len(pixel_list)
    if rows > 0:
        columns = int(pixel_count/rows)
        if pixel_count % rows:
            columns += 1
        print(f'extract: rows {rows}  columns {columns}')
    else:   # make a square-ish image
        rows = sqrt(pixel_count)
        columns = rows = int(rows)
        calc_size = rows*columns
        while calc_size < pixel_count:
            columns += 1
            calc_size = rows * columns

    #create new PIL object, put in unique pixels and return it
    imnew = Image.new('RGB', (columns, rows), color = (255, 255, 255))
    pixels = imnew.load()
    for nx in range(pixel_count):
        pixels[pixel_from_index(nx, (columns, rows))] = pixel_list[nx]

    if savefile != "":
        if verbose:
            print(f'saved {savefile}')

        imnew.save(savefile)

    return imnew

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='compress png or jpg to unique pixels')
    parser.add_argument('files', nargs='+', help="jpg/png files you wish to harvest")

    args = parser.parse_args()

    print(f'{args}')
    print(f'checking files {args.files}')
    for tocheck in args.files:
        image_uniquefile(tocheck, target="", verbose=False)
