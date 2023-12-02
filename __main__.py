import socket
import qrcode
import sys

from time import sleep
from configparser import ConfigParser
from PIL import Image, ImageDraw, ImageFont

from serial import Serial, SerialException
from serial.tools import list_ports

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5 import QtGui

from design import Ui_MainWindow
from niimprint import printencoder, printerclient


class DsPrint(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.printing)
        self.pushButton_2.clicked.connect(self.testing)
        self.pushButton_3.clicked.connect(self.length)
        self.pushButton_4.clicked.connect(self.mac)
        self.pushButton_5.clicked.connect(self.change_mode)
        self.pushButton_7.clicked.connect(self.coms)
        self.coms()
        config = ConfigParser()
        config.read("settings.ini")
        self.lineEdit.setText(config["DEFAULT"]["MAC"])

    def keyPressEvent(self, event):
        match event.key():
            case Qt.Key_Space:
                self.printing()
            case Qt.Key_T:
                self.testing()
            case Qt.Key_Enter:
                self.mac()
            case Qt.Key_L:
                self.length()

    def testing(self):
        global test_in
        test_in = False
        self.printing()

    def printing(self):
        global label_len, test_in, ser
        com = self.comboBox.currentText()
        if com == "COM MARK":
            QMessageBox.critical(self, "Ошибка", "Выберите COM порт маркировщика")
            self.coms()
            return

        if not ser or not ser.is_open:
            try:
                ser = Serial(com, baudrate=115200, timeout=0.1)
            except SerialException:
                QMessageBox.critical(self, "Ошибка", "Переподключите маркировщик")
                return
        did = ""
        c = 0
        while len(did) != 16:
            c += 1
            try:
                ser.flushInput()
                did = ser.readline().decode()[:16]
            except UnicodeDecodeError:
                continue
            except SerialException:
                QMessageBox.critical(self, "Ошибка", "Переподключите маркировщик")
                ser = False
                return
            print(did)
            if did.count("0") == 16:
                QMessageBox.critical(self, "Ошибка", "Подключите датчик")
                return
            if c > 20:
                QMessageBox.critical(self, "Ошибка", "Неверный COM порт")
                ser = False
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

        fnt = ImageFont.truetype("src/consola.ttf", 30)
        im = Image.new("RGB", (599, 96), "white")
        draw = ImageDraw.Draw(im)
        draw.text((127, 34), f"SMC-DS-{label_len}  {did}", font=fnt, fill="black")
        im.paste(img, (10, 2))
        im.save("src/img.png")

        self.label.setPixmap(QtGui.QPixmap("src/img.png"))
        if not test_in:
            test_in = True
            return

        config = ConfigParser()
        config.read("settings.ini")

        args = [config["DEFAULT"]["MAC"], True, 2, 1, 1, im]
        img = args[5]

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
            while (printer.get_print_status())['page'] != args[4]:
                sleep(0.1)
            printer.end_print()
            return

        with open("ids.txt", "r") as f:
            f = f.read().split("\n")
            f = f[:-1]
        with open("ids.txt", "w") as ff:
            ff.write("\n".join(f))
        return

    def mac(self):
        printer_mac = self.lineEdit.text()
        config = ConfigParser()
        config.read("settings.ini")
        if len(printer_mac) == 17 and printer_mac.count(":") == 5:
            config["DEFAULT"]["MAC"] = printer_mac
            with open("settings.ini", "w") as f:
                config.write(f)
        else:
            QMessageBox.about(self, "Ошибка", "Неверный MAC адрес")

    def length(self):
        global label_len, test_in
        label_len += 1
        if label_len == 4:
            label_len = 1
        test_in = False
        self.printing()

    def coms(self):
        a = list_ports.comports(include_links=False)
        comports = []
        for i in a:
            if i.pid:
                comports.append(i.name)
        comports.append("COM MARK")
        self.comboBox.clear()
        self.comboBox.addItems(comports)

    def change_mode(self):
        splash = QSplashScreen(self, QPixmap('src/help.jpg'))
        splash.show()


if __name__ == '__main__':
    ser = False
    test_in = True
    label_len = 3
    app = QApplication(sys.argv)
    ex = DsPrint()
    ex.show()
    sys.exit(app.exec())
