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
        for name in ["Rural", "Urbain", "Aquatique", "Routes","Trait de côte","Eaux intérieurs"]:
            cb = QtWidgets.QCheckBox(name)
            layout.addWidget(cb)
            self.checkboxes.append(cb)
        widget.setLayout(layout)
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(widget)
        self.addAction(action)


class ExploWindow(object):
    def __init__(self, mission_name, lat_ini, lon_ini, zoom):
        self.mission_name = mission_name
        self.lat = lat_ini
        self.lon = lon_ini
        self.zoom = zoom

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

        # 2) Segmentation / préparation du helper
        tmp = "_tmp_mosaic.png"
        base.save(tmp)
        method = self.comboMethod.currentText()
        if method == "Satellite":
            seg_img, helper = base.copy(), Traitement_image(tmp)
        elif method == "K-means":
            seg_obj = Kmean(tmp)
            seg_img, helper = seg_obj.segmented_img, seg_obj
        else:  # "Variance"
            seg_obj = Moyenne_couleur(tmp)
            seg_img, helper = seg_obj.img, seg_obj

        # 3) Recharger les masques dans helper
        helper.img       = seg_img
        helper.img_array = np.array(seg_img)
        helper.hauteur, helper.largeur = helper.img_array.shape[:2]
        helper.creer_masques_couleurs()
        helper.tracer_trait_de_cote()
        # on construit aussi le masque des eaux intérieures
        helper.trouver_eaux_interieur()  # doit remplir helper.eaux_interieur

        # 4) Préparer le mapping case→(attribut, couleur)
        filter_map = {
            "Rural":            ("rural",          (34, 139,  34)),
            "Urbain":           ("urbain",         (105,105, 105)),
            "Aquatique":        ("marin",          (  0,   0, 255)),
            "Routes":           ("routes",         (255,215,   0)),
            "Trait de côte":    ("trait_de_cote",  (255,  0,   0)),
            "Eaux intérieurs":  ("eaux_interieur", (  0, 255, 255)),
        }

        # 5) Si aucune case n'est cochée → on affiche la base
        checks = self.terrainMenu.checkboxes
        if not any(cb.isChecked() for cb in checks):
            return self._display(base)

        # 6) Sinon on part de la mosaïque brute et on applique les filtres dans l’ordre visuel
        img = base.copy()
        for cb in checks:
            if not cb.isChecked():
                continue
            name = cb.text()                    # ex. "Aquatique"
            attr, color = filter_map[name]      # ex. ("marin", (0,0,255))
            mask = getattr(helper, attr)        # helper.marin, helper.trait_de_cote, etc.
            # mettre à jour le helper avec l'image courante
            helper.img_array = np.array(img)
            helper.hauteur, helper.largeur = helper.img_array.shape[:2]
            # appliquer le masque
            img = helper.appliquer_masque(mask, color)

        # 7) Affichage final
        self._display(img)

    def _capture(self):

        self.drone.capture_image(self.lat, self.lon, self.zoom)
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
    ui  = ExploWindow("Test", 48.0, -4.0,11)
    ui.setupUi(w)
    w.show()
    sys.exit(app.exec_())
