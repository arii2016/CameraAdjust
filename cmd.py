# coding: UTF-8

import sys, os, time
import serial
from serial.tools import list_ports
import requests
import socket

base_url = ""
SERIAL_PORT = ""
img_datas = ""

def get_command(device):
    rx_buffer = ""
    timeout = time.time()
    while True:
        if (time.time() - timeout) > 5.0:
            return "NG"
        chars = device.read()
        if chars == ",":
            break
        rx_buffer += chars
    return rx_buffer

def get_line(device):
    rx_buffer = ""
    timeout = time.time()
    while True:
        if (time.time() - timeout) > 3.0:
            return "NG"
        chars = device.read()
        if chars == "\n":
            break
        rx_buffer += chars
    return rx_buffer

# ELボード初期化
def init_el_board():
    # コマンドモードに変更
    device.write(chr(0x13))

    # 再起動
    device.write("S01\n")
    strRet = get_line(device)
    if strRet != "OK":
        return False

    timeout = time.time()
    while True:
        if (time.time() - timeout) > 5.0:
            return False
        device.write(chr(0x16))
        chars = device.read()
        if chars == chr(0x06):
            device.flushInput()
            break

    # コマンドモードに変更
    device.write(chr(0x13))

    # カメラエラーチェック
    device.write("E01\n")
    strRet = get_line(device)
    if strRet != "OK":
        return False

    return True

# 撮像
def capture():
    # 撮像
    device.write("C01\n")
    strRet = get_command(device)
    if strRet == "NG":
        return False

    iSize = int(strRet)
    iCnt = 0
    global img_datas
    img_datas = ""
    while True:
        chars = device.read(30000)
        if len(chars) > 0:
            img_datas = img_datas + chars
            iCnt = iCnt + len(chars)
        if iSize <= iCnt:
            break

    return True

# 画像をサーバーに保存
def save_image(qr_code):
    headers = {'Content-Type': 'image/jpeg'}
    url = base_url + "upload_image?serial_no=" + qr_code + "&img_type=0"

    global img_datas
    logger.info(qr_code + " image size: " + str(len(img_datas)))
    response = requests.post(url, img_datas, headers=headers)
    if response.status_code != 200:
        return False

    return True

# IPアドレスを取得する##################################
if sys.platform == "linux" or sys.platform == "linux2":
    address = "ubuntu.local"
elif sys.platform == "darwin":
    address = "localhost"

ip = socket.gethostbyname(address)
base_url = "http://" + ip + "/"

# ポート番号を取得する##################################
if os.name == 'nt':
    matched_ports = list_ports.grep("USB Serial Port ")
elif os.name == 'posix':
    if sys.platform == "linux" or sys.platform == "linux2":
        matched_ports = list_ports.grep("ttyUSB")
    elif sys.platform == "darwin":
        matched_ports = list_ports.grep("cu.usbserial-")
for match_tuple in matched_ports:
    SERIAL_PORT = match_tuple[0]
    break
#####################################################
# ポートを開く
device = serial.Serial(SERIAL_PORT, 921600, timeout=1, writeTimeout=0.1)

if init_el_board() == False:
    sys.stderr.write('カメラ初期化失敗\n')
    sys.exit(1)

if capture() == False:
    sys.stderr.write('撮影失敗\n')
    sys.exit(1)

if save_image("ELCAM9J0001") == False:
    sys.stderr.write('撮影失敗\n')
    sys.exit(1)

sys.exit(0)


