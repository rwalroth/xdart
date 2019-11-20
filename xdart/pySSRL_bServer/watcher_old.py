import os, imp, time
from fnmatch import filter

import pandas as pd

import bServer_funcs; imp.reload(bServer_funcs)
from bServer_funcs import *

from multiprocessing import Queue, Process

class Watcher(Process):
    def __init__(self,
                 watchPaths = ["P:\\bl2-1", "Z:\\"],
                 filetypes = ['pdi', 'raw'],
                 pollingPeriod = 0.1,
                 queue = Queue(),
                 **kwargs):
        
        super().__init__()
        
        self.watchPaths = watchPaths
        self.filetypes = filetypes
        self.pollingPeriod = pollingPeriod
        self.queue = queue
        
    
    def run(self):
        paths, filetypes = self.watchPaths, self.filetypes
        
        before = dict( [filetype, dict([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])] for (path, filetype) in zip(paths, filetypes) )

        while 1:
            ctr = 1
            time.sleep (self.pollingPeriod)
            after = dict ( [filetype, dict ([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])]
                    for (path, filetype) in zip(paths, filetypes) )
            
            for filetype in after.keys():
                added = [f for f in after[filetype] if not f in before[filetype]]
                removed = [f for f in before[filetype] if not f in after[filetype]]
                if added: print(f"{filetype} - Added: {''.join (added)}")
                if removed: print(f"{filetype} - Removed: {', '.join (removed)}")
                
                self.queue.put(added)
                                
                if len(added) == 0:
                    continue
                
            before = after
            
            data = get_plot_points()

            if len(data.columns) != 128:
                continue

            print(len(data))
            #print(data)
            
            if ctr == 1:
                prev_data = data

            if len(data) == len(prev_data):
                #time.sleep(1)
                continue
            else:
                print(data)
                prev_data = data
                
            ctr += 1

            