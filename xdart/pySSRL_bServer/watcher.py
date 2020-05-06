import os, imp, time
from fnmatch import filter

from multiprocessing import Queue, Process

class Watcher(Process):
    """
    Run background process to monitor when new files are added to watched folders

    Inheritance:
        Process: from multiprocessing module

    Attributes:
        watchpPaths: list of folders to watch
        filetypes: list of filetypes to watch in each folder
        pollingPeriod: interval between polling the folders
        queues: Dictionary of queues in which changes in each folder are stored
        command_q: Queue object from multuprocessing module
        verbose: Flag to enable output messages (for debugging)
    """
    def __init__(self,
                 watchPaths = ["Z:\\", "P:\\bl2-1"],
                 filetypes = ['raw', 'pdi'],
                 pollingPeriod = 0.1,
                 queues = {},
                 command_q = Queue(),
                 verbose=False,
                 **kwargs):
        
        super().__init__()
        
        self.watchPaths = watchPaths
        self.filetypes = filetypes
        self.pollingPeriod = pollingPeriod
        if len(queues) < 1:
            self.queues = {ftype: Queue() for ftype in filetypes}
        else:
            self.queues = queues
        self.command_q = command_q
        self.verbose = verbose
        
    
    def run(self):
        """Run the watcher process to watch changes in folders
        """
        paths, filetypes = self.watchPaths, self.filetypes
        paths_dict = {filetype:path for filetype, path in zip(filetypes, paths)}
        
        before = dict( [filetype, dict([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])]
                      for (path, filetype) in zip(paths, filetypes) )
        
        while 1:
            if not self.command_q.empty():
                command_q = self.command_q.get()
                if command_q == 'stop':
                    for _, q in self.queues.items():
                        q.put('BREAK')
                    break
                
            after = dict ( [filetype, dict ([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])]
                          for (path, filetype) in zip(paths, filetypes) )
    
            for filetype in after.keys():
                added = sorted([os.path.join(paths_dict[filetype], f)
                                for f in after[filetype] 
                                if not f in before[filetype]])
                
                if added:
                    if self.verbose: print(f"{filetype} - Added: {added}")
                    for f in added:
                        self.queues[filetype].put(f)
                        
                    before[filetype] = after[filetype]
                
            time.sleep (self.pollingPeriod)