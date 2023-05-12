import os
import sys
import ftplib
import argparse
import datetime
import tarfile
import pytz
import smtplib
from email.mime.text import MIMEText

parser = argparse.ArgumentParser(description="Upload files to an FTP server")
parser.add_argument("-u", "--username", help="FTP username")
parser.add_argument("-m", "--mail", help="Mail to get notified to")
parser.add_argument("-p", "--password", help="FTP password")
parser.add_argument("-f", "--file", help="File containing list of file paths to upload", required=True)
parser.add_argument("-t", "--type", help="Type of backup (tot, tar, snap, inc)", choices=["tot", "tar", "snap", "inc"], required=True)
parser.add_argument("-d", "--date", help="Date for incremental backup in %d%m%y%H%M format", type=str)
args = parser.parse_args()

username = args.username
password = args.password
file_path = args.file
ftp_folder = f"backups"

def send_email_notification(subject, body):
    sender_email = 'back2upreports@gmail.com'
    receiver_email = args.mail
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = 'back2upreports@gmail.com'
    smtp_password = 'kakibcesjlasphfn'

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_username, smtp_password)
        server.sendmail(sender_email, receiver_email, message.as_string())


def upload_file(ftp, local_file_path, remote_file_name):
    with open(local_file_path, "rb") as file:
        ftp.storbinary(f"STOR {remote_file_name}", file)

def upload_directory(ftp, local_dir_path, remote_dir_path):
    try:
        ftp.mkd(remote_dir_path)
        print("Created remote directory:", remote_dir_path)
    except ftplib.error_perm as e:
        print("Failed to create remote directory:", remote_dir_path)
        print("Error:", e)
        return

    print("Uploading directory:", local_dir_path)
    print("Remote directory path:", remote_dir_path)

    for root, dirs, files in os.walk(local_dir_path):
        relative_dir_path = os.path.relpath(root, local_dir_path)
        remote_subdir_path = os.path.normpath(os.path.join(remote_dir_path, relative_dir_path))

        print("Uploading files to remote directory:", remote_subdir_path)

        try:
            ftp.mkd(remote_subdir_path)
            print("Created remote subdirectory:", remote_subdir_path)
        except ftplib.error_perm:
            pass

        for name in files:
            local_file_path = os.path.join(root, name)
            remote_file_name = os.path.join(remote_subdir_path, name)
            print("Uploading file:", local_file_path)
            print("Remote file name:", remote_file_name)
            upload_file(ftp, local_file_path, remote_file_name)

def remove_directory_recursive(ftp, remote_dir_path):
    try:
        ftp.cwd(remote_dir_path)
    except ftplib.error_perm:
        return

    file_list = ftp.nlst()

    for item in file_list:
        if item in (".", ".."):
            continue

        try:
            ftp.cwd(item)
            remove_directory_recursive(ftp, item)  # Recursive call for subdirectories
            ftp.cwd("..")
            ftp.rmd(item)  # Remove subdirectory
        except ftplib.error_perm:
            ftp.delete(item)  # Delete file

    ftp.rmd(remote_dir_path)  # Remove the parent directory


with ftplib.FTP() as ftp:
    ftp.connect('10.80.0.12', 21)
    ftp.login(username, password)
    try:
        ftp.cwd(ftp_folder)
    except ftplib.error_perm as e:
        print("Failed to change directory:", e)
        print("FTP Folder:", ftp_folder)
        print("Current working directory:", ftp.pwd())
        raise

    with open(args.file) as f:
        file_paths = f.readlines()

    if args.type == "tot":
        now = datetime.datetime.now()
        folder_name = now.strftime("%d%m%y%H%M")
        backup_folder = os.path.join(ftp_folder, folder_name)
        current_dir = ftp.pwd()
        print(f"Creating backup folder: {backup_folder}")
        print(f"Current directory: {current_dir}")
        ftp.mkd(folder_name)
        ftp.cwd(folder_name)

        for file_path in file_paths:
            file_path = file_path.strip()
            if os.path.isfile(file_path):
                remote_file_name = os.path.basename(file_path)
                upload_file(ftp, file_path, remote_file_name)
            elif os.path.isdir(file_path):
                remote_dir_name = os.path.basename(file_path)
                remote_dir_path = os.path.join("", remote_dir_name)
                print(remote_dir_path)
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
        if not args.date:
                print("No date input, use format: %d%m%y%H%M")
                sys.exit(1)
        else:
            folder_name = now.strftime("%d%m%y%H%M")

        backup_folder = os.path.join("", args.date)
        ftp.cwd(backup_folder)
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
            
                 remove_directory_recursive(ftp, os.path.basename(file_path))
                 upload_directory(ftp, file_path, os.path.basename(file_path))
                 

        
ftp.close()

if args.mail:
    subject = "Backup Complete"
    body = "The backup has been completed successfully."
    send_email_notification(subject, body)
