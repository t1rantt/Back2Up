import os
import sys
import ftplib
import argparse
import datetime

parser = argparse.ArgumentParser(description="Upload files to an FTP server")
parser.add_argument("-u", "--username", help="FTP username")
parser.add_argument("-p", "--password", help="FTP password")
parser.add_argument("-f", "--file", help="File containing list of file paths to upload", required=True)
parser.add_argument("-t", "--type", help="Type of backup (tot, tar, snap, inc)", choices=["tot", "tar", "snap", "inc"], required=True)
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
        for name in dirs:
            local_subdir_path = os.path.join(root, name)
            remote_subdir_path = os.path.join(remote_dir_path, local_subdir_path[len(local_dir_path)+1:])
            upload_directory(ftp, local_subdir_path, remote_subdir_path)

with ftplib.FTP() as ftp:
    ftp.connect('62.15.36.215', 8005)
    ftp.login(username, password)
    ftp.cwd(ftp_folder)

    with open(args.file) as f:
        file_paths = f.readlines()

    if args.type == "tot":
        # Implement the tot backup option here
        pass

    elif args.type == "tar":
        # Implement the tar backup option here
        pass

    elif args.type == "snap":
        # Implement the snap backup option here
        pass

    elif args.type == "inc":
        # Implement the inc backup option here
        pass

ftp.close()
