import os
import sys
import ftplib
import argparse

parser = argparse.ArgumentParser(description="Upload files to an FTP server")
parser.add_argument("-u", "--username", help="FTP username")
parser.add_argument("-p", "--password", help="FTP password")
parser.add_argument("-f", "--file", help="File containing list of file paths to upload", required=True)
args = parser.parse_args()

username = args.username
password = args.password
file_path = args.file
ftp_folder = "/home/" + args.username + "/backups"

def upload_file(ftp, local_file_path, remote_file_name):
    with open(local_file_path, 'rb') as file:
        ftp.storbinary(f"STOR {remote_file_name}", file)

def upload_directory(ftp, local_dir_path, remote_dir_path):
    try:
        ftp.mkd(remote_dir_path)
    except ftplib.error_perm:
        pass

    for root, dirs, files in os.walk(local_dir_path):
        for name in files:
            local_file_path = os.path.join(root, name)
            remote_file_name = os.path.join(remote_dir_path, local_file_path[len(local_dir_path)+1:])
            upload_file(ftp, local_file_path, remote_file_name)

with ftplib.FTP() as ftp:
    ftp.connect('62.15.36.215', 8005)
    ftp.login(username, password)
    ftp.cwd(ftp_folder)

    with open(args.file) as f:
        file_paths = f.readlines()

    for file_path in file_paths:
        file_path = file_path.strip()
        if os.path.isdir(file_path):
            upload_directory(ftp, file_path, os.path.join(ftp_folder, os.path.basename(file_path)))
        else:
            upload_file(ftp, file_path, os.path.basename(file_path))

ftp.close()
