# -*- coding: utf-8 -*-
import os
import numpy as np
from io import BytesIO
from PIL import Image
import math
import requests

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from Drone import Drone
from Traitement_image import Kmean, Moyenne_couleur

class CheckableMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        self.checkboxes = []
        for name in ["Rural", "Urbain", "Aquatique", "Routes"]:
            cb = QtWidgets.QCheckBox(name)
            layout.addWidget(cb)
            self.checkboxes.append(cb)
        widget.setLayout(layout)
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(widget)
        self.addAction(action)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1059, 843)
        self.centralwidget = QtWidgets.QWidget(MainWindow)

        # Barre du haut
        hlw = QtWidgets.QWidget(self.centralwidget)
        hlw.setGeometry(QtCore.QRect(0, 0, 1045, 194))
        hlay = QtWidgets.QHBoxLayout(hlw)
        hlay.setContentsMargins(10, 10, 10, 10)
        hlay.setSpacing(20)

        # Bouton "Lancer"
        self.pushButton_5 = QtWidgets.QPushButton("Lancer", hlw)
        hlay.addWidget(self.pushButton_5)

        # Choix méthode de vue (Satellite par défaut)
        self.label_methode = QtWidgets.QLabel("Méthode de vue :", hlw)
        hlay.addWidget(self.label_methode)
        self.comboBox_2 = QtWidgets.QComboBox(hlw)
        self.comboBox_2.addItems(["Satellite", "K-means", "Variance"])
        hlay.addWidget(self.comboBox_2)
        # Bouton OK (lance segmentation + masques)
        self.okButton = QtWidgets.QPushButton("Appliquer les filtres", hlw)
        hlay.addWidget(self.okButton)

        # Choix zoom
        self.comboBox = QtWidgets.QComboBox(hlw)
        self.comboBox.addItems([f"Zoom : {z}" for z in (8, 10, 12)])
        hlay.addWidget(self.comboBox)

        # Bouton Terrain (cases à cocher)
        self.terrainButton = QtWidgets.QToolButton(hlw)
        self.terrainButton.setText("Terrain")
        self.terrainButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.terrainMenu = CheckableMenu(MainWindow)
        self.terrainButton.setMenu(self.terrainMenu)
        hlay.addWidget(self.terrainButton)

        # Espaceur
        hlay.addSpacerItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Expanding,
                                  QtWidgets.QSizePolicy.Minimum)
        )

        # Boutons "Enregistrer la vue" et "Fin de la mission"
        self.pushButton_6 = QtWidgets.QPushButton("Enregistrer la vue", hlw)
        hlay.addWidget(self.pushButton_6)
        self.pushButton_7 = QtWidgets.QPushButton("Fin de la mission", hlw)
        hlay.addWidget(self.pushButton_7)

        # Zone directionnelle
        glw = QtWidgets.QWidget(self.centralwidget)
        glw.setGeometry(QtCore.QRect(240, 700, 295, 80))
        gl = QtWidgets.QGridLayout(glw)
        self.pushButton_2 = QtWidgets.QPushButton("Haut", glw)
        gl.addWidget(self.pushButton_2, 0, 1)
        self.pushButton   = QtWidgets.QPushButton("Gauche", glw)
        gl.addWidget(self.pushButton, 1, 0)
        self.pushButton_3 = QtWidgets.QPushButton("Bas", glw)
        gl.addWidget(self.pushButton_3, 1, 1)
        self.pushButton_4 = QtWidgets.QPushButton("Droite", glw)
        gl.addWidget(self.pushButton_4, 1, 2)

        # Vue image
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(30, 200, 931, 481))

        MainWindow.setCentralWidget(self.centralwidget)
        MainWindow.setStatusBar(QtWidgets.QStatusBar(MainWindow))

        # Connexions
        self.drone = Drone()
        self.pushButton_5.clicked.connect(self._capture)
        self.pushButton.clicked.connect(lambda: self._move("gauche"))
        self.pushButton_2.clicked.connect(lambda: self._move("haut"))
        self.pushButton_3.clicked.connect(lambda: self._move("bas"))
        self.pushButton_4.clicked.connect(lambda: self._move("droite"))
        self.okButton.clicked.connect(self._process_and_display)
        self.pushButton_6.clicked.connect(self._save)
        self.pushButton_7.clicked.connect(QtWidgets.qApp.quit)

    def _display(self, pil_img):
        data = pil_img.tobytes('raw', 'RGB')
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height,
                            QtGui.QImage.Format_RGB888)
        pix = QtGui.QPixmap.fromImage(qimg)
        scene = QtWidgets.QGraphicsScene()
        scene.addPixmap(pix)
        self.graphicsView.setScene(scene)
        self.graphicsView.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def _show_base(self):
        """Affiche la mosaïque brute sans segmentation ni masques."""
        base = self.drone.recoller()
        if base is not None:
            self._display(base)

    def _process_and_display(self):
        """Pipeline complet : segmentation + masquage, exécuté au clic OK."""
        base = self.drone.recoller()
        if base is None:
            return

        method = self.comboBox_2.currentText()
        if method == "Satellite":
            to_show = base
        else:
            tmp = "_tmp_mosaic.png"
            base.save(tmp)
            if method == "K-means":
                seg = Kmean(tmp)
                seg_img = seg.k_means()
            else:  # "Variance"
                seg = Moyenne_couleur(tmp)
                seg_img = Image.open("Moyenne_couleur.png")

            seg.img        = seg_img
            seg.img_array  = np.array(seg_img)
            seg.hauteur, seg.largeur = seg.img_array.shape[:2]
            seg.creer_masques_couleurs()

            seg_arr  = np.array(seg_img)
            base_arr = np.array(base)
            mask     = np.zeros((seg.hauteur, seg.largeur), dtype=bool)
            names    = ["rural", "urbain", "marin", "routes"]
            for cb, attr in zip(self.terrainMenu.checkboxes, names):
                if cb.isChecked():
                    mask |= getattr(seg, attr)

            base_arr[mask] = seg_arr[mask]
            to_show = Image.fromarray(base_arr)

        self._display(to_show)

    def _capture(self):
        """Capture initiale et affiche la mosaïque brute."""
        lat_min, lon_min, lat_max, lon_max = 47.7, -5.1, 48.8, -3.2
        lat = (lat_min + lat_max) / 2
        lon = (lon_min + lon_max) / 2
        zoom = int(self.comboBox.currentText().split(":")[1])
        self.drone.capture_image(lat, lon, zoom)
        self._show_base()

    def _move(self, direction):
        """Déplacement du drone + affichage de la mosaïque brute."""
        self.drone.deplacement(direction)
        self._show_base()

    def _save(self):
        if not self.drone.captured_image:
            QMessageBox.warning(None, "Erreur", "Aucune image à enregistrer.")
            return
        path, _ = QFileDialog.getSaveFileName(None, "Enregistrer la vue", "", "PNG (*.png)")
        if path:
            pixmap = self.graphicsView.grab()
            pixmap.save(path, "PNG")
            QMessageBox.information(None, "Enregistré", f"Image sauvegardée dans :\n{path}")

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
