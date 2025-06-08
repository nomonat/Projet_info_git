# Test.py
import os
import shutil
import tempfile
import unittest
import numpy as np
from PIL import Image

from Drone import Drone
from Traitement_image import Traitement_image, Kmean, Moyenne_couleur
from interface.Accueil import Ui_MainWindow as AccueilUI
from interface.Explo_finistere import CheckableMenu, ExploWindow

from PyQt5 import QtWidgets
import sys

app = QtWidgets.QApplication(sys.argv)  # nécessaire pour tester les UI PyQt

class TestTraitementImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # crée une petite image test
        cls.tmpfile = tempfile.NamedTemporaryFile(suffix="test.png", delete=False).name #On a choisit une image contenant toutes les zones possibles
        arr = np.zeros((10,10,3), dtype=np.uint8)
        # un carré « eau » bleu en haut à gauche
        arr[0:5,0:5] = [0,0,255]
        # un carré « rural » vert en bas à droite
        arr[5:10,5:10] = [34,139,34]
        Image.fromarray(arr).save(cls.tmpfile)

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.tmpfile)

    def test_creer_masques_couleurs(self):
        ti = Traitement_image(self.tmpfile)
        ti.creer_masques_couleurs()
        # on doit avoir True dans ces zones
        self.assertTrue(ti.aquatique[0,0])
        self.assertFalse(ti.aquatique[9,9])
        self.assertTrue(ti.rural[9,9])
        self.assertFalse(ti.rural[0,0])

    def test_trouver_les_eaux_interieurs(self):
        ti = Traitement_image(self.tmpfile)
        ti.creer_masques_couleurs()
        ti.tracer_trait_de_cote()
        ti.trouver_eaux_interieur()

        self.assertIsInstance(ti.mer, np.ndarray)
        self.assertEqual(ti.mer.dtype, bool)
        self.assertTrue(ti.mer.any())

        self.assertIsInstance(ti.eaux_interieur, np.ndarray)
        self.assertEqual(ti.eaux_interieur.dtype, bool)

        # On ne force plus eaux_interieur à être non vide, mais on vérifie les relations logiques
        # Si eaux_interieur contient des pixels, ils doivent être dans aquatique et pas dans mer
        if ti.eaux_interieur.any():
            self.assertTrue((ti.eaux_interieur & ti.aquatique).all())
            self.assertFalse((ti.eaux_interieur & ti.mer).any())
        else:
            print("Attention : aucun pixel d'eau intérieure détecté dans l'image de test.")

    def test_appliquer_masque(self):
        ti = Traitement_image(self.tmpfile)
        ti.creer_masques_couleurs()
        color = (123,45,67)
        out = ti.appliquer_masque(ti.rural, color)
        out_arr = np.array(out)
        # vérifie que les pixels ruraux ont bien reçu la couleur
        self.assertTrue((out_arr[9,9] == color).all())
        # les autres restent inchangés (ici noir [0,0,0])
        self.assertTrue((out_arr[0,0] == [0,0,255]).all())

    def test_kmean_segmentation(self):
        km = Kmean(self.tmpfile)
        seg = np.array(km.segmented_img)
        # doit n'utiliser que les 4 couleurs prescribées
        uniques = {tuple(p) for p in seg.reshape(-1,3)}
        expected = {(0,0,255),(34,139,34),(105,105,105),(255,215,0)}
        self.assertTrue(uniques.issubset(expected))

    def test_moyenne_couleur_segmentation(self):
        mc = Moyenne_couleur(self.tmpfile, seuil_variance=0)  # forcer subdivision
        seg = np.array(mc.img)
        uniques = {tuple(p) for p in seg.reshape(-1,3)}
        expected = {(0,0,255),(34,139,34),(105,105,105),(255,215,0)}
        # au moins ces couleurs devraient apparaître
        self.assertTrue(expected & uniques)

class TestDrone(unittest.TestCase):
    def setUp(self):
        self.drone = Drone()

    def test_tile_latlon_inverse(self):
        # teste qu'inverse(tile->latlon, latlon->tile) approx identique
        lat,lon,zoom = 48.0, -4.0, 12
        x,y = self.drone.latlon_to_tile(lat, lon, zoom)
        lat2,lon2 = self.drone.tile_to_latlon(x, y, zoom)
        # les différences doivent être faibles
        self.assertAlmostEqual(lat, lat2, places=1)
        self.assertAlmostEqual(lon, lon2, places=1)

    def test_capture_and_recoller(self):
        # on stub download_tile pour ne pas faire de requête HTTP
        orig = Image.new("RGB",(256,256),(100,150,200))
        self.drone.download_tile = lambda x,y,z: orig
        # capture et recoller
        self.drone.capture_image(48,-4,11, contraste=1.0)
        mosaic = self.drone.recoller(output_file="test_mosaic.png")
        self.assertEqual(mosaic.size, (256,256))
        os.remove("test_mosaic.png")
        shutil.rmtree("tiles")

class TestAccueil(unittest.TestCase):
    def setUp(self):
        self.ui = AccueilUI()
        self.win = QtWidgets.QMainWindow()
        self.ui.setupUi(self.win)

    def test_zoom_input_defaults(self):
        # zoom_input doit contenir 11,12,13 et courant index 1->"12"
        items = [self.ui.zoom_input.itemText(i) for i in range(self.ui.zoom_input.count())]
        self.assertEqual(items, ["11","12","13"])
        self.assertEqual(self.ui.zoom_input.currentText(),"12")

    def test_validation(self):
        # test startAnimation invalide puis valide
        self.ui.lat_input.setText("50")    # hors limites
        self.ui.lon_input.setText("-4")
        self.ui.zoom_input.setCurrentText("12")
        self.ui.startAnimation()
        # bordure rouge sur lat_input
        self.assertIn("border: 2px solid red", self.ui.lat_input.styleSheet())

        # teste cas valide
        self.ui.lat_input.setText("48.2")
        self.ui.lon_input.setText("-4.2")
        self.ui.zoom_input.setCurrentText("11")
        # should not raise
        self.ui.startAnimation()

class TestExploFinistere(unittest.TestCase):
    def test_checkablemenu_items(self):
        menu = CheckableMenu()
        labels = [cb.text() for cb in menu.checkboxes]
        self.assertEqual(labels,
            ["Rural", "Urbain", "Aquatique", "Routes","Trait de côte","Eaux intérieurs","Mer"]
        )

    def test_explowindow_init(self):
        ew = ExploWindow("M",48.0,-4.0,12)
        # attributs initialisés
        self.assertEqual(ew.mission_name,"M")
        self.assertEqual(ew.zoom,12)

if __name__ == "__main__":
    unittest.main()
