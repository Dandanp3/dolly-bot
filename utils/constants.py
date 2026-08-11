import random

NATURE_WORDS = ["leao", "savana", "arvore", "rio", "elefante", "girafa", "pedra", "sol", "grama", "chuva", "zebra", "hiena"]

def generate_verification_code():
    return " ".join(random.sample(NATURE_WORDS, 5))