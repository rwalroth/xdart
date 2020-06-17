# -*- coding: utf-8 -*-
"""
@author: thampy
"""

# Standard library imports
import requests
import time
import sys

# Other imports
import uuid
import pandas as pd
import re

try:
    from xdart.utils import find_between, find_between_r
except ImportError:
    sys.path.append('C:\\Users\\Public\\repos\\xdart')
    from xdart.utils import find_between, find_between_r

#  Hard coded server address - to be changed
bServer = "http://127.0.0.1:18085/SIS/"


def create_UUID():
    """Create unique ID to identify scan

    Returns:
        str -- unique ID
    """
    unique_uuid = uuid.uuid4().hex[:8].upper()
    return unique_uuid


def is_available(debug=False):
    """Check if SPEC is available to send commands.

    Keyword Arguments:
        debug {bool} --  Prints out SIS message if true (default: {False})

    Returns:
        bool -- True/False
    """
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
    """Another way to check if SPEC is available to send commands.

    Keyword Arguments:
        debug {bool} --  Prints out SIS message if true (default: {False})

    Returns:
        bool -- True/False
    """
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
    """Yet another way to heck if SPEC is busy.
    SpecInfoServer doesn't always track SPEC status well. 
    So it's good to try out different ways to make sure
 
    Keyword Arguments:
        debug {bool} --  Prints out SIS message if true (default: {False})

    Returns:
        bool -- True/False
    """
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
    """"Wait till SPEC finishes executing current command.
    

    Keyword Arguments:
        debug {bool} -- Print output of SIS command if true (default: {False})
        polling_time {float} -- Time to eait before querying again (default: {1})
    """
    while is_SpecBusy():
        time.sleep(polling_time)
        if not is_busy():
            break
        
    return
      
    
def wait_until_SPECfinished_old():
    """Deprecated"""
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


def specCommand(cmd, queue=False, debug=False, print_console=True):
    """Function to send command to SPEC through SIS

    Arguments:
        cmd {str} -- SPEC command

    Keyword Arguments:
        queue {bool} -- Flag to enable queueing of command (default: {False})
        debug {bool} -- Flag to show output of SIS (default: {False})
        print_console {bool} -- Flag to print output to console (default: {True})
    """
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
        
    payload = {'spec_cmd': f"{cmd}"}
    if print_console:
        payload = {'spec_cmd': f"print '{cmd}';{cmd}"}
    r = requests.get(bServer + "execute_command", params=payload)
    if debug: 
        g = r.json()
        print(r, g['data'])
    
    print('Executed', '\n')
    #r = requests.get(bServer + "release_remote_control")
    return
    
    
def get_counter_mnemonics(debug=False):
    """Get the names of counters (Monitor, PD1 etc.)

    Keyword Arguments:
        debug {bool} -- Print output of SIS command (default: {False})

    Returns:
        [str] -- List of counter names (Monitor, PD1 etc.)
    """
    t0 = time.time()
    
    #Get the counters and put in dictionary
    r = requests.get(bServer + "get_all_counter_mnemonics", params={})
    counter_mnemonics = r.json()['data']
    
    if debug: print(time.time() - t0)
        
    return counter_mnemonics
        
    
def get_counter_values(debug=False):
    """Get the values of counters (Monitor, PD1 etc.)

    Keyword Arguments:
        debug {bool} -- Print output of SIS command (default: {False})

    Returns:
        [float] -- List of counter values
    """
    t0 = time.time()
    
    #Get the counters and put in dictionary
    r = requests.get(bServer + "get_all_counters", params={})
    counter_values = r.json()['data']
    
    if debug: print(time.time() - t0)
        
    return counter_values

    
def read_counters(debug=False):
    """Return dictionary containing counter names and values

    Keyword Arguments:
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        dict -- counter names and values
    """
    t0 = time.time()
    
    #Get the counters and put in dictionary
    counter_mnemonics = get_counter_mnemonics()
    counter_values = get_counter_values()
    
    if debug: print(time.time() - t0)

    return dict(zip(counter_mnemonics, counter_values))


def get_motor_mnemonics(debug=False):
    """Get the names of motors

    Keyword Arguments:
        debug {bool} -- Print output of SIS command (default: {False})

    Returns:
        [str] -- List of motor names
    """
    t0 = time.time()
    
    #Get the motor positions and put in dictionary
    r = requests.get(bServer + "get_all_motor_mnemonics", params={})
    motor_mnemonics = r.json()['data']

    if debug: print(time.time() - t0)
    
    return motor_mnemonics


