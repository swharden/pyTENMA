"""quick and dirty demo how to plot a text file log."""
import pylab
import numpy as np
#import datetime
if __name__=="__main__":
    with open("log.txt") as f:
        raw=f.read()
    raw=raw.split("\n#")[-1] # select the last log session
    raw=raw.strip().split("\n") # make it multiline (easy for data conversion)
    timestamp,data=raw[0],np.array(raw[1:]).astype(np.float) # data is now np
    #timestamp=int(timestamp.strip().split(" ")[1]) # epoch seconds
    #start=datetime.datetime.fromtimestamp(timestamp) # datetime object
    
    # we have our data as a numpy array ready for plotting
    # we have the start time we could use for the X axis if we wanted to
    print("Plotting data:", data) # we now have the data ready to plot
    pylab.figure(figsize=(6,4))
    pylab.grid(alpha=.5)
    pylab.title("pyTENMA Demo Data")
    pylab.ylabel("measurement (V)")
    pylab.xlabel("experiment duration (min)")
    Xs=np.arange(len(data))/60.0
    pylab.plot(Xs,data,alpha=.5)
    pylab.margins(0,.1)
    pylab.axhline(0,color='r',lw=2,alpha=.5,ls="--")
    pylab.axhline(5,color='r',lw=2,alpha=.5,ls="--")
    pylab.tight_layout()
    pylab.savefig("logDemo.png",dpi=300) # save it to disk
    #pylab.show() # launch an interactive plot
    print("DONE")
    
    
