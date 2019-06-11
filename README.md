# ImageDetectionHW2  

HOG + SVM Object Detect Implementation on FPGA  
Target device is Ultra96(rev1). The version of Vivado and Vivado HLS is 2018.2.  
In this project, the system detects red traffic signal from USB webcam captured image in real time.  
- HLS IP Latency: min:153838 max:196936 (not fully pipelined)  
- Achieved FPS: 142fps (including DMA data transmission time)  

## usage  



## file description  
### data  
Training data. This files are used `python/vdtools.py`  
### python  
python and scikit-learn library are used to train, verify accuracy and export trained weight to cpp header file.  
### hls  
HOG + SVM Vivado HLS project.
### vivado  
Vivado project contains Vivado HLS synthesized-IP.
### cpp  
Some SW-level applications to verify porting from python to C++.  
### overlay  
In this repo, fpga is configured by Linux Device Tree Overlay function.  
This directory contains device tree file and shell script running device tree overlay.  
### sw  
These application only works on Ultra96, containing interface layer to call FPGA IP.

### util  
Utility program.

##reference  

