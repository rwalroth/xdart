import os, imp, time
from fnmatch import filter

from multiprocessing import Queue, Process

class Watcher(Process):
    def __init__(self,
                 watchPaths = ["Z:\\", "P:\\bl2-1"],
                 filetypes = ['raw', 'pdi'],
                 pollingPeriod = 0.1,
                 queues = {},
                 verbose=False,
                 **kwargs):
        
        super().__init__()
        
        self.watchPaths = watchPaths
        self.filetypes = filetypes
        self.pollingPeriod = pollingPeriod
        if len(queues) < 1:
            self.queues = {ftype: Queue() for ftype in filetypes}
        self.verbose = verbose
        
    
    def run(self):
        paths, filetypes = self.watchPaths, self.filetypes
        
        before = dict( [filetype, dict([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])]
                      for (path, filetype) in zip(paths, filetypes) )
        
        while 1:
            after = dict ( [filetype, dict ([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])]
                          for (path, filetype) in zip(paths, filetypes) )
    
            for filetype in after.keys():
                added = sorted([f for f in after[filetype] if not f in before[filetype]])
                if added:
                    if self.verbose: print(f"{filetype} - Added: {added}")
                    for f in added:
                        self.queues[filetype].put(f)
                        
                    before[filetype] = after[filetype]
                
            time.sleep (self.pollingPeriod)