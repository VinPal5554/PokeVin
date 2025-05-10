from dotenv import load_dotenv
import os
import django
from asgiref.sync import sync_to_async
import aiohttp
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set the default settings module for the 'django' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PokeVin_Backend.settings')

# Setup Django
django.setup()

import discord
from discord.ext import commands
from django.core.exceptions import ObjectDoesNotExist
from prices.models import PokemonPrice, WishlistItem

intents = discord.Intents.default()
intents.message_content = True  # Required to read message text
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')

async def get_matching_cards(card_name):
    url = f"https://api.pokemontcg.io/v2/cards?q=name:{card_name}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            cards = data.get("data", [])
            return cards

# Create a sync function to check if the item exists
@sync_to_async
def check_if_item_exists(user_id, pokemon_name, set_name, card_id):
    # Check if the item already exists in the user's wishlist
    return WishlistItem.objects.filter(
        discord_user_id=user_id,
        pokemon_name=pokemon_name,
        set_name=set_name,
        card_id=card_id
    ).exists()

# Create a sync function to add a new wishlist item
@sync_to_async
def add_wishlist_item(user_id, pokemon_name, set_name, card_id):
    # Create and save a new WishlistItem with pokemon_name, set_name, and card_id
    WishlistItem.objects.create(
        discord_user_id=user_id,
        pokemon_name=pokemon_name,
        set_name=set_name,
        card_id=card_id
    )


async def fetch_cards_by_name(pokemon_name: str):
    url = f"https://api.pokemontcg.io/v2/cards?q=name:{pokemon_name}"

    # Perform an asynchronous GET request to the API
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # If the request was successful (status code 200)
            if response.status == 200:
                data = await response.json()

                # Check if there are any cards in the response data
                if "data" in data:
                    return data["data"]
                else:
                    return []  # No cards found

            else:
                # Handle API request errors
                print(f"Error fetching cards for {pokemon_name}: {response.status}")
                return []


# Modify the add_wishlist command to suggest cards
@bot.command(name='add_wishlist')
async def add_to_wishlist(ctx, *, card_info: str):
    user = ctx.author  # Get the current user

    # Split the input by commas
    parts = [part.strip() for part in card_info.split(',')]

    # Ensure there are exactly 3 parts (pokemon_name, set_name, card_id)
    if len(parts) != 3:
        await ctx.send("Invalid format! Please use the format: `!add_wishlist <pokemon_name>, <set_name>, <id>`.")
        return

    # Extract pokemon_name, set_name, and card_id from the input
    pokemon_name, set_name, card_id = parts

    # Fetch cards matching the pokemon_name
    cards = await fetch_cards_by_name(pokemon_name)

    # If no cards are found, let the user know
    if not cards:
        await ctx.send(f"No cards found matching '{pokemon_name}'. Please try again with a valid name.")
        return

    # Check if any of the fetched cards match the exact set and ID
    matched_card = None
    for card in cards:
        if card['set']['name'] == set_name and card['id'] == card_id:
            matched_card = card
            break

    if matched_card:
        # If a matching card is found, check if it's already in the user's wishlist
        if await check_if_item_exists(user.id, pokemon_name, set_name, card_id):
            await ctx.send(f"{pokemon_name} (Set: {set_name}, ID: {card_id}) is already in your wishlist!")
        else:
            # Add the matched card to the wishlist with full details
            await add_wishlist_item(user.id, pokemon_name, set_name, card_id)
            await ctx.send(f"{matched_card['name']} (Set: {set_name}, ID: {card_id}) has been added to your wishlist!")
    else:
        # If no matching card is found with the exact set and ID
        await ctx.send(f"No card found matching '{pokemon_name}' (Set: {set_name}, ID: {card_id}). Please try again with the correct details.")



# Sync function to fetch the user's wishlist from the database
@sync_to_async
def get_user_wishlist(user_id):
    wishlist_items = WishlistItem.objects.filter(discord_user_id=user_id)
    return [item.pokemon_name for item in wishlist_items]

@bot.command(name='wishlist')
async def view_wishlist(ctx):
    user = ctx.author  # Get the current user

    # Get the user's wishlist asynchronously
    wishlist = await get_user_wishlist(user.id)

    if not wishlist:
        await ctx.send("Your wishlist is currently empty.")
    else:
        # Format the wishlist into a string for display
        wishlist_str = "\n".join(wishlist)
        await ctx.send(f"Your wishlist:\n{wishlist_str}")

@sync_to_async
def remove_from_user_wishlist(user_id, pokemon_name):
    try:
        # Try to fetch and delete the wishlist item
        wishlist_item = WishlistItem.objects.get(discord_user_id=user_id, pokemon_name=pokemon_name)
        wishlist_item.delete()  # Remove the item from the wishlist
        return True
    except WishlistItem.DoesNotExist:
        return False  # Pokémon not found in the wishlist


@bot.command(name='remove_wishlist')
async def remove_wishlist(ctx, pokemon_name: str):
    user = ctx.author  # Get the current user

    # Try to remove the Pokémon from the user's wishlist asynchronously
    success = await remove_from_user_wishlist(user.id, pokemon_name)

    if success:
        await ctx.send(f"{pokemon_name} has been removed from your wishlist.")
    else:
        await ctx.send(f"{pokemon_name} was not found in your wishlist.")


@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

bot.run(TOKEN)

