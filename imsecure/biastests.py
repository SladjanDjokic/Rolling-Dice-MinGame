#!/usr/bin/env python3

import argparse
import os
from imsecure.entropy import eta

def countSetBits(num):

     # convert given number into binary
     # output will be like bin(11)=0b1101
     binary = bin(num)

     # now separate out all 1's from binary string
     # we need to skip starting two characters
     # of binary string i.e; 0b
     setBits = [ones for ones in binary[2:] if ones=='1']
     return len(setBits)
'''
we are looking for how many ones there are versus zeroes in a pixel
for an ideal random data, we are hoping to get very close to even
'''
def rgb_bias(pixel, eight_bit):
    red = countSetBits(pixel[1][0])
    green = countSetBits(pixel[1][1])
    blue = countSetBits(pixel[1][2])
    ones = red + green + blue
    if eight_bit:
        bias = 12 - ones
    else:
        bias = 24 - ones
    return bias

def check_file_data(im, filename, keysize, color_count, data_ratio, color_ratio, \
                    min_ratio, verbose, pixels_needed, pixelsize):
    error = ""
    min_color_ratio = min_ratio/4
    if data_ratio < min_ratio:
        error += f"key to pixels ratio too small {data_ratio:0.1f} {pixels_needed} {pixelsize}, "
    if color_ratio < min_color_ratio:
        error += f"key to unique color ratio too small got-{color_ratio:0.1f} '\
            ' min-{min_color_ratio:0.1f}  pixels got-{pixels_needed} {pixelsize}, "

    good = True if error == "" else False
    if verbose:
        print(f'Data test:         {"Pass" if good else "Fail"} - {filename} ' \
              f'pixels: {im.size[0]*im.size[1]}, {im.size[1]}x{im.size[0]}, colors {color_count}')
        print(f'                      keysize {keysize}, pixel ratio {data_ratio} ' \
              f'min {min_ratio}, color ratio: {color_ratio:.1f}, min {min_color_ratio:.1f}')

    return good, error

def check_entropy(key, keysize, verbose):
    entropy = eta(key)
    error = ""
    if keysize >= 512 and entropy < 4.5:
        error += f"entropy {entropy:.2f} for keysize {keysize} should be above 4.5" + ", "
    if keysize >= 2048 and entropy < 7:
        error += f"entropy {entropy:.2f} for keysize {keysize} should be above 7" + ", "
    good = True if error == "" else False
    if (verbose):
        print(f'Entropy test:      {"Pass" if good else "Fail"} {keysize} bits - {entropy:.2f} ')
    return good, entropy, error


def check_odd_bias(data, verbose = False):
    odd = 0
    even = 0
    all = len(data)
    bitcount = all * 8
    if all == 0:
        return 0, 0, 0
    # by byte
    for val in data:
        #by bit
        for _ in range(8):
            if val & 1:
                odd += 1
            else:
                even += 1
            val >>= 1

    odd_bias = odd / bitcount
    good = True if abs(odd_bias - 0.5) < 0.125 else False
    if (verbose):
        print(f'Bias test:         {"Pass" if good else "Fail"} {bitcount} ' \
              f'bits - {odd} odd, even {even} bias = {odd_bias: .3f} - 0.5 is neutral, +-0.125 ok')

    return  good, odd_bias, all

def check_odd_even_run(data, verbose = False):
    odd = 0
    even = 0
    long_odd = 0
    long_even = 0
    last = None
    same = 0
    long_same = 0

    all = len(data)
    bitcount = all * 8

    if all == 0:
        return 0, 0, 0, 0
    for val in data:
        #print(f'val is {val:02x}')
        for _ in range(8):
            bit = val & 1
            #print(f'val is {val:02x}  bit is {bit}')
            val >>= 1
            if bit == last:
                same += 1
                if same > long_same:
                    long_same = same
            else:
                same = 0
            last = bit

            if bit == 1:
                odd += 1
                even = 0
                if odd > long_odd:
                    long_odd = odd

            else:
                even += 1
                odd = 0
                if even > long_even:
                    long_even = even


    good = False if long_even > 15 else True
    if good:
        good = False if long_odd > 15 else True
    if (verbose):
        print(f'Long Run test:     {"Pass" if good else "Fail"} {bitcount} ' \
              f'bits - longest odd run: {long_odd}, longest even run: {long_even}, limit 15 ')

    return  good, long_even, long_odd, all

