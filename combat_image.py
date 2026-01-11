# combat_image.py
from PIL import Image, ImageDraw, ImageFont
import io

def creer_image_combat(joueur, ennemi, fond_path="images/region/fond.png"):
    """
    Crée une image du combat avec :
    - Fond
    - Joueur à gauche
    - Ennemi à droite
    - Barres de PV avec couleur pleine + fond gris
    Retourne un BytesIO pour Discord
    """
    # Charger images
    fond = Image.open(fond_path).convert("RGBA")
    perso_img = Image.open(joueur["image"]).convert("RGBA")
    ennemi_img = Image.open(ennemi["image"]).convert("RGBA")

    # Redimensionner
    perso_img = perso_img.resize((150, 150))
    ennemi_img = ennemi_img.resize((150, 150))

    # Coller sur le fond
    fond.paste(perso_img, (50, fond.height - 200), perso_img)
    fond.paste(ennemi_img, (fond.width - 200, 50), ennemi_img)

    # Dessiner barres de PV
    draw = ImageDraw.Draw(fond)
    font = ImageFont.load_default()

    # Paramètres barre
    barre_largeur = 150
    barre_hauteur = 10

    # ------------------ Joueur ------------------
    pv_joueur = max(joueur["pv"], 0)
    pv_max_joueur = joueur["pv_max"]

    # Fond gris
    draw.rectangle(
        (50, fond.height - 220, 50 + barre_largeur, fond.height - 220 + barre_hauteur),
        fill=(50, 50, 50)  # gris foncé
    )
    # Partie pleine (verte)
    draw.rectangle(
        (50, fond.height - 220, 50 + int(barre_largeur * pv_joueur / pv_max_joueur), fond.height - 220 + barre_hauteur),
        fill=(0, 255, 0)
    )
    draw.text((50, fond.height - 235), f"{joueur['nom']} {pv_joueur}/{pv_max_joueur} PV", fill="white", font=font)

    # ------------------ Ennemi ------------------
    pv_ennemi = max(ennemi["pv"], 0)
    pv_max_ennemi = ennemi["pv_max"]

    # Fond gris
    draw.rectangle(
        (fond.width - 200, 30, fond.width - 200 + barre_largeur, 30 + barre_hauteur),
        fill=(50, 50, 50)
    )
    # Partie pleine (rouge)
    draw.rectangle(
        (fond.width - 200, 30, fond.width - 200 + int(barre_largeur * pv_ennemi / pv_max_ennemi), 30 + barre_hauteur),
        fill=(255, 0, 0)
    )
    draw.text((fond.width - 200, 10), f"{ennemi['nom']} {pv_ennemi}/{pv_max_ennemi} PV", fill="white", font=font)

    # Retourner en BytesIO
    output = io.BytesIO()
    fond.save(output, format="PNG")
    output.seek(0)
    return output
