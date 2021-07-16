#!/usr/bin/env python3
import argparse
from PIL import Image
import PIL.ImageOps as ImageOps
import io
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from imsecure.entropy import eta
from imsecure.biastests import check_odd_bias, check_odd_even_run, distro, \
 save_to_bin, check_entropy, check_file_data
import math
import os
import sys
from imsecure.pillowutil import image_unique, image_extract_from_list

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class ImageSecure:
    def __init__(self, filename="", pin="000000", factor="", keysize=256, mode="lowxor",
        ratio=1000, compress=False, ncount=3, verbose=0, frombytes=False, imagedata=None):
        self.valid = False
        self.keysize = keysize
        self.min_ratio = ratio
        self.compress = compress
        self.ncount = ncount
        self.factor = factor
        self.error = ""
        self.sanity = {}
        self.pixel_count = 0
        self.frombytes = frombytes


        self.verbose = int(verbose)
        self.key = []
        self.filename = ''

        self.set_mode(mode)
        self.set_pin(pin)
        if filename != "" or frombytes:
            self.load(filename, imagedata)


    @classmethod
    def modes(cls):
        return ['lowbit', 'lowxor','lowmerge', 'pixelxor',
            'product', 'colorcode', 'simplepixel', 'simplecolor']

    @classmethod
    def mode_invert_ok(cls, mode):
        if mode in ['lowbit', 'lowxor','lowmerge', 'product']:
            return False
        else:
            return True



    '''
    set_mode takes the mode requested and translates that into the parameters
    that are going to be used to harvest.  some modes go by pixel index, some
    by color index
    '''
    def set_mode(self, mode):
        if mode not in self.modes():
            raise ValueError("set_mode: {mode} not in {self.modes()}")

        self.mode = mode
        self.fetch_by_pixel = True
        self.invert_ok = self.mode_invert_ok(mode)
        self.pixels_needed = 0
        self.colors_needed = 0

        if mode == "lowbit":
            self.bits_per_pixel = 1
            self.colors_needed = self.keysize
            self.fetch_by_pixel = False
        elif mode in ["lowmerge","simplepixel", "product"]:
            self.bits_per_pixel = 8
            self.pixels_needed = int(self.keysize/self.bits_per_pixel)
            if self.keysize%self.bits_per_pixel:
                self.pixels_needed += 1
        elif mode == "colorcode":
            self.bits_per_pixel = 24
            self.pixels_needed = int(self.keysize/self.bits_per_pixel)
            if self.keysize%self.bits_per_pixel:
                self.pixels_needed += 1
        elif mode == "simplecolor":
            self.bits_per_pixel = 8
            self.colors_needed = int(self.keysize/self.bits_per_pixel)
        elif mode == 'pixelxor':
            self.bits_per_pixel = 8/self.ncount
            self.pixels_needed = int(self.keysize/self.bits_per_pixel)
            self.fetch_by_pixel = True
        elif mode == 'lowxor':
            self.bits_per_pixel = 1/self.ncount
            self.pixels_needed = self.keysize* self.ncount
            self.fetch_by_pixel = True
        else:
            raise ValueError(f"mode {mode} missing handler")

        if self.verbose:
            print(f'set_mode: pixels_needed {self.pixels_needed}  colors_needed {self.colors_needed}  ')
            print(f'keysize {self.keysize}   bits per pixel {self.bits_per_pixel:.2f}')

    def __repr__(self):
        return f'ImageSecure({self.filename}, {self.mode}, {self.key})'
    '''
    the pin is nominally 6 digits, but we choose to bring it in a a string.  we
    will actualy take letters and longer than 6 chars.  the pin digits are used
    for processing options, but the whole pin is used for a hash that guides scatter
    '''
    def set_pin(self, userpin):
        if len(userpin) < 6:
            err = f'PIN {userpin} must be at least 6 digits'
            raise ValueError(err)
        self.userpin = userpin
        self.pin_digits = []
        the_pin = userpin[-6:] # just last 6 digits in case longer
        for next in range(6):
            digit = int(the_pin[next]) & 0x0F
            if (digit) > 9:
                digit = 9
            self.pin_digits.append(digit)
        if self.verbose:
            print(f'userpin {self.userpin} digits {self.pin_digits}')

    '''
    load pulls in image file, performs any manipulation specified by the pin
    and loads the file, accessible via pixel array
    '''
    def load(self, filename, imagedata=None):
        if self.frombytes == False:
            self.filename = filename
            self.im = Image.open(self.filename)
        else:
            f = io.BytesIO(imagedata)
            self.filename = 'None'
            self.im = Image.open(f)

        self.pixels = self.im.load()
        if self.verbose> 2:
            print(f'hash from pixels, pre-rotate : {self.hash_image().hex()}')
        if self.compress:
            self.im = image_unique(self.im, self.verbose) # gets us a unique set of pixels
        self.rotateby, self.invert = self.set_orientation()

        """
        if self.rotateby:
            self.im = self.im.rotate(self.rotateby)
        if self.invert:
            self.im = ImageOps.invert(self.im)
        """

        #harvest attributes after manipulation
        self.size = self.im.size     #do after rotate, can change x,y
        self.rows = self.size[0]
        self.columns = self.size[1]
        self.color_per_row = (self.columns * 3)
        self.pixelsize = self.rows * self.columns
        self.colorsize = self.pixelsize * 3

        colors = self.im.getcolors(self.pixelsize)
        self.color_count = len(colors)
        self.color_ratio = self.pixelsize/self.color_count

        self.pixels = self.im.load()
        if self.verbose > 2:
            print(f'hash from pixels, post-rotate: {self.hash_image().hex()}')
        self.save_orientation()

    def hash_image(self):
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        for x in range(self.im.size[0]):
            row = []
            for y in range(self.im.size[1]):
                pixel = self.pixels[x,y]
                row.extend([pixel[0], pixel[1], pixel[2]])
            digest.update(bytes(row))
        return digest.finalize()



    def save_orientation(self):
        # save corner pixels and middle 2
        self.orient_list = [ (0,0),
                            (0,self.columns - 1),
                            (int(self.rows/2),int(self.columns/3)),
                            (int(self.rows/2),int(self.columns*2/3)),
                            (self.rows - 1,0),
                            (self.rows - 1,self.columns - 1)]

        #print(f"orient_list: {self.orient_list}")
        self.orient = []
        self.orient_text = ""    # use to salt hash with pixel data as well
        try:
            for addr in self.orient_list:
                self.orient.append(addr)
                print(f"addr: {addr}, text: {self.orient_text}")
                pixel = self.pixels[addr]
                self.orient_text = ''.join([self.orient_text, chr(pixel[0]), chr(pixel[1]), chr(pixel[2])])
        except Exception as inst:
            print(inst)          # __str__ allows args to be printed directly,response = {
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args

    '''
    process_pin takes the user's pin and sets up processing based on the digits.
    this hugely affects the harvesting of the key.
    orientation digit (5) is done before the file is processed, it affects
    the files characteristics, so it is not included in process_pin

    the other pin bits are here, they must be processed after load becase they
    are based on file dimensions.
    '''
    def process_pin(self):
        self.set_scramble()
        self.set_increment()
        self.set_horiz_start()
        self.set_vert_start()
        self.set_scatter()
        self.set_access_plan()
        if self.verbose:
            self.info()


    def scramble_digit(self): return self.pin_digits[0]
    def increment_digit(self): return self.pin_digits[1]
    def horiz_start_digit(self): return self.pin_digits[2]
    def vert_start_digit(self): return self.pin_digits[3]
    def scatter_digit(self): return self.pin_digits[4]
    def orient_digit(self): return self.pin_digits[5]

    def info(self):
        print(f'set_mode: {self.mode} ncount {self.ncount}')
        print(f'set_orientation - digit {self.orient_digit()}, rotateby {self.rotateby}, invert {self.invert}')
        print(f'set_scramble {self.scramble_digit()} index {self.scramble_index}')
        print(f'set_increment:{self.increment_digit()} adj: {self.incr}  size: {self.pixelsize}  bits per pixel:  {self.bits_per_pixel:.2f}')
        print(f'set_horiz_start - horizontal {self.columns} digit {self.horiz_start_digit()}, start {self.columns_start}')
        print(f'set_vert_start  - vertical {self.rows} digit {self.vert_start_digit()},  start {self.rows_start}')
        print(f'set_scatter {self.scatter_digit()}  digest: {self.scatter_digest.hex()}')
        print(f'set_access_plan - start pixel{self.next_pixel}  color {self.next_color} data ratio {self.data_ratio}')
        print(f'pixel {self.pixel_from_index(self.next_pixel)}  color {self.color_from_index(self.next_color)}')
        print(f'orient_text: {self.orient_text}')


    # this is where we start get pixels to drive scrambling the access pattern
    def set_scramble(self):
        self.scramble_index = int((self.pixelsize /17) * (self.scramble_digit() + 1))

    def set_orientation(self):
        if self.invert_ok:
            orientation = (
                (0, False),  (90, False),  (180, False), (270, False),
                (0, True),   (90, True),   (180, True),  (270, True),
                (45, False), (135, False), (225, False), (315, False),
                (45, True),  (135, True),  (225, True),  (315, True))
        else:
            orientation = (
                (0, False),  (90, False),  (180, False), (270, False),
                (0, False),  (90, False),  (180, False), (270, False),
                (0, False),  (90, False),  (180, False), (270, False),
                (0, False),  (90, False),  (180, False), (270, False),
                (0, False),  (90, False),  (180, False), (270, False),
                )

        rotateby, invert = orientation[self.orient_digit() & 0x0f]

        return rotateby, invert

    def set_increment(self):
        digit = self.increment_digit()
        #nominal, set up to sample equidistant whole image
        if self.pixels_needed > 0:
            self.incr_uniform = int(self.pixelsize/self.pixels_needed)
        else:
            self.incr_uniform = int(self.colorsize/self.colors_needed)
        '''
        we tweak inrement so its going to be off the exact increment, but still
        cover essentially the whole image.  if digit is 10, we go 10% faster
        '''
        self.incr = self.incr_uniform *(1 + (digit/100))
        self.incr = int(self.incr)
        if self.colors_needed and self.incr%3 == 0:
            self.incr += 1   # in case of colors, we do not want same color every time!
        return self.incr

    '''
    the vertical (row) and horizontal (column) start are taken from pin digits
    the pixel and column access methods logically flatten the pixel array, this
    calulates the index of the flattened array.  same if we access by color
    instead of pixel.
    '''
    def set_vert_start(self):
        self.rows_start = int(self.rows/(self.vert_start_digit() + 1))

    def set_horiz_start(self):
        self.columns_start = int(self.columns/(self.horiz_start_digit() + 1)) * self.horiz_start_digit()

    '''
    Here is the process to obfuscate how harvesting is done:
    1. build a list (indexes) of pixels or colors needed. equally spaced based on
    how many we need to harvest
    2. add jitter to index from a hash and user digit factor
    3. shuffle/scramble index so harvest in not mononic incresing across the image.
    shuffle itself is driven off colors in the image, so its is a type of
    linear feedback inspired by LFSR.
    '''
    def set_access_plan(self):
        # the user set where in the picture we start, 0-9, scaled,
        # horizontal an vertical.  equivalent for pixel and color access
        self.next_pixel = (self.rows_start * self.columns) + self.columns_start
        self.next_color = self.next_pixel * 3
        self.pixel_select = []
        self.color_select = []
        self.pixel_distro = {}

        if self.pixels_needed > 0:
            self.data_ratio = self.pixelsize/self.pixels_needed
            self.set_pixel_access()
            if self.verbose > 1:
                print(f'pixel select: before:\n{self.pixel_select}')

            self.scramble(self.pixel_select)
            if self.verbose > 1:
                print(f'pixel select: after \n{self.pixel_select}')

        if self.colors_needed > 0:
            self.data_ratio = self.colorsize/self.colors_needed
            self.set_color_access()
            if self.verbose > 1:
                print(f'color select: before\n{self.color_select}')
            self.scramble(self.color_select)
            if self.verbose > 1:
                print(f'color select: after\n{self.color_select}')
            if self.data_ratio < self.min_ratio:
                print(f"key to pixels ratio too small got-{self.data_ratio:0.3} min-{self.min_ratio}'\
                '  colors: min-{self.colors_needed} got-{self.colorsize}")


        # we now switch use to a counter mode to pull out of list
        self.next_color = 0
        self.next_pixel = 0

    '''
    build list of all colors (row, column, color) or pixels (row, column) that
    we must access to harvest key of desired size.  the mode will determib=ne
    if we harvest via pixel or discrete color.  The scatter is done to make the
    access jittery and unpredictable, based on user input.

    step 1: scatter the access location. scatter is done via a SHA2 of userpin
    setp 2: bump base location via increment

    both steps must calculate wrap
    '''
    def set_pixel_access(self):
        for _ in range(self.pixels_needed):

            # the scatter affect only the current one
            next_pixel = self.pixel_wrap(self.next_pixel + self.next_scatter())
            self.pixel_select.append(next_pixel)

            # we calculate the next base one without scatter
            self.next_pixel = self.pixel_wrap(self.next_pixel + self.incr)

    def set_color_access(self):
        for _ in range(self.colors_needed):

            # the scatter affect only the current one
            next_color = self.color_wrap(self.next_color + self.next_scatter())
            self.color_select.append(next_color)
            # we calculate the next base one without scatter
            self.next_color = self.color_wrap(self.next_color + self.incr)


    '''
    scatter is a radomizing process for accessing pixels/colors.  The userpin
    string and orientment pixels are hashed, so both those pixels and the pin
    materially affect the access plan thru the hash.

    The PIN is nominally 6 digits ***however***, as long as the string is at
    least 6 characters, we don't care.  If they give us a 1000 character string
    it gets hashed, and the scatter pattern is different.  So, "123456", "0123456"
    and "00123456" hash differently

    scatter can be viewed as jitter or vibration.  the nominal pixels/colors
    harvested have a uniform distribution.  The jitter leaves the distribution
    pretty uniform but makes sure you can't guess exactly which pixels are touched
    '''
    def set_scatter(self):
        tohash = self.userpin + self.orient_text + self.factor

        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(bytes(tohash, 'utf-8'))
        self.scatter_digest = digest.finalize()
        self.scatter_mod = self.scatter_digit() + 1 # we can't use 0, its a multiplier
        self.scatter_index = 0


    '''
    this is a modified knuth shuffle, randrange is implemented using image data
    it will shuffle any interable, but the intent is to shuffle the pixel or
    color access plan, so if there image has a gradual transition from sky above and
    rocks below, the order we access is helter-skelter
    '''
    def scramble(self, x):
        for i in range(len(x)-1, 0, -1):
            j = self.randrange(i + 1)
            x[i], x[j] = x[j], x[i]

    '''
    method works like randrange from python lib, but we use pixels in the
    image to fetch the random value.  2 reasons.  1, this has to give the same
    answer everytime, the lib function implementaion may vary.  2.  this is a
    way to feedback entropy of the image into the output.
    we return first hit between 0 and up to stop
    '''
    def randrange(self, stop):
        for _ in range(30): #avoid dupe pixels up to a point
            pixel = self.pixels[self.pixel_from_index(self.scramble_index)]
            self.scramble_index = self.pixel_wrap(self.scramble_index + self.incr) #bump scramble index
            if pixel not in self.rand_pixels:
                self.rand_pixels.append(pixel)
                break

        cp = self.colorproduct(pixel)   #take pixel, generate a number out of it
        rando = cp % stop
        if self.verbose > 2:
            print(f'   stop {stop:04x}  rando {rando:03x} pixel{pixel} cp:{cp:06x} {self.scramble_index}')

        return rando

    # a helper function to give a pixel as a colorcode, rotating what color is extractred first
    def colorcode(self, pixel, rotate=0):
        value = pixel[rotate%3]
        value <<= 8
        value |= pixel[(rotate +1)%3]
        value <<= 8
        value |= pixel[(rotate +2)%3]
        return value

    # a helper to multiply RGB by each other.  avoing zero so don't get degenrate results
    def colorproduct(self, pixel):
        return max(1, pixel[0]) * max(1, pixel[1]) * max(1, pixel[2])

    '''
    The scatter digest has a hash of the pin.  we are going to loop thru each byte
    of the hash, multiply it by the user pin digit and call it the scatter index.
    It will be added to the normal next fetch location.  In this way, we randomize
    where we are picking up data out of the pixel array
    '''
    def next_scatter(self):
        value = self.scatter_digest[self.scatter_index ] * self.scatter_mod
        self.scatter_index += 1
        if self.scatter_index >= len(self.scatter_digest):
            self.scatter_index = 0
        return value

    '''
    we logically flatten the 2 dimensioanl row, column of pixels into a one
    dimensional array so we can address a pixel by a single index.  These are
    helpers to do that

    some modes access by pixel and separately access color, they use this method
    '''
    def pixel_from_color(self, color):
        row, column, color = self.color_from_index(color)
        return self.pixels[row, column]

    def get_pixels_used(self):
        if self.colors_needed:
            return [self.pixel_from_color(color) for color in self.color_select]
        else:
            return self.pixel_select

    def get_next_pixel(self):
        next_pixel = self.pixel_select[self.next_pixel]
        if next_pixel not in self.pixel_distro:
            self.pixel_distro[next_pixel] = 1
        else:
            self.pixel_distro[next_pixel] += 1

        row, column = self.pixel_from_index(next_pixel)
        pixel = self.pixels[row, column]

        if self.verbose > 3:
            print(f'next pixel is {self.next_pixel}  mapped {self.pixel_select[self.next_pixel]}')

        self.next_pixel += 1
        return pixel

    def get_next_color(self):
        next_color = self.color_select[self.next_color]
        row, column, color = self.color_from_index(next_color)
        pixel = self.pixels[row, column]
        if pixel not in self.pixel_distro:
            self.pixel_distro[pixel] = 1
        else:
            self.pixel_distro[pixel] += 1

        colorbyte = pixel[color]
        if self.verbose > 3:
            print(f'pixel: {pixel}  color: {color} colorbyte {colorbyte}')
            print(f'next color is {self.next_color}  mapped {self.color_select[self.next_color]}')

        self.next_color += 1

        return colorbyte
    '''
    we logically flatten the 3 dimensional row, column, color of pixels into a one
    dimensional array so we can address a color by a single index.  We appy a
    scatter factor to each fetch which makes the pixel unpredictable to an
    outside observer.  the scatter factor may create an index beyond the pixel
    range, we simply wrap around.

    some modes access by color without regard to pixel alignment, they use this method
    '''

    def pixel_from_index(self, nx):
        if self.rotateby == 90:
            column = int(nx/self.rows)
            row = nx%self.rows
        elif self.rotateby == 180:
            nx = self.pixel_count - nx -1
            row = int(nx/self.columns)
            column = nx%self.columns
            pass
        elif self.rotateby == 270:
            nx = self.pixel_count - nx -1
            column = int(nx/self.rows)
            row = nx%self.rows
        else:
            row = int(nx/self.columns)
            column = nx%self.columns

        return row, column

    def color_from_index(self, nx):
        row = int(nx/self.color_per_row)
        colorsize = nx%self.color_per_row
        column = int(colorsize/3)
        color = colorsize%3
        return row, column, color

    #safe methods used to increment and wrap if needed
    def pixel_wrap(self, next):
        if next >= self.pixelsize:
            return next - self.pixelsize
        else:
            return next

    def color_wrap(self, next):
        if next >= self.colorsize:
            return next - self.colorsize
        else:
            return next

    def next_key_byte(self, nextbyte):
        self.key.append(nextbyte & 255)

    '''
    This is the big kahuna harvest function.  It is made to be called multiple
    times for the same image and possibly the same pin.

    It calls a vartiety of modes, chosen by the caller.  The modes evolved from
    simple stupid to sophisticated.  The NIST tests influenced the growth.  I
    left the mdoe that suck in here becasue they give nice test fodder to
    provide we can detect not up to the job images and modes.

    Oversimplifying, the modes that take only the low bits of colors do better,
    that is where images are noisy.  Modes that XOR tend to remove bias, just like
    Linear FeedbackShift Registers(LFSR) do in their world.  About 4 seems to
    perform much better on the NIST tests.

    We do a sanity check on what we harvest.  NIST actually gives guidelines for
    self checking of entropy harvest engines (discovered later).  This is not
    the full set NIST set, it was what was added as I learned.


    '''

    def harvest(self, filename="", mode="", pin=""):
        self.key = []
        self.rand_pixels = []
        self.valid = False

        if mode != "":
            self.set_mode(mode)
        else:
            mode = self.mode

        if pin != "":
            # if you change the orientation digit, file has to be reloaded
            if self.filename != "" and filename == "":
                orient = self.orient_digit()
                self.set_pin(pin)
                if orient != self.orient_digit():
                    filename = filename
            else:
                self.set_pin(pin)

        self.error = ""
        self.sanity = {}
        
        if filename != "":
            self.load(filename)
        elif self.filename == "":
            raise ValueError(f'no file loaded')


        self.process_pin()

        #low bit modes
        if mode == "lowbit":
            self.harvest_lowbit()
        elif mode == "lowxor":
            self.harvest_lowxor()

        # comnining modes
        elif mode == "lowmerge":
            self.harvest_lowmerge()
        elif mode == "pixelxor":
            self.harvest_pixelxor()
        elif mode == "product":
            self.harvest_product()

        #raw modes
        elif mode == "colorcode":
            self.harvest_colorcode()
        elif mode == "simplecolor":
            self.harvest_simplecolor()
        elif mode == "simplepixel":
            self.harvest_simplepixel()
        else:
            raise ValueError(f'mode {mode} not defined')

        if self.verbose:
            print(f'harvest key: {bytes(self.key).hex()}')


        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(bytes(self.key))
        self.key_hash = digest.finalize()

        self.sanity_check()
        return self.key


    def check_pixel_distro(self):
        pixels_needed = self.pixels_needed if self.pixels_needed != 0 else self.colors_needed
        got = len(self.pixel_distro)
        needed = (pixels_needed * .9)
        good = got > needed
        if self.verbose:
            print(f'Pixel test:        {"Pass" if good else "Fail"} ' \
                  f'pixels {pixels_needed}, unique {got}, min was {needed} keyzize {self.keysize} ')
        return good, got, needed

    def sanity_check(self):
        if self.verbose:
            print(f'sanity_check:')

        # general info
        self.sanity.update(
            [('pin',self.userpin), ('file',self.filename), ('keysize',self.keysize),
            ('key',bytes(self.key).hex())])

        # did file have enough data??
        good, error = check_file_data(self.im, self.filename, self.keysize, self.color_count,
            self.data_ratio, self.color_ratio, self.min_ratio, self.verbose,
            self.pixels_needed, self.pixelsize)
        if good == False:
            self.error += error
        self.sanity["data_ratio"] = self.data_ratio
        self.sanity["color_ratio"] = self.color_ratio


        # check sufficient entropy
        good, entropy, error = check_entropy(self.key, self.keysize, self.verbose)
        self.sanity['entropy'] = entropy
        if good == False:
            self.error += error

        self.sanity['entropy_ratio'] = int(len(self.key)/entropy)

        # check bias
        good, odd_bias, all = check_odd_bias(self.key, verbose=self.verbose)

        self.sanity['odd_even'] = (odd_bias, all)
        if good == False:
            self.error += f"odd even bias {odd_bias} > +- 0.1" + ", "


        # check odd even runs
        good, long_even, long_odd, all = check_odd_even_run(self.key, verbose=self.verbose)
        self.sanity['odd_even_run'] = (long_even, long_odd, all)
        if long_even > 15:
            self.error += f"long even {long_even} > 15" + ", "
        if long_odd > 15:
            self.error += f"long odd {long_odd} > 15" + ", "

        # check pixel variation
        good, got, needed = self.check_pixel_distro()
        if good == False:
            self.error += f"pixel not enough unique: got {got}, needed {needed}"

        # check distribution
        good, _, excess_map = distro(self.key, self.verbose)
        if good == False:
            self.error += f"distibution bias: {excess_map}"

        if self.error != "":
            eprint(f'key FAILS tests: {self.error}')
            self.sanity['error'] = self.error
            if self.verbose:
                print(f'sanity check errors: {self.error}')
        else:
            self.valid = True

        if self.verbose:
            print(f'sanity check {"valid" if self.valid else "FAIL"}:\n{self.sanity}')



    def save_to_file(self, extra=""):
        if extra == "":
            extra = f'_{self.mode}_{self.userpin}'
        return save_to_bin(self.key, self.filename, extra)

    '''
    These are the individual mode harvests.  Do not call these directly, only
    through the harvest() method.
    '''

    # this harvests the low order  bit of a color
    def harvest_lowbit(self):
        self.key = []
        bitcount = 0
        nextbyte = 0

        for _ in range(self.keysize):
            nextbyte <<= 1  #shift what we have so far

            # get a byte, save the low order bit, add it to previous
            cb = self.get_next_color()
            if self.verbose > 2:
                print(f'color byte {cb:02x}')
            nextbyte += cb & 1
            bitcount += 1

            #flush when we have a full byte
            if bitcount == 8:
                self.next_key_byte(nextbyte)
                bitcount = 0
                nextbyte = 0

        return self.key

    # this XORs the RGB bytes in n pixels, keep low order bit, builds a byte of key data
    def harvest_lowxor(self):
        self.key = []
        bitcount = 0
        pixel_count = 0
        nextbyte = 0
        cb = 0

        for _ in range(self.pixels_needed):

            # get a pixel, xor colors together, with previous results
            pixel = self.get_next_pixel()
            cb ^=  pixel[0] ^ pixel[1] ^ pixel[2]


            if self.verbose > 1:
                print(f'pixel 0x{pixel[0]:02x}:{pixel[1]:02x}:{pixel[2]:02x}, xor {cb:02x}')

            pixel_count += 1
            if pixel_count >= self.ncount:
                pixel_count = 0
                nextbyte <<= 1  #shift what we have so far
                nextbyte += cb & 1
                bitcount += 1

                if self.verbose > 1:
                    print(f'xor low bit next: {nextbyte:02x}  pixel xor result: {cb:02x}')
                #flush when we have a full byte
                if bitcount == 8:
                    if self.verbose > 1:
                        print(f'xor low bit result: {nextbyte:02x}  pixel xor result: {cb:02x}')
                    self.next_key_byte(nextbyte)
                    bitcount = 0
                    nextbyte = 0
                cb = 0

        return self.key

    # this XORs the RGB bytes in n pixels to form one key byte
    def harvest_pixelxor(self):
        self.key = []
        nextbyte = 0
        count = 0
        for _ in range(self.pixels_needed):

            # get a pixel, xor colors together, save it
            pixel = self.get_next_pixel()
            nextbyte = nextbyte ^ pixel[0] ^ pixel[1] ^ pixel[2]
            count += 1
            if count == self.ncount:
                if self.verbose > 1:
                    print(f'pixel 0x{pixel[0]:02x}:{pixel[1]:02x}:{pixel[2]:02x}, xor {nextbyte:02x}')
                self.next_key_byte(nextbyte)
                count = 0


        return self.key

    # this merges ths lower order 2 or 3 bits of RGB (rotate) to form a key byte
    def harvest_lowmerge(self):
        self.key = []
        nextbyte = 0
        mixer = 0
        low_3_bits = int('0111', 2)
        low_2_bits = int('011', 2)


        for _ in range(self.pixels_needed):
            pixel = self.get_next_pixel()
            if mixer == 0:
                nextbyte = pixel[0] & low_3_bits
                nextbyte |= (pixel[1] & low_3_bits)  << 3
                nextbyte |= (pixel[2] & low_2_bits) << 6
            elif mixer == 1:
                nextbyte = pixel[1] & low_3_bits
                nextbyte |= (pixel[2] & low_3_bits)  << 3
                nextbyte |= (pixel[0] & low_2_bits) << 6
            elif mixer == 2:
                nextbyte = pixel[2] & low_3_bits
                nextbyte |= (pixel[0] & low_3_bits)  << 3
                nextbyte |= (pixel[1] & low_2_bits) << 6
            mixer += 1
            if mixer >= 3:
                mixer = 0

            if self.verbose:
                print(f'lowmerge: pixel {pixel} next: {nextbyte:02x}')
            self.next_key_byte(nextbyte)

        if self.verbose:
            print(f'lowmerge: key: {bytes(self.key).hex()}')
        return self.key

    # this multiplies the RGB byte by each other the low order byte is saved to key
    def harvest_product(self):
        self.key = []
        nextbyte = 0

        for _ in range(self.pixels_needed):
            pixel = self.get_next_pixel()
            nextbyte = self.colorproduct(pixel) & 0xff
            self.next_key_byte(nextbyte)

        return self.key

    #this just picks up the RGB as consecutive bytes
    def harvest_colorcode(self):
        self.key = []
        #nextbyte = 0

        pixels = self.pixels_needed
        leftover = self.pixels_needed%3
        if leftover:
            pixels -= 1
        for _ in range(pixels):
            pixel = self.get_next_pixel()
            byte1 = pixel[0]
            self.next_key_byte(byte1)
            byte2 = pixel[1]
            self.next_key_byte(byte2)
            byte3 = pixel[2]
            self.next_key_byte(byte3)
            if self.verbose > 1:
                print(f'pixel {pixel} next: 0x{byte1:02x}{byte2:02x}{byte3:02x}')
        if leftover > 0:
            pixel = self.get_next_pixel()
            byte1 = pixel[0]
            self.next_key_byte(byte1)
            if leftover == 2:
                byte2 = pixel[1]
                self.next_key_byte(byte2)
            else:
                byte2 = 0
            if self.verbose > 1:
                print(f'pixel {pixel} next: 0x{byte1:02x}{byte2:02x}')

        return self.key

    # this harvests one byte out of a pixel on a rotating basis
    def harvest_simplepixel(self):
        self.key = []
        color_index = 3

        for _ in range(self.pixels_needed):
            if color_index == 3:
                pixel = self.get_next_pixel()
                color_index = 0
                if self.verbose:
                    print(f'pixel {pixel} ')
            self.next_key_byte(pixel[color_index])
            color_index += 1

        return self.key

    def harvest_simplecolor(self):
        self.key = []

        for _ in range(self.colors_needed):
            color = self.get_next_color()
            if self.verbose:
                print(f'color 0x{color:02x} ')
            self.next_key_byte(color)

        return self.key

