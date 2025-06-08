# -*- coding: utf-8 -*-
import os
import shutil
import numpy as np
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from Drone import Drone
from Traitement_image import Kmean, Moyenne_couleur, Traitement_image

class CheckableMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        self.checkboxes = []
        for name in ["Trait de côte", "Rural", "Urbain", "Aquatique", "Routes"]:
            cb = QtWidgets.QCheckBox(name)
            layout.addWidget(cb)
            self.checkboxes.append(cb)
        widget.setLayout(layout)
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(widget)
        self.addAction(action)


class ExploWindow(object):
    def __init__(self, mission_name, lat_ini, lon_ini):
        self.mission_name = mission_name
        self.lat = lat_ini
        self.lon = lon_ini

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle(f"Mission : {self.mission_name}")
        MainWindow.resize(1059, 843)
        cw = QtWidgets.QWidget(MainWindow)

        # === barre du haut ===
        hlw = QtWidgets.QWidget(cw)
        hlw.setGeometry(0, 0, 1045, 194)
        hlay = QtWidgets.QHBoxLayout(hlw)
        hlay.setContentsMargins(10, 10, 10, 10)
        hlay.setSpacing(20)

        # lancement, méthode, appliquer, zoom, terrain, save, quit
        self.btnLaunch  = QtWidgets.QPushButton("Lancer", hlw)
        self.comboMethod= QtWidgets.QComboBox(hlw)
        self.comboMethod.addItems(["Satellite", "K-means", "Variance"])
        self.btnApply   = QtWidgets.QPushButton("Appliquer les filtres", hlw)
        self.comboZoom  = QtWidgets.QComboBox(hlw)
        self.comboZoom.addItems([f"Zoom : {z}" for z in (11, 12, 13)])
        self.btnTerrain = QtWidgets.QToolButton(hlw)
        self.btnTerrain.setText("Terrain")
        self.btnTerrain.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.terrainMenu= CheckableMenu(MainWindow)
        self.btnTerrain.setMenu(self.terrainMenu)
        self.btnSave    = QtWidgets.QPushButton("Enregistrer la vue", hlw)
        self.btnQuit    = QtWidgets.QPushButton("Fin de la mission", hlw)

        for w in (self.btnLaunch,
                  QtWidgets.QLabel("Méthode de vue :", hlw),
                  self.comboMethod,
                  self.btnApply,
                  self.comboZoom,
                  self.btnTerrain):
            hlay.addWidget(w)
        hlay.addSpacerItem(QtWidgets.QSpacerItem(40,20,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Minimum))
        hlay.addWidget(self.btnSave)
        hlay.addWidget(self.btnQuit)

        # ==== zone directionnelle ====
        glw = QtWidgets.QWidget(cw)
        glw.setGeometry(240, 700, 295, 80)
        gl = QtWidgets.QGridLayout(glw)
        self.btnUp    = QtWidgets.QPushButton("Haut", glw);  gl.addWidget(self.btnUp,0,1)
        self.btnLeft  = QtWidgets.QPushButton("Gauche",glw); gl.addWidget(self.btnLeft,1,0)
        self.btnDown  = QtWidgets.QPushButton("Bas",glw);    gl.addWidget(self.btnDown,1,1)
        self.btnRight = QtWidgets.QPushButton("Droite",glw); gl.addWidget(self.btnRight,1,2)

        # ==== vue image + coord label ====
        self.view = QtWidgets.QGraphicsView(cw)
        self.view.setGeometry(30, 200, 931, 481)
        self.coord_label = QtWidgets.QLabel(cw)
        self.coord_label.setGeometry(QtCore.QRect(750, 700, 250, 30))
        font = QtGui.QFont(); font.setPointSize(10)
        self.coord_label.setFont(font)
        self.coord_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.coord_label.setText(f"Lat: {self.lat:.4f} | Lon: {self.lon:.4f}")

        MainWindow.setCentralWidget(cw)
        MainWindow.setStatusBar(QtWidgets.QStatusBar(MainWindow))

        # connexions
        self.drone       = Drone()
        self.btnLaunch.clicked.connect(self._capture)
        self.btnLeft.clicked.connect(lambda: self._move("gauche"))
        self.btnUp.clicked.connect(lambda: self._move("haut"))
        self.btnDown.clicked.connect(lambda: self._move("bas"))
        self.btnRight.clicked.connect(lambda: self._move("droite"))
        self.btnApply.clicked.connect(self._process_and_display)
        self.btnSave.clicked.connect(self._save)
        self.btnQuit.clicked.connect(self._finish)

    def _display(self, pil_img):
        data = pil_img.tobytes('raw','RGB')
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_RGB888)
        pix  = QtGui.QPixmap.fromImage(qimg)
        scene= QtWidgets.QGraphicsScene()
        scene.addPixmap(pix)
        self.view.setScene(scene)
        self.view.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def _show_base(self):
        base = self.drone.recoller()
        if base is not None:
            self._display(base)

    def _process_and_display(self):
        # 1) Reconstruire la mosaïque brute
        base = self.drone.recoller()
        if base is None:
            return

        # 2) Choix de la méthode
        tmp = "_tmp_mosaic.png"
        base.save(tmp)
        method = self.comboMethod.currentText()
        if method == "Satellite":
            seg_img, helper = base.copy(), Traitement_image(tmp)
        elif method == "K-means":
            seg = Kmean(tmp);
            seg_img, helper = seg.segmented_img, seg
        else:  # Variance
            seg_v = Moyenne_couleur(tmp);
            seg_img, helper = seg_v.img, seg_v

        # 3) Initialisation des masques
        helper.img = seg_img
        helper.img_array = np.array(seg_img)
        helper.hauteur, helper.largeur = helper.img_array.shape[:2]
        helper.creer_masques_couleurs()

        # 4) Préparer le trait de côte (mais on l'appliquera tout dernier)
        helper.tracer_trait_de_cote()

        # 5) Récupérer les cases cochées
        checks = self.terrainMenu.checkboxes
        names = ["trait_de_cote", "rural", "urbain", "marin", "routes"]
        colors = {
            "trait_de_cote": (255, 0, 0),
            "rural": (34, 139, 34),
            "urbain": (105, 105, 105),
            "marin": (0, 0, 255),
            "routes": (255, 215, 0),
        }

        # 6) Appliquer d'abord les filtres terrain, puis le trait de côte
        if any(cb.isChecked() for cb in checks):
            img_courante = base.copy()

            # 6a) terrain filters (skip trait_de_cote for l'instant)
            for cb, attr in zip(checks[1:], names[1:]):
                if not cb.isChecked():
                    continue
                # on met à jour helper sur l'image actuelle
                helper.img_array = np.array(img_courante)
                helper.hauteur, helper.largeur = helper.img_array.shape[:2]
                img_courante = helper.appliquer_masque(getattr(helper, attr), colors[attr])

            # 6b) trait de côte en dernier
            if checks[0].isChecked():
                helper.img_array = np.array(img_courante)
                helper.hauteur, helper.largeur = helper.img_array.shape[:2]
                img_courante = helper.appliquer_masque(helper.trait_de_cote, colors["trait_de_cote"])

            to_show = img_courante
        else:
            to_show = base

        # 7) Affichage final
        self._display(to_show)

    def _capture(self):
        zoom = int(self.comboZoom.currentText().split(":")[1])
        self.drone.capture_image(self.lat, self.lon, zoom)
        self.lat, self.lon = self.drone.get_coordinates()
        self.coord_label.setText(f"Lat: {self.lat:.4f} | Lon: {self.lon:.4f}")
        self._show_base()

    def _move(self, direction):
        self.drone.deplacement(direction)
        self._show_base()
        self.lat, self.lon = self.drone.get_coordinates()
        self.coord_label.setText(f"Lat: {self.lat:.4f} | Lon: {self.lon:.4f}")

    def _save(self):
        if not self.drone.captured_image:
            QMessageBox.warning(None, "Erreur", "Aucune image à enregistrer.")
            return
        path, _ = QFileDialog.getSaveFileName(None, "Enregistrer la vue", "", "PNG (*.png)")
        if path:
            self.view.grab().save(path, "PNG")
            QMessageBox.information(None, "Enregistré", f"Image sauvegardée dans :\n{path}")

    def _finish(self):
        # nettoyage
        if os.path.isdir("tiles"):
            shutil.rmtree("tiles")
        for f in ("mosaic.png","_tmp_mosaic.png","Kmean.png","Moyenne_couleur.png"):
            try:    os.remove(f)
            except: pass
        QtWidgets.qApp.quit()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w   = QtWidgets.QMainWindow()
    ui  = ExploWindow("Test", 48.0, -4.0)
    ui.setupUi(w)
    w.show()
    sys.exit(app.exec_())
