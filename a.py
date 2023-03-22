import os
import subprocess
import sys

# Replace these with the appropriate values for your environment
source_disk = "/dev/sda"  # Source disk device, e.g., /dev/sda or /dev/nvme0n1
output_dir = "./"
raw_image_name = "disk_image.raw"
qcow2_image_name = "disk_image.qcow2"

# Step 1: Create a disk image using dd
try:
    raw_image_path = os.path.join(output_dir, raw_image_name)
    dd_command = f"sudo dd if={source_disk} of={raw_image_path} bs=64K conv=noerror,sync status=progress"
    subprocess.run(dd_command, shell=True, check=True)
    print(f"Raw disk image created at {raw_image_path}")
except subprocess.CalledProcessError as e:
    print(f"Error during disk image creation: {e}")
    sys.exit(1)
# Step 2: Convert the raw disk image to qcow2 format using qemu-img
try:
    raw_image_path = os.path.join(output_dir, raw_image_name)
    qcow2_image_path = os.path.join(output_dir, qcow2_image_name)
    qemu_img_command = f"qemu-img convert -f raw -O qcow2 {raw_image_path} {qcow2_image_path}"
    subprocess.run(qemu_img_command, shell=True, check=True)
    print(f"qcow2 disk image created at {qcow2_image_path}")
except subprocess.CalledProcessError as e:
    print(f"Error during disk image conversion: {e}")
    sys.exit(1)
