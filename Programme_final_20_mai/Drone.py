import math
import requests
from PIL import Image, ImageEnhance
from io import BytesIO

class Drone:
    def __init__(self):
        """
        Initialise les attributs du drone.
        """
        self.zoom = None
        self.lat_min = None
        self.lat_max = None
        self.lon_min = None
        self.lon_max = None
        self.num_tiles = 0
        self.captured_image = None

    def latlon_to_tile(self, lat, lon, zoom):
        lat_rad = math.radians(lat)
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
        return x, y

    def tiles_from_bbox(self, min_lat, min_lon, max_lat, max_lon, zoom):
        x_min, y_max = self.latlon_to_tile(min_lat, min_lon, zoom)
        x_max, y_min = self.latlon_to_tile(max_lat, max_lon, zoom)

        tile_list = []
        for x in range(min(x_min, x_max), max(x_min, x_max) + 1):
            for y in range(min(y_min, y_max), max(y_min, y_max) + 1):
                tile_list.append((x, y, zoom))

        return tile_list

    def download_tile(self, x, y, zoom):
        url = f"https://basemaps.cartocdn.com/rastertiles/voyager_nolabels/{zoom}/{x}/{y}.png"
        headers = {
            "User-Agent": "DroneMappingSim/1.0 (contact: noam.grolleau@ensta.fr)"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")

    def create_image_from_tiles(self, tiles):
        tile_size = 256
        min_x = min(tile[0] for tile in tiles)
        min_y = min(tile[1] for tile in tiles)
        max_x = max(tile[0] for tile in tiles)
        max_y = max(tile[1] for tile in tiles)

        width = (max_x - min_x + 1) * tile_size
        height = (max_y - min_y + 1) * tile_size
        image = Image.new('RGB', (width, height))

        for x, y, zoom in tiles:
            tile_img = self.download_tile(x, y, zoom)
            pos_x = (x - min_x) * tile_size
            pos_y = (y - min_y) * tile_size
            image.paste(tile_img, (pos_x, pos_y))

        return image

    def enhance_contrast(self, img, facteur=1.8):
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(facteur)

    def clear_attributes(self):
        self.zoom = None
        self.lat_min = None
        self.lat_max = None
        self.lon_min = None
        self.lon_max = None
        self.num_tiles = 0
        self.captured_image = None

    def capture_image(self, lat_min, lon_min, lat_max, lon_max, zoom, contraste=1.8):
        """
        Capture une image de la zone spécifiée et améliore le contraste.
        L'image n'est pas affichée automatiquement.
        """
        self.lat_min = lat_min
        self.lon_min = lon_min
        self.lat_max = lat_max
        self.lon_max = lon_max
        self.zoom = zoom

        tiles = self.tiles_from_bbox(lat_min, lon_min, lat_max, lon_max, zoom)
        self.num_tiles = len(tiles)
        print(f"{self.num_tiles} tuiles trouvées.")

        image = self.create_image_from_tiles(tiles)
        self.captured_image = self.enhance_contrast(image, facteur=contraste)

    def afficher_image(self):
        """
        Affiche l'image capturée si elle existe.
        """
        if self.captured_image:
            self.captured_image.show()
        else:
            print("Aucune image à afficher. Veuillez d'abord appeler capture_image().")
if __name__ == "__main__":
    # Création d'une instance de drone
    drone = Drone()

    # Paramètres de la zone à capturer (ex: Finistère)
    lat_min = 47.7
    lon_min = -5.1
    lat_max = 48.8
    lon_max = -3.2
    zoom = 11
    contraste = 1.8

    # Capture de l'image
    drone.capture_image(lat_min, lon_min, lat_max, lon_max, zoom, contraste)

    # Affichage de l'image capturée
    drone.afficher_image()
