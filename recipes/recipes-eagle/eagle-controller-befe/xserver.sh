#!/bin/sh

# X send a USR1 signal to its parent (if USR1 signal is ignore in its own process) to warn that it is ready to receive connection 
# So we launched it in a subshell and wait for USR1 signal before starting other graphical processes
# https://www.x.org/archive/X11R6.8.1/doc/Xserver.1.html#sect11

sigusr1_handler()
{
   echo "USR1 signal received from X : Server started and ready to receive connection"
}
trap 'sigusr1_handler' USR1 

# In a subprocess:
# trap '' USR1   : ignore USR1 signal
# exec X .... : replace the current shell by X process to keep the USR1 signal ignored
# X options
# -wr : white background
# -nolisten tcp : disable remote access
# -novtswitch : disable virtual terminal switch
( trap '' USR1; exec X -nocursor -wr -nolisten tcp -novtswitch )&

# Wait will be interrupted by the USR1 signal send by XServer
XSERVER_PID=$!
echo "Wait for X server to be ready to receive connections"
wait $XSERVER_PID

export DISPLAY=:0

# Force no border for created window (that removes the border created when "display" command is used to display images)
xrdb -retain -merge << EOF
*borderWidth:0
EOF

# Display a background empty image waiting for eagle to start
# -size 320x240 : force fullscreen
# -window root : set image on root window background and exit
# The final '; true' ensure that the return value of the script is 0. It is
# needed because the 'display' command return 1 and systemd take it as a failure
display -size 320x240 -window root /home/root/images/HACH_SPLASH_320x240.bmp; true
