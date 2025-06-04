import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

class TraitementImage:
    def __init__(self):
        """
        Initialisation de la classe sans avoir besoin de télécharger l'image.
        """
        self.img = None
        self.segmented_img = None
        self.labels = None

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

    def afficher_paysage(self, type_paysage="all"):
        """
        Superpose sur l'image originale les zones segmentées issues de l'image traitée (segmentation K-means),
        selon les types de paysages spécifiés.

        Args:
            type_paysage (str): Type de paysage à afficher. Valeurs possibles : "urbain", "rural", "aquatique", ou "all".

        Affiche l'image originale avec les zones sélectionnées superposées à partir de l'image segmentée.
        """
        if self.img is None or self.segmented_img is None or self.labels is None:
            print("Données manquantes pour l'affichage (image originale, segmentée ou labels).")
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
        elif isinstance(type_paysage, str):
            type_paysage = type_paysage.lower()
            if type_paysage not in paysages:
                print(f"Type de paysage inconnu : {type_paysage}")
                return
            types_a_afficher = [type_paysage]
        else:
            print("Argument invalide. Veuillez fournir un type de paysage valide.")
            return

        # Convertir les images en tableaux numpy
        base_img = np.array(self.img).copy()
        segmented_array = np.array(self.segmented_img)

        # Superposer les zones souhaitées
        for type_ in types_a_afficher:
            label = paysages[type_]
            masque = (self.labels.reshape(base_img.shape[:2]) == label)
            base_img[masque, :] = segmented_array[masque, :]

        # Affichage
        image_resultat = Image.fromarray(base_img)
        plt.figure(figsize=(6, 6))
        plt.imshow(image_resultat)
        plt.title(f"Superposition : {', '.join(types_a_afficher)}")
        plt.axis("off")
        plt.show()






# Exemple d'utilisation
if __name__ == "__main__":
    # Charger l'image d'entrée (ici un exemple avec une image locale ou URL)
    img = Image.open("../finistere_tile.png")  # Remplacez "exemple_image.png" par votre propre image
    traitement = TraitementImage()

    # Segmenter l'image (k=3 pour 3 types de paysages)
    segmentee = traitement.k_means(img)
    traitement.afficher_paysage("all")


