import os
import sys
import ftplib
import argparse
import datetime
import tarfile
import pytz

parser = argparse.ArgumentParser(description="Upload files to an FTP server")
parser.add_argument("-u", "--username", help="FTP username")
parser.add_argument("-p", "--password", help="FTP password")
parser.add_argument("-f", "--file", help="File containing list of file paths to upload", required=True)
parser.add_argument("-t", "--type", help="Type of backup (tot, tar, snap, inc)", choices=["tot", "tar", "snap", "inc"], required=True)
parser.add_argument("-d", "--date", help="Date for incremental backup in %d%m%y%H%M format", type=str, required=True)
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
        now = datetime.datetime.now()
        folder_name = now.strftime("%d%m%y%H%M")
        backup_folder = os.path.join(ftp_folder, folder_name)
        ftp.mkd(backup_folder)
        ftp.cwd(backup_folder)

        for file_path in file_paths:
            file_path = file_path.strip()
            if os.path.isfile(file_path):
                remote_file_name = os.path.basename(file_path)
                upload_file(ftp, file_path, remote_file_name)
            elif os.path.isdir(file_path):
                remote_dir_name = os.path.basename(file_path)
                remote_dir_path = os.path.join(backup_folder, remote_dir_name)
                upload_directory(ftp, file_path, remote_dir_path)

    elif args.type == "tar":
        now = datetime.datetime.now()
        tarball_name = now.strftime("%d%m%y%H%M") + ".tar.gz"
        tarball_path = os.path.join(os.getcwd(), tarball_name)

        with tarfile.open(tarball_path, "w:gz") as tar:
            for file_path in file_paths:
                file_path = file_path.strip()
                if os.path.isfile(file_path) or os.path.isdir(file_path):
                    tar.add(file_path, arcname=os.path.basename(file_path))

        upload_file(ftp, tarball_path, tarball_name)
        os.remove(tarball_path)

    elif args.type == "snap":
        pass

    elif args.type == "inc":
        now = datetime.datetime.now()
        if args.date:
            try:
                datetime.datetime.strptime(args.date, "%d%m%y%H%M")
            except ValueError:
                print("Invalid date format. Use %d%m%y%H%M")
                sys.exit(1)
            folder_name = args.date
        else:
            folder_name = now.strftime("%d%m%y%H%M")

        backup_folder = os.path.join(ftp_folder, folder_name)

        try:
            ftp.cwd(backup_folder)
        except ftplib.error_perm:
            folder_name = now.strftime("%d%m%y%H%M")
            backup_folder = os.path.join(ftp_folder, folder_name)
            ftp.cwd(ftp_folder)
            ftp.mkd(backup_folder)
            ftp.cwd(backup_folder)
    
            for file_path in file_paths:
                file_path = file_path.strip()
                if os.path.isfile(file_path):
                    remote_file_name = os.path.basename(file_path)
                    upload_file(ftp, file_path, remote_file_name)
                elif os.path.isdir(file_path):
                    remote_dir_name = os.path.basename(file_path)
                    remote_dir_path = os.path.join(backup_folder, remote_dir_name)
                    upload_directory(ftp, file_path, remote_dir_path)
        else:
            for file_path in file_paths:
                file_path = file_path.strip()
                if os.path.isfile(file_path):
                    remote_file_name = os.path.basename(file_path)
                    local_mtime = os.path.getmtime(file_path)
                    local_mtime_utc = datetime.datetime.utcfromtimestamp(local_mtime).replace(tzinfo=pytz.UTC)
    
                    try:
                        remote_mtime = ftp.sendcmd(f"MDTM {remote_file_name}").split()[-1]
                        remote_mtime = datetime.datetime.strptime(remote_mtime, "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                    except ftplib.error_perm:
                        remote_mtime = None
    
                    if not remote_mtime or local_mtime_utc > remote_mtime:
                        upload_file(ftp, file_path, remote_file_name)
                elif os.path.isdir(file_path):
                    remote_dir_name = os.path.basename(file_path)
                    remote_dir_path = os.path.join(backup_folder, remote_dir_name)
                    upload_directory(ftp, file_path, remote_dir_path)
        
ftp.close()