'''
python image_secure.py -pin 00000123456 -keysize 256 -v 2 -m lowxor -n 4 IMG_0216.JPG
'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='harvest secure from png or jpg')
    parser.add_argument('files', nargs='+', help="jpg/png files you wish to harvest")

    parser.add_argument('-pin', default="092291", type=str,
                    dest='pin',
                    help='6 digit pin, greater than 1000')

    parser.add_argument('-factor', default="0", type=str,
                    dest='factor',
                    help='2 factor authorization factor, 6-8 digits')

    parser.add_argument('-mode', default="lowbit", type=str,
                    dest='mode', choices=ImageSecure.modes(),
                    help='mode for harvesting key')

    parser.add_argument('-keysize', default=256, type=int,
                    dest='keysize',
                    help='keysize in bits (multiple of 8): ')

    parser.add_argument('-ncount', default=1, type=int,
                    dest='ncount',
                    help='number of pixels in multi modes: ')

    parser.add_argument('-v', dest='verbose',
                    default=1,
                    help='verbose details')

    parser.add_argument('-ratio', default=1000, type=int,
                    dest='ratio',
                    help='ratio of pixels required per key bit')

    parser.add_argument('--compress', dest='compress',
                    default=False, action='store_true',
                    help='compress eliminates duplicate pixels')

    parser.add_argument('--no-compress', dest='compress',
                    default=False, action='store_false',
                    help='no eliminate duplicate pixels')

    args = parser.parse_args()

    if args.verbose:
        print(f'{args}')
        print(f'checking files {args.files}')
    for tocheck in args.files:
        secure = ImageSecure(tocheck, args.pin, args.factor, keysize=args.keysize,
            mode=args.mode, compress=args.compress, ncount=args.ncount,
            ratio=args.ratio, verbose=args.verbose)
        #secure.test_incr()
        key = secure.harvest()
        saved = secure.save_to_file()
