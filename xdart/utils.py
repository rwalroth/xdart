import numpy as np

def write_xye(fname, xdata, ydata):
    with open(fname, "w") as file:
        for i in range(0, len(xdata)):
            file.write(
                str(xdata[i]) + "\t" + 
                str(ydata[i]) + "\t" + 
                str(np.sqrt(ydata[i])) + "\n"
            )

def write_csv(fname, xdata, ydata):
    with open(fname, 'w') as file:
        for i in range(0, len(xdata)):
            file.write(str(xdata[i]) + ', ' + str(ydata[i]) + '\n')