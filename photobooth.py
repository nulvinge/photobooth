#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by br _at_ re-web _dot_ eu, 2015-2016

import os
from datetime import datetime
from glob import glob
from sys import exit
from time import sleep, time
import cStringIO as StringIO
import pygame

from PIL import Image

from gui import GUI_PyGame as GuiModule
# from camera import CameraException, Camera_cv as CameraModule
from camera import CameraException, Camera_gPhoto as CameraModule
from slideshow import Slideshow
from events import Rpi_GPIO as GPIO

#####################
### Configuration ###
#####################

# Screen size
display_size = (1366, 768)

# Maximum size of assembled image
image_size = (2352, 1568)

# Size of pictures in the assembled image
thumb_size = (1176, 784)

# Image basename
picture_basename = datetime.now().strftime("%Y-%m-%d/pic")
print_basename = datetime.now().strftime("%Y-%m-%d-print/pic")

# GPIO channel of switch to shutdown the Photobooth
gpio_shutdown_channel = 24 # pin 18 in all Raspi-Versions

# GPIO channel of switch to take pictures
gpio_trigger_channel = 23 # pin 16 in all Raspi-Versions

# GPIO output channel for (blinking) lamp
gpio_lamp_channel = 4 # pin 7 in all Raspi-Versions

# Waiting time in seconds for posing
pose_time_first = 10
# Waiting time in seconds for posing
pose_time = -1

# Display time for assembled picture
display_time = 10

# Show a slideshow of existing pictures when idle
idle_slideshow = True

# Display time of pictures in the slideshow
slideshow_display_time = 5

mode = 'L'

###############
### Classes ###
###############

