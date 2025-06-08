import os
import math
import requests
from io import BytesIO
from PIL import Image, ImageEnhance, ImageDraw

class Drone:
    def __init__(self):
        """
        Initialise les attributs du drone.
        """
        self.zoom = None
        self.lat = None
        self.lon = None
        self.x = None
        self.y = None
        self.captured_image = None
        self.visited_tiles = []

    def get_coordinates(self):
        return(self.lat, self.lon)

    def latlon_to_tile(self, lat, lon, zoom):
        """
        Convertit une paire (lat, lon) en indices de tuile (x, y)
        pour le niveau de zoom donné (slippy map).
        """
        lat_rad = math.radians(lat)
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.log(math.tan(lat_rad) + 1/math.cos(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def tile_to_latlon(self, x, y, zoom):
        """
        Convertit les indices de tuile (x, y) en coordonnées géographiques (lat, lon)
        pour le niveau de zoom donné.
        """
        n = 2 ** zoom
        lon = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat = math.degrees(lat_rad)
        return lat, lon

    def download_tile(self, x, y, zoom):
        """
        Télécharge la tuile cartographique (256×256) à l’indice (x,y,zoom).
        """
        url = f"https://basemaps.cartocdn.com/rastertiles/voyager_nolabels/{zoom}/{x}/{y}.png"
        headers = {"User-Agent": "DroneMappingSim/1.0 (contact: you@domain.com)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")

    def enhance_contrast(self, img, facteur=1.8):
        """
        Renforce le contraste de l’image PIL par le facteur indiqué.
        """
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(facteur)

    def _draw_marker(self, img, cx, cy, radius=10, color=(255, 0, 0)):
        """
        Trace un cercle plein de couleur `color` de rayon `radius`
        centré en (cx, cy) sur l’image PIL `img`.
        """
        draw = ImageDraw.Draw(img)
        bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.ellipse(bbox, fill=color)

    def capture_image(self, lat, lon, zoom, contraste=1.8):
        """
        Capture la tuile correspondant à (lat, lon, zoom), améliore son contraste,
        dessine le marqueur au centre, sauvegarde dans tiles/ et met à jour self.captured_image.
        """
        self.lat, self.lon, self.zoom = lat, lon, zoom
        self.x, self.y = self.latlon_to_tile(lat, lon, zoom)

        # Téléchargement
        tile = self.download_tile(self.x, self.y, zoom)

        # Contraste
        img = self.enhance_contrast(tile, facteur=contraste)

        # Marqueur au centre de la tuile (256×256)
        cx, cy = img.width // 2, img.height // 2
        self._draw_marker(img, cx, cy)

        # Sauvegarde
        os.makedirs("tiles", exist_ok=True)
        path = f"tiles/tuile_{zoom}_{self.x}_{self.y}.png"
        tile.save(path)

        # Mise à jour des attributs
        self.captured_image = img
        self.visited_tiles.append((self.x, self.y, zoom))
        print(f"Tuiles téléchargées : 1 (x={self.x}, y={self.y}, zoom={zoom}) → {path}")

    def deplacement(self, direction: str):
        """
        Déplace la tuile courante d’un pas selon `direction`,
        télécharge, dessine le marqueur, sauvegarde et met à jour self.captured_image.
        """
        if self.x is None or self.y is None:
            print("donner coordonnées init")
            return

        # Nord = y–, Sud = y+, Est = x+, Ouest = x–
        if direction == "droite":
            self.x += 1
        elif direction == "gauche":
            self.x -= 1
        elif direction == "haut":
            self.y -= 1
        elif direction == "bas":
            self.y += 1
        else:
            print(f"Direction inconnue : {direction}")
            return
        self.lat, self.lon = self.tile_to_latlon(self.x, self.y, self.zoom)
        print(f"Nouvelles coordonnées de tuile : x={self.x}, y={self.y}, zoom={self.zoom}")

        tile = self.download_tile(self.x, self.y, self.zoom)
        img = self.enhance_contrast(tile, facteur=1.8)

        # Marqueur au centre de la tuile
        cx, cy = img.width // 2, img.height // 2
        self._draw_marker(img, cx, cy)

        os.makedirs("tiles", exist_ok=True)
        path = f"tiles/tuile_{self.zoom}_{self.x}_{self.y}.png"
        tile.save(path)
        self.captured_image = img
        self.visited_tiles.append((self.x, self.y, self.zoom))
        print(f"Tuiles sauvegardée : {path}")

    def recoller(self, output_file: str = "mosaic.png") -> Image.Image:
        """
        Reconstruit une mosaïque de toutes les tuiles déjà téléchargées,
        la sauvegarde sous `output_file` et la renvoie comme PIL.Image.
        """
        if not self.visited_tiles:
            print("Aucune tuile à recoller.")
            return None

        tile_size = 256
        xs = [t[0] for t in self.visited_tiles]
        ys = [t[1] for t in self.visited_tiles]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        width  = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size
        mosaic = Image.new("RGB", (width, height))

        for x, y, zoom in self.visited_tiles:
            path = f"tiles/tuile_{zoom}_{x}_{y}.png"
            try:
                tile = Image.open(path)
            except FileNotFoundError:
                print(f"Fichier manquant : {path}")
                continue
            mosaic.paste(tile, ((x - min_x) * tile_size,
                                (y - min_y) * tile_size))

        mosaic.save(output_file)
        print(f"Mosaïque sauvegardée sous : {output_file}")
        return mosaic

    def afficher_image(self):
        """
        (désactivée) – l'interface doit récupérer self.captured_image.
        """
        print("afficher_image() est désactivé, utilisez self.captured_image dans l'UI.")