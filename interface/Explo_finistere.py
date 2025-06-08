import os
import shutil
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from Drone import Drone
from Traitement_image import Kmean, Moyenne_couleur, Traitement_image

class CheckableMenu(QtWidgets.QMenu):
    """Créé le menu contenant des cases à cocher"""
    def __init__(self, parent=None):
        super().__init__(parent)
        widget = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        self.checkboxes = []
        for name in ["Rural", "Urbain", "Aquatique", "Routes","Trait de côte","Eaux intérieurs","Mer"]:
            cb = QtWidgets.QCheckBox(name)
            layout.addWidget(cb)
            self.checkboxes.append(cb)
        widget.setLayout(layout)
        action = QtWidgets.QWidgetAction(self)
        action.setDefaultWidget(widget)
        self.addAction(action)


class ExploWindow(object):
    """Fenêtre d'exploration"""
    def __init__(self, mission_name, lat_ini, lon_ini, zoom):
        """Initialisation de la classe"""
        self.mission_name = mission_name
        self.lat = lat_ini
        self.lon = lon_ini
        self.zoom = zoom

    def setupUi(self, MainWindow):
        """Configuration de la fenêtre"""
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowTitle(f"Mission : {self.mission_name}")
        MainWindow.resize(1059, 843)
        cw = QtWidgets.QWidget(MainWindow)

        #Barre du haut
        hlw = QtWidgets.QWidget(cw)
        hlw.setGeometry(0, 0, 1045, 194)
        hlay = QtWidgets.QHBoxLayout(hlw)
        hlay.setContentsMargins(10, 10, 10, 10)
        hlay.setSpacing(20)

        #Création boutons
        self.btnLaunch = QtWidgets.QPushButton("Lancer", hlw)
        self.comboMethod = QtWidgets.QComboBox(hlw)
        self.comboMethod.addItems(["Satellite", "K-means", "Variance"])
        self.btnApply = QtWidgets.QPushButton("Appliquer les filtres", hlw)

        self.btnTerrain = QtWidgets.QToolButton(hlw)
        self.btnTerrain.setText("Terrain")
        self.btnTerrain.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.terrainMenu = CheckableMenu(MainWindow)
        self.btnTerrain.setMenu(self.terrainMenu)
        self.btnSave = QtWidgets.QPushButton("Enregistrer la vue", hlw)
        self.btnQuit = QtWidgets.QPushButton("Fin de la mission", hlw)

        #Conteneur horizontal pour comboMethod, btnTerrain et btnApply
        middle_widget = QtWidgets.QWidget(hlw)
        middle_layout = QtWidgets.QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(10)
        middle_layout.addWidget(self.comboMethod)
        middle_layout.addWidget(self.btnTerrain)
        middle_layout.addWidget(self.btnApply)

        for w in (self.btnLaunch,middle_widget):
            hlay.addWidget(w)
        hlay.addSpacerItem(
            QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))
        hlay.addWidget(self.btnSave)
        hlay.addWidget(self.btnQuit)
        #Pavé direction
        glw = QtWidgets.QWidget(cw)
        glw.setGeometry(240, 700, 295, 80)
        gl = QtWidgets.QGridLayout(glw)
        self.btnUp    = QtWidgets.QPushButton("Haut", glw);  gl.addWidget(self.btnUp,0,1)
        self.btnLeft  = QtWidgets.QPushButton("Gauche",glw); gl.addWidget(self.btnLeft,1,0)
        self.btnDown  = QtWidgets.QPushButton("Bas",glw);    gl.addWidget(self.btnDown,1,1)
        self.btnRight = QtWidgets.QPushButton("Droite",glw); gl.addWidget(self.btnRight,1,2)

        #Affichage carte
        self.view = QtWidgets.QGraphicsView(cw)
        self.view.setGeometry(30, 200, 931, 481)
        # === légende à droite ===
        self.legend_widget = QtWidgets.QWidget(cw)
        self.legend_widget.setGeometry(QtCore.QRect(975, 200, 150, 250))  # à droite de la carte
        legend_layout = QtWidgets.QVBoxLayout(self.legend_widget)
        legend_layout.setContentsMargins(5, 5, 5, 5)
        legend_layout.setSpacing(5)

        self.legend_labels = []
        legend_items = {
            "Rural": (34, 139, 34),
            "Urbain": (105, 105, 105),
            "Aquatique": (0, 0, 255),
            "Routes": (255, 215, 0),
            "Trait de côte": (255, 0, 0),
            "Eaux intérieurs": (0, 255, 255),
            "Mer": (0, 0, 125),
        }

        for name, color in legend_items.items():
            hbox = QtWidgets.QHBoxLayout()
            color_label = QtWidgets.QLabel()
            color_label.setFixedSize(20, 20)
            color_label.setStyleSheet(f"background-color: rgb{color}; border: 1px solid black;")
            text_label = QtWidgets.QLabel(name)
            hbox.addWidget(color_label)
            hbox.addWidget(text_label)
            legend_layout.addLayout(hbox)
            self.legend_labels.append((color_label, text_label))

        self.coord_label = QtWidgets.QLabel(cw)
        self.coord_label.setGeometry(QtCore.QRect(750, 700, 250, 30))
        font = QtGui.QFont(); font.setPointSize(10)
        self.coord_label.setFont(font)
        self.coord_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.coord_label.setText(f"Lat: {self.lat:.4f} | Lon: {self.lon:.4f}")

        MainWindow.setCentralWidget(cw)
        MainWindow.setStatusBar(QtWidgets.QStatusBar(MainWindow))

        #Connexions
        self.drone       = Drone()
        self.btnLaunch.clicked.connect(self.capture)
        self.btnLeft.clicked.connect(lambda: self.move("gauche"))
        self.btnUp.clicked.connect(lambda: self.move("haut"))
        self.btnDown.clicked.connect(lambda: self.move("bas"))
        self.btnRight.clicked.connect(lambda: self.move("droite"))
        self.btnApply.clicked.connect(self.traitement_et_affichage)
        self.btnSave.clicked.connect(self.save)
        self.btnQuit.clicked.connect(self.finish)

    def affichage(self, pil_img):
        """Affichage de l'image"""
        data = pil_img.tobytes('raw','RGB')
        qimg = QtGui.QImage(data, pil_img.width, pil_img.height, QtGui.QImage.Format_RGB888)
        pix  = QtGui.QPixmap.fromImage(qimg)
        scene= QtWidgets.QGraphicsScene()
        scene.addPixmap(pix)
        self.view.setScene(scene)
        self.view.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def base(self):
        """utilise la fonction recoller de Drone """
        base = self.drone.recoller()
        if base is not None:
            self.affichage(base)

    def traitement_et_affichage(self):
        #Reconstruire l'image satellite
        base = self.drone.recoller()
        if base is None:
            return

        #Application de la méthode de traitement utilisée
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

        #Recharger les masques dans helper
        helper.img       = seg_img
        helper.img_array = np.array(seg_img)
        helper.hauteur, helper.largeur = helper.img_array.shape[:2]
        helper.creer_masques_couleurs()
        helper.tracer_trait_de_cote()
        helper.trouver_eaux_interieur()

    #Préparation du  mapping
        filter_map = {
            "Rural":            ("rural",          (34, 139,  34)),
            "Urbain":           ("urbain",         (105,105, 105)),
            "Aquatique":        ("aquatique",          (  0,   0, 255)),
            "Routes":           ("routes",         (255,215,   0)),
            "Trait de côte":    ("trait_de_cote",  (255,  0,   0)),
            "Eaux intérieurs":  ("eaux_interieur", (  0, 255, 255)),
            "Mer":              ("mer",            (0, 0, 125)),
        }

        #Si aucune case n'est cochée, on affiche la base
        checks = self.terrainMenu.checkboxes
        if not any(cb.isChecked() for cb in checks):
            return self.affichage(base)

        #On ajoute les masques coché dans l'ordre de superposition
        img = base.copy()
        for cb in checks:
            if not cb.isChecked():
                continue
            name = cb.text()
            attr, color = filter_map[name]
            mask = getattr(helper, attr)
            helper.img_array = np.array(img)
            helper.hauteur, helper.largeur = helper.img_array.shape[:2]
            img = helper.appliquer_masque(mask, color)

        #Affichage final
        self.affichage(img)

    def capture(self):
        """Utilise la méthode de capture d'image de Drone"""
        self.drone.capture_image(self.lat, self.lon, self.zoom)
        self.lat, self.lon = self.drone.get_coordinates()
        self.coord_label.setText(f"Lat: {self.lat:.4f} | Lon: {self.lon:.4f}")
        self.base()

    def move(self, direction):
        """Permet la capture de la tuile suivante avec le déplacement de Drone"""
        self.drone.deplacement(direction)
        self.base()
        self.lat, self.lon = self.drone.get_coordinates()
        self.coord_label.setText(f"Lat: {self.lat:.4f} | Lon: {self.lon:.4f}")

    def save(self):
        """Enregistrement de l'image dans le fichier"""
        if not self.drone.captured_image:
            QMessageBox.warning(None, "Erreur", "Aucune image à enregistrer.")
            return

        filtre = self.comboMethod.currentText().replace(" ", "_")
        filename = f"{self.mission_name}_zoom{self.zoom}_{filtre}.png"

        path, _ = QFileDialog.getSaveFileName(None, "Enregistrer la vue", filename, "PNG (*.png)")
        if path:
            self.view.grab().save(path, "PNG")
            QMessageBox.information(None, "Enregistré", f"Image sauvegardée dans :\n{path}")

    def finish(self):
        """Supprime les fichiers provisoires et ferme proprement la fenêtre"""
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
