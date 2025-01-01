#!/usr/bin/with-contenv bashio

TVIP=$(bashio::config 'tv')
SUBFOLDER=$(bashio::config 'subfolder')
FILTER=$(bashio::config 'filter')
MATTE=$(bashio::config 'matte')
MATTE_COLOR=$(bashio::config 'matte_color')

mkdir -p /media/frame
echo "Using ${TVIP} as the IP of the Samsung Frame"
echo "Subfolder ${SUBFOLDER} as image folder"
python3 art.py --ip ${TVIP} --subfolder ${SUBFOLDER} --filter ${FILTER} --matte ${MATTE} --matte-color ${MATTE_COLOR}
echo "done, closing now!"
kill -s SIGHUP 1

