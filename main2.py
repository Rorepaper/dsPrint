import socket
import printerclient
import printencoder
from tkinter import *
from PIL import Image, ImageDraw, ImageFont
import time
import qrcode
import serial
import sys
from serial.tools import list_ports
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from design import Ui_MainWindow
from PyQt5.QtCore import Qt


class DsPrint(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.printik)
        self.pushButton_2.clicked.connect(self.testik)
        self.pushButton_3.clicked.connect(self.length)
        self.pushButton_4.clicked.connect(self.mac)
        a = list_ports.comports(include_links=False)
        compots = []
        for i in a:
            if i.pid:
                compots.append(i.name)
        compots.append("Выбор COM")
        self.comboBox.clear()
        self.comboBox.addItems(compots)

        with open("MAC.txt", "r") as f:
            self.lineEdit.setText(f.readline().strip())

    def keyPressEvent(self, event):
        match event.key:
            case Qt.Key_Space:
                self.printik()
            case Qt.Key_T:
                self.testik()
            case Qt.Key_Enter:
                self.mac()
            case Qt.Key_L:
                self.length()

    def testik(self):
        global test_in
        test_in = False
        self.printik()

    def printik(self):
        global did, kagamineLen, test_in
        com = self.comboBox.currentText()
        if com == "Выбор COM":
            QMessageBox.critical(self, "Ошибка", "Выберите COM порт")
            self.coms()
            return
        ser = serial.Serial(com, baudrate=115200, timeout=1)
        did = ser.readline().decode("utf-8")[:16]

        if len(did) != 16:
            QMessageBox.about(self, "Ошибка", "Неверный COM порт\nИли не закончилась инициализация ESP")
            return

        with open("ids.txt", "r") as f:
            lines = f.readlines()
        with open("ids.txt", "a") as f:
            if did in lines:
                QMessageBox.about(self, "Ошибка", "Датчик не сменился или неисправен")
                return
            else:
                if test_in:
                    f.write("\n" + did)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4.5,
            border=1,
        )
        qr.add_data(did)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        fnt = ImageFont.truetype("consola.ttf", 30)
        im = Image.new("RGB", (599, 96), "white")
        draw = ImageDraw.Draw(im)
        draw.text((127, 34), f"SMC-DS-{kagamineLen}  {did}", font=fnt, fill="black")
        im.paste(img, (10, 2))
        im.save("img.png")
        args = [self.lineEdit.text(), True, 2, 1, 1, im]
        img = args[5]
        self.frame.setStyleSheet("background-image: url(img.png);")

        if not test_in:
            test_in = True
            return

        if img.width / img.height > 1:
            img = img.transpose(Image.ROTATE_270)
        assert args[1] or (img.width == 96 and img.height < 600)

        try:
            sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            sock.connect((args[0], 1))
        except TimeoutError:
            QMessageBox.critical(self, "Ошибка", "Принтер не подключен")
        except OSError:
            QMessageBox.critical(self, "Ошибка", "Bluetooth выключен")
        else:
            printer = printerclient.PrinterClient(sock)
            printer.set_label_type(args[3])
            printer.set_label_density(args[2])
            printer.start_print()
            printer.allow_print_clear()
            printer.start_page_print()
            printer.set_dimension(img.height, img.width)
            printer.set_quantity(args[4])

            for pkt in printencoder.naive_encoder(img):
                printer._send(pkt)

            printer.end_page_print()
            while (a := printer.get_print_status())['page'] != args[4]:
                time.sleep(0.1)
            printer.end_print()
            return
        with open("ids.txt", "r") as f:
            f = f.read().split("\n")
            f = f[:-1]
        with open("ids.txt", "w") as ff:
            ff.write("\n".join(f))
        return


    def mac(self):
        macu = self.lineEdit.text()
        if len(macu) == 17 and macu.count(":") == 5:
            with open("MAC.txt", "w") as f:
                f.writelines(self.lineEdit.text())
        else:
            QMessageBox.about(self, "Ошибка", "Неверный MAC адресс")

    def length(self):
        global kagamineLen, test_in
        kagamineLen += 1
        if kagamineLen == 4:
            kagamineLen = 1
        test_in = False
        self.printik()

    def coms(self):
        a = list_ports.comports(include_links=False)
        compots = []
        for i in a:
            if i.pid:
                compots.append(i.name)
        compots.append("Выбор COM")
        self.comboBox.clear()
        self.comboBox.addItems(compots)


if __name__ == '__main__':
    did = ""
    tes = 0
    test_in = True
    kagamineLen = 3
    app = QApplication(sys.argv)
    ex = DsPrint()
    ex.show()
    sys.exit(app.exec())
