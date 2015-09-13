#!/bin/env python

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import argparse
import math
import struct
import time

import evdev
import pyaudio
from setproctitle import setproctitle


keymap_en = {
    'KEY_A' : 'a', 'KEY_B' : 'b', 'KEY_C' : 'c', 'KEY_D' : 'd', 'KEY_E' : 'e',
    'KEY_F' : 'f', 'KEY_G' : 'g', 'KEY_H' : 'h', 'KEY_I' : 'i', 'KEY_J' : 'j',
    'KEY_K' : 'k', 'KEY_L' : 'l', 'KEY_M' : 'm', 'KEY_N' : 'n', 'KEY_O' : 'o',
    'KEY_P' : 'p', 'KEY_Q' : 'q', 'KEY_R' : 'r', 'KEY_S' : 's', 'KEY_T' : 't',
    'KEY_U' : 'u', 'KEY_V' : 'v', 'KEY_W' : 'w', 'KEY_X' : 'x', 'KEY_Y' : 'y',
    'KEY_Z' : 'z', 'KEY_0' : '0', 'KEY_1' : '1', 'KEY_2' : '2', 'KEY_3' : '3',
    'KEY_4' : '4', 'KEY_5' : '5', 'KEY_6' : '6', 'KEY_7' : '7', 'KEY_8' : '8',
    'KEY_9' : '9', 'KEY_SPACE' : ' ', 'KEY_ENTER' : ' ',
}

keymap_de = {
    'KEY_A' : 'a', 'KEY_B' : 'b', 'KEY_C' : 'c', 'KEY_D' : 'd', 'KEY_E' : 'e',
    'KEY_F' : 'f', 'KEY_G' : 'g', 'KEY_H' : 'h', 'KEY_I' : 'i', 'KEY_J' : 'j',
    'KEY_K' : 'k', 'KEY_L' : 'l', 'KEY_M' : 'm', 'KEY_N' : 'n', 'KEY_O' : 'o',
    'KEY_P' : 'p', 'KEY_Q' : 'q', 'KEY_R' : 'r', 'KEY_S' : 's', 'KEY_T' : 't',
    'KEY_U' : 'u', 'KEY_V' : 'v', 'KEY_W' : 'w', 'KEY_X' : 'x', 'KEY_Y' : 'z',
    'KEY_Z' : 'y', 'KEY_0' : '0', 'KEY_1' : '1', 'KEY_2' : '2', 'KEY_3' : '3',
    'KEY_4' : '4', 'KEY_5' : '5', 'KEY_6' : '6', 'KEY_7' : '7', 'KEY_8' : '8',
    'KEY_9' : '9', 'KEY_SPACE' : ' ', 'KEY_ENTER' : ' ', }

class MorsePlayer(object):

    morsecode = {
        'a' : '.-', 'b' : '-...', 'c' : '-.-.', 'd' : '-..', 'e' : '.',
        'f' : '..-.', 'g' : '--.', 'h' : '....', 'i' : '..', 'j' : '.---',
        'k' : '-.-', 'l' : '.-..', 'm' : '--', 'n' : '-.', 'o' : '---',
        'p' : '.--.', 'q' : '--.-', 'r' : '.-.', 's' : '...', 't' : '-',
        'u' : '..-', 'v' : '...-', 'w' : '.--', 'x' : '-..-', 'y' : '-.--',
        'z' : '--..', '0' : '-----', '1' : '.----', '2' : '..---', '3' : '...--',
        '4' : '....-', '5' : '.....', '6' : '-....', '7' : '--...', '8' : '---..',
        '9' : '----.', ' ' : ' '
    }

    done = property(lambda self: len(self.__queue) == 0)

    def __init__(self, device_index=0, frequency=700, word_speed=20):
        self.__queue = bytes()
        self.__player = pyaudio.PyAudio()
        
        dit_len = 1.2 / word_speed
        dah_len = dit_len * 3
        
        sample_rate = 44100
        samples = sample_rate // frequency
        amplitude = 30000
        wave = [int(math.sin(2*math.pi * x / samples) * amplitude) for x in range(samples)]
        wave = b''.join([struct.pack('h', x) for x in wave])


        self.__dit = wave * int(frequency * dit_len)
        self.__dah = wave * int(frequency * dah_len)
        self.__wordspace = bytes(len(self.__dit) * 7)
        self.__bitspace = bytes(len(self.__dit))
        self.__charspace = bytes(len(self.__dah))

        self.__stream = self.__player.open(format = self.__player.get_format_from_width(2),
                                           channels = 1,
                                           rate = sample_rate,
                                           output = True,
                                           stream_callback = lambda *args: self.__callback(*args),
                                           output_device_index=device_index)
        
        self.__stream.start_stream()
        self.__queue += self.__charspace


    def play(self, word):
        for char in word.lower():
            code = self.morsecode.get(char, None)
            if code is None:
                continue

            for c in code:
                if c == '.':
                    self.__queue += self.__dit
                    self.__queue += self.__bitspace
                elif c == '-':
                    self.__queue += self.__dah
                    self.__queue += self.__bitspace
                elif c == ' ':
                    self.__queue += self.__wordspace

            self.__queue += self.__charspace
    
    def __callback(self, in_data, frame_count, time_info, status):
        data = self.__queue[0:frame_count*2]
        self.__queue = self.__queue[2*frame_count:]
        data += bytes(2*frame_count - len(data))

        return (data, pyaudio.paContinue)


    def __del__(self):
        self.__stream.stop_stream()
        self.__stream.close()
        self.__player.terminate()


