import discord
from discord.ui import View, Select
import json
import random
import os

from combat_image import creer_image_combat
from personnage_db import (
    get_personnage, 
    update_personnage_pv, 
    personnage_existe, 
    supprimer_personnage,
    update_personnage_stats,
    update_personnage_attaques
)
from shop import afficher_shop


# ===== CONFIGURATION DES RÉGIONS =====
REGIONS_DISPONIBLES = [
    "foret",
    "desert"
]
# =====================================

def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def calcul_degats(attaque, attaquant, defenseur):
    """Calcule les dégâts d'une attaque en prenant en compte les ratios force/magie et les armures."""
    degats = attaque["degats"]
    
    ratio_attk = attaque.get("ratioattk", 0) / 100
    ratio_magie = attaque.get("ratiomagie", 0) / 100
    
    degats += attaquant.get("force", 0) * ratio_attk
    degats += attaquant.get("magie", 0) * ratio_magie
    
    if attaque["type"] == "magique":
        degats *= (1 - defenseur.get("armure_magique", 0) / 100)
    elif attaque["type"] == "physique":
        degats *= (1 - defenseur.get("armure", 0) / 100)
    elif attaque["type"] == "hybride":
        reduction = (defenseur.get("armure", 0) + defenseur.get("armure_magique", 0)) / 2
        degats *= (1 - reduction / 100)
    
    return max(1, int(degats))