def get_motor_positions(debug=False):
    """Get the values of motors

    Keyword Arguments:
        debug {bool} -- Print output of SIS command (default: {False})

    Returns:
        [float] -- List of motor values
    """
    t0 = time.time()
    
    #Get the motor positions and put in dictionary
    r = requests.get(bServer + "get_all_motor_positions", params={})
    motor_positions = r.json()['data']

    if debug: print(time.time() - t0)
    
    return motor_positions


def read_motors(debug=False):
    """Return dictionary containing motor names and values

    Keyword Arguments:
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        dict -- motor names and values
    """
    t0 = time.time()
    
    #Get the motor positions and put in dictionary
    motor_mnemonics = get_motor_mnemonics()
    motor_positions = get_motor_positions()
    
    if debug: print(time.time() - t0)
    
    return dict(zip(motor_mnemonics, motor_positions))


def get_current_scan_details(debug=False):
    """Get details of current scan

    Keyword Arguments:
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        str -- scan status (busy, done, unknown)
    """
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
    """Get details of current scan

    Keyword Arguments:
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        str -- scan status (busy, done, unknown)
    """
    #Get current scan details
    try: 
        r = requests.get(bServer + "get_current_scan_details", params={})
        scan_details = r.json()['data']
        return re.search('status=(.*) ID', scan_details).group(1)
    except:
        return 'unknown'
    
    
def get_last_scan_details(debug=False):
    """Get details of last finished scan

    Keyword Arguments:
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        dict -- scan details (scan_type, scan_number, scan_sfx, scan_pts)
    """
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
    """Return name of current SPEC user

    Returns:
        str -- SPEC user name
    """
    t0 = time.time()
    
    #Get user name
    r = requests.get(bServer + "get_user", params={})
    user = r.json()['data']
    
    return user


def abort_command():
    """Abort current command

    Returns:
        str -- Result of abort command returned by SIS
    """
    #Abort - similar to Ctrl-C in SPEC
    r = requests.get(bServer + "abort_command", params={})
    result = r.json()['data']
    
    return result


def set_sis_logging(set_logging_on=True, debug=False):
    """Enable SIS logging that is useful for debugging

    Keyword Arguments:
        set_logging_on {bool} -- Enables logging (default: {True})
        debug {bool} -- Print output of SIS command to enable logging (default: {False})

    Returns:
        str -- result of SIS command to enable logging (success/fail)
    """
    t0 = time.time()
    
    #Get current scan details
    payload = {'set_logging_on': set_logging_on}
    r = requests.get(bServer + "get_sis_logs", params=payload)
    result = r.json()['data']
    
    if debug: print(r, time.time() - t0)
    return result


def get_sis_logs(num_entries=None, debug=False):
    """Get last num_entries lines of SIS log. Returns the whole log if num_entries is None

    Keyword Arguments:
        num_entries {int} -- Last number of lines of log to return (default: {None})
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        [str] -- Lines of SIS log
    """
    t0 = time.time()
    
    #Get log from SIS log
    payload = {'num_entries': num_entries}
    r = requests.get(bServer + "get_sis_logs", params=payload)
    log = r.json()['data']
    
    if debug: print(time.time() - t0)
    return log


def get_plot_points(num_pts=None, debug=False, columns=None):
    """Return all the values recorded for scan points. The last num_pts are
    reported. If num_pts is None, the entire last scan is reported 

    Keyword Arguments:
        num_pts {int} -- Number of scan points to report (default: {None})
        debug {bool} -- Print output of SIS command if True (default: {False})
        columns {[str]} -- list of column values to return (default: {None})

    Returns:
        pandas dataframe -- dataframe containing columns and related values
    """
    t0 = time.time()
    
    #Get log from SIS log
    payload = {'num_pts': num_pts}
    r = requests.get(bServer + "get_plot_points", params=payload)
    data = pd.DataFrame(r.json()['data'], columns=columns)
    
    if debug: print(time.time() - t0)
    
    return data


def get_spec_result(debug=False):
    """Return result of last SPEC command

    Keyword Arguments:
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        str -- Result of last scan command
    """
    t0 = time.time()
    
    #Get log from SIS log
    payload = {}
    r = requests.get(bServer + "retrieve_result", params=payload)
    log = r.json()['data']
    
    if debug: print(time.time() - t0)
    return log


def get_console_output(idx=1, debug=False):
    """Return the console output for idx number of lines

    Keyword Arguments:
        idx {int} -- Number of lines of console output to return (default: {1})
        debug {bool} -- Print output of SIS command if true (default: {False})

    Returns:
        [str] -- Console output
    """
    t0 = time.time()
    
    #Get log from SIS log
    payload = {'N': idx}
    r = requests.get(bServer + "get_console_output_buffer", params=payload)
    log = r.json()['data']
    
    if debug: print(time.time() - t0)
    return log