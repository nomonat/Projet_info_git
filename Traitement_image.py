import numpy as np
from PIL import Image
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

class Kmean(Traitement_image):
    def __init__(self, file: str, k: int = 3):
        """
        Initialisation de la classe : charge l’image, lance la segmentation K-means,
        affiche et enregistre le résultat, puis prépare la possibilité d’afficher un paysage.
        """
        super().__init__(file)
        self.segmented_img = None
        self.labels = None

        # 1) Exécute la segmentation K-means dès l'instanciation
        img_segmentee = self.k_means(k)

        # 2) Affiche et enregistre l’image segmentée
        img_segmentee.show()
        img_segmentee.save("Kmean.png")

    def k_means(self, k: int = 3):
        """
        Appliquer K-means pour segmenter l'image chargée (self.img_array)
        en 3 zones spécifiques (bleu, vert, pâle).
        :param k: Nombre de clusters (zones)
        :return: L'image segmentée et les labels des pixels
        """
        # On travaille sur self.img (chargée dans le parent)
        img_np = self.img_array
        h, w, _ = img_np.shape
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

        # Appliquer les couleurs aux pixels en fonction des labels (reconstruction)
        cluster_colors = np.array([
            [0, 0, 255],    # Bleu (eau)
            [34, 139, 34],  # Vert (rural)
            [105, 105, 105] # Gris foncé (urbain)
        ])
        colored_pixels = cluster_colors[self.labels].reshape((h, w, 3))

        # Convertir en image PIL
        self.segmented_img = Image.fromarray(colored_pixels.astype(np.uint8))
        return self.segmented_img

    def afficher_paysage(self, type_paysage: str = "all"):
        """
        Superpose sur l'image originale les zones segmentées issues de l'image traitée (segmentation K-means),
        selon les types de paysages spécifiés.

        Args:
            type_paysage (str): "urbain", "rural", "aquatique" ou "all".
        """
        if self.img is None or self.segmented_img is None or self.labels is None:
            print("Données manquantes pour l'affichage (image, segmentée ou labels).")
            return

        # Dictionnaire des types de paysages avec leurs labels
        paysages = {
            "aquatique": 0,
            "rural": 1,
            "urbain": 2
        }

        # Gérer les options
        if type_paysage == "all":
            types_a_afficher = list(paysages.keys())
        else:
            type_paysage = type_paysage.lower()
            if type_paysage not in paysages:
                print(f"Type de paysage inconnu : {type_paysage}")
                return
            types_a_afficher = [type_paysage]

        # Convertir les images en tableaux numpy
        base_img = self.img_array.copy()
        segmented_array = np.array(self.segmented_img)

        # Superposer les zones souhaitées
        for type_ in types_a_afficher:
            label = paysages[type_]
            masque = (self.labels.reshape(base_img.shape[:2]) == label)
            base_img[masque] = segmented_array[masque]

        # Affichage
        image_resultat = Image.fromarray(base_img)
        plt.figure(figsize=(6, 6))
        plt.imshow(image_resultat)
        plt.title(f"Superposition : {', '.join(types_a_afficher)}")
        plt.axis("off")
        plt.show()


class Moyenne_couleur(Traitement_image):
    def __init__(self, file: str, seuil_variance: float = 200):
        """
        - file : chemin vers l’image à traiter
        - seuil_variance : variance maximale pour considérer une tuile homogène

        À l’instanciation, on construit automatiquement l’arbre et on reconstruit l’image,
        puis on affiche le résultat.
        """
        super().__init__(file)
        self.seuil_variance = seuil_variance
        self.tree = None

        # 1) Construire l’arbre de segmentation (quadtree)
        self.tree = self.recurrence(self.img_array)

        # 2) Reconstruire l’image à partir de cet arbre
        reconstructed_array = self.build_reconstructed()

        # 3) Convertir en PIL Image et afficher
        reconstructed_img = Image.fromarray(reconstructed_array)
        reconstructed_img.show()
        reconstructed_img.save("Moyenne_couleur.png")  # Si on veut aussi sauvegarder

    def variance_tile(self, tile_array: np.ndarray) -> np.ndarray:
        h_tile, w_tile, _ = tile_array.shape
        moy = np.array([np.mean(tile_array[:, :, k]) for k in range(3)], dtype=float)

        V = np.zeros(3, dtype=float)
        for i in range(h_tile):
            for j in range(w_tile):
                for k in range(3):
                    diff = float(tile_array[i, j, k]) - moy[k]
                    V[k] += diff ** 2

        return V / (h_tile * w_tile)

    def quelle_couleur(self, moyenne: np.ndarray, seuil_dom: int = 30) -> tuple:
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

    def moy_une_tuile(self, tile_array: np.ndarray) -> tuple:
        moyenne = tile_array.reshape(-1, 3).mean(axis=0)
        return self.quelle_couleur(moyenne)

    def recurrence(self, tile_array: np.ndarray):
        h, w, _ = tile_array.shape
        var_rgb = self.variance_tile(tile_array)

        if (var_rgb < self.seuil_variance).all():
            return self.moy_une_tuile(tile_array)

        mid_y = h // 2
        mid_x = w // 2

        arr_tl = tile_array[0:mid_y, 0:mid_x]
        arr_tr = tile_array[0:mid_y, mid_x:w]
        arr_bl = tile_array[mid_y:h, 0:mid_x]
        arr_br = tile_array[mid_y:h, mid_x:w]

        res_tl = self.recurrence(arr_tl)
        res_tr = self.recurrence(arr_tr)
        res_bl = self.recurrence(arr_bl)
        res_br = self.recurrence(arr_br)

        return [res_tl, res_tr, res_bl, res_br]

    def build_reconstructed(self) -> np.ndarray:
        canvas = np.zeros((self.hauteur, self.largeur, 3), dtype=np.uint8)
        self._reconstruct_image(self.tree, canvas, 0, 0, self.hauteur, self.largeur)
        return canvas

    def _reconstruct_image(self, tree, canvas: np.ndarray, x0: int, y0: int, h: int, w: int):
        if isinstance(tree, tuple) and len(tree) == 3:
            r, g, b = tree
            canvas[y0:y0+h, x0:x0+w] = (r, g, b)
            return

        mid_y = h // 2
        mid_x = w // 2

        if tree[0] is not None:
            self._reconstruct_image(tree[0], canvas, x0,        y0,        mid_y,   mid_x)
        if tree[1] is not None:
            self._reconstruct_image(tree[1], canvas, x0+mid_x,  y0,        mid_y,   w-mid_x)
        if tree[2] is not None:
            self._reconstruct_image(tree[2], canvas, x0,        y0+mid_y,  h-mid_y, mid_x)
        if tree[3] is not None:
            self._reconstruct_image(tree[3], canvas, x0+mid_x,  y0+mid_y,  h-mid_y, w-mid_x)




if __name__ == "__main__":
    Kmean("Ploug.png")
    Moyenne_couleur("Ploug.png")
