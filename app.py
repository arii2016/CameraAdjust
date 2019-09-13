# coding: UTF-8

import sys, os, time
import serial
from serial.tools import list_ports
import cv2
import numpy
from PIL import Image, ImageTk
import Tkinter
import threading
# from io import BytesIO

SERIAL_PORT = ""
DEF_IMG_W = 1600
DEF_IMG_H = 1200

def get_command(device):
    rx_buffer = ""
    while True:
        chars = device.read()
        if chars == ",":
            break
        rx_buffer += chars
    return rx_buffer

def get_line(device):
    rx_buffer = ""
    while True:
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

    while True:
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
    if strRet == "NG":
        return False


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
    datas = ""
    while True:
        chars = device.read(30000)
        if len(chars) > 0:
            datas = datas + chars
            iCnt = iCnt + len(chars)
        if iSize <= iCnt:
            break

    # try:
    #     img = Image.open(BytesIO(datas))
    # except:
    #     Lb_Judge.configure(text='撮像失敗')
    #     return

    # img = img.resize((MAIN_IMG_W, MAIN_IMG_H))
    # main_canvas.photo = ImageTk.PhotoImage(img)
    # main_canvas.create_image(0, 0, image=canvas.photo, anchor=Tkinter.NW)

    img_array = numpy.fromstring(datas, numpy.uint8)
    src_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    img = Image.fromarray(src_img)
    # 全体画像に表示
    resize_img = img.resize((MAIN_IMG_W, MAIN_IMG_H))
    main_canvas.photo = ImageTk.PhotoImage(resize_img)
    main_canvas.create_image(0, 0, image=main_canvas.photo, anchor=Tkinter.NW)
    # 画像変換
    dec_img = cv2.cvtColor(src_img, cv2.COLOR_RGB2GRAY)
    lap_img = cv2.Laplacian(dec_img, cv2.CV_16S, ksize = 3, scale = 1, delta = 0, borderType = cv2.BORDER_DEFAULT)
    abs_img = cv2.convertScaleAbs(lap_img)
    # スコア計算
    mean, stddev = cv2.meanStdDev(abs_img)
    Lb_Judge.configure(text=str(int(stddev[0] * stddev[0])))

    # # 拡大画像表示
    # crop_img = Image.fromarray(src_img[700 : 900, 525 : 675])
    # up_canvas.photo = ImageTk.PhotoImage(crop_img)
    # up_canvas.create_image(0, 0, image=up_canvas.photo, anchor=Tkinter.NW)


def th_init_el_board(event):
    Lb_Judge.configure(text='起動中')
    init_el_board()
    Lb_Judge.configure(text='起動完了')

    lock.release()

def th_capture(event):
    Lb_Judge.configure(text='撮影中')
    # up_canvas.delete("all")
    # lap_canvas.delete("all")
    main_canvas.delete("all")

    capture()

    lock.release()


def key(event):
    if event.char == chr(0x0D):
        if lock.acquire(False):
            th = threading.Thread(target=th_init_el_board, args=(event,))
            th.start()
    if event.char == ' ':
        if lock.acquire(False):
            th = threading.Thread(target=th_capture, args=(event,))
            th.start()


# ポート番号を取得する##################################
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

# frame = Tkinter.Frame(root)
# frame.pack(side='left', expand=True, fill="both")

Lb_Judge = Tkinter.Label(root, text='--', height=4, font=("", 50))
# Lb_Judge.pack(side='top', expand=True, fill="x")
Lb_Judge.pack(side='left', expand=True, fill="x")

# UP_IMG_W = 200
# UP_IMG_H = 150
# up_canvas = Tkinter.Canvas(frame, bg = "black", width=UP_IMG_W, height=UP_IMG_H)
# up_canvas.pack(side='top')

# lap_canvas = Tkinter.Canvas(frame, bg = "black", width=UP_IMG_W, height=UP_IMG_H)
# lap_canvas.pack(side='top')

MAIN_IMG_W = root.winfo_screenwidth() / 4 * 3
MAIN_IMG_H = int(round(DEF_IMG_H * MAIN_IMG_W / DEF_IMG_W))

main_canvas = Tkinter.Canvas(root, bg = "black", width=MAIN_IMG_W, height=MAIN_IMG_H)
main_canvas.pack(side='right')

root.mainloop()

device.close()
