# coding: UTF-8

import sys, os, time
import serial
from serial.tools import list_ports
import cv2
import numpy
from PIL import Image, ImageTk
import Tkinter
import threading
import requests
import logging
import logging.handlers

SERIAL_PORT = ""
DEF_IMG_W = 1600
DEF_IMG_H = 1200
UP_SHOW_IMG_W = 360
UP_SHOW_IMG_H = 300
UP_IMG_W = 120
UP_IMG_H = 100
UP_IMG_OFFSET_X = 100
UP_IMG_OFFSET_Y = 100

line_buf = ""
img_datas = ""

logger = logging.getLogger('CameraAddjust')
logger.setLevel(logging.INFO)
handler = logging.handlers.SysLogHandler(address = ('ubuntu.local', 514))
logger.addHandler(handler)

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
        Lb_Judge.configure(text='reboot1失敗')
        return False

    timeout = time.time()
    while True:
        if (time.time() - timeout) > 5.0:
            Lb_Judge.configure(text='reboot2失敗')
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
        Lb_Judge.configure(text='起動失敗1')
        return False

    return True

# 撮像
def capture():
    # 撮像
    device.write("C01\n")
    strRet = get_command(device)
    if strRet == "NG":
        Lb_Judge.configure(text='撮像失敗')
        return

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

    img_array = numpy.fromstring(img_datas, numpy.uint8)
    src_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    img = Image.fromarray(src_img)
    # 全体画像に表示
    resize_img = img.resize((MAIN_IMG_W, MAIN_IMG_H))
    main_canvas.photo = ImageTk.PhotoImage(resize_img)
    main_canvas.create_image(0, 0, image=main_canvas.photo, anchor=Tkinter.NW)
    # 拡大画像
    up_img = img.crop(((DEF_IMG_W / 2) - (UP_IMG_W / 2) + UP_IMG_OFFSET_X, (DEF_IMG_H / 2) - (UP_IMG_H / 2) + UP_IMG_OFFSET_Y, (DEF_IMG_W / 2) + (UP_IMG_W / 2) + UP_IMG_OFFSET_X, (DEF_IMG_H / 2) + (UP_IMG_H / 2) + UP_IMG_OFFSET_Y))
    up_resize_img = up_img.resize((UP_SHOW_IMG_W, UP_SHOW_IMG_H))
    up_canvas.photo = ImageTk.PhotoImage(up_resize_img)
    up_canvas.create_image(0, 0, image=up_canvas.photo, anchor=Tkinter.NW)
    # 画像変換
    dec_img = cv2.cvtColor(src_img, cv2.COLOR_RGB2GRAY)
    lap_img = cv2.Laplacian(dec_img, cv2.CV_16S, ksize = 3, scale = 1, delta = 0, borderType = cv2.BORDER_DEFAULT)
    abs_img = cv2.convertScaleAbs(lap_img)
    # エッジ拡大画像
    img = Image.fromarray(lap_img)
    edge_img = img.crop(((DEF_IMG_W / 2) - (UP_IMG_W / 2) + UP_IMG_OFFSET_X, (DEF_IMG_H / 2) - (UP_IMG_H / 2) + UP_IMG_OFFSET_Y, (DEF_IMG_W / 2) + (UP_IMG_W / 2) + UP_IMG_OFFSET_X, (DEF_IMG_H / 2) + (UP_IMG_H / 2) + UP_IMG_OFFSET_Y))
    edge_resize_img = edge_img.resize((UP_SHOW_IMG_W, UP_SHOW_IMG_H))
    edge_canvas.photo = ImageTk.PhotoImage(edge_resize_img)
    edge_canvas.create_image(0, 0, image=edge_canvas.photo, anchor=Tkinter.NW)
    # スコア計算
    mean, stddev = cv2.meanStdDev(abs_img)
    Lb_Judge.configure(text=str(int(stddev[0] * stddev[0])))


# 画像をサーバーに保存
def save_image(qr_code):
    headers = {'Content-Type': 'image/jpeg'}
    url = "http://ubuntu.local/upload_image?serial_no=" + qr_code + "&img_type=0"

    global img_datas
    logger.info("image size: " + len(img_datas))
    response = requests.post(url, img_datas, headers=headers)
    if response.status_code != 200:
        Lb_Judge.configure(text='保存失敗')
        return

    Lb_Judge.configure(text='保存成功')


def th_init_el_board(event):
    Lb_Judge.configure(text='起動中')
    if init_el_board() == True:
        Lb_Judge.configure(text='起動完了')

    lock.release()

def th_capture(event):
    Lb_Judge.configure(text='撮影中')
    main_canvas.delete("all")
    up_canvas.delete("all")
    edge_canvas.delete("all")

    capture()

    lock.release()

def th_save_image(buf):
    Lb_Judge.configure(text='保存中')

    save_image(buf)

    lock.release()


def key(event):
    global line_buf

    if event.char == ' ':
        if lock.acquire(False):
            th = threading.Thread(target=th_capture, args=(event,))
            th.start()
        return

    if event.char != chr(0x0D):
        line_buf = line_buf + event.char
        return

    if line_buf.startswith("ELCAM"):
        if lock.acquire(False):
            th = threading.Thread(target=th_save_image, args=(line_buf,))
            th.start()
    else:
        if lock.acquire(False):
            th = threading.Thread(target=th_init_el_board, args=(event,))
            th.start()

    line_buf = ""


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
# コマンドモードに変更
device.write(chr(0x13))

lock = threading.Lock()

root = Tkinter.Tk()
root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))
root.bind("<Key>", key)

Fr_Side = Tkinter.Frame(root)
Fr_Side.pack(side='left', expand=True, fill="none")

Lb_Judge = Tkinter.Label(Fr_Side, text='--', height=2, font=("", 38))
Lb_Judge.pack(anchor='n' , side='top', expand=True, fill="none")

up_canvas = Tkinter.Canvas(Fr_Side, bg = "black", width=UP_SHOW_IMG_W, height=UP_SHOW_IMG_H)
up_canvas.pack(side='top')

edge_canvas = Tkinter.Canvas(Fr_Side, bg = "black", width=UP_SHOW_IMG_W, height=UP_SHOW_IMG_H)
edge_canvas.pack(side='top')

MAIN_IMG_W = root.winfo_screenwidth() / 4 * 3
MAIN_IMG_H = int(round(DEF_IMG_H * MAIN_IMG_W / DEF_IMG_W))

main_canvas = Tkinter.Canvas(root, bg = "black", width=MAIN_IMG_W, height=MAIN_IMG_H)
main_canvas.pack(side='right')

root.mainloop()

device.close()
