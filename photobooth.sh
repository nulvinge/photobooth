#!/bin/bash

#PHOTOBOOTH_DIR=/home/pi/photobooth

#cd "${PHOTOBOOTH_DIR}"

#if [[ $1 == "set-time" ]]; then
#  sudo python set-time.py
#fi

rm log
rm err

for i in {1..10}
do
    service bluetooth restart
    sleep 10
    python -u photobooth.py >>log 2>>err
    #if [ $? -eq 0 ]; then
    #    break
    #fi
    sleep 1
    killall python gatttool
    sleep 10
done

sleep 120
reboot

#cd -

