import cv2
import os
import glob
import numpy as np
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import cv2
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
import time
from flask_mysqldb import MySQL
import pymysql
from datetime import datetime

#remmember to convert the image to about 400X400 for easy and fast processing
from googleapiclient.http import MediaFileUpload
import face_recognition
class core:
    def image_w():
        return 450
    
    def image_h():
        return 450
    
    def drive_folder_id():
        id="13boG4AzmmaMC7lnPJ3cwBmScsMMxPkfD"
        return id
    
    def checkin_drive_folder_id():
        id="1MaXa1sZhUbe2d1loM0hV_5M0ZayWBiAA"
        return id
    
    def create_service():
        # If modifying these scopes, delete the file token.json.
        SCOPES = ['https://www.googleapis.com/auth/drive']
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        try:
            service = build('drive', 'v3', credentials=creds)
            return service
        except HttpError as error:
            # TODO(developer) - Handle errors from drive API.
            print(f'An error occurred: {error}')
            return 
        
    def compare(eid,img_test,service):
        image_file_name = eid+'.jpg'

        # Search for the image file inside the folder
        results = service.files().list(
            q=f"'{core.drive_folder_id()}' in parents and name = '{image_file_name}' and trashed=false",
            fields="files(id)"
        ).execute()

        # Get the image file ID
        try:
            file_id = results['files'][0]['id']
        except:
            out='no face in database'
            return out

        # Read the image file content
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = io.BytesIO()
        downloader.write(request.execute())
        downloader.seek(0)
        img_array = np.asarray(bytearray(downloader.read()), dtype=np.uint8)
        img_val = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img_val, cv2.COLOR_BGR2RGB)
        img_encoding = face_recognition.face_encodings(rgb_img)[0]

        rgb_img = cv2.cvtColor(img_test, cv2.COLOR_BGR2RGB)
        img_encoding2 = face_recognition.face_encodings(rgb_img)[0]

        result = face_recognition.compare_faces([img_encoding], img_encoding2)
        print("Result: ", result)
        if(result[0]==True):
            out='recognize'
        else:
            out='Not recognize'
        return out
    
    def preprocess_image (img):
        dim = (core.image_w(), core.image_h())
        # resize image
        resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
        return resized

    def upload_image(eid, img, service):
        # Resize image
        resized = core.preprocess_image(img)
        cv2.imwrite('holder.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 100])
        image_id = eid + '.jpg'

        file_metadata = {
            'name': image_id,
            'parents': [core.drive_folder_id()]
        }

        media = MediaFileUpload('holder.jpg', mimetype='image/jpeg')

        # Check if a file with the same name already exists
        response = service.files().list(q=f"name='{image_id}' and trashed=false").execute()
        existing_files = response.get('files', [])

        if existing_files:
            # Update the existing file with the new content
            file = existing_files[0]
            request = service.files().update(
                fileId=file['id'],
                media_body=media
            )
            request.execute()
            id = file['id']
        else:
            # Create a new file
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            id = file.get("id")

        return id
    
    def upload_check_in_image(eid,img,service,check):
        # resize image
        resized = core.preprocess_image(img)
        cv2.imwrite('holder.jpeg', resized, [cv2.IMWRITE_JPEG_QUALITY, 100])
        image_id=core.get_check_in_name(eid,check)

        file_metadata = {'name': image_id,
                        'parents' :[core.checkin_drive_folder_id()]}
        media = MediaFileUpload('holder.jpeg',
                                mimetype='image/jpeg')
        # pylint: disable=maybe-no-member
        file = service.files().create(body=file_metadata, media_body=media,
                                    fields='id').execute()
        id=file.get("id")
        return id
    
    def create_cursor():
        db = pymysql.connect(host='khoaluandb.cx4dxwmzciis.ap-southeast-1.rds.amazonaws.com', user='admin', password='1709hung2000', database='khoaluan')
        cur = db.cursor(pymysql.cursors.DictCursor)
        return cur
    
    def total_user(cur):
        cur.execute('SELECT COUNT(*) AS COUNT FROM Auth_user')
        total = cur.fetchone()
        total=int(total['COUNT'])
        return total
    
    def has_user_check_in(cur,eid):
        # Execute multiple statements separately
        cur.execute('USE khoaluan')
        cur.execute('CALL CheckLastEvent(%s, @result, @lastEventTime)', (eid,))
        cur.execute('SELECT @result AS result, @lastEventTime AS lastEventTime;')
        total = cur.fetchone()
        if(total):
            result=str(total['result'])
            time=str(total['lastEventTime'])
        else :
            result='No Employee has that id'
            time='0000-00-00 00:00:00'
        return result,time
    
    def check_in_out(cur,eid,check,service,image):
        if check=='check_in':
            imid=core.upload_check_in_image(eid,image,service,check)
            cur.execute('USE khoaluan')
            cur.execute('INSERT INTO Event (Employee_ID, Event_Time, Event_Type_ID, Image_ID, Created_at, Updated_at) VALUES (%s, NOW(), 1, %s, NOW(), NOW())',(eid,imid,))
            cur.commit()
            status='successfully check in'
            return status
        elif check=='check_out':
            imid=core.upload_check_in_image(eid,image,service,check)
            cur.execute('USE khoaluan')
            cur.execute('INSERT INTO Event (Employee_ID, Event_Time, Event_Type_ID, Image_ID, Created_at, Updated_at) VALUES (%s, NOW(), 2, %s, NOW(), NOW())',(eid,imid,))
            cur.commit()
            status='successfully check out'
            return status
        
    def get_check_in_name(eid,check):
        # datetime object containing current date and time
        now = datetime.now()
        # dd/mm/YY H:M:S
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        combined=eid+check+dt_string+'.jpg'
        return combined
