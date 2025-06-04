import numpy as np
from PIL import Image

class Traitement_image:
    def __init__(self, file):
        self.img = Image.open(file).convert("RGB")
        self.img_array = np.array(self.img)
        self.hauteur, self.largeur, _ = self.img_array.shape
        self.rural = None
        self.urbain = None
        self.marin = None

class Moyenne_couleur(Traitement_image):
    def __init__(self, file):
        super().__init__(file)

    def variance(self):
        """
        Calcule la variance de chaque canal R, G, B sur self.img_array.
        Méthode manuelle par boucles, divisée par (hauteur * largeur).
        Renvoie un tableau shape (3,) : [var_R, var_G, var_B].
        """
        moy = []
        moy=np.array([np.mean(self.img_array[:,:,k]) for k in range(3)])

        V = np.zeros(3, dtype=float)
        for i in range(self.hauteur):
            for j in range(self.largeur):
                for k in range(3):
                    diff =self.img_array[i, j, k] - moy[k]
                    V[k] += diff**2
        n_pixels = self.hauteur * self.largeur
        return V / n_pixels

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

    def moy_une_tuile(self):
        tile=self.img_array
        moyenne = tile.reshape(-1, 3).mean(axis=0)
        return self.quelle_couleur(moyenne)

    def recurrence(self,seuil_variance,tuile):
        if (seuil_variance>tuile.variance()).all():
            return tuile.moy_une_tuile()
        else:




if __name__ == "__main__":
    traitement = Moyenne_couleur("Ploug.png")
    img=traitement.img_array
