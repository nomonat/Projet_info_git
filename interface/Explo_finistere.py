# -*- coding: utf-8 -*-
import os, shutil, numpy as np
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from Drone import Drone
from Traitement_image import Kmean, Moyenne_couleur, Traitement_image

class CheckableMenu(QtWidgets.QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        w = QtWidgets.QWidget(self)
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(10,10,10,10); lay.setSpacing(5)
        self.checkboxes = []
        for name in ["Rural","Urbain","Aquatique","Routes","Trait de côte"]:
            cb = QtWidgets.QCheckBox(name)
            lay.addWidget(cb); self.checkboxes.append(cb)
        w.setLayout(lay)
        a = QtWidgets.QWidgetAction(self)
        a.setDefaultWidget(w)
        self.addAction(a)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1059,843)
        cw = QtWidgets.QWidget(MainWindow)

        # barre du haut
        hlw = QtWidgets.QWidget(cw); hlw.setGeometry(0,0,1045,194)
        hlay = QtWidgets.QHBoxLayout(hlw)
        hlay.setContentsMargins(10,10,10,10); hlay.setSpacing(20)

        self.btnLaunch   = QtWidgets.QPushButton("Lancer", hlw)
        self.comboMethod = QtWidgets.QComboBox(hlw)
        self.comboMethod.addItems(["Satellite","K-means","Variance"])
        self.btnApply    = QtWidgets.QPushButton("Appliquer les filtres", hlw)
        self.comboZoom   = QtWidgets.QComboBox(hlw)
        self.comboZoom.addItems([f"Zoom : {z}" for z in (11,12,13)])
        self.btnTerrain  = QtWidgets.QToolButton(hlw)
        self.btnTerrain.setText("Terrain")
        self.btnTerrain.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.terrainMenu = CheckableMenu(MainWindow)
        self.btnTerrain.setMenu(self.terrainMenu)
        self.btnSave     = QtWidgets.QPushButton("Enregistrer la vue", hlw)
        self.btnQuit     = QtWidgets.QPushButton("Fin de la mission", hlw)

        # ajouter au layout
        hlay.addWidget(self.btnLaunch)
        hlay.addWidget(QtWidgets.QLabel("Méthode de vue :", hlw))
        hlay.addWidget(self.comboMethod)
        hlay.addWidget(self.btnApply)
        hlay.addWidget(self.comboZoom)
        hlay.addWidget(self.btnTerrain)
        hlay.addSpacerItem(QtWidgets.QSpacerItem(40,20,
            QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Minimum))
        hlay.addWidget(self.btnSave)
        hlay.addWidget(self.btnQuit)

        # zone directionnelle
        glw = QtWidgets.QWidget(cw); glw.setGeometry(240,700,295,80)
        gl = QtWidgets.QGridLayout(glw)
        self.btnUp    = QtWidgets.QPushButton("Haut", glw);  gl.addWidget(self.btnUp,0,1)
        self.btnLeft  = QtWidgets.QPushButton("Gauche",glw); gl.addWidget(self.btnLeft,1,0)
        self.btnDown  = QtWidgets.QPushButton("Bas",glw);    gl.addWidget(self.btnDown,1,1)
        self.btnRight = QtWidgets.QPushButton("Droite",glw); gl.addWidget(self.btnRight,1,2)

        # vue
        self.view = QtWidgets.QGraphicsView(cw)
        self.view.setGeometry(30,200,931,481)

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

    def _display(self, pil):
        data = pil.tobytes('raw','RGB')
        qimg = QtGui.QImage(data,pil.width,pil.height,QtGui.QImage.Format_RGB888)
        pix  = QtGui.QPixmap.fromImage(qimg)
        scene= QtWidgets.QGraphicsScene()
        scene.addPixmap(pix)
        self.view.setScene(scene)
        self.view.fitInView(scene.sceneRect(),QtCore.Qt.KeepAspectRatio)

    def _show_base(self):
        base = self.drone.recoller()
        if base: self._display(base)

    def _process_and_display(self):
        # 1) mosaïque brute
        base = self.drone.recoller()
        if base is None: return

        # 2) segmentation
        tmp = "_tmp_mosaic.png"; base.save(tmp)
        m = self.comboMethod.currentText()
        if m=="Satellite":
            seg_img, helper = base.copy(), Traitement_image(tmp)
        elif m=="K-means":
            seg_k, helper = Kmean(tmp), None
            seg_img, helper = seg_k.segmented_img, seg_k
        else:
            seg_v, helper = Moyenne_couleur(tmp), None
            seg_img, helper = seg_v.img, seg_v

        # 3) préparer masques + trait de côte
        helper.img = seg_img
        helper.img_array = np.array(seg_img)
        helper.hauteur, helper.largeur = helper.img_array.shape[:2]
        helper.creer_masques_couleurs()
        helper.tracer_trait_de_cote(seuil=0.5)

        # 4) quels filtres ?
        names   = ["rural","urbain","marin","routes","trait_de_cote"]
        checked = [attr for cb,attr in zip(self.terrainMenu.checkboxes,names)
                   if cb.isChecked()]

        if checked:
            # On part de la mosaïque brute
            img_courante = base.copy()  # PIL.Image

            # Couleurs associées à chaque attribut
            couleurs = {
                "marin": (0, 0, 255),
                "rural": (34, 139, 34),
                "urbain": (105, 105, 105),
                "routes": (255, 215, 0),
                "trait_de_cote": (255, 0, 0),
            }

            # On applique chaque masque l’un après l’autre
            for attr in checked:
                masque = getattr(helper, attr)  # ex. helper.rural ou helper.trait_de_cote
                couleur = couleurs[attr]

                # on met à jour helper.img_array sur l'image courante
                helper.img_array = np.array(img_courante)
                helper.hauteur, helper.largeur = helper.img_array.shape[:2]

                # et on recolore
                img_courante = helper.appliquer_masque(masque, couleur)

            to_show = img_courante
        else:
            to_show = base

        self._display(to_show)

    def _capture(self):
        lat_min,lon_min,lat_max,lon_max = 47.7,-5.1,48.8,-3.2
        lat = (lat_min+lat_max)/2; lon=(lon_min+lon_max)/2
        z   = int(self.comboZoom.currentText().split(":")[1])
        self.drone.capture_image(lat,lon,z)
        self._show_base()

    def _move(self,d):
        self.drone.deplacement(d)
        self._show_base()

    def _save(self):
        if not self.drone.captured_image:
            QMessageBox.warning(None,"Erreur","Aucune image à enregistrer."); return
        p,_ = QFileDialog.getSaveFileName(None,"Enregistrer","","PNG (*.png)")
        if p:
            self.view.grab().save(p,"PNG")
            QMessageBox.information(None,"Enregistré",f"Sauvé dans :\n{p}")

    def _finish(self):
        if os.path.isdir("tiles"): shutil.rmtree("tiles")
        for f in ("mosaic.png","_tmp_mosaic.png","Kmean.png","Moyenne_couleur.png"):
            if os.path.isfile(f): os.remove(f)
        QtWidgets.qApp.quit()

if __name__=="__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()
    ui=Ui_MainWindow(); ui.setupUi(w); w.show()
    sys.exit(app.exec_())
