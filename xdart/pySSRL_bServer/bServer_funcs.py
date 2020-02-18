import requests
import time
import uuid
import pandas as pd
import re
import time
try:
    from .helper_funcs import find_between, find_between_r
except ImportError:
    from helper_funcs import find_between, find_between_r

bServer = "http://127.0.0.1:18085/SIS/"


def create_UUID():
    """UUIDs will be unique for a given run of the kernel"""
    unique_uuid = uuid.uuid4().hex[:8].upper()
    return unique_uuid


def is_available(debug=False):
    t0 = time.time()
    for i in range(5):
        try:
            r = requests.get(bServer + "is_available")
            rv = r.json()['data']
            if debug: print(f'{i+1} Tries, {time.time()-t0:.3f} s')
            return rv
        except:
            pass
        
        time.sleep(0.05)
        
    if debug: print(f'{i+1} Tries, {time.time()-t0:0.3f} s')
    return False
          

def is_busy(debug=False):
    t0 = time.time()
    for i in range(5):
        try:
            r = requests.get(bServer + "is_busy")
            rv = r.json()['data']
            if debug: print(f'{i+1} Tries, {time.time()-t0:.3f} s')
            return rv
        except:
            rv = True
        
        time.sleep(0.5)
        
    if debug: print(f'{i+1} Tries, {time.time()-t0:0.3f} s')
    return rv


def is_SpecBusy(debug=False):
    t0 = time.time()
    
    rv = True
    
    #Read last line from SIS log
    last_line = get_sis_logs(num_entries=1)
    try:
        if ('reply' in last_line[0]) or ('Error' in last_line[0]):
            rv = False
    except:
        pass

    if debug: print(time.time() - t0)
    return rv

  
def wait_until_SPECfinished(debug=False, polling_time=1):
    while is_SpecBusy():
        time.sleep(polling_time)
        if not is_busy():
            break
        
    return
      
    
def wait_until_SPECfinished_old():
    t0 = time.time()
    while True:
        try:
            r = requests.get(bServer + "is_busy")
            is_busy = r.json()['data']
        except:
            is_busy = True
            
        if is_busy is False:
            break
        
        time.sleep(1)
    return time.time() - t0


def specCommand(cmd, queue=False, debug=False):
    #if (not is_available()) or (status is 'running'):
    if (is_SpecBusy()) and (not is_available()):
        if queue:
            print('SPEC busy. Command Queued')
            wait_until_SPECfinished()
        else:
            print('SPEC not available')
            return
    
    r = requests.get(bServer + "get_remote_control")
    if debug: print(r.json())
    
    payload = {'spec_cmd': f"print '{cmd}';{cmd}"} #{UUID}'}
    r = requests.get(bServer + "execute_command", params=payload)
    if debug: 
        g = r.json()
        print(r, g['data'])
    
    #r = requests.get(bServer + "release_remote_control")
    return
    
    
def get_counter_mnemonics(debug=False):
    t0 = time.time()
    
    #Get the counters and put in dictionary
    r = requests.get(bServer + "get_all_counter_mnemonics", params={})
    counter_mnemonics = r.json()['data']
    
    if debug: print(time.time() - t0)
        
    return counter_mnemonics
        
    
def get_counter_values(debug=False):
    t0 = time.time()
    
    #Get the counters and put in dictionary
    r = requests.get(bServer + "get_all_counters", params={})
    counter_values = r.json()['data']
    
    if debug: print(time.time() - t0)
        
    return counter_values

    
def read_counters(debug=False):
    t0 = time.time()
    
    #Get the counters and put in dictionary
    counter_mnemonics = get_counter_mnemonics()
    counter_values = get_counter_values()
    
    if debug: print(time.time() - t0)

    return dict(zip(counter_mnemonics, counter_values))


def get_motor_mnemonics(debug=False):
    t0 = time.time()
    
    #Get the motor positions and put in dictionary
    r = requests.get(bServer + "get_all_motor_mnemonics", params={})
    motor_mnemonics = r.json()['data']

    if debug: print(time.time() - t0)
    
    return motor_mnemonics


def get_motor_positions(debug=False):
    t0 = time.time()
    
    #Get the motor positions and put in dictionary
    r = requests.get(bServer + "get_all_motor_positions", params={})
    motor_positions = r.json()['data']

    if debug: print(time.time() - t0)
    
    return motor_positions


def read_motors(debug=False):
    t0 = time.time()
    
    #Get the motor positions and put in dictionary
    motor_mnemonics = get_motor_mnemonics()
    motor_positions = get_motor_positions()
    
    if debug: print(time.time() - t0)
    
    return dict(zip(motor_mnemonics, motor_positions))


def get_current_scan_details(debug=False):
    t0 = time.time()
    
    #Get current scan details
    for i in range(10):
        try:
            r = requests.get(bServer + "get_current_scan_details", params={})
            if debug: print(time.time() - t0)
            return r.json()['data']
        except:
            pass
        
    return 'unknown'
    
    
def get_scan_status(debug=False):
    #Get current scan details
    try: 
        r = requests.get(bServer + "get_current_scan_details", params={})
        scan_details = r.json()['data']
        return re.search('status=(.*) ID', scan_details).group(1)
    except:
        return 'unknown'
    
    
def get_last_scan_details(debug=False):
    t0 = time.time()
    
    #Get current scan details
    while get_scan_status() != 'finished':
        time.sleep(0.1)
        
    try: 
        r = requests.get(bServer + "get_current_scan_details", params={})
        scan_details = r.json()['data']
        
        scan_type = re.search('X_lbl=(.*) Y_lbl', scan_details).group(1)
        scan_npts = re.search('pt=(.*) type', scan_details).group(1)[-3:]

        scan_name = re.search('ID=(.*) pt', scan_details).group(1)
        scan_number = find_between_r(scan_name, '_', '')
        scan_sfx = scan_name[:-len(scan_number)]

        return {'scan_type': scan_type,
                'scan_number': scan_number, 
                'scan_sfx': scan_sfx, 
                'scan_npts': scan_npts}
    except:
        return 'Cannot determine scan details'    
    

def get_user():
    t0 = time.time()
    
    #Get user name
    r = requests.get(bServer + "get_user", params={})
    user = r.json()['data']
    
    return user


def abort_command():
    #Abort - similar to Ctrl-C in SPEC
    r = requests.get(bServer + "abort_command", params={})
    result = r.json()['data']
    
    return result


def set_sis_logging(set_logging_on=True, debug=False):
    t0 = time.time()
    
    #Get current scan details
    payload = {'set_logging_on': set_logging_on}
    r = requests.get(bServer + "get_sis_logs", params=payload)
    result = r.json()['data']
    
    if debug: print(r, time.time() - t0)
    return result


def get_sis_logs(num_entries=None, debug=False):
    t0 = time.time()
    
    #Get log from SIS log
    payload = {'num_entries': num_entries}
    r = requests.get(bServer + "get_sis_logs", params=payload)
    log = r.json()['data']
    
    if debug: print(time.time() - t0)
    return log


def get_plot_points(num_pts=None, debug=False, columns=None):
    t0 = time.time()
    
    #Get log from SIS log
    payload = {'num_pts': num_pts}
    r = requests.get(bServer + "get_plot_points", params=payload)
    data = pd.DataFrame(r.json()['data'], columns=columns)
    
    if debug: print(time.time() - t0)
    
    return data