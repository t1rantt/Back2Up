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
parser.add_argument(
    "-f", "--file", help="File containing list of file paths to upload", required=True)
parser.add_argument("-t", "--type", help="Type of backup (tot, tar, snap, inc)",
                    choices=["tot", "tar", "snap", "inc"], required=True)
parser.add_argument(
    "-d", "--date", help="Date for incremental backup in %d%m%y%H%M format", type=str)
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
    except ftplib.error_perm as e:
        return

    for root, dirs, files in os.walk(local_dir_path):
        relative_dir_path = os.path.relpath(root, local_dir_path)
        remote_subdir_path = os.path.normpath(
            os.path.join(remote_dir_path, relative_dir_path))

        try:
            ftp.mkd(remote_subdir_path)
        except ftplib.error_perm:
            pass

        for name in files:
            local_file_path = os.path.join(root, name)
            remote_file_name = os.path.join(remote_subdir_path, name)
            upload_file(ftp, local_file_path, remote_file_name)


def incremental(ftp, paths, directory, depth=0):
    ftp.cwd(directory)

    if (depth == 0):
        ftpfiles = ftp.nlst()  # ls del ftp
        for ftp_file_or_dir_name in ftpfiles:

            if ftp_file_or_dir_name not in paths:
                if is_file(ftp, ftp_file_or_dir_name):
                    ftp.delete(ftp_file_or_dir_name)
                else:
                    try:
                        ftp.rmd(ftp_file_or_dir_name)
                    except:
                        delete_dir_recursive(ftp, ftp_file_or_dir_name)

    for file_or_dir_path in paths:
        file_or_dir_path = file_or_dir_path.strip()

        if os.path.isfile(file_or_dir_path):
            remote_file_name = os.path.basename(file_or_dir_path)
            local_mtime = os.path.getmtime(file_or_dir_path)
            local_mtime_utc = datetime.datetime.utcfromtimestamp(
                local_mtime).replace(tzinfo=pytz.UTC)

            try:
                remote_mtime = ftp.sendcmd(
                    f"MDTM {remote_file_name}").split()[-1]
                remote_mtime = datetime.datetime.strptime(
                    remote_mtime, "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
            except ftplib.error_perm:
                remote_mtime = None

            if not remote_mtime or local_mtime_utc > remote_mtime:
                upload_file(ftp, file_or_dir_path, remote_file_name)

        elif os.path.isdir(file_or_dir_path):

            ftp.cwd(os.path.basename(file_or_dir_path))

            ftpfiles = ftp.nlst()  # ls del ftp
            local_files_or_dirs_names = os.listdir(
                file_or_dir_path)  # ls del local
            local_files_or_dirs_paths = []

            for child_file_or_dir_name in local_files_or_dirs_names:

                child_file_or_dir_path = os.path.join(
                    file_or_dir_path, child_file_or_dir_name)
                local_files_or_dirs_paths.append(child_file_or_dir_path)

                if child_file_or_dir_name not in ftpfiles:
                    if os.path.isfile(child_file_or_dir_path):
                        upload_file(ftp, child_file_or_dir_path,
                                    child_file_or_dir_name)
                    else:
                        upload_directory(
                            ftp, child_file_or_dir_path, child_file_or_dir_name)

            for ftp_file_or_dir_name in ftpfiles:

                if ftp_file_or_dir_name not in local_files_or_dirs_names:
                    if is_file(ftp, ftp_file_or_dir_name):
                        ftp.delete(ftp_file_or_dir_name)
                    else:
                        try:
                            ftp.rmd(ftp_file_or_dir_name)
                        except:
                            delete_dir_recursive(ftp, ftp_file_or_dir_name)

            ftp.cwd("..")
            incremental(ftp, local_files_or_dirs_paths,
                        os.path.basename(file_or_dir_path), depth+1)


def delete_dir_recursive(ftp, dirname):
    ftp.cwd(dirname)
    contents = ftp.nlst()
    for content in contents:
        if is_file(ftp, content):
            ftp.delete(content)
        else:
            try:
                ftp.rmd(content)
            except:
                delete_dir_recursive(ftp, content)

    ftp.cwd("..")
    ftp.rmd(dirname)


def is_file(ftp, filename):
    try:
        ftp.cwd(filename)
        ftp.cwd('..')
        return False
    except:
        return True

def total(ftp, folder_name, file_paths):
    backup_folder = os.path.join("backups", folder_name)
    current_dir = ftp.pwd()
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
            upload_directory(ftp, file_path, remote_dir_path)

with ftplib.FTP() as ftp:
    ftp.connect('10.80.0.12', 21)
    ftp.login(username, password)
    try:
        ftp.cwd(ftp_folder)
    except ftplib.error_perm as e:
        raise

    with open(args.file) as f:
        file_paths = f.readlines()

    if args.type == "tot":
        now = datetime.datetime.now()
        folder_name = now.strftime("%d%m%y%H%M")
        total(ftp, folder_name, file_paths)

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
        if not args.date:
            print("No date input, use format: %d%m%y%H%M")
            sys.exit(1)
        else:
            incremental(ftp, file_paths, args.date)

ftp.close()

if args.mail:
    subject = "Backup Complete"
    body = "The backup has been completed successfully."
    send_email_notification(subject, body)

