import re


def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def find_between_r( s, first, last ):
    try:
        start = s.rindex( first ) + len( first )
        end = s.rindex( last, start )
        return s[start:end]
    except ValueError:
        return ""
    
    
def get_from_pdi(pdi_file):

    with open(pdi_file, 'r') as f:
        pdi_data = f.read()
    
    pdi_data = pdi_data.replace('\n', ';')
    
    counters = re.search('All Counters;(.*);;# All Motors', pdi_data).group(1)
    cts = re.split(';|=', counters)
    Counters = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}

    motors = find_between(pdi_data, 'All Motors;', ';#')
    cts = re.split(';|=', motors)
    Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
    
    return Counters, Motors


def get_from_pdi(pdi_file):

    with open(pdi_file, 'r') as f:
        pdi_data = f.read()

    pdi_data = pdi_data.replace('\n', ';')
    
    try:
        counters = re.search('All Counters;(.*);;# All Motors', pdi_data).group(1)
        cts = re.split(';|=', counters)
        Counters = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}

        motors = find_between(pdi_data, 'All Motors;', ';#')
        cts = re.split(';|=', motors)
        Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
    except:
        ss1 = '# Diffractometer Motor Positions for image;# '
        ss2 = ';# Calculated Detector Calibration Parameters for image:'
        
        motors = re.search(f'{ss1}(.*){ss2}', pdi_data).group(1)
        cts = re.split(';|=', motors)
        Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}
        Motors['TwoTheta'] = Motors['2Theta']
        Counters = {}

    return Counters, Motors


def get_motor_val(pdi_file, motor):
    Counters, Motors = get_from_pdi(pdi_file)
    
    return Motors[motor]


def read_image_file(fname, return_float=False, shape_100K=(195, 487), shape_300K=(195,1475), verbose=False):
    if verbose: print('Reading image data into numpy array..')
    if 'tif' in fname[-5:]:
        img = np.asarray(io.imread(fname))
    else:
        try:
            img = np.asarray(np.fromfile(fname, dtype='int32', sep="").reshape(shape_100K))
        except:
            img = np.asarray(np.fromfile(fname, dtype='int32', sep="").reshape(shape_300K))
            
    if return_float:
        img = np.asarray(img, np.float)
        
    return img
    
    
def smooth_img(img, kernel_size=3, window_size=3, order=0):
    if (np.mod(kernel_size, 2) == 0) or (np.mod(window_size, 2) == 0):
        print('Smoothing windows should be odd integers')
        return img
    
    if order >= window_size:
        order = window_size - 1
        
    if kernel_size > 1:
        img = medfilt2d(img, 3)
    if window_size > 1:
        img = ndimage.gaussian_filter(img, sigma=(window_size, window_size), order=order)
        
    return img