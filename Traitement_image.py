import numpy as np
from PIL import Image
from scipy import ndimage
from sklearn.cluster import KMeans

class Traitement_image:
    """
    Classe mère du traitement
    Permet d'initialiser les différentes zones et d'avoir des méthodes communes aux
    traitements d'images K-means et Moyenne_couleur à écrire qu'une fois
    """
    def __init__(self, file: str):
        """
        Ouvre le fichier image et le convertit en un tableau numpy de taille hauteur*largeur*3.
        Ainsi, img_array[i,j] est le RGB du pixel à la position (i,j).
        Initialise les zones masques des futurs zones.
        """
        self.img = Image.open(file).convert("RGB")
        self.img_array = np.array(self.img)
        self.hauteur, self.largeur, _ = self.img_array.shape
        self.rural = None
        self.urbain = None
        self.aquatique = None
        self.routes = None
        self.trait_de_cote = None
        self.eaux_interieur=None
        self.mer=None

    def tracer_trait_de_cote(self):
        """
        Calcule et stock le masque du trait de côte dans self.trait_de_cote.
        Suppose que la mer est liée à une extrémité de l'image .
        Stop la mer à l'embouchure des rivières
        """
        if self.aquatique is None:
            self.creer_masques_couleurs()

        labels, nb = ndimage.label(self.aquatique)  #identifie toutes les zones connexes

        #On garde que les zones qui touchent le bord
        self.mer = np.zeros_like(self.aquatique)
        for i in range(1, nb + 1):
            comp_mask = (labels == i)
            if (
                comp_mask[0, :].any()
                or comp_mask[-1, :].any()
                or comp_mask[:, 0].any()
                or comp_mask[:, -1].any()
            ):
                self.mer |= comp_mask

        #Gradient de Sobel sur le masque pour trouver les pixels de changement entre terre et mer
        grad_x = ndimage.sobel(self.mer.astype(float), axis=1)
        grad_y = ndimage.sobel(self.mer.astype(float), axis=0)
        grad   = np.hypot(grad_x, grad_y)

        #Permet de faire un trait fin
        self.trait_de_cote = grad > 1

    def creer_masques_couleurs(self):
        """
        Crée les 4 masques à partir deu filtre (K-means ou Moyenne_couleur)
        """
        arr = self.img_array
        self.aquatique = (arr[:, :, 0] == 0)   & (arr[:, :, 1] == 0)   & (arr[:, :, 2] == 255)
        self.rural  = (arr[:, :, 0] == 34)  & (arr[:, :, 1] == 139) & (arr[:, :, 2] == 34)
        self.urbain = (arr[:, :, 0] == 105) & (arr[:, :, 1] == 105) & (arr[:, :, 2] == 105)
        self.routes = (arr[:, :, 0] == 255) & (arr[:, :, 1] == 215) & (arr[:, :, 2] == 0)

    def appliquer_masque(self, masque, couleur):
        """
        Prend en paramètre un masque et une couleur RGB.
        Retourne un PIL.Image où les pixels du masque sont recoloriés.
        """
        img_mod = self.img_array.copy()
        img_mod[masque] = couleur
        return Image.fromarray(img_mod)

    def trouver_eaux_interieur(self, seuil: float = 0.5) -> np.ndarray:
        """
        Les eaux intérieures sont les pixels qui ne sont pas la mer
        """
        self.eaux_interieur = self.aquatique & (~self.mer)
        return self.eaux_interieur