def check_repeats(data, repeat_range = 1, verbose = 0):
    lastfew = []
    repeats = 0
    last_repeat = 0
    for idx, val in enumerate(data):
        if len(lastfew) > repeat_range:
            lastfew.pop(0)
        if val in lastfew:
            repeats += 1
            if verbose > 1:
                print(f'index {idx:5} val {val:3} is in {lastfew}, since last {idx - last_repeat}')
            last_repeat = idx
        lastfew.append(val)

    rate = repeats/len(data) if len(data) else 0
    if verbose:
        print(f'{len(data)} elements {repeats} repeats, rate {rate:0.3} ' \
              f'check repeats within {repeat_range}')
    return repeats, rate, len(data)

def distro(lookup, verbose=0):
    distro_map = {}
    bucket_map = {}
    excess_map = {}
    biggest = 0
    excess = max(int(len(lookup)*0.05), 3)
    bad_one = 0
    for entry in lookup:
        if entry in distro_map:
            distro_map[entry] += 1
        else:
            distro_map[entry] = 1
        if distro_map[entry] > excess:
            excess_map[entry] = distro_map[entry]
        if distro_map[entry] > biggest:
            biggest = distro_map[entry]
            bad_one = entry


        bucket = entry & 0xf0  #divide this into 8 buckets
        if bucket in bucket_map:
            bucket_map[bucket] += 1
        else:
            bucket_map[bucket] = 1


    repeats = 0
    missing = 0
    unique = 0
    good = True if len(excess_map) == 0 else False
    if verbose:
        print(f'Distribution test: {"Pass" if good else "Fail"} {len(lookup)} ' \
              f'bytes - most was {biggest} for {bad_one:02x}, limit is {excess}')
        news = "range      "
        for ix in range(16):
            news += f'   _{ix:01x}'
        print(news)
        for ixrow in range(16):
            ix = ixrow * 16
            news = f'0x{ix:02x}-0x{ix+0xf:02x}:  '
            for ixcol in range(16):
                check = ix + ixcol
                if check in distro_map:
                    val = distro_map[check]
                    unique += 1
                    if val > 1:
                        repeats += val - 1
                else:
                    val = 0
                    missing += 1
                news += f'{val:4} '
            print(news)

        #look at what we have in buckets,
        print("\n")
        header = 'in range:     '
        news   = 'count       '
        for ix in range(0, 0x100, 0x10):
            val = bucket_map[ix] if ix in bucket_map else 0
            header += f'{ix:02x}   '
            news   += f'{val:4} '
        print(header)
        print(news)

    return good, biggest, [(k, v) for k, v in excess_map.items()]

def save_to_bin(data, basename, type):
    path = f'{os.path.splitext(basename)[0]}{type}.bin'
    print(f'target file: {path}')
    newfile=open(path,'wb')
    newfile.write(bytes(data))
    newfile.close()
    return path




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='bias tests')
    parser.add_argument('files', nargs='+', help="jpg/png files you wish to check")

    parser.add_argument('-m', default='1',
                    dest='mode', type=int,
                    help='only color low bits=1, colors=2, stuff=3, products=4')

    parser.add_argument('-p', default='1',
                    dest='pin', type=int,
                    help='pin used as skip value')

    parser.add_argument('-r', default='1',
                    dest='repeats', type=int,
                    help='repeated value within range')

    args = parser.parse_args()
    tocheck = args.files
    print(f' mode {args.mode}, pin {args.pin}, rpeat within {args.repeats}')
    print(args.files)

    check_odd_even_run([1,2,1,2,2,2,2], verbose = True)
