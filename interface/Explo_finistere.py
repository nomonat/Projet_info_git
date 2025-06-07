# -*- coding: utf-8 -*-
import os
import math
import requests
from io import BytesIO
from PIL import Image, ImageEnhance

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from Drone import Drone  # importe la classe Drone du script Drone.py

class CheckableMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Widget container avec layout vertical
        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # Création des checkboxes
        self.checkboxes = []
        for name in ["Rural", "Urbain", "Aquatique", "Routes"]:
            cb = QtWidgets.QCheckBox(name)
            layout.addWidget(cb)
            self.checkboxes.append(cb)

        widget.setLayout(layout)

        # Ajouter le widget dans le menu via QWidgetAction
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(widget)
        self.addAction(action)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1059, 843)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Barre horizontale en haut
        self.horizontalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(0, 0, 1045, 194))
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setContentsMargins(10, 10, 10, 10)
        self.horizontalLayout.setSpacing(20)
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.pushButton_5 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_5.setObjectName("pushButton_5")
        self.horizontalLayout.addWidget(self.pushButton_5)

        self.comboBox_2 = QtWidgets.QComboBox(self.horizontalLayoutWidget)
        self.comboBox_2.setObjectName("comboBox_2")
        self.comboBox_2.addItem("K-means")
        self.comboBox_2.addItem("Récursive")
        self.horizontalLayout.addWidget(self.comboBox_2)

        self.comboBox = QtWidgets.QComboBox(self.horizontalLayoutWidget)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.addItem("Zoom : 8")
        self.comboBox.addItem("Zoom : 10")
        self.comboBox.addItem("Zoom : 12")
        self.horizontalLayout.addWidget(self.comboBox)

        # Nouveau bouton Terrain avec menu custom checkable
        self.terrainButton = QtWidgets.QToolButton(self.horizontalLayoutWidget)
        self.terrainButton.setText("Terrain")
        self.terrainButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.terrainMenu = CheckableMenu(MainWindow)
        self.terrainButton.setMenu(self.terrainMenu)
        self.horizontalLayout.addWidget(self.terrainButton)

        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)

        self.pushButton_6 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_6.setObjectName("pushButton_6")
        self.horizontalLayout.addWidget(self.pushButton_6)

        self.pushButton_7 = QtWidgets.QPushButton(self.horizontalLayoutWidget)
        self.pushButton_7.setObjectName("pushButton_7")
        self.horizontalLayout.addWidget(self.pushButton_7)

        # Zone directionnelle en bas
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(780, 730, 55, 16))
        self.label.setObjectName("label")

        self.gridLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(240, 700, 295, 80))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")

        self.pushButton_2 = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.pushButton_2.setObjectName("pushButton_2")
        self.gridLayout.addWidget(self.pushButton_2, 0, 1, 1, 1)

        self.pushButton = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.pushButton.setObjectName("pushButton")
        self.gridLayout.addWidget(self.pushButton, 1, 0, 1, 1)

        self.pushButton_3 = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.pushButton_3.setObjectName("pushButton_3")
        self.gridLayout.addWidget(self.pushButton_3, 1, 1, 1, 1)

        self.pushButton_4 = QtWidgets.QPushButton(self.gridLayoutWidget)
        self.pushButton_4.setObjectName("pushButton_4")
        self.gridLayout.addWidget(self.pushButton_4, 1, 2, 1, 1)

        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(30, 200, 931, 481))
        self.graphicsView.setObjectName("graphicsView")

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1059, 26))
        self.menubar.setObjectName("menubar")

        self.menuFin = QtWidgets.QMenu(self.menubar)
        self.menuFin.setObjectName("menuFin")

        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Connexions aux actions Drone
        self.drone = Drone()
        self.pushButton_5.clicked.connect(self._capture)
        self.pushButton.clicked.connect(lambda: self._move("gauche"))
        self.pushButton_2.clicked.connect(lambda: self._move("haut"))
        self.pushButton_3.clicked.connect(lambda: self._move("bas"))
        self.pushButton_4.clicked.connect(lambda: self._move("droite"))
        self.pushButton_6.clicked.connect(self._save)
        self.pushButton_7.clicked.connect(QtWidgets.qApp.quit)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Vue_aerienne"))
        self.pushButton_5.setText(_translate("MainWindow", "Lancer"))
        self.pushButton_6.setText(_translate("MainWindow", "Enregistrer la vue"))
        self.pushButton_7.setText(_translate("MainWindow", "Fin de la mission"))
        self.label.setText(_translate("MainWindow", "Zone de déplacement"))
        self.pushButton_2.setText(_translate("MainWindow", "Haut"))
        self.pushButton.setText(_translate("MainWindow", "Gauche"))
        self.pushButton_3.setText(_translate("MainWindow", "Bas"))
        self.pushButton_4.setText(_translate("MainWindow", "Droite"))

    # Méthodes liées au Drone
    def _display(self, pil_img):
        data = pil_img.tobytes('raw', 'RGB')
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        scene = QtWidgets.QGraphicsScene()
        scene.addPixmap(pix)
        self.graphicsView.setScene(scene)
        self.graphicsView.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def _capture(self):
        # On centre sur la même zone définie en dur
        lat_min, lon_min, lat_max, lon_max = 47.7, -5.1, 48.8, -3.2
        lat = (lat_min + lat_max) / 2
        lon = (lon_min + lon_max) / 2
        zoom = int(self.comboBox.currentText().split(':')[1])
        self.drone.capture_image(lat, lon, zoom)
        self._display(self.drone.captured_image)

    def _move(self, direction):
        # 1) Mise à jour des indices et téléchargement de la nouvelle tuile
        self.drone.deplacement(direction)

        # 2) On recolle toutes les tuiles visitées en une seule mosaïque
        #    (le paramètre est optionnel, par défaut ça crée 'mosaic.png')
        self.drone.recoller("current_mosaic.png")

        # 3) Affichage de la mosaïque dans le GraphicsView
        self._display(self.drone.captured_image)


    def _save(self):
        if not self.drone.captured_image:
            QMessageBox.warning(None, "Erreur", "Aucune image à enregistrer.")
            return
        path, _ = QFileDialog.getSaveFileName(None, "Enregistrer la vue", "", "PNG (*.png)")
        if path:
            self.drone.captured_image.save(path)
            QMessageBox.information(None, "Enregistré", f"Image sauvegardée dans:\n{path}")

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