class PictureList:
    """A simple helper class.

    It provides the filenames for the assembled pictures and keeps count
    of taken and previously existing pictures.
    """

    def __init__(self, basename):
        """Initialize filenames to the given basename and search for
        existing files. Set the counter accordingly.
        """

        # Set basename and suffix
        self.basename = basename
        self.suffix = ".jpg"
        self.count_width = 5

        # Ensure directory exists
        dirname = os.path.dirname(self.basename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        # Find existing files
        count_pattern = "[0-9]" * self.count_width
        pictures = glob(self.basename + count_pattern + self.suffix)

        # Get number of latest file
        if len(pictures) == 0:
            self.counter = 0
        else:
            pictures.sort()
            last_picture = pictures[-1]
            self.counter = int(last_picture[-(self.count_width+len(self.suffix)):-len(self.suffix)])

        # Print initial infos
        print("Info: Number of last existing file: " + str(self.counter))
        print("Info: Saving assembled pictures as: " + self.basename + "XXXXX.jpg")

    def get(self, count):
        return self.basename + str(count).zfill(self.count_width) + self.suffix

    def get_last(self):
        return self.get(self.counter)

    def get_next(self):
        self.counter += 1
        return self.get(self.counter)


class Photobooth:
    """The main class.

    It contains all the logic for the photobooth.
    """

    def __init__(self, display_size, picture_basename, picture_size,
                 pose_time_first, pose_time, display_time, trigger_channel,
                 shutdown_channel, lamp_channel, idle_slideshow,
                 slideshow_display_time):
        self.display      = GuiModule('Photobooth', display_size)
        self.pictures     = PictureList(picture_basename)
        self.prints       = PictureList(print_basename)
        self.camera       = CameraModule(picture_size)

        self.pic_size     = picture_size
        self.pose_time_first = pose_time_first
        self.pose_time    = pose_time
        self.display_time = display_time

        self.trigger_channel  = trigger_channel
        self.shutdown_channel = shutdown_channel
        self.lamp_channel     = lamp_channel

        self.idle_slideshow = idle_slideshow
        if self.idle_slideshow:
            self.slideshow_display_time = slideshow_display_time
            self.slideshow = Slideshow(display_size, display_time, 
                                       os.path.dirname(os.path.realpath(picture_basename)))

        input_channels    = [ trigger_channel, shutdown_channel ]
        output_channels   = [ lamp_channel ]
        self.gpio         = GPIO(self.handle_gpio, input_channels, output_channels)

    def teardown(self):
        self.display.clear()
        self.display.show_message(u"Stänger av...")
        self.display.apply()
        self.gpio.set_output(self.lamp_channel, 0)
        self.display.cancel_events()
        self.display.teardown()
        self.gpio.teardown()
        exit(0)

    def _run_plain(self):
        while True:
            self.camera.set_idle()

            # Display default message
            self.display.clear()
            #self.display.show_message(u"Tryck på knappen!")
            self.display.show_message(u"Ta bild       Preview           \n   |         |                 \n   |         |                 \n   |         |                 \n   v        v                 \n")
            self.display.apply()

            # Wait for an event and handle it
            event = self.display.wait_for_event()
            self.handle_event(event)

    def _run_slideshow(self):
        while True:
            self.camera.set_idle()
            #self.slideshow.display_next(u"Tryck på knappen!")
            self.slideshow.display_next(u"Ta bild       Preview           \n   |         |                 \n   |         |                 \n   |         |                 \n   v        v                 \n")
            tic = time()
            while time() - tic < self.slideshow_display_time:
                self.check_and_handle_events()

    def run(self):
        while True:
            try:
                # Enable lamp
                self.gpio.set_output(self.lamp_channel, 1)

                # Select idle screen type
                if self.idle_slideshow:
                    self._run_slideshow()
                else:
                    self._run_plain()

            # Catch exceptions and display message
            except CameraException as e:
                self.handle_exception(e.message)
            # Do not catch KeyboardInterrupt and SystemExit
            except (KeyboardInterrupt): #, SystemExit):
                raise
            except Exception as e:
                print('SERIOUS ERROR: ' + repr(e))
                self.handle_exception("SERIOUS ERROR!")

    def check_and_handle_events(self):
        r, e = self.display.check_for_event()
        while r:
            self.handle_event(e)
            r, e = self.display.check_for_event()

    def handle_gpio(self, channel):
        if channel in [ self.trigger_channel, self.shutdown_channel ]:
            self.display.trigger_event(channel)

    def handle_event(self, event):
        if event.type == 0:
            self.teardown()
        elif event.type == 1:
            self.handle_keypress(event.value)
        elif event.type == 2:
            self.handle_mousebutton(event.value[0], event.value[1])
        elif event.type == 3:
            self.handle_gpio_event(event.value)

    def handle_keypress(self, key):
        """Implements the actions for the different keypress events"""
        # Exit the application
        if key == ord('q'):
            self.teardown()
        # Take pictures
        elif key == ord('c'):
            self.take_picture()
            self.display.cancel_events()
        # Preview
        elif key == ord('u'):
            self.show_preview(20, False)
            self.display.cancel_events()

    def handle_mousebutton(self, key, pos):
        """Implements the actions for the different mousebutton events"""
        # Take a picture
        if key == 1:
            self.take_picture()

    def handle_gpio_event(self, channel):
        """Implements the actions taken for a GPIO event"""
        if channel == self.trigger_channel:
            self.take_picture()
        elif channel == self.shutdown_channel:
            self.teardown()

    def handle_exception(self, msg):
        """Displays an error message and returns"""
        self.display.clear()
        print("Error: " + msg)
        self.display.show_message(u"FEL:\n\n" + msg)
        #self.display.show_message(u"Avbryt      Skriv ut            \n   |         |                 \n   |         |                 \n   |         |                 \n   v        v                 \n")
        #self.display.show_message(u"Ta bild       Preview           \n   |         |                 \n   |         |                 \n   |         |                 \n   v        v                 \n")
        self.display.apply()
        self.display.cancel_events()
        exit(1)


    def assemble_pictures(self, input_filenames, size):
        """Assembles four pictures into a 2x2 grid

        It assumes, all original pictures have the same aspect ratio as
        the resulting image.

        For the thumbnail sizes we have:
        h = (H - 2 * a - 2 * b) / 2
        w = (W - 2 * a - 2 * b) / 2

                                    W
               |---------------------------------------|

          ---  +---+-------------+---+-------------+---+  ---
           |   |                                       |   |  a
           |   |   +-------------+   +-------------+   |  ---
           |   |   |             |   |             |   |   |
           |   |   |      0      |   |      1      |   |   |  h
           |   |   |             |   |             |   |   |
           |   |   +-------------+   +-------------+   |  ---
         H |   |                                       |   |  2*b
           |   |   +-------------+   +-------------+   |  ---
           |   |   |             |   |             |   |   |
           |   |   |      2      |   |      3      |   |   |  h
           |   |   |             |   |             |   |   |
           |   |   +-------------+   +-------------+   |  ---
           |   |                                       |   |  a
          ---  +---+-------------+---+-------------+---+  ---

               |---|-------------|---|-------------|---|
                 a        w       2*b       w        a
        """

        # Thumbnail size of pictures
        outer_border = 40
        inner_border = 20
        thumb_box = ( int( size[0] / 2 ) ,
                      int( size[1] / 2 ) )
        thumb_size = ( thumb_box[0] - outer_border - inner_border ,
                       thumb_box[1] - outer_border - inner_border )

        # Create output image with white background
        output_image = Image.new('RGB', size, (0, 0, 0))

        # Image 0
        img = Image.open(input_filenames[0])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] - inner_border - img.size[0] ,
                   thumb_box[1] - inner_border - img.size[1] )
        output_image.paste(img, offset)

        # Image 1
        img = Image.open(input_filenames[1])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] + inner_border,
                   thumb_box[1] - inner_border - img.size[1] )
        output_image.paste(img, offset)

        # Image 2
        img = Image.open(input_filenames[2])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] - inner_border - img.size[0] ,
                   thumb_box[1] + inner_border )
        output_image.paste(img, offset)

        # Image 3
        img = Image.open(input_filenames[3])
        img.thumbnail(thumb_size)
        offset = ( thumb_box[0] + inner_border ,
                   thumb_box[1] + inner_border )
        output_image.paste(img, offset)

        output_image = output_image.convert(mode)

        # Save assembled image
        output_filename = self.pictures.get_next()
        output_image.save(output_filename, "JPEG")
        return output_filename

    def assemble_print(self, input_filenames, size):
        """Assembles four pictures into a 2x2 grid

        It assumes, all original pictures have the same aspect ratio as
        the resulting image.

        For the thumbnail sizes we have:
        h = (H - 2*a - 6*b) / 4
        w = (W - 2*a - 2*b) / 2

                                    W
               |---------------------------------------|
                   w0                w1
          ---  +---+-------------+---+-------------+---+  ---
           |   |                                       |   |  a
           |   |   +-------------+   +-------------+   |  --- h0
           |   |   |             |   |             |   |   |
           |   |   |      0      |   |      0      |   |   |  h
           |   |   |             |   |             |   |   |
           |   |   +-------------+   +-------------+   |  ---
           |   |                                       |   |  b
           |   |   +-------------+   +-------------+   |  --- h1
           |   |   |             |   |             |   |   |
           |   |   |      1      |   |      1      |   |   |  h
           |   |   |             |   |             |   |   |
           |   |   +-------------+   +-------------+   |  ---
         H |   |                                       |   |  b
           |   |   +-------------+   +-------------+   |  --- h2
           |   |   |             |   |             |   |   |
           |   |   |      2      |   |      2      |   |   |  h
           |   |   |             |   |             |   |   |
           |   |   +-------------+   +-------------+   |  ---
           |   |                                       |   |  b
           |   |   +-------------+   +-------------+   |  --- h3
           |   |   |             |   |             |   |   |
           |   |   |      3      |   |      3      |   |   |  h
           |   |   |             |   |             |   |   |
           |   |   +-------------+   +-------------+   |  ---
           |   |                                       |   |  a
          ---  +---+-------------+---+-------------+---+  ---

               |---|-------------|---|-------------|---|
                 a        w        b        w        a
        """

        # Thumbnail size of pictures
        outer_borderx = 0
        outer_bordery = 110
        inner_borderx = 20
        inner_bordery = 10
        thumb_size = ( int((size[0] - 2*outer_borderx - inner_borderx)/2) ,
                       int((size[1] - 2*outer_bordery - 3*inner_bordery)/4) )
        w = [outer_borderx
            ,outer_borderx+thumb_size[0]+inner_borderx
            ]
        h = [outer_bordery
            ,outer_bordery+1*(thumb_size[1]+inner_bordery)
            ,outer_bordery+2*(thumb_size[1]+inner_bordery)
            ,outer_bordery+3*(thumb_size[1]+inner_bordery)
            ]

        # Create output image with white background
        output_image = Image.new('RGB', size, (255, 255, 255))

        # Image 0
        img = Image.open(input_filenames[0])
        img.thumbnail(thumb_size, Image.ANTIALIAS)
        output_image.paste(img, (w[0],h[0]))
        output_image.paste(img, (w[1],h[0]))

        # Image 1
        img = Image.open(input_filenames[1])
        img.thumbnail(thumb_size, Image.ANTIALIAS)
        output_image.paste(img, (w[0],h[1]))
        output_image.paste(img, (w[1],h[1]))

        # Image 2
        img = Image.open(input_filenames[2])
        img.thumbnail(thumb_size, Image.ANTIALIAS)
        output_image.paste(img, (w[0],h[2]))
        output_image.paste(img, (w[1],h[2]))

        # Image 3
        img = Image.open(input_filenames[3])
        img.thumbnail(thumb_size, Image.ANTIALIAS)
        output_image.paste(img, (w[0],h[3]))
        output_image.paste(img, (w[1],h[3]))

        output_image = output_image.convert(mode)

        # Save assembled image
        output_filename = self.prints.get_next()
        output_image.save(output_filename, "JPEG")
        return output_filename

    def show_preview(self, seconds, should_count=True):
        secs = abs(seconds)
        if secs == 1:
            sleep(1)
            self.display.cancel_events()
        elif self.camera.has_preview() and not seconds < 0:
            tic = time()
            toc = time() - tic
            while toc < secs:
                self.display.clear()
                buff = self.camera.take_preview_buff()
                img = Image.open(StringIO.StringIO(buff))
                img = img.convert(mode)
                img = img.convert("RGB")
                pygameimg = pygame.image.frombuffer(img.tobytes(), img.size, img.mode)
                self.display.show_picture(image=pygameimg, flip=True) 
                self.display.show_message(str(secs - int(toc)) + "                                    ")
                if toc < 10 and not should_count:
                    self.display.show_message(u"            Avbryt              \n            |                 \n            |                 \n            |                 \n            v                 \n")

                self.display.apply()

                # Limit progress to 1 "second" per preview (e.g., too slow on Raspi 1)
                toc = min(toc + 1, time() - tic)

                r, e = self.display.check_for_event()
                if not should_count and r and e.type == 1 and e.value == ord('u'):
                    self.display.cancel_events()
                    return
        else:
            for i in range(secs):
                self.display.clear()
                self.display.show_message(str(secs - i))
                self.display.apply()
                sleep(1)

    def take_picture(self):
        """Implements the picture taking routine"""
        # Disable lamp
        self.gpio.set_output(self.lamp_channel, 0)

        # Show pose message
        self.display.clear()
        self.display.show_message(u"POSERA!\n\nTar fyra bilder...");
        self.display.apply()
        sleep(2)

        # Extract display and image sizes
        display_size = self.display.get_size()
        outsize = (int(display_size[0]/2), int(display_size[1]/2))

        # Take pictures
        filenames = [i for i in range(4)]
        for x in range(4):
            # Countdown
            if x==0:
                self.show_preview(self.pose_time_first)
            else:
                self.show_preview(self.pose_time)

            # Try each picture up to 3 times
            remaining_attempts = 3
            while remaining_attempts > 0:
                remaining_attempts = remaining_attempts - 1

                self.display.clear()
                self.display.show_message(u"OMELETT!!!\n\n" + str(x+1) + " av 4")
                self.display.apply()

                tic = time()

                try:
                    filenames[x] = self.camera.take_picture("/tmp/photobooth_%02d.jpg" % x)
                    remaining_attempts = 0
                except CameraException as e:
                    # On recoverable errors: display message and retry
                    if e.recoverable:
                        if remaining_attempts > 0:
                            self.display.clear()
                            self.display.show_message(e.message)  
                            self.display.apply()
                            sleep(5)
                        else:
                            raise CameraException("Giving up! Please start over!", False)
                    else:
                       raise e

                # Measure used time and sleep a second if too fast 
                toc = time() - tic
                if toc < 1.0:
                    sleep(1.0 - toc)

        # Show 'Wait'
        self.display.clear()
        self.display.show_message(u"Vänta!\n\nLaddar...")
        self.display.apply()

        self.camera.set_idle()

        # Assemble them
        outfile = self.assemble_pictures(filenames, display_size)

        # Show pictures for 10 seconds
        self.display.clear()
        self.display.show_picture(outfile, display_size, (0,0))
        self.display.apply()
        sleep(2)

        self.display.clear()
        self.display.show_picture(outfile, display_size, (0,0))
        self.display.show_message(u"Skriv ut    Avbryt              \n   |         |                 \n   |         |                 \n   |         |                 \n   v        v                 \n")
        self.display.apply()
        self.run_after(filenames)

        #self.display.clear()
        #self.display.show_picture(outfile, display_size, (0,0))
        #self.display.show_message(u"Laddar upp")
        #self.display.apply()
        #self.upload(filenames)

        # Reenable lamp
        self.gpio.set_output(self.lamp_channel, 1)

    def run_after(self,filenames):
        while True:
            event = self.display.wait_for_event()
            if not self.handle_event_after(event,filenames):
                return

    def handle_event_after(self, event, filesnames):
        if event.type == 0:
            self.teardown()
        elif event.type == 1:
            key = event.value
            if key == ord('q'):
                self.teardown()
            elif key == ord('u'):
                self.display.cancel_events()
                return False
            elif key == ord('c'):
                self.print_out(filesnames)
                self.display.cancel_events()
                return False
        return True

    def print_out(self, filenames):
        display_size = self.display.get_size()

        # Show 'Wait'
        self.display.clear()
        self.display.show_message(u"Vänta!\n\nLaddar...")
        self.display.apply()

        # Assemble them
        outfile = self.assemble_print(filenames, (self.pic_size[1],self.pic_size[0]))

        # Show pictures for 10 seconds
        self.display.clear()
        self.display.show_picture(outfile, display_size, (0,0))
        self.display.show_message(u"Vänta!\n\nSkriver ut...")
        self.display.apply()

        os.system("lp -o fit-to-page %s" % outfile)

    def upload(self, filenames):
        sleep(10)


#################
### Functions ###
#################

def main():
    photobooth = Photobooth(display_size, picture_basename, image_size,
                            pose_time_first, pose_time, display_time, 
                            gpio_trigger_channel, gpio_shutdown_channel,
                            gpio_lamp_channel, 
                            idle_slideshow, slideshow_display_time)
    photobooth.run()
    photobooth.teardown()
    return 0

if __name__ == "__main__":
    exit(main())
