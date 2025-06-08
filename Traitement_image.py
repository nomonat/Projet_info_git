# -*- coding: utf-8 -*-
import numpy as np
from PIL import Image
from scipy import ndimage
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

class Traitement_image:
    def __init__(self, file: str):
        self.img = Image.open(file).convert("RGB")
        self.img_array = np.array(self.img)
        self.hauteur, self.largeur, _ = self.img_array.shape
        self.rural = None
        self.urbain = None
        self.marin = None
        self.routes = None
        self.trait_de_cote = None

    def tracer_trait_de_cote(self, seuil: float = 0.5):
        """Calcule et stocke dans self.trait_de_cote le bord des pixels bleus."""
        masque_bleu = (self.img_array[:, :, 0] == 0) & \
                      (self.img_array[:, :, 1] == 0) & \
                      (self.img_array[:, :, 2] == 255)
        grad_x = ndimage.sobel(masque_bleu.astype(float), axis=1)
        grad_y = ndimage.sobel(masque_bleu.astype(float), axis=0)
        grad = np.hypot(grad_x, grad_y)
        self.trait_de_cote = grad > seuil

    def creer_masques_couleurs(self):
        """Crée les 4 masques issus de la segmentation (K-means ou Moyenne_couleur)."""
        arr = self.img_array
        self.marin  = (arr[:, :, 0] == 0)   & (arr[:, :, 1] == 0)   & (arr[:, :, 2] == 255)
        self.rural  = (arr[:, :, 0] == 34)  & (arr[:, :, 1] == 139) & (arr[:, :, 2] == 34)
        self.urbain = (arr[:, :, 0] == 105) & (arr[:, :, 1] == 105) & (arr[:, :, 2] == 105)
        self.routes = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 215) & (arr[:, :, 2] == 0)

    def appliquer_masque(self, masque, couleur):
        """
        Retourne un PIL.Image où les pixels du masque sont recoloriés.
        - masque  : array booléen (hauteur×largeur)
        - couleur : tuple (R, G, B) à appliquer
        """
        img_mod = self.img_array.copy()
        img_mod[masque] = couleur
        return Image.fromarray(img_mod)

    def points_interet(self, interet):
        # à implémenter plus tard
        return


class Kmean(Traitement_image):
    def __init__(self, file: str, k: int = 4):
        super().__init__(file)
        self.segmented_img = self.k_means(k)
        self.segmented_img.save("Kmean.png")
        self.img = self.segmented_img
        self.img_array = np.array(self.segmented_img)
        self.creer_masques_couleurs()

    def k_means(self, k: int = 4):
        pixels = self.img_array.reshape(-1, 3)
        centers = np.array([
            [195, 229, 235],
            [218, 238, 199],
            [255, 255, 249],
            [255, 255, 150]
        ], dtype=np.uint8)
        km = KMeans(n_clusters=k, init=centers, n_init=1, random_state=0).fit(pixels)
        cols = np.array([
            [0,   0,   255],
            [34, 139,  34],
            [105,105, 105],
            [255,215,   0]
        ])
        img = cols[km.labels_].reshape(self.hauteur, self.largeur, 3)
        return Image.fromarray(img.astype(np.uint8))


class Moyenne_couleur(Traitement_image):
    def __init__(self, file: str, seuil_variance: float = 50):
        super().__init__(file)
        self.seuil_variance = seuil_variance
        self.tree = self.recurrence(self.img_array)
        recon = self.build_reconstructed()
        Image.fromarray(recon).save("Moyenne_couleur.png")
        self.img = Image.fromarray(recon)
        self.img_array = recon
        self.creer_masques_couleurs()

    def variance_tile(self, tile):
        h, w, _ = tile.shape
        moy = tile.reshape(-1, 3).mean(0)
        V = ((tile - moy) ** 2).sum(axis=(0, 1))
        return V / (h * w)

    def quelle_couleur(self, moyenne: np.ndarray) -> tuple:
        """
        À partir d'une moyenne [R,G,B], retourne la couleur la plus proche
        parmi les centres initiaux, ou gris si aucune n'est suffisamment proche.
        """
        r, g, b = map(int, moyenne)
        CB = (195, 229, 235)  # eau
        CG = (218, 238, 199)  # rural
        CP = (255, 255, 249)  # urbain pâle
        CY = (255, 255, 150)  # routes
        SEUIL = 60

        d = lambda C: abs(r - C[0]) + abs(g - C[1]) + abs(b - C[2])
        db, dg, dp, dy = d(CB), d(CG), d(CP), d(CY)

        if db <= SEUIL and db < dg and db < dp and db < dy:
            return (0, 0, 255)
        elif dg <= SEUIL and dg < db and dg < dp and dg < dy:
            return (34, 139, 34)
        elif dp <= SEUIL and dp < db and dp < dg and dp < dy:
            return (105, 105, 105)
        elif dy <= SEUIL and dy < db and dy < dg and dy < dp:
            return (255, 215, 0)
        else:
            return (105, 105, 105)

    def recurrence(self, tile):
        h, w, _ = tile.shape
        # cas de base : variance faible ou tile trop petite
        if h * w == 0 or h <= 1 or w <= 1 or (self.variance_tile(tile) < self.seuil_variance).all():
            moy = tile.reshape(-1, 3).mean(0)
            return self.quelle_couleur(moy)
        # sinon, on découpe en 4 et on descend
        my, mx = h // 2, w // 2
        return [
            self.recurrence(tile[0:my,      0:mx]),
            self.recurrence(tile[0:my,      mx:w]),
            self.recurrence(tile[my:h,      0:mx]),
            self.recurrence(tile[my:h,      mx:w]),
        ]

    def build_reconstructed(self):
        canvas = np.zeros((self.hauteur, self.largeur, 3), dtype=np.uint8)
        def _fill(node, y0, x0, h, w):
            if isinstance(node, tuple):
                canvas[y0:y0+h, x0:x0+w] = node
                return
            my, mx = h // 2, w // 2
            _fill(node[0], y0,      x0,      my,   mx)
            _fill(node[1], y0,      x0+mx,   my,   w-mx)
            _fill(node[2], y0+my,   x0,      h-my, mx)
            _fill(node[3], y0+my,   x0+mx,   h-my, w-mx)
        _fill(self.tree, 0, 0, self.hauteur, self.largeur)
        return canvas


if __name__ == "__main__":
    # test rapide
    mc = Moyenne_couleur("riviere.png")
    mc.img.show()