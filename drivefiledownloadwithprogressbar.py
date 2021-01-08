# import the required libraries 
from __future__ import print_function 
import pickle 
import os
import os.path 
import io 
import shutil 
import requests 
import json
import hashlib
import sys
import configparser
from tqdm import tqdm
from mimetypes import MimeTypes 
from googleapiclient.discovery import build 
from google_auth_oauthlib.flow import InstalledAppFlow 
from google.auth.transport.requests import Request 
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload 
  
class DriveAPI: 
    global SCOPES 
      
    # Define the scopes 
    SCOPES = ['https://www.googleapis.com/auth/drive'] 
    #SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
  
    def __init__(self): 
        
        # Variable self.creds will 
        # store the user access token. 
        # If no valid token found 
        # we will create one. 
        self.creds = None
  
        # The file token.pickle stores the 
        # user's access and refresh tokens. It is 
        # created automatically when the authorization 
        # flow completes for the first time. 
  
        # Check if file token.pickle exists 
        if os.path.exists('token.pickle'): 
  
            # Read the token from the file and 
            # store it in the variable self.creds 
            with open('token.pickle', 'rb') as token: 
                self.creds = pickle.load(token) 
  
        # If no valid credentials are available, 
        # request the user to log in. 
        if not self.creds or not self.creds.valid: 
  
            # If token is expired, it will be refreshed, 
            # else, we will request a new one. 
            if self.creds and self.creds.expired and self.creds.refresh_token: 
                self.creds.refresh(Request()) 
            else: 
                flow = InstalledAppFlow.from_client_secrets_file( 
                    'credentials (1).json', SCOPES) 
                self.creds = flow.run_local_server(port=0) 
  
            # Save the access token in token.pickle 
            # file for future usage 
            with open('token.pickle', 'wb') as token: 
                pickle.dump(self.creds, token) 
  
        # Connect to the API service 
        self.service = build('drive', 'v3', credentials=self.creds) 
    '''
        # request a list of first N files or 
        # folders with name and id from the API. 
        results = self.service.files().list( 
            pageSize=100, fields="files(*)").execute() 
        items = results.get('files', []) 
  
        # print a list of files 
    
        print("Here's a list of files: \n") 
        print(*items, sep="\n", end="\n\n") 
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
    '''
    
    def md5(self, fname):
        if(os.path.exists(fname)):
            hash_md5 = hashlib.md5()
            with open(fname, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        else:
            return ''
            
    def queryCheckSum(self, f_path, operation=0):
        #0=normal flow
        #1=recompute hash of file even though its entry exist
        if(not os.path.exists(f_path)):
            return ''
        last_instance=f_path.rfind('\\')
        if(last_instance == -1):
            f_path='.\\'+f_path
            last_instance=f_path.rfind('\\')
        directory_name=f_path[:last_instance]
        file_name=f_path[last_instance+1:]
        checksum_file='checksum.ini'
        section_name='File Hashes'
        config = configparser.ConfigParser()
        config.read(directory_name+'\\'+checksum_file)
        if(not config.has_section(section_name)):
            config.add_section(section_name)
        if(int(operation) == 0 and config.has_option(section_name, file_name)):
            return config[section_name][file_name]
        else:
            file_hash=self.md5(f_path)
            config[section_name][file_name]=file_hash
        with open(directory_name+'\\'+checksum_file, 'w') as configfile:
            config.write(configfile)
        return config[section_name][file_name]
    
    def QueryFile(self, query=''):
        #q=u"'{0}' in parents and mimeType='application/vnd.google-apps.folder'".format(folder_id)).execute() 
        results = self.service.files().list( 
            pageSize=1000, fields="files(id,name,mimeType,md5Checksum,size)",
            q=u"{0}".format(query)).execute() 
        items = results.get('files', []) 

        return items
    
    def DownloadSyncFolder(self,folder_name,path='.',parent='',parent_id=''):
        folder_id=''
        # print a list of files 
        if(parent_id != ''):
            items = self.QueryFile(u"name='{0}' and '{1}' in parents".format(folder_name, parent_id))
        elif(parent != ''):
            items = self.QueryFile(u"name='{0}'".format(parent))
            if(len(items) != 1):
                print("result for parent is more than 1 item or no item in result")
                print(*items, sep="\n", end="\n\n")
                return
            parent_id=items[0]['id']
            items = self.QueryFile(u"name='{0}' and '{1}' in parents".format(folder_name, parent_id))
        else:
            items = self.QueryFile(u"name='{0}'".format(folder_name))
        if(len(items) != 1):
            print("Folder to be synced is more than 1 item or no item in result")
            print(*items, sep="\n", end="\n\n")
            return
        else:
            folder_id=items[0]['id']
            items = self.QueryFile(u"'{0}' in parents".format(folder_id))
            #print("Here's a list of files/folders:") 
            #print(*items, sep="\n", end="\n\n")
        for item in items:
            if(item['mimeType'] != 'application/vnd.google-apps.folder'):
                if (not (os.path.exists(path+'\\'+folder_name))):
                    os.makedirs(path+'\\'+folder_name)
                '''
                try:
                    os.makedirs(path+'\\'+folder_name)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                '''
                #get items in folder and download
                if(item['md5Checksum'] != self.queryCheckSum(path+'\\'+folder_name+'\\'+item['name'], 0)):
                    if os.path.exists(path+'\\'+folder_name+'\\'+item['name']):
                        os.remove(path+'\\'+folder_name+'\\'+item['name'])
                    self.FileDownload(item['id'], path+'\\'+folder_name+'\\'+item['name'], item['size'])
                    print(u'Hash for "{}" is {}'.format(item['name'], self.queryCheckSum(path+'\\'+folder_name+'\\'+item['name'], 1)))
            else:
                self.DownloadSyncFolder(item['name'], path+'\\'+folder_name, folder_name, folder_id)
        #print("Here's a list of files/folders: \n") 
        #print(*items, sep="\n", end="\n\n")
        #print(items[0]['id'])
        #print(path)
    
    def FileDownload(self, file_id, file_name, total_size=204800): 
        request = self.service.files().get_media(fileId=file_id) 
        fh = io.FileIO(file_name, "wb") 
        size=(int)(total_size)
        if(size > 104857600):#11048576 is 1 MB
            size = size/10
        else:
            size = size/4
        # Initialise a downloader object to download the file 
        downloader = MediaIoBaseDownload(fh, request, chunksize=size) 
        done = False
  
        try: 
            # Download the data in chunks 
            '''
            with click.progressbar(length=100, label='Downloading '+file_name) as bar:
                pstatus = 1
                bar.update(int(pstatus))
                while not done: 
                    status, done = downloader.next_chunk()
                    status = int(status.progress() * 100)
                    if(int(status) > 1):
                        bar.update(int(status - pstatus))
                        pstatus = status
            '''
            with tqdm(total=int(total_size), unit='B', unit_scale=True, unit_divisor=1024, maxinterval=3, miniters=0) as bar:
                pstatus = 0
                bar.monitor_interval = 3
                bar.write(u"Downloading {0}".format(file_name))
                bar.update(int(pstatus))
                bar.refresh()
                while not done: 
                    status, done = downloader.next_chunk()
                    #status = int(status.progress() * 100)
                    status = int(status.resumable_progress)
                    bar.update(int(status - pstatus))
                    bar.refresh()
                    pstatus = status
            fh.seek(0) 

            print(u"Downloaded {0}".format(file_name)) 
            # Return True if file Downloaded successfully 
            return True
        except Exception as e: 
            
            # Return False if something went wrong
            print(sys.exc_info())            
            #print("Something went wrong.") 
            return False
  
    def FileUpload(self, filepath): 
        
        # Extract the file name out of the file path 
        name = filepath.split('/')[-1] 
          
        # Find the MimeType of the file 
        mimetype = MimeTypes().guess_type(name)[0] 
          
        # create file metadata 
        file_metadata = {'name': name} 
  
        try: 
            media = MediaFileUpload(filepath, mimetype=mimetype) 
              
            # Create a new file in the Drive storage 
            file = self.service.files().create( 
                body=file_metadata, media_body=media, fields='id').execute() 
              
            print("File Uploaded.") 
          
        except: 
              
            # Raise UploadError if file is not uploaded. 
            raise UploadError("Can't Upload File.") 
  
if __name__ == "__main__": 
    obj = DriveAPI()
    while(True):
        try:
            i = int(input("Enter your choice: 0- Exit, 1 - Download file, 2- Upload File, 3- Download Sync Folder, 4- MD5 of file., 5-Query file\n")) 
              
            if i == 1: 
                f_id = input("Enter file id: ") 
                f_name = input("Enter file name: ") 
                f_size = input("Enter file size in bytes (Optional): ")
                obj.FileDownload(f_id, f_name, f_size) 
                  
            elif i == 2: 
                f_path = input("Enter full file path: ") 
                obj.FileUpload(f_path)
                
            elif i == 3: 
                f_name = input("Enter full folder name: ") 
                f_parent = input("Enter full parent folder name (Optional): ") 
                obj.DownloadSyncFolder(f_name,parent=f_parent)
                
            elif i == 4: 
                f_name = input("Enter file_name: ") 
                print(obj.md5(f_name))
              
            elif i == 5:
                q = input("Enter query: ")
                items = obj.QueryFile(q)
                print(*items, sep="\n", end="\n\n")
            else: 
                exit() 
        except Exception as e:
            print(sys.exc_info())