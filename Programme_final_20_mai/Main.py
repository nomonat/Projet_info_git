from Drone import *
from traitement_image import *
import os

class Mission():

    def __init__(self, nom_de_mission, nb_drones, lat_min, lat_max, lon_min, lon_max, liste_zoom):
        assert nb_drones == len(liste_zoom), "Il doit y avoir autant de drones que de niveaux de zoom"
        self.nb_drones = nb_drones
        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.liste_zoom = liste_zoom
        self.liste_drones = [Drone() for _ in range(nb_drones)]
        self.nom_de_mission = nom_de_mission

    def lancer_reconnaissance(self):
        for i in range(len(self.liste_drones)):
            self.liste_drones[i].capture_image(
                self.lat_min,
                self.lon_min,
                self.lat_max,
                self.lon_max,
                self.liste_zoom[i]
            )

    def enregistrer_image(self, drone, img):
        nom_fichier = f"img_traitee_{self.nom_de_mission}_zoom_{drone.zoom}.png"
        chemin_complet = os.path.join(os.getcwd(), nom_fichier)
        img.save(chemin_complet)
        print(f"Image enregistrée sous : {chemin_complet}")

    def print_save(self, paysages="all", bool_save=True):
        for drone in self.liste_drones:
            traiter = TraitementImage()
            img_traitee = traiter.k_means(drone.captured_image, k=4)  # ✅ k=4 pour inclure les routes
            traiter.afficher_paysage(paysages)
            if bool_save:
                self.enregistrer_image(drone, img_traitee)
            del traiter


# Exemple d'exécution
min_lat, min_lon = 47.7, -5.1
max_lat, max_lon = 48.8, -3.2
zoom = 11

if __name__ == "__main__":
    Mission_test = Mission("test", 1, min_lat, max_lat, min_lon, max_lon, [zoom])
    Mission_test.lancer_reconnaissance()
    Mission_test.print_save("all", True)