class CombatView(View):
    def __init__(self, user_id, nb_regions=3, nb_ennemis_par_region=10):
        super().__init__(timeout=None)

        self.user_id = user_id
        self.combat_message = None  # Référence au message de combat
        
        # Charger le personnage depuis la base de données
        self.joueur = get_personnage(user_id)
        if not self.joueur:
            raise ValueError("Personnage introuvable dans la base de données")
        
        # Configuration des régions
        self.nb_ennemis_par_region = nb_ennemis_par_region
        self.regions_queue = random.sample(REGIONS_DISPONIBLES, k=min(nb_regions, len(REGIONS_DISPONIBLES)))
        
        # Charger la première région
        self.region = self.regions_queue.pop(0)
        self.image_fond = f"images/fond/{self.region}.png"
        
        # Charger les ennemis de la région actuelle
        region_enemies = load_json(f"json/ennemies/{self.region}.json")
        self.ennemis_queue = random.sample(region_enemies, k=min(nb_ennemis_par_region, len(region_enemies)))
        self.ennemi = self.ennemis_queue.pop(0)

        # Qui attaque en premier
        self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]

        # Select pour attaques du joueur
        self.update_attack_select()

    def update_attack_select(self):
        """Met à jour le menu de sélection des attaques."""
        # Retirer l'ancien select s'il existe
        for item in self.children[:]:
            if isinstance(item, Select):
                self.remove_item(item)
        
        options = [
            discord.SelectOption(label=a["nom"], description=f"Dégâts : {a['degats']}")
            for a in self.joueur["attaques"]
        ]
        self.select_attacks = Select(placeholder="Choisis une attaque", options=options)
        self.select_attacks.callback = self.joueur_attaque
        self.add_item(self.select_attacks)

    def get_combat_image(self):
        """Génère et retourne l'image du combat."""
        image_combat = creer_image_combat(self.joueur, self.ennemi, self.image_fond)
        return discord.File(fp=image_combat, filename="combat.png")

    def pv_text(self):
        """Texte des PV du joueur et de l'ennemi."""
        regions_restantes = len(self.regions_queue)
        return (
            f"🗺️ **Région : {self.region.capitalize()}** ({len(self.ennemis_queue) + 1} ennemis | {regions_restantes} régions restantes)\n"
            f"🧑 {self.joueur['nom']} ❤️ {max(self.joueur['pv'], 0)} / {self.joueur.get('pv_max', self.joueur['pv'])} PV | "
            f"👾 {self.ennemi['nom']} ❤️ {max(self.ennemi['pv'], 0)} / {self.ennemi.get('pv_max', self.ennemi['pv'])} PV\n"
        )

    def get_initial_message_content(self):
        """Retourne le contenu du message initial avec l'image."""
        content = self.pv_text()
        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"
        return content

    async def update_message(self, interaction, extra_text=""):
        """Met à jour le message Discord avec l'image du combat et le texte."""
        file = self.get_combat_image()

        content = self.pv_text()
        if extra_text:
            content += extra_text + "\n"
        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"

        # Utiliser la référence du message de combat
        if self.combat_message:
            await self.combat_message.edit(
                content=content,
                view=self if self.tour_joueur else None,
                attachments=[file]
            )
        else:
            await interaction.message.edit(
                content=content,
                view=self if self.tour_joueur else None,
                attachments=[file]
            )
        
        # Sauvegarder les stats dans la base de données
        update_personnage_pv(self.user_id, self.joueur["pv"])
        update_personnage_stats(self.user_id, self.joueur)
        update_personnage_attaques(self.user_id, self.joueur["attaques"])

    async def continuer_vers_prochaine_region(self, interaction, channel):
        """Continue vers la prochaine région après le shop."""
        if not self.regions_queue:
            # Plus de régions - victoire finale
            update_personnage_pv(self.user_id, self.joueur["pv"])
            update_personnage_stats(self.user_id, self.joueur)
            
            file = discord.File(fp="images/fin/fin.png", filename="fin.png")
            await channel.send(
                content=f"🏆 **Félicitations ! Vous avez vaincu toutes les régions !**\n"
                        f"❤️ PV restants : {self.joueur['pv']}/{self.joueur['pv_max']}",
                file=file
            )
            supprimer_personnage(self.user_id)
            user = await interaction.client.fetch_user(int(self.user_id))
            await channel.send(
                f"🗑️ {user.mention} Votre personnage a été supprimé après le combat. "
                "Vous pouvez en créer un nouveau avec `/creer_personnage` !"
            )
            return
        
        # Passer à la région suivante
        self.region = self.regions_queue.pop(0)
        self.image_fond = f"images/fond/{self.region}.png"
        
        region_enemies = load_json(f"json/ennemies/{self.region}.json")
        self.ennemis_queue = random.sample(region_enemies, k=min(self.nb_ennemis_par_region, len(region_enemies)))
        self.ennemi = self.ennemis_queue.pop(0)
        self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]
        
        # Mettre à jour le select d'attaques au cas où de nouvelles ont été achetées
        self.update_attack_select()
        
        # Restaurer les PV du joueur pour la nouvelle région
        self.joueur['pv'] = self.joueur['pv_max']
        update_personnage_pv(self.user_id, self.joueur['pv'])
        
        # Créer un NOUVEAU message de combat
        file = self.get_combat_image()
        content = self.pv_text()
        content += f"🗺️ **Nouvelle région : {self.region.capitalize()} !**\n"
        content += f"💚 **Vos PV ont été restaurés !**\n"
        content += f"👾 **Premier ennemi : {self.ennemi['nom']} !**\n"
        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"
        
        # Envoyer le nouveau message et garder la référence
        self.combat_message = await channel.send(
            content=content,
            view=self if self.tour_joueur else None,
            file=file
        )

    async def joueur_attaque(self, interaction: discord.Interaction):
        # Vérifier que c'est bien le joueur qui a lancé le combat
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas votre combat !",
                ephemeral=True
            )
            return
            
        if not self.tour_joueur:
            await interaction.response.defer()
            return
        await interaction.response.defer()

        attaque = next(a for a in self.joueur["attaques"] if a["nom"] == self.select_attacks.values[0])
        degats = calcul_degats(attaque, self.joueur, self.ennemi)
        self.ennemi["pv"] -= degats

        # Ennemi KO
        if self.ennemi["pv"] <= 0:
            if self.ennemis_queue:
                # Passer au prochain ennemi dans la même région
                self.ennemi = self.ennemis_queue.pop(0)
                self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]
                await self.update_message(
                    interaction,
                    extra_text=f"💥 **{attaque['nom']} inflige {degats} PV !**\n🏆 **Vous avez vaincu cet ennemi !**\n"
                               f"👾 **Prochain ennemi : {self.ennemi['nom']} !**"
                )
                return
            else:
                # Région terminée - afficher le shop
                await self.update_message(
                    interaction,
                    extra_text=f"💥 **{attaque['nom']} inflige {degats} PV !**\n🎉 **Région {self.region.capitalize()} terminée !**"
                )
                
                # Afficher le shop
                await afficher_shop(
                    interaction,
                    self.user_id,
                    self.region,
                    self.joueur,
                    self.continuer_vers_prochaine_region
                )
                return

        # Passage au tour de l'ennemi
        self.tour_joueur = False
        await self.update_message(interaction, extra_text=f"💥 **Vous utilisez {attaque['nom']} et infligez {degats} PV !**")
        await self.ennemi_attaque(interaction)

    async def ennemi_attaque(self, interaction: discord.Interaction):
        attaque = random.choice(self.ennemi["attaques"])
        degats = calcul_degats(attaque, self.ennemi, self.joueur)
        self.joueur["pv"] -= degats

        if self.joueur["pv"] <= 0:
            # Joueur KO - sauvegarder les PV à 0
            update_personnage_pv(self.user_id, 0)
            
            await self.update_message(
                interaction,
                extra_text=f"💥 **{self.ennemi['nom']} inflige {degats} PV avec {attaque['nom']} !**\n💀 **Vous avez été vaincu...**"
            )
            # Reset automatique du personnage
            supprimer_personnage(self.user_id)
            
            return
        else:
            # Retour au joueur
            self.tour_joueur = True
            await self.update_message(
                interaction,
                extra_text=f"💥 **{self.ennemi['nom']} inflige {degats} PV avec {attaque['nom']} !**"
            )


async def demarrer_combat(interaction: discord.Interaction, nb_regions=3, nb_ennemis_par_region=10):
    """Démarre un combat pour l'utilisateur."""
    user_id = str(interaction.user.id)
    
    # Vérifier que l'utilisateur a un personnage
    if not personnage_existe(user_id):
        await interaction.response.send_message(
            "❌ Vous n'avez pas de personnage ! Utilisez `/creer_personnage` d'abord.",
            ephemeral=True
        )
        return
    
    # Charger le personnage
    joueur = get_personnage(user_id)
    
    # Vérifier que le joueur a des PV
    if joueur["pv"] <= 0:
        await interaction.response.send_message(
            "❌ Votre personnage est KO ! Utilisez `/soigner` pour restaurer vos PV.",
            ephemeral=True
        )
        return
    
    # Créer la vue de combat
    try:
        view = CombatView(user_id, nb_regions, nb_ennemis_par_region)
        file = view.get_combat_image()
        
        await interaction.response.send_message(
            content=view.get_initial_message_content(),
            view=view,
            file=file
        )
        
        # Garder la référence du message initial
        view.combat_message = await interaction.original_response()
        
    except ValueError as e:
        await interaction.response.send_message(
            f"❌ Erreur : {str(e)}",
            ephemeral=True
        )