# Iiwari-demo
The goal of this repo is to capture video events from a raspberry pi when a tag reaches a specified area and send the
video back to a server.

## Tech
Iiwari-demo uses a number of open source projects to work properly:
- [python3](https://www.python.org/) - utilize the OpenCV library
- [OpenCV](https://opencv.org/) - handle camera operations such as saving video frames to a buffer
- [websockets](https://websockets.readthedocs.io/en/stable/) - provide full-duplex communication channels over a single TCP connection
- [websocket-client](https://pypi.org/project/websocket-client/) - a library iiwari used for broadcasting data streams of tag positions
- [ftplib](https://docs.python.org/3/library/ftplib.html) - a library for handling data transfers via FTP
- [pymysql](https://pypi.org/project/PyMySQL/) - handle mysql operations with python

## Setup
Make sure your hostname is *dev-iiwari*.  
RPI clients will connect to *dev-iiwari.local* instead of an ip_address that changes constantly.

Make sure you have MySQL installed.
Create a database called *iiwari_db*.
```sh
sudo mysql
CREATE DATABASE iiwari_db;
```
Create table *trigger_table* for storing trigger data in *iiwari_db*.
```sh
USE iiwari_db;
CREATE TABLE trigger_table (
    id int NOT NULL,
    camera varchar(255) NOT NULL,
    trigger_position json NOT NULL,
    trigger_threshold int NOT NULL,
    clip_duration int NOT NULL,
    tag_delay int NOT NULL,
    PRIMARY KEY (id)
);
```
Create table *camera_table* for storing camera data in *iiwari_db*.
```sh
USE iiwari_db;
CREATE TABLE camera_table (
    camera varchar(255) NOT NULL,
    camera_position json NOT NULL,
    camera_fov int NOT NULL,
);
```

Iiwari-demo requires **pip3** (Python's package manager) to install the dependencies.  
Instructions for pip3 [installation](https://www.educative.io/edpresso/installing-pip3-in-ubuntu).
If pip3 is installed, run these commands:
```sh
cd iiwari-demo
pip3 install -r requirements.txt
```

Iiwari-demo requires Python3.x to run the scripts successfully.  
Instructions for Python3 [installation](https://docs.python-guide.org/starting/install3/linux/).

## RUN DEMO WITH MOUSE SIMULATOR
1. In a new terminal, run mouse_sim.
```sh
cd iiwari-demo
python3 mouse_sim.py
```
Any trigger points will be drawn to a window *Room Layout*.  
Move mouse to window *Room Layout* to start tracking mouse position relative to window.

2. Set **USE_MOUSE_SIM** to true. In a new terminal, run broadcaster.
```sh
cd iiwari-demo
python3 broadcaster.py
```
Connect to websocket server in mouse_sim.  
Start its own websocket server for handling RPI clients and sending commands.

3. In a raspberry pi terminal, run rpi.
```sh
cd iiwari-demo
python3 rpi.py
```
Connect to websocket server in broadcaster.  
Capture videos and save it to a buffer.


## Hardware requirements
- Screen - visualise windows
- Keyboard - type to run scripts
- Mouse - when using mouse_sim.py
- RPI with a camera - run rpi
