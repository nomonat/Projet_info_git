import numpy as np
from PIL import Image, ImageDraw

def load_image_array(file: str) -> np.ndarray:
    """
    Charge une image depuis `file` et renvoie un array NumPy (hauteur, largeur, 3).
    """
    img = Image.open(file).convert("RGB")
    return np.array(img)


def variance_tile(tile_array: np.ndarray) -> np.ndarray:
    """
    Calcule la variance de chaque canal R, G, B sur `tile_array`.
    Méthode manuelle par boucles imbriquées, divisée par (h_tile * w_tile).
    Renvoie un ndarray shape (3,) : [var_R, var_G, var_B].
    """
    h_tile, w_tile, _ = tile_array.shape
    # Moyennes par canal
    moy = np.array([np.mean(tile_array[:, :, k]) for k in range(3)], dtype=float)

    # Somme des carrés des écarts
    V = np.zeros(3, dtype=float)
    for i in range(h_tile):
        for j in range(w_tile):
            for k in range(3):
                diff = float(tile_array[i, j, k]) - moy[k]
                V[k] += diff ** 2

    n_pixels = h_tile * w_tile
    return V / n_pixels


def quelle_couleur(moyenne: np.ndarray, seuil_dom: int = 30) -> tuple:
    """
    À partir d'une moyenne [R, G, B], renvoie la couleur dominante :
    - bleu si b > 200 et b > r,g
    - sinon bleu si b > g+adapt et b > r+adapt
    - sinon vert si g > r+adapt et g > b+adapt
    - sinon gris (127,127,127)
    """
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


def moy_une_tuile(tile_array: np.ndarray) -> tuple:
    """
    Calcule la couleur dominante (R,G,B → bleu, vert ou gris) sur `tile_array`.
    """
    moyenne = tile_array.reshape(-1, 3).mean(axis=0)
    return quelle_couleur(moyenne)


def recurrence(seuil_variance: float, tile_array: np.ndarray):
    """
    Si la variance RGB de `tile_array` est entièrement < seuil_variance,
    renvoie la couleur dominante de cette tuile (tuple (R,G,B)).
    Sinon, découpe `tile_array` en 4 sous-tuiles (TL, TR, BL, BR) et appelle
    récursivement `recurrence` sur chacune. Retourne une liste [res_TL, res_TR, res_BL, res_BR],
    où chaque élément est soit un triplet (R,G,B) soit une liste de 4 éléments (descente récursive).
    """
    h, w, _ = tile_array.shape
    var_rgb = variance_tile(tile_array)

    # Si tous les canaux sont sous le seuil, on renvoie la couleur dominante
    if (var_rgb < seuil_variance).all():
        return moy_une_tuile(tile_array)

    # Sinon, on découpe en 4 sous-tuiles
    mid_y = h // 2
    mid_x = w // 2

    arr_tl = tile_array[0:mid_y, 0:mid_x]       # haut-gauche
    arr_tr = tile_array[0:mid_y, mid_x:w]       # haut-droit
    arr_bl = tile_array[mid_y:h, 0:mid_x]       # bas-gauche
    arr_br = tile_array[mid_y:h, mid_x:w]       # bas-droit

    # Appel récursif pour chaque quadrant
    res_tl = recurrence(seuil_variance, arr_tl)
    res_tr = recurrence(seuil_variance, arr_tr)
    res_bl = recurrence(seuil_variance, arr_bl)
    res_br = recurrence(seuil_variance, arr_br)

    return [res_tl, res_tr, res_bl, res_br]


def reconstruct_image(tree, canvas: np.ndarray, x0: int, y0: int, h: int, w: int):
    """
    Reconstruit l'image à partir du résultat `tree` de `recurrence`.
    - tree : soit un tuple (R,G,B) pour une région homogène, soit
             une liste de 4 éléments [TL, TR, BL, BR], où chaque élément
             a la même structure récursive.
    - canvas : ndarray (hauteur_globale, largeur_globale, 3) à remplir.
    - (x0, y0) : coin supérieur gauche de la région à traiter.
    - h, w : dimensions de la région (hauteur, largeur).
    Cette fonction remplit `canvas[y0:y0+h, x0:x0+w]` en place.
    """
    # Si `tree` est un triplet de longueur 3, c'est un feuillu : on remplit la région
    if isinstance(tree, tuple) and len(tree) == 3:
        r, g, b = tree
        canvas[y0:y0+h, x0:x0+w] = (r, g, b)
        return

    # Sinon, `tree` est une liste de 4 sous-résultats [TL, TR, BL, BR]
    # On doit découper la région en 4. On se base sur la même logique que `recurrence`.
    mid_y = h // 2
    mid_x = w // 2

    # TL
    if tree[0] is not None:
        reconstruct_image(tree[0], canvas, x0,         y0,         mid_y, mid_x)
    # TR
    if tree[1] is not None:
        reconstruct_image(tree[1], canvas, x0+mid_x,   y0,         mid_y, w-mid_x)
    # BL
    if tree[2] is not None:
        reconstruct_image(tree[2], canvas, x0,         y0+mid_y,   h-mid_y, mid_x)
    # BR
    if tree[3] is not None:
        reconstruct_image(tree[3], canvas, x0+mid_x,   y0+mid_y,   h-mid_y, w-mid_x)


def build_reconstructed(tree, shape: tuple) -> np.ndarray:
    """
    Crée un canvas vierge de forme `shape = (hauteur, largeur, 3)`, et
    remplit chaque région à l'aide de `reconstruct_image`.
    Retourne le tableau final.
    """
    hauteur, largeur = shape[0], shape[1]
    canvas = np.zeros((hauteur, largeur, 3), dtype=np.uint8)
    reconstruct_image(tree, canvas, 0, 0, hauteur, largeur)
    return canvas


if __name__ == "__main__":
    # 1) Charger l'image originale
    img_array = load_image_array("Ploug.png")
    hauteur, largeur, _ = img_array.shape

    # 2) Calculer l'arbre (quadtree) avec un seuil donné
    seuil = 200
    tree = recurrence(seuil, img_array)

    # 3) Reconstruire l'image à partir de `tree`
    reconstructed_array = build_reconstructed(tree, (hauteur, largeur, 3))

    # 4) Convertir en PIL Image et afficher / sauvegarder
    reconstructed_img = Image.fromarray(reconstructed_array)
    reconstructed_img.show()           # Affiche l'image reconstruite
    # Ou pour sauvegarder :
    # reconstructed_img.save("reconstructed.png")
