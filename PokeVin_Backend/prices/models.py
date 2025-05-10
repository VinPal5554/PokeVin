from django.db import models
from django.contrib.auth.models import User  # Associating users with wishlists


class PokemonPrice(models.Model):
    name = models.CharField(max_length=100)  # Name of the Pokémon
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price of the Pokémon
    source = models.CharField(max_length=100)  # Source where the price was fetched from (e.g., Ebay)
    date_fetched = models.DateTimeField(auto_now_add=True)  # Date and time when the price was fetched

    def __str__(self):
        return f"{self.name} - ${self.price}"


class WishlistItem(models.Model):
    discord_user_id = models.BigIntegerField()  # The Discord user ID
    pokemon_name = models.CharField(max_length=100)  # Store the name of the Pokémon
    set_name = models.CharField(max_length=255)  # Store the set name
    card_id = models.CharField(max_length=255)  # Store the card ID

    def __str__(self):
        return f"Wishlist for user {self.discord_user_id}: {self.pokemon_name}"

