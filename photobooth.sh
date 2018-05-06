#!/bin/bash

#PHOTOBOOTH_DIR=/home/pi/photobooth

#cd "${PHOTOBOOTH_DIR}"

#if [[ $1 == "set-time" ]]; then
#  sudo python set-time.py
#fi

while true;
do
    python photobooth.py >>photobooth.log 2>>photobooth.err
    if [ $? -eq 0 ]; then
        break
    fi
    sleep 3
done

#cd -

