import numpy as np
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

class Traitement_image:
    def __init__(self, file):
        self.img = Image.open(file).convert("RGB")
        self.img_array = np.array(self.img)
        self.hauteur, self.largeur, _ = self.img_array.shape
        self.rural=None
        self.urbain= None
        self.marin=None

class Kmeans(Traitement_image):
    def k_means(self, img, k=3):
        """
        Appliquer K-means pour segmenter l'image en 3 zones spécifiques (bleu, vert, pâle).
        :param img: Image d'entrée à segmenter
        :param k: Nombre de clusters (zones)
        :return: L'image segmentée et les labels des pixels
        """
        self.img = img.convert("RGB")  # Stocke l'image reçue en entrée
        # Convertir l'image en tableau numpy
        img_np = np.array(self.img)
        h, w, d = img_np.shape
        pixels = img_np.reshape((-1, 3))

        # Couleurs spécifiques à utiliser pour les clusters
        initial_centers = np.array([
            [195, 229, 235],  # Bleu
            [218, 238, 199],  # Vert
            [255, 255, 249]   # Pâle
        ], dtype=np.uint8)

        # Appliquer K-means en initialisant les centres avec les couleurs spécifiques
        kmeans = KMeans(n_clusters=k, init=initial_centers, n_init=1, random_state=0)
        kmeans.fit(pixels)

        # Obtenir les labels des pixels
        self.labels = kmeans.labels_

        # Appliquer les couleurs aux pixels en fonction des labels (reconstruction de l'image segmentée)
        cluster_colors = np.array([
            [0, 0, 255],    # Bleu (eau)
            [34, 139, 34],  # Vert (rural)
            [105, 105, 105] # Gris foncé (urbain)
        ])
        colored_pixels = cluster_colors[self.labels].reshape((h, w, 3))

        # Convertir le tableau numpy en image avec le bon type de données
        colored_pixels = np.array(colored_pixels, dtype=np.uint8)
        self.segmented_img = Image.fromarray(colored_pixels)

        return self.segmented_img

class MoyenneCouleur(Traitement_image):
    def quelle_couleur(self, moyenne, seuil_dom=30):
        r, g, b = moyenne
        adapt = max(10, seuil_dom - int((r + g + b) / 15))
        if b > 200 and b > r and b > g:
            return (0, 0, 255)
        if b > g + adapt and b > r + adapt:
            return (0, 0, 255)
        elif g > r + adapt and g > b + adapt:
            return (0, 255, 0)
        else:
            return (127, 127, 127)

    def moy_une_tuile(self, tile):
        h, w, _ = tile.shape
        moyenne = tile.reshape(-1, 3).mean(axis=0)
        return self.quelle_couleur(moyenne)

    def decouper_image_en_tuiles(self, l_tuile):
        nb_tuiles_x = (self.largeur + l_tuile - 1) // l_tuile
        nb_tuiles_y = (self.hauteur + l_tuile - 1) // l_tuile
        RGB = np.zeros((nb_tuiles_x, nb_tuiles_y, 3))

        for j in range(nb_tuiles_y):
            for i in range(nb_tuiles_x):
                x = i * l_tuile
                y = j * l_tuile
                tile = self.img_array[y:min(y + l_tuile, self.hauteur), x:min(x + l_tuile, self.largeur)]
                RGB[i, j] = self.moy_une_tuile(tile)

        return RGB, l_tuile

    def construire_image_moyenne(self, RGB, l_tuile, nom="image_reconstruite.png"):
        hauteur = RGB.shape[1] * l_tuile
        largeur = RGB.shape[0] * l_tuile
        image = Image.new("RGB", (largeur, hauteur))
        draw = ImageDraw.Draw(image)

        for x in range(RGB.shape[0]):
            for y in range(RGB.shape[1]):
                color = tuple(map(int, RGB[x, y]))
                for i in range(l_tuile):
                    for j in range(l_tuile):
                        xi = x * l_tuile + i
                        yj = y * l_tuile + j
                        if xi < largeur and yj < hauteur:
                            draw.point((xi, yj), fill=color)

        image.save(nom)
        print(f"Image enregistrée sous {nom}")

    def variance_acceptable(self, tile_array, seuil_variance=1000):
        pixels = tile_array.reshape(-1, 3)
        var = np.var(pixels, axis=0)
        return np.mean(var) < seuil_variance

    def tuiles_variance_test(self, l_tuile, seuil_variance):
        nb_x = (self.largeur + l_tuile - 1) // l_tuile
        nb_y = (self.hauteur + l_tuile - 1) // l_tuile

        for j in range(nb_y):
            for i in range(nb_x):
                x = i * l_tuile
                y = j * l_tuile
                tile = self.img_array[y:min(y + l_tuile, self.hauteur), x:min(x + l_tuile, self.largeur)]
                if not self.variance_acceptable(tile, seuil_variance):
                    return False
        return True

    def l_tuile_max_recursive_desc(self, l_tuile, step, seuil_variance=1000):
        if l_tuile <= 1:
            return 1
        if self.tuiles_variance_test(l_tuile, seuil_variance):
            return l_tuile
        else:
            return self.l_tuile_max_recursive_desc(l_tuile - step, step, seuil_variance)

    def traitement_image_auto_desc(self, seuil_variance=1000, step=2):
        l_tuile_max = min(self.hauteur, self.largeur)
        taille_optimale = self.l_tuile_max_recursive_desc(l_tuile_max, step, seuil_variance)
        print(f"Taille de tuile optimale trouvée (desc): {taille_optimale}")
        RGB_result, l_tuile = self.decouper_image_en_tuiles(taille_optimale)
        self.construire_image_moyenne(RGB_result, l_tuile)

    def afficher_variance_tuile(self, l_tuile, x, y):
        tile = self.img_array[y:y + l_tuile, x:x + l_tuile]
        pixels = tile.reshape(-1, 3)
        var = np.var(pixels, axis=0)
        print(f"Variance R,G,B: {var}, Moyenne: {np.mean(var)}")


if __name__=="__main__":
    traitement = Kmeans("ploug.png")
    traitement.k_means()
    traitement.afficher_paysage("all")