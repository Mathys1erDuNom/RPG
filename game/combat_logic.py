import random

def attack(attacker, defender):
    damage = max(1, attacker["atk"] - defender["def"] + random.randint(-2, 2))
    defender["hp"] -= damage
    return damage
