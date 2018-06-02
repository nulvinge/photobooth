#!/bin/bash

#PHOTOBOOTH_DIR=/home/pi/photobooth

#cd "${PHOTOBOOTH_DIR}"

#if [[ $1 == "set-time" ]]; then
#  sudo python set-time.py
#fi

rm photobooth.log
rm photobooth.err

#while true;
#do
    service bluetooth restart
    python photobooth.py >>photobooth.log 2>>photobooth.err
#    if [ $? -eq 0 ]; then
#        break
#    fi
#    sleep 3
#done

#cd -

