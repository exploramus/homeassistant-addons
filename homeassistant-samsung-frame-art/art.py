import sys
import random
import json
import os
import asyncio
import logging
import argparse
from PIL import Image, ImageOps

from samsungtvws.async_art import SamsungTVAsyncArt
from samsungtvws import exceptions

class StateData:
    def __init__(self, last_content_id=None, uploaded_photos=None):
        self.LastContentID = last_content_id
        self.Uploaded_Photos = uploaded_photos if uploaded_photos is not None else []

    def to_dict(self):
        return {
            "LastContentID": self.LastContentID,
            "Uploaded_Photos": self.Uploaded_Files
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            last_content_id=data.get("LastContentID"),
            uploaded_photos=data.get("Uploaded_Files", [])
        )

def load_state_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            data = json.load(file)
            return UploadData.from_dict(data)
    return UploadData()

def save_state_data(filepath, upload_data):
    with open(filepath, 'w') as file:
        json.dump(upload_data.to_dict(), file)


def parseargs():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Example async art Samsung Frame TV.')
    parser.add_argument('--ip', action="store", type=str, default=None, help='ip address of TV (default: %(default)s))')
    parser.add_argument('--subfolder', action="store", type=str, default=None, help='subfolder to display (default: %(default)s))')
    parser.add_argument('--filter', action="store", type=str, default="none", help='photo filter to apply (default: %(default)s))')
    parser.add_argument('--matte', action="store", type=str, default="none", help='matte to apply (default: %(default)s))')
    parser.add_argument('--matte-color', action="store", type=str, default="black", help='matte color to apply (default: %(default)s))')
    return parser.parse_args()
    

async def main():
    # Set log level
    logging.basicConfig(level=logging.INFO) #or logging.DEBUG to see messages

    sys.path.append('../')

    # Parse command line parameters
    args = parseargs()
    logging.info('Parameters: {}'.format(args))

    # Set the path to the folder containing the images
    folder_path = '/media/frame'
    logging.info('Folder is (1): {}'.format(folder_path))
    if args.subfolder:
        if args.subfolder != "":
            folder_path = os.path.join(folder_path, args.subfolder)
    logging.info('Folder is (2): {}'.format(folder_path))

    # Set the path to the file containing the state of the addon 
    state_json_path = '/data/frame_switcher_state.json'

    # Load the state of the addon (last 5 uploaded pictures & last content ID)
    frame_state = load_state_data(state_json_path)
    if not frame_state:
        frame_state = StateData()
    logging.info('frame addon state: {}'.format(frame_state))
    
    # Get the list of all photos in the folder
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    if len(files) > 5:
        # Exclude the photos on the uploaded list
        available_files = [f for f in files if f not in frame_state.Uploaded_Photos]

        # Select a random photo from the available files
        selected_photo = random.choice(available_files)
    else:
        selected_photo = random.choice(files)


    matte = args.matte
    matte_color = args.matte_color

    # Set the matte and matte color

    if matte != 'none':
        matte_var = f"{matte}_{matte_color}"
    else:
        matte_var = matte

    tv = SamsungTVAsyncArt(host=args.ip, port=8002)
    await tv.start_listening()

    supported = await tv.supported()
    if supported:
        logging.info('This TV is supported')

    else:
        logging.info('This TV is not supported')
   
    if supported:
        try:
            # is tv on (calls tv rest api)
            tv_on = await tv.on()
            logging.info('tv is on: {}'.format(tv_on))
            
            # is art mode on
            # art_mode = await tv.get_artmode()                  # calls websocket command to determine status
            art_mode = tv.art_mode                              # passive, listens for websocket messages to determine art mode status
            logging.info('art mode is on: {}'.format(art_mode))

            # get current artwork
            current = await tv.get_current()
            logging.info('current artwork: {}'.format(current))
            current_content_id = current.get('content_id', None)
            if current_content_id is None:
                logging.error('Current artwork does not have a content_id')
                return

            photos = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg'))]
            if not photos:
                logging.info('No PNG or JPG photos found in the folder')
                return
            else:
                selected_photo = photos[0]  # Assuming selected_photo is the first photo in the list
                filename = os.path.join(folder_path, selected_photo)
                new_filename = os.path.join(folder_path, os.path.basename(filename).lower())
                try:
                    os.rename(filename, new_filename)
                except FileNotFoundError:
                    logging.error('File not found: {}'.format(filename))
                    return
                filename = new_filename
                logging.info('Selected and renamed photo: {}'.format(filename))

                image = Image.open(filename)
                image = ImageOps.exif_transpose(image)
                new_image = image.resize((3840, 2160))
                new_image.save(filename)

                content_id = None
                if filename:
                    with open(filename, "rb") as f:
                        file_data = f.read()
                    file_type = os.path.splitext(filename)[1][1:] 
                    content_id = await tv.upload(file_data, file_type=file_type, matte=matte_var) 
                    logging.info('uploaded {} to tv as {}'.format(filename, content_id))
                    await tv.set_photo_filter(content_id, args.filter)

                    await tv.select_image(content_id, show=False)
                    logging.info('set artwork to {}'.format(content_id))

               
                    #delete the file that was showing before if uploaded through this script
                    #checking if current artwork was uploaded through this script
                    if current_content_id == frame_state.LastContentID:
                        await tv.delete_list([current_content_id])
                        logging.info('deleted from tv: {}'.format([current_content_id]))  

                    frame_state.Uploaded_Photos.append(selected_photo)
                    if len(frame_state.Uploaded_Photos.) > 5:
                        frame_state.Uploaded_Photos..pop(0)
                    
                    save_state_data(state_json_path,frame_state)

            await asyncio.sleep(15)

        except exceptions.ResponseError as e:
            logging.warning('ERROR: {}'.format(e))
        except AssertionError as e:
            logging.warning('no data received: {}'.format(e))

        
    await tv.close()


asyncio.run(main())
