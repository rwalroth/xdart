import os, time
from fnmatch import filter

pdi_path = "P:\\bl2-1\\Dunn"
img_path = "Z:\\"

paths = [pdi_path, img_path]
filetypes = ['pdi', 'raw']

before = dict( [filetype, dict([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])]
               for (path, filetype) in zip(paths, filetypes) )

while 1:
    time.sleep (0.1)
    after = dict ( [filetype, dict ([(f, None) for f in filter(os.listdir (path), f'*{filetype}')])]
               for (path, filetype) in zip(paths, filetypes) )
    
    for filetype in after.keys():
        added = [f for f in after[filetype] if not f in before[filetype]]
        removed = [f for f in before[filetype] if not f in after[filetype]]
        if added: print(f"{filetype} - Added: {''.join (added)}")
        if removed: print(f"{filetype} - Removed: {', '.join (removed)}")
    
    before = after