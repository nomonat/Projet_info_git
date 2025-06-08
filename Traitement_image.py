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

    def tracer_trait_de_cote(self, output_file: str = "trait_de_cote_rouge.png", seuil: float = 0.5):
        img_array = self.img_array
        # 1. Masque binaire des pixels bleus
        masque_bleu = np.zeros((self.hauteur, self.largeur), dtype=bool)
        for y in range(self.hauteur):
            for x in range(self.largeur):
                pixel = img_array[y, x]
                if (pixel[0] == 0) and (pixel[1] == 0) and (pixel[2] == 255):
                    masque_bleu[y, x] = True

        # 2. Convertir en float pour Sobel
        masque_flou = masque_bleu.astype(float)

        # 3. Gradients de Sobel
        grad_x = ndimage.sobel(masque_flou, axis=1)
        grad_y = ndimage.sobel(masque_flou, axis=0)
        grad   = np.hypot(grad_x, grad_y)

        # 4. Seuil et stockage
        self.trait_de_cote = (grad > seuil)

    def creer_masques_couleurs(self):
        arr = self.img_array
        self.marin  = (arr[:,:,0]==0)   & (arr[:,:,1]==0)   & (arr[:,:,2]==255)
        self.rural  = (arr[:,:,0]==34)  & (arr[:,:,1]==139) & (arr[:,:,2]==34)
        self.urbain = (arr[:,:,0]==105) & (arr[:,:,1]==105) & (arr[:,:,2]==105)
        self.routes = (arr[:,:,0]==255) & (arr[:,:,1]==215) & (arr[:,:,2]==0)

    def appliquer_masque(self, masque):
        """Exemple de méthode pour modifier self.img_array selon un masque."""
        img_mod = self.img_array.copy()
        img_mod[masque] = [255, 0, 0]
        return Image.fromarray(img_mod)


class Kmean(Traitement_image):
    def __init__(self, file: str, k: int = 4):
        super().__init__(file)
        self.segmented_img = None
        self.labels = None
        img_segmentee = self.k_means(k)
        img_segmentee.save("Kmean.png")
        self.creer_masques_couleurs()

    def k_means(self, k: int = 4):
        img_np = self.img_array
        h, w, _ = img_np.shape
        pixels = img_np.reshape((-1,3))

        initial_centers = np.array([
            [195,229,235],
            [218,238,199],
            [255,255,249],
            [255,255,150]
        ], dtype=np.uint8)

        kmeans = KMeans(n_clusters=k, init=initial_centers, n_init=1, random_state=0)
        kmeans.fit(pixels)
        self.labels = kmeans.labels_

        cluster_colors = np.array([
            [0,0,255],
            [34,139,34],
            [105,105,105],
            [255,215,0]
        ])
        colored = cluster_colors[self.labels].reshape((h,w,3))
        self.segmented_img = Image.fromarray(colored.astype(np.uint8))
        return self.segmented_img

    def afficher_paysage(self, type_paysage: str = "all"):
        if self.segmented_img is None or self.labels is None:
            print("Segmentation non réalisée.")
            return

        mapping = {"aquatique":0, "rural":1, "urbain":2, "routes":3}
        if type_paysage=="all":
            types_ = mapping.keys()
        else:
            t = type_paysage.lower()
            if t not in mapping:
                print("Type inconnu")
                return
            types_ = [t]

        base = self.img_array.copy()
        seg_arr = np.array(self.segmented_img)
        for t in types_:
            lbl = mapping[t]
            mask = (self.labels.reshape(base.shape[:2])==lbl)
            base[mask] = seg_arr[mask]

        plt.imshow(base)
        plt.axis("off")
        plt.show()


class Moyenne_couleur(Traitement_image):
    def __init__(self, file: str, seuil_variance: float = 100):
        super().__init__(file)
        self.seuil_variance = seuil_variance
        self.tree = self.recurrence(self.img_array)
        rec = self.build_reconstructed()
        Image.fromarray(rec).save("Moyenne_couleur.png")
        self.creer_masques_couleurs()

    def variance_tile(self, tile: np.ndarray):
        h, w, _ = tile.shape
        moy = tile.reshape(-1,3).mean(axis=0)
        V = ((tile - moy)**2).sum(axis=(0,1))
        return V / (h*w)

    def quelle_couleur(self, moyenne: np.ndarray) -> tuple:
        r,g,b = map(int, moyenne)
        # centres
        CB = (195,229,235); CG = (218,238,199)
        CP = (255,255,249); CY = (255,255,150)
        S = 60
        d = lambda C: abs(r-C[0])+abs(g-C[1])+abs(b-C[2])
        db, dg, dp, dy = d(CB), d(CG), d(CP), d(CY)
        if db<=S and db<dg and db<dp and db<dy: return (0,0,255)
        if dg<=S and dg<db and dg<dp and dg<dy: return (34,139,34)
        if dp<=S and dp<db and dp<dg and dp<dy: return (105,105,105)
        if dy<=S and dy<db and dy<dg and dy<dp: return (255,215,0)
        return (105,105,105)

    def recurrence(self, tile: np.ndarray):
        h, w, _ = tile.shape
        if h*w==0:
            return (127,127,127)
        if h<=1 or w<=1:
            return self.quelle_couleur(tile.reshape(-1,3).mean(axis=0))

        var = self.variance_tile(tile)
        if (var < self.seuil_variance).all():
            return self.quelle_couleur(tile.reshape(-1,3).mean(axis=0))

        my, mx = h//2, w//2
        if my==0 or mx==0:
            return self.quelle_couleur(tile.reshape(-1,3).mean(axis=0))

        tl = self.recurrence(tile[0:my,   0:mx])
        tr = self.recurrence(tile[0:my,   mx:w])
        bl = self.recurrence(tile[my:h,   0:mx])
        br = self.recurrence(tile[my:h,   mx:w])
        return [tl, tr, bl, br]

    def build_reconstructed(self) -> np.ndarray:
        canvas = np.zeros((self.hauteur, self.largeur,3), dtype=np.uint8)
        def _fill(tree, y0, x0, h, w):
            if isinstance(tree, tuple):
                canvas[y0:y0+h, x0:x0+w] = tree; return
            my, mx = h//2, w//2
            _fill(tree[0], y0,    x0,    my,   mx)
            _fill(tree[1], y0,    x0+mx, my,   w-mx)
            _fill(tree[2], y0+my, x0,    h-my, mx)
            _fill(tree[3], y0+my, x0+mx, h-my, w-mx)
        _fill(self.tree, 0,0, self.hauteur, self.largeur)
        return canvas


if __name__ == "__main__":
    # test rapide
    Moyenne_couleur("riviere.png")
