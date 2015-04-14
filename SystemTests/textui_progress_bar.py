#!/usr/bin/python
'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''

'''===========================================================================
13-Jan-2015    evgenyl    Initial implementation.
==========================================================================='''

import time
import sys

'''------------------------------------------------------------------------'''


class TextUIProgressBar:
    '''
    @summary: This class simulates Progress Bar GUI widget in UNIX terminal.
    '''

    '''--------------------------------------------------------------------'''
    def __init__(self):
        '''
        @summary: CTOR, define some constant mapping
        '''
        self.colors = {}
        self.colors['gray'] = '30'
        self.colors['red'] = '31'
        self.colors['green'] = '32'
        self.colors['yellow'] = '33'
        self.colors['blue'] = '34'
        self.colors['magenta'] = '35'
        self.colors['cyan'] = '36'
        self.colors['white'] = '37'

    '''--------------------------------------------------------------------'''
    def update_progress_bar(self, complete, total, caption = '', color='' ):
        '''
        @summary:        update_progress_bar
                         Drawing code. The idea is 
                         - jump to the beginning of the line
                         - print the same amount of characters 
                           but in a different proportion (complete/total)
        @param complete: How many steps were completed?
        @type  complete: Integer, not-negative
        @param total:    How many steps are there at all?
        @type  total:    Integer, not-negative
        @param caption:  Description to add after the bar
        @type  caption:  String
        @param color:    Which color to use while drawing? 
                         Only a predefined set of colors is supported
        @type color:     String
        '''
        color = self.colors.get(color, self.colors['white']) 
        color_start = '\033[01;' + color + 'm'
        color_stop = '\033[00m' 
        print '\r' + color_start + u'\u2591'*complete + \
               u'\u2593'*(total-complete) + color_stop,
        if 0 < len(caption):
            print '{0}'.format(caption) ,
        sys.stdout.flush()

    '''--------------------------------------------------------------------'''
    def test(self):
        '''
        @summary: test
                  Unit test. Simulate a process of 10 steps with 
                  delay of one second after each step. 
        '''
        k = self.colors.keys()
        l = len(k)
        for j in range(1, l+1):
            self.update_progress_bar(j, l, str(j), k[j-1])
            time.sleep(1)

'''============================= END OF FILE =============================='''
