from django.db import models

class PokemonPrice(models.Model):
    name = models.CharField(max_length=100)  # Name of the Pokémon
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price of the Pokémon
    source = models.CharField(max_length=100)  # Source where the price was fetched from (e.g., TCGPlayer)
    date_fetched = models.DateTimeField(auto_now_add=True)  # Date and time when the price was fetched

    def __str__(self):
        return f"{self.name} - ${self.price}"