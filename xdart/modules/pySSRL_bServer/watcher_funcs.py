import re
from helper_funcs import find_between

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
    
 
def get_from_pdi2(pdi_file):

    with open(pdi_file, 'r') as f:
        pdi_data = f.read()
        
    counters = find_between(pdi_data, 'All Counters\n', '\n\n# All Motors')
    cts = re.split('\n|=', counters)
    Counters = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}

    motors = find_between(pdi_data, 'All Motors\n', '\n#')
    cts = re.split('\n|=', motors)
    Motors = {c.split()[0]: float(cs) for c, cs in zip(cts[::2], cts[1::2])}

    return Counters, Motors