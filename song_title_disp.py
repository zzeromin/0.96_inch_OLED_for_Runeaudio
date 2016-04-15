# -*- coding: utf-8 -*- 
# reference: 
# https://brunch.co.kr/@gogamza/6
# https://github.com/haven-jeon/piAu_volumio
# https://pypi.python.org/pypi/Pillow/2.1.0
# installed python package: python2-pip, i2c-tools, python-imaging, python-mpd2, gcc
# This code edited for rpi2 runeaudio by zzeromin
# 1. album to artist
# 2. fonts
# 3. from PIL import Image

import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
#import Image
#import ImageDraw
#import ImageFont

from mpd import MPDClient, MPDError, CommandError
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# Raspberry Pi pin configuration:
RST = 24
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0



# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)





class PollerError(Exception):
    """Fatal error in poller."""


class MPDPoller(object):
    def __init__(self, host="localhost", port="6600", password=None):
        self._host = host
        self._port = port
        self._password = password
        self._client = MPDClient()

    def connect(self):
        try:
            self._client.connect(self._host, self._port)
        # Catch socket errors
        except IOError as err:
            errno, strerror = err
            raise PollerError("Could not connect to '%s': %s" %
                              (self._host, strerror))

        # Catch all other possible errors
        # ConnectionError and ProtocolError are always fatal.  Others may not
        # be, but we don't know how to handle them here, so treat them as if
        # they are instead of ignoring them.
        except MPDError as e:
            raise PollerError("Could not connect to '%s': %s" %
                              (self._host, e))

        if self._password:
            try:
                self._client.password(self._password)

            # Catch errors with the password command (e.g., wrong password)
            except CommandError as e:
                raise PollerError("Could not connect to '%s': "
                                  "password commmand failed: %s" %
                                  (self._host, e))

            # Catch all other possible errors
            except (MPDError, IOError) as e:
                raise PollerError("Could not connect to '%s': "
                                  "error with password command: %s" %
                                  (self._host, e))

    def disconnect(self):
        # Try to tell MPD we're closing the connection first
        try:
            self._client.close()

        # If that fails, don't worry, just ignore it and disconnect
        except (MPDError, IOError):
            pass

        try:
            self._client.disconnect()

        # Disconnecting failed, so use a new client object instead
        # This should never happen.  If it does, something is seriously broken,
        # and the client object shouldn't be trusted to be re-used.
        except (MPDError, IOError):
            self._client = MPDClient()

    def poll(self):
        try:
            song = self._client.currentsong()
            stats =self._client.status()
            if stats['state'] == 'stop':
                return(None)
            print(stats)
            print(song)
            if 'artist' not in song:
                artist = ""
            else:
                artist = song['artist']
            
            if 'title' not in song:
                title = ""
            else:    
                title =song['title']
            songplayed = stats['elapsed']
            vol = stats['volume']
            m, s = divmod(float(songplayed), 60)
            h, m = divmod(m, 60)
            

        # Couldn't get the current song, so try reconnecting and retrying
        except (MPDError, IOError):
            # No error handling required here
            # Our disconnect function catches all exceptions, and therefore
            # should never raise any.
            self.disconnect()

            try:
                self.connect()

            # Reconnecting failed
            except PollerError as e:
                raise PollerError("Reconnecting failed: %s" % e)

            try:
                song = self._client.currentsong()

            # Failed again, just give up
            except (MPDError, IOError) as e:
                raise PollerError("Couldn't retrieve current song: %s" % e)

        # Hurray!  We got the current song without any errors!
        print(song)
        print(songplayed)
        eltime = "%d:%02d:%02d" % (h, m, s)
        return({'artist':artist, 'title':title, 'eltime':eltime, 'volume':int(vol)})



def main():
    from time import sleep
    # Initialize library.
    disp.begin()

    # Clear display.
    disp.clear()
    disp.display()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    # Draw some shapes.
    # First define some constants to allow easy resizing of shapes.
    padding = 2
    shape_width = 20
    top = padding
    bottom = height-padding
    x = padding
    # Load default font.
    font_alb = ImageFont.truetype('/root/setupfiles/piAu_volumio/NanumGothic.ttf', 13)
    poller = MPDPoller()
    poller.connect()
    
    font_tit = ImageFont.truetype('/root/setupfiles/piAu_volumio/NanumGothic.ttf', 13)
    font_tm = ImageFont.truetype('/root/setupfiles/piAu_volumio/NanumGothic.ttf', 14)
    while True:
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        status = poller.poll()
        if status is None:
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            continue
        artist = status['artist']
        title = status['title']
        eltime = status['eltime']
        vol =status['volume']
        print artist
        print title
        print eltime
        print vol
        div_vol = vol // 10
        vol_str = ""
        for i in range(div_vol):
            vol_str =vol_str + '+' 
        for i in range(10 - div_vol):
            vol_str = vol_str + '-'
        draw.text((0, top), unicode(artist).center(20,' '), font=font_alb, fill=255)
        draw.text((0, top+15), unicode(title).center(20, ' '), font=font_tit, fill=255)
        draw.text((0, top+30), eltime.center(24, ' '), font=font_tm, fill=255)
        draw.text((0, top+45), vol_str, font=font_tm, fill=255)
        draw.text((80, top+45),"vol " +  str(vol) , font=font_tm, fill=255)

        disp.image(image)
        disp.display()
        sleep(1)


if __name__ == "__main__":
    import sys

    try:
        main()

    # Catch fatal poller errors
    except PollerError as e:
        sys.stderr.write("Fatal poller error: %s" % e)
        sys.exit(1)

    # Catch all other non-exit errors
    except Exception as e:
        sys.stderr.write("Unexpected exception: %s" % e)
        sys.exit(1)

    # Catch the remaining exit errors
    except:
        sys.exit(0)
