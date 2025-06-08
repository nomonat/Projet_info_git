import unittest
import numpy as np
from PIL import Image
import os
from Traitement_image import Traitement_image


class TestTraitementImage(unittest.TestCase):
    def setUp(self):
        # On crée une image 4x4 avec 4 colonnes de couleurs différentes :
        # - Colonne 0 : bleu → zone aquatique
        # - Colonne 1 : vert forêt → zone rurale
        # - Colonne 2 : gris foncé → zone urbaine
        # - Colonne 3 : jaune → route
        self.image_test = Image.new("RGB", (4, 4))
        for y in range(4):
            for x in range(4):
                if x == 0:
                    couleur = (0, 0, 255)
                elif x == 1:
                    couleur = (34, 139, 34)
                elif x == 2:
                    couleur = (105, 105, 105)
                else:
                    couleur = (255, 215, 0)
                self.image_test.putpixel((x, y), couleur)

        # On sauvegarde l'image pour l'utiliser dans les tests
        self.chemin_image = "test_image.png"
        self.image_test.save(self.chemin_image)

    def tearDown(self):
        # On supprime l'image test après les tests pour ne pas polluer le dossier
        if os.path.exists(self.chemin_image):
            os.remove(self.chemin_image)

    def test_creation_masques(self):
        # On vérifie que les zones sont bien détectées par couleur
        traitement = Traitement_image(self.chemin_image)
        traitement.creer_masques_couleurs()

        # Vérifie que chaque colonne est bien détectée comme son type
        self.assertTrue(np.all(traitement.aquatique[:, 0]))  # Colonne 0 = bleu
        self.assertTrue(np.all(traitement.rural[:, 1]))      # Colonne 1 = vert
        self.assertTrue(np.all(traitement.urbain[:, 2]))     # Colonne 2 = gris
        self.assertTrue(np.all(traitement.routes[:, 3]))     # Colonne 3 = jaune

        # Vérifie que les autres colonnes ne sont pas faussement détectées
        self.assertTrue(np.all(~traitement.aquatique[:, 1:]))
        self.assertTrue(np.all(~traitement.rural[:, [0, 2, 3]]))
        self.assertTrue(np.all(~traitement.urbain[:, [0, 1, 3]]))
        self.assertTrue(np.all(~traitement.routes[:, :3]))

    def test_application_masque(self):
        # On teste l’application d’un masque avec une couleur rouge
        traitement = Traitement_image(self.chemin_image)
        traitement.creer_masques_couleurs()

        rouge = (255, 0, 0)
        image_modifiee = traitement.appliquer_masque(traitement.aquatique, rouge)
        tableau_pixels = np.array(image_modifiee)

        # Tous les pixels bleus (colonne 0) doivent être devenus rouges
        self.assertTrue(np.all(tableau_pixels[:, 0] == rouge))

        # Les autres colonnes doivent rester inchangées
        self.assertTrue(np.all(tableau_pixels[:, 1] == [34, 139, 34]))
        self.assertTrue(np.all(tableau_pixels[:, 2] == [105, 105, 105]))
        self.assertTrue(np.all(tableau_pixels[:, 3] == [255, 215, 0]))

    def test_detection_eaux_interieures(self):
        # On simule une mer sur la bordure gauche, et on vérifie que le reste est ignoré
        traitement = Traitement_image(self.chemin_image)
        traitement.creer_masques_couleurs()

        traitement.mer = np.zeros_like(traitement.aquatique)
        traitement.mer[:, 0] = True  # On dit que la colonne 0 est de la mer

        traitement.trouver_eaux_interieur()

        # Il ne devrait pas y avoir d’eaux intérieures car la mer est en bordure
        self.assertTrue(np.all(~traitement.eaux_interieur))

    def test_detection_trait_de_cote(self):
        # On vérifie que le trait de côte est bien détecté entre la mer et le reste
        traitement = Traitement_image(self.chemin_image)
        traitement.creer_masques_couleurs()
        traitement.tracer_trait_de_cote()

        # Il doit y avoir un trait entre les zones aquatiques (colonne 0) et le reste
        self.assertTrue(np.any(traitement.trait_de_cote))


if __name__ == "__main__":
    unittest.main()