def main():
    setproctitle('echomorse')
    parser = argparse.ArgumentParser(
        prog = 'echomorse',
        description = 'Listen for keyboard events and play the corresponding ' \
                      'morse code over pulseaudio'
    )

    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('-a', '--audio-index', type=int, default=None, help='Index of the output audio device')
    parser.add_argument('-i', '--event-index', type=int, help='Index of the input device to listen to')
    parser.add_argument('-d', '--device', type=str, help='Path of the event to listen to')
    parser.add_argument('-k', '--keymap', type=str, default='de', help='Keymap: de or en')
    parser.add_argument('--wpm', type=int, default=25, help='Words per minute')
    parser.add_argument('--frequency', type=int, default=750, help='Audio frequency')
    parser.add_argument('--test', type=str, help='Test output')
    
    if len(sys.argv) == 1:
        sys.argv.append('--help')

    args = parser.parse_args()


    # Setup input listener
    devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
    p = pyaudio.PyAudio()
    if args.list:
        print('Input devices:')
        for idx, dev in enumerate(devices):
            print('{}: {}'.format(idx, dev.name))

        print()
        print('Audio devices:')
        for idx in range(p.get_device_count()):
            info = p.get_device_info_by_index(idx)
            print('{}: {}'.format(idx, info['name']))

        return 0


    # Setup for MorsePlayer
    if args.wpm <= 0:
        print('WPM must be greater than zero')
        return 1

    if args.frequency <= 0:
        print('Frequency must be greater than zero')
        return 1

    if args.audio_index is None:
        # Choose default sink if it exists
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['name'] == 'default':
                args.audio_index = i
                break
        else:
            args.audio_index = 0
    elif not (0 <= args.audio_index < pyaudio.PyAudio().get_device_count()):
        print('Audio device does not exist')
        return 1

    player = MorsePlayer(frequency = args.frequency,
                         word_speed = args.wpm,
                         device_index = args.audio_index)

    if args.test is not None:
        player.play(args.test)
        while not player.done:
            time.sleep(0.1)
        return 0

    try:
        keymap = globals()['keymap_' + args.keymap]
    except:
        print('Unrecognized keymap {}'.format(args.keymap))
        return 1
    
    if ((args.event_index is not None and args.device is not None) or
        (args.event_index is None and args.device is None)):
        print('Either device or index have to be specified, but not both')
        return 1

    if args.event_index is not None:
        if not (0 <= args.event_index < len(devices)):
            print('Device does not exist')
            return 1
        device = devices[args.event_index]
    elif args.device is not None:
        if not os.path.exists(args.device):
            print('Device does not exist')
            return 1
        device = evdev.InputDevice(args.device)
    else:
        assert False

    # Event loop
    for event in device.read_loop():
        if event.type == evdev.ecodes.EV_KEY and event.value == 1:
            key = keymap.get(evdev.KeyEvent(event).keycode, None)
            if key is not None:
                player.play(key)

    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