class Kmean(Traitement_image):
    """Noam"""
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
    """Florian - Traitement d'une image par segmentation en tuiles à qui on applique une couleur uniforme"""
    def __init__(self, file: str, seuil_variance: float = 50):
        """Initialisation de la classe"""
        super().__init__(file) #On récupère tous les attributs de la classe mère : Traitement_image et on charge l'image
        self.seuil_variance = seuil_variance #contrôle la précision de la segmentation
        self.arbre = self.recurrence(self.img_array) #la méthode se fait par récurrence et on stock le résultat dans un arbre
        reconstruite = self.reconstruction() #Une fois segmentée et traitée, on recolle l'image
        Image.fromarray(reconstruite).save("Moyenne_couleur.png") #On enregistre l'image
        self.img = Image.fromarray(reconstruite)
        self.img_array = reconstruite
        self.creer_masques_couleurs() #créé les masques

    def variance_tile(self, tile):
        """Calcul de la variance d'une tuile"""
        h, w, _ = tile.shape
        moy = tile.reshape(-1, 3).mean(0)
        V = ((tile - moy) ** 2).sum(axis=(0, 1))
        return V / (h * w)


    def quelle_couleur(self, moyenne: np.ndarray) -> tuple:
        """
        À partir d'une moyenne [R,G,B], retourne la couleur la plus proche
        parmi les couleurs de la carte, ou gris si aucune n'est proche.
        """
        r, g, b = map(int, moyenne)
        dico={"bleu" : (195, 229, 235),  # eau
        "vert" : (218, 238, 199),  # rural
        "gris" : (255, 255, 249),  # urbain pâle
        "jaune" : (255, 255, 150),  # routes
              }
        seuil = 60

        def distance(r, g, b, couleur):
            """Fonction interne calculant la distance des pixels aux couleurs qu'on souhaite"""
            return abs(r - couleur[0]) + abs(g - couleur[1]) + abs(b - couleur[2])

        [db, dv, dg, dj]=[distance(r,g,b,couleur) for couleur in dico.values()]

        if db <= seuil and db < dv and db < dg and db < dj:
            return (0, 0, 255)  # bleu pur pour eau
        elif dv <= seuil and dv < db and dv < dg and dv < dj:
            return (34, 139, 34)  # vert foncé pour rural
        elif dg <= seuil and dg < db and dg < dv and dg < dj:
            return (105, 105, 105)  # gris foncé pour urbain
        elif dj <= seuil and dj < db and dj < dv and dj < dg:
            return (255, 215, 0)  # jaune doré pour routes
        else:
            return (105, 105, 105)  # sinon gris foncé par défaut

    def recurrence(self, tile):
        """
        Fonction récursive qui découpe la tuile en quatre si les couleurs varient trop.
        On répète tant que la variance soit acceptable
        """
        h, l, _ = tile.shape
        #Condition d'arrêt : variance faible ou tuile trop petite
        if h * l == 0 or h <= 1 or l <= 1 or (self.variance_tile(tile) < self.seuil_variance).all():
            moy = tile.reshape(-1, 3).mean(0)
            return self.quelle_couleur(moy)
        # sinon, on découpe en 4 et on continue la récurrence
        h0, l0 = h // 2, l // 2
        return [
            self.recurrence(tile[0:h0,0:l0]),
            self.recurrence(tile[0:h0,l0:l]),
            self.recurrence(tile[h0:h,0:l0]),
            self.recurrence(tile[h0:h,l0:l]),
        ]

    def reconstruction(self):
        """
        Fonction permettant la reconstruction de l'image
        """
        final = np.zeros((self.hauteur, self.largeur, 3), dtype=np.uint8) #initialisation du tableau de l'image finale
        def _fill(arbre, y0, x0, h, l):
            """Fonction récursive interne qui rempli final à partir de l'arbre"""
            if isinstance(arbre, tuple): #si arbre est une couleur on peut remplir la zone
                final[y0:y0+h, x0:x0+l] = arbre
                return
            h0, l0 = h // 2, l // 2
            _fill(arbre[0], y0, x0, h0, l0)
            _fill(arbre[1], y0, x0 + l0, h0, l - l0)
            _fill(arbre[2], y0 + h0, x0, h - h0, l0)
            _fill(arbre[3], y0 + h0, x0 + l0, h - h0, l - l0)

        _fill(self.arbre, 0, 0, self.hauteur, self.largeur)
        return final


if __name__ == "__main__":
    # Charger l'image avec ta classe Moyenne_couleur (ou Kmean)
    mc = Moyenne_couleur("riviere.png")

    # Calculer le trait de côte
    mc.tracer_trait_de_cote()

    # Le trait de côte est dans mc.trait_de_cote, un masque booléen
    # Pour l'afficher, on va créer une image où le trait de côte est en rouge par exemple

    # Copier l'image d'origine
    img_mod = mc.img_array.copy()

    # Colorier les pixels du trait de côte en rouge (R=255, G=0, B=0)
    img_mod[mc.trait_de_cote] = [255, 0, 0]

    # Convertir en image PIL et afficher
    Image.fromarray(img_mod).show()
