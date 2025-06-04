import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

class TraitementImage:
    def __init__(self):
        self.img = None
        self.segmented_img = None
        self.labels = None

    def k_means(self, img, k=4):
        """
        Appliquer K-means pour segmenter l'image en 4 zones spécifiques (eau, rural, urbain, routes).
        """
        self.img = img.convert("RGB")
        img_np = np.array(self.img)
        h, w, d = img_np.shape
        pixels = img_np.reshape((-1, 3))

        # Centres initiaux pour les 4 types de zones
        initial_centers = np.array([
            [195, 229, 235],  # Bleu (eau)
            [218, 238, 199],  # Vert clair (rural)
            [255, 255, 249],  # Pâle (urbain)
            [255, 255, 150]   # Jaune clair (routes)
        ], dtype=np.uint8)

        kmeans = KMeans(n_clusters=k, init=initial_centers, n_init=1, random_state=0)
        kmeans.fit(pixels)

        self.labels = kmeans.labels_

        # Couleurs pour afficher chaque zone
        cluster_colors = np.array([
            [0, 0, 255],      # Eau
            [34, 139, 34],    # Rural
            [105, 105, 105],  # Urbain
            [255, 215, 0]     # Routes (jaune doré)
        ])
        colored_pixels = cluster_colors[self.labels].reshape((h, w, 3))
        self.segmented_img = Image.fromarray(np.uint8(colored_pixels))

        return self.segmented_img

    def afficher_paysage(self, type_paysage="all"):
        if self.img is None or self.segmented_img is None or self.labels is None:
            print("Données manquantes pour l'affichage.")
            return

        # Mise à jour : ajout du type "routes"
        paysages = {
            "aquatique": 0,
            "rural": 1,
            "urbain": 2,
            "routes": 3
        }

        if type_paysage == "all":
            types_a_afficher = list(paysages.keys())
        elif isinstance(type_paysage, str):
            type_paysage = type_paysage.lower()
            if type_paysage not in paysages:
                print(f"Type de paysage inconnu : {type_paysage}")
                return
            types_a_afficher = [type_paysage]
        else:
            print("Argument invalide.")
            return

        base_img = np.array(self.img).copy()
        segmented_array = np.array(self.segmented_img)

        for type_ in types_a_afficher:
            label = paysages[type_]
            masque = (self.labels.reshape(base_img.shape[:2]) == label)
            base_img[masque, :] = segmented_array[masque, :]

        image_resultat = Image.fromarray(base_img)
        plt.figure(figsize=(6, 6))
        plt.imshow(image_resultat)
        plt.title(f"Superposition : {', '.join(types_a_afficher)}")
        plt.axis("off")
        plt.show()

# Exemple d'utilisation
if __name__ == "__main__":
    img = Image.open("cartenontraitee.PNG")  # Remplacez par votre chemin d'image
    traitement = TraitementImage()

    segmentee = traitement.k_means(img, k=4)  # k=4 pour inclure les routes
    traitement.afficher_paysage("all")        # Afficher toutes les zones



