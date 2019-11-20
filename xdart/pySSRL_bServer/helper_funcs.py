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