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
        self.route= None

    def tracer_trait_de_cote(self, output_file: str = "trait_de_cote_rouge.png", seuil: float = 0.5):
        """
        Détecte les pixels bleus (== [0,0,255]) dans self.img_array, calcule
        le bord (trait de côte) avec un opérateur de Sobel, puis superpose
        ce trait en rouge sur l’image et sauvegarde le résultat.

        - output_file : nom du fichier PNG de sortie
        - seuil       : seuil sur l’amplitude du gradient pour tracer le trait
        """
        img_array = self.img_array

        # 1. Masque binaire des pixels exactement bleus
        masque_bleu = np.zeros((self.hauteur, self.largeur), dtype=bool)
        for y in range(self.hauteur):
            for x in range(self.largeur):
                pixel = img_array[y, x]
                if (pixel[0] == 0) and (pixel[1] == 0) and (pixel[2] == 255):
                    masque_bleu[y, x] = True

        # 2. Convertir en float pour calcul Sobel
        masque_flou = masque_bleu.astype(float)

        # 3. Calcul des gradients de Sobel
        grad_x = ndimage.sobel(masque_flou, axis=1)
        grad_y = ndimage.sobel(masque_flou, axis=0)
        grad = np.hypot(grad_x, grad_y)

        # 4. Seuil pour obtenir un trait fin
        trait_de_cote = grad > seuil

        # 5. Superposer le trait rouge
        img_trait = img_array.copy()
        img_trait[trait_de_cote] = [255, 0, 0]

        # 6. Sauvegarde
        Image.fromarray(img_trait).save(output_file)
        Image.fromarray(img_trait).show()

    def creer_masques_couleurs(self):
        """
        Crée des masques booléens pour les pixels exactement :
        - bleu  = [0, 0, 255]
        - vert  = [0, 255, 0]
        - rouge = [255, 0, 0]
        - jaune = [255, 255, 0]
        et stocke ces masques dans self.bleu, self.vert, self.rouge et self.jaune.
        """
        arr = self.img_array
        # Bleu
        self.bleu = (arr[:, :, 0] == 0) & (arr[:, :, 1] == 0) & (arr[:, :, 2] == 255)
        # Vert
        self.vert = (arr[:, :, 0] == 0) & (arr[:, :, 1] == 255) & (arr[:, :, 2] == 0)
        # Rouge
        self.rouge = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 0) & (arr[:, :, 2] == 0)
        # Jaune
        self.jaune = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 255) & (arr[:, :, 2] == 0)


class Kmean(Traitement_image):
    def __init__(self, file: str, k: int = 4):
        """
        Initialisation : charge l’image, segmente dès l’instanciation,
        affiche et enregistre le résultat.
        """
        super().__init__(file)
        self.segmented_img = None
        self.labels = None

        # 1) Exécute la segmentation K-means
        img_segmentee = self.k_means(k)

        # 2) Affiche et enregistre l’image segmentée
        img_segmentee.show()
        img_segmentee.save("Kmean.png")
        self.creer_masques_couleurs()

    def k_means(self, k: int = 4):
        """
        Appliquer K-means pour segmenter l'image chargée (self.img_array)
        en 4 zones : eau, rural, urbain, routes. Retourne l’image segmentée.
        """
        img_np = self.img_array
        h, w, _ = img_np.shape
        pixels = img_np.reshape((-1, 3))

        initial_centers = np.array([
            [195, 229, 235],  # Bleu (eau)
            [218, 238, 199],  # Vert clair (rural)
            [255, 255, 249],  # Pâle (urbain)
            [255, 255, 150]   # Jaune clair (routes)
        ], dtype=np.uint8)

        kmeans = KMeans(n_clusters=k, init=initial_centers, n_init=1, random_state=0)
        kmeans.fit(pixels)
        self.labels = kmeans.labels_

        cluster_colors = np.array([
            [0,   0,   255],  # Eau
            [34, 139,  34],   # Rural
            [105, 105, 105],  # Urbain
            [255, 215,   0]   # Routes
        ])
        colored_pixels = cluster_colors[self.labels].reshape((h, w, 3))
        self.segmented_img = Image.fromarray(colored_pixels.astype(np.uint8))
        return self.segmented_img

    def afficher_paysage(self, type_paysage: str = "all"):
        """
        Superpose sur l'image originale les zones segmentées (K-means),
        selon le type de paysage ("aquatique", "rural", "urbain", "routes" ou "all").
        """
        if self.img is None or self.segmented_img is None or self.labels is None:
            print("Données manquantes pour l'affichage.")
            return

        paysages = {
            "aquatique": 0,
            "rural": 1,
            "urbain": 2,
            "routes": 3
        }

        if type_paysage == "all":
            types_a_afficher = list(paysages.keys())
        else:
            type_paysage = type_paysage.lower()
            if type_paysage not in paysages:
                print(f"Type de paysage inconnu : {type_paysage}")
                return
            types_a_afficher = [type_paysage]

        base_img = self.img_array.copy()
        segmented_array = np.array(self.segmented_img)
        for type_ in types_a_afficher:
            label = paysages[type_]
            masque = (self.labels.reshape(base_img.shape[:2]) == label)
            base_img[masque] = segmented_array[masque]

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

        À l’instanciation, construit l’arbre quadtree et reconstruit l’image.
        """
        super().__init__(file)
        self.seuil_variance = seuil_variance
        self.tree = self.recurrence(self.img_array)

        reconstructed_array = self.build_reconstructed()
        reconstructed_img = Image.fromarray(reconstructed_array)
        reconstructed_img.show()
        reconstructed_img.save("Moyenne_couleur.png")
        self.creer_masques_couleurs()

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
    # Exemple d'utilisation de la détection du trait de côte sur une image reconstruite
    ti = Traitement_image("Kmean.png")
    ti.tracer_trait_de_cote()
