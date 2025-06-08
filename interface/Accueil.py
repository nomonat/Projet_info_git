# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QRegion, QPainterPath
from PyQt5.QtCore import QTimer


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        self.MainWindow = MainWindow

        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1059, 1000)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
                font-family: 'Segoe UI';
                font-size: 12pt;
            }
            QLineEdit {
                padding: 6px;
                border: 2px solid #ccc;
                border-radius: 8px;
                background-color: white;
            }
            QPushButton {
                background-color: #2e86de;
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1b4f72;
            }
        """)

        # Image d’accueil proportionnelle
        self.imageAccueil = QtWidgets.QLabel(self.centralwidget)
        self.imageAccueil.setGeometry(QtCore.QRect(0, 0, 1059, 450))
        pixmap = QtGui.QPixmap("image_accueil.png")
        scaled_pixmap = pixmap.scaledToHeight(450, QtCore.Qt.SmoothTransformation)
        self.imageAccueil.setPixmap(scaled_pixmap)
        self.imageAccueil.setAlignment(QtCore.Qt.AlignCenter)

        # Nom mission
        self.missionName = QtWidgets.QLineEdit(self.centralwidget)
        self.missionName.setGeometry(QtCore.QRect(40, 480, 300, 40))
        self.missionName.setPlaceholderText("Nom de la mission")
        # Zoom déplacé ici :
        self.zoomLabel = QtWidgets.QLabel("Zoom :", self.centralwidget)
        self.zoomLabel.setGeometry(QtCore.QRect(360, 480, 60, 40))

        self.zoom_input = QtWidgets.QComboBox(self.centralwidget)
        self.zoom_input.setGeometry(QtCore.QRect(420, 480, 100, 40))
        self.zoom_input.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 2px solid #ccc;
                border-radius: 8px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.zoom_input.addItems(["11", "12", "13"])
        self.zoom_input.setCurrentIndex(1)

        # Message info
        self.infoText = QtWidgets.QLabel(self.centralwidget)
        self.infoText.setGeometry(QtCore.QRect(40, 530, 600, 50))
        self.infoText.setText("Entrez une latitude entre 47.7 et 48.8\net une longitude entre -5.1 et -3.2")
        self.infoText.setStyleSheet("font-size: 11pt; color: #333;")


        # Entrées coordonnées
        self.coordWidget = QtWidgets.QWidget(self.centralwidget)
        self.coordWidget.setGeometry(QtCore.QRect(40, 590, 700, 60))
        self.coordLayout = QtWidgets.QHBoxLayout(self.coordWidget)
        self.coordLayout.setContentsMargins(0, 0, 0, 0)
        self.coordLayout.setSpacing(40)

        self.lat_input = QtWidgets.QLineEdit()
        self.lat_input.setFixedHeight(40)
        self.lat_input.setPlaceholderText("Latitude (ex: 48.0)")

        self.lon_input = QtWidgets.QLineEdit()
        self.lon_input.setFixedHeight(40)
        self.lon_input.setPlaceholderText("Longitude (ex: -4.5)")

        self.coordLayout.addWidget(QtWidgets.QLabel("Latitude :"))
        self.coordLayout.addWidget(self.lat_input)
        self.coordLayout.addWidget(QtWidgets.QLabel("Longitude :"))
        self.coordLayout.addWidget(self.lon_input)



        # Bouton lancement
        self.launchButton = QtWidgets.QPushButton(self.centralwidget)
        self.launchButton.setGeometry(QtCore.QRect(40, 670, 200, 40))
        self.launchButton.setText("Lancer")
        self.launchButton.clicked.connect(self.startAnimation)

        # Conteneur circulaire pour le GIF centré
        self.gifFrame = QtWidgets.QFrame(self.centralwidget)
        self.gifFrame.setGeometry(QtCore.QRect((1059 - 150)//2, 740, 150, 150))  # Centré horizontalement
        self.gifFrame.setStyleSheet("background-color: white; border: 2px solid #bbb; border-radius: 75px;")
        self.gifFrame.setVisible(False)

        path = QPainterPath()
        path.addEllipse(0, 0, 140, 140)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.gifFrame.setMask(region)

        self.loadingAnimation = QtWidgets.QLabel(self.gifFrame)
        self.loadingAnimation.setGeometry(0, 0, 150, 150)
        self.loadingAnimation.setAlignment(QtCore.Qt.AlignCenter)

        self.movie = QtGui.QMovie("loading.gif")
        self.movie.setScaledSize(QtCore.QSize(150, 150))
        self.loadingAnimation.setMovie(self.movie)

        # Menu & statusbar
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)

    def startAnimation(self):
        lat_text = self.lat_input.text()
        lon_text = self.lon_input.text()
        zoom_text = self.zoom_input.currentText()
        valid = True

        self.lat_input.setStyleSheet("")
        self.lon_input.setStyleSheet("")

        try:
            lat = float(lat_text)
            if not (47.7 <= lat <= 48.8):
                raise ValueError
        except ValueError:
            self.lat_input.setStyleSheet("border: 2px solid red;")
            valid = False

        try:
            lon = float(lon_text)
            if not (-5.1 <= lon <= -3.2):
                raise ValueError
        except ValueError:
            self.lon_input.setStyleSheet("border: 2px solid red;")
            valid = False

        try:
            zoom = int(zoom_text)
            if zoom not in [11, 12, 13]:
                raise ValueError
        except ValueError:
            valid = False

        if valid:
            self.gifFrame.setVisible(True)
            self.movie.start()
            QTimer.singleShot(1000, lambda: self.emit_launch(lat, lon, zoom))

    def emit_launch(self, lat, lon,zoom):
        mission_name = self.missionName.text().strip() or "Mission"

        # Ferme la fenêtre principale proprement
        self.MainWindow.close()

        # Lance l'autre interface directement
        from interface.Explo_finistere import ExploWindow as ExploWindow
        self.explo_main = QtWidgets.QMainWindow()
        self.explo_ui = ExploWindow(mission_name, lat, lon, zoom)


        self.explo_ui.setupUi(self.explo_main)
        self.explo_main.show()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
