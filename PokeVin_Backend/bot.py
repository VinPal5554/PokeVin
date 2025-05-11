from dotenv import load_dotenv
import os
import django
from asgiref.sync import sync_to_async
import aiohttp
import asyncio
import random
import urllib.parse
import requests

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
    WishlistItem.objects.create(
        discord_user_id=user_id,
        pokemon_name=pokemon_name,
        set_name=set_name,
        card_id=card_id
    )


async def fetch_cards_by_name(pokemon_name: str):
    # Encode the pokemon_name to safely use in URL
    pokemon_name_encoded = urllib.parse.quote(pokemon_name)

    url = f"https://api.pokemontcg.io/v2/cards?q=name:{pokemon_name_encoded}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                print(f"Fetched data for {pokemon_name}: {data}")  # Debugging line
                return data.get("data", [])
            else:
                print(f"Error fetching data for {pokemon_name}: {response.status}")  # Debugging line
                return []


# Fetch cards from the external API based on the card ID
async def fetch_cards_by_id(card_id):
    url = f"https://api.pokemontcg.io/v2/cards/{card_id}"  # The endpoint to fetch card details by ID

    try:
        # Make the request to the API
        response = requests.get(url)

        # Check if the response is valid
        if response.status_code == 200:
            card_data = response.json()  # Parse the JSON response
            return [card_data['data']]  # Return the card data (as a list for consistency with the other fetch function)
        else:
            print(f"Error fetching card by ID {card_id}: {response.status_code}")
            return []  # Return an empty list if no data is found or if the API request fails
    except Exception as e:
        print(f"Error fetching card by ID {card_id}: {e}")
        return []  # Return an empty list in case of any exception


# Modify the add_wishlist command to suggest cards
@bot.command(name='add_wishlist')
async def add_to_wishlist(ctx, *, card_info: str):
    user = ctx.author  # Get the current user

    # Split the input by commas
    parts = [part.strip() for part in card_info.split(',')]

    # If user only provided the Pokémon name, suggest a random card
    if len(parts) == 1:
        pokemon_name = parts[0]
        cards = await fetch_cards_by_name(pokemon_name)

        if not cards:
            await ctx.send(f"No cards found matching '{pokemon_name}'. Please try again with a valid name.")
            return

        suggested = random.choice(cards)
        example_text = (
            f"Invalid format! Please use:\n"
            f"`!add_wishlist <pokemon_name>, <set_name>, <card_id>`\n"
            f"For example, based on what you typed:\n"
            f"`!add_wishlist {suggested['name']}, {suggested['set']['name']}, {suggested['id']}`"
        )
        await ctx.send(example_text)
        return

    # Ensure there are exactly 3 parts (pokemon_name, set_name, card_id)
    if len(parts) != 3:
        await ctx.send("Invalid format! Please use the format: `!add_wishlist <pokemon_name>, <set_name>, <id>`.")
        return

    # Extract pokemon_name, set_name, and card_id from the input
    pokemon_name, set_name, card_id = parts

    # First, try to fetch the card by name
    cards = await fetch_cards_by_name(pokemon_name)

    if not cards:
        # If no cards are found by name, try fetching by card ID
        cards = await fetch_cards_by_id(card_id)

    # If no cards are found by name or ID, let the user know
    if not cards:
        await ctx.send(
            f"No cards found matching '{pokemon_name}' (Set: {set_name}, ID: {card_id}). Please try again with a valid name or ID.")
        return

    # Check if any of the fetched cards match the exact set and ID
    matched_card = None
    for card in cards:
        if card['set']['name'] == set_name and card['id'] == card_id:
            matched_card = card
            break

    if matched_card:
        # If a matching card is found, add it to the wishlist
        await add_wishlist_item(user.id, matched_card["name"], set_name, card_id)

        # Create an embed with the card image and information
        embed = discord.Embed(
            title=f"{matched_card['name']} Added to Wishlist",
            description=f"Set: {set_name}\nCard ID: {card_id}",
            color=discord.Color.blue()
        )
        embed.set_image(url=matched_card['images']['large'])  # Assuming the image URL is in 'large' field

        # Send the embed
        await ctx.send(embed=embed)

    else:
        # If no matching card is found with the exact set and ID
        await ctx.send(
            f"No card found matching '{pokemon_name}' (Set: {set_name}, ID: {card_id}). Please try again with the correct details.")



# Sync function to fetch the user's wishlist from the database
@sync_to_async
def get_user_wishlist(user_id):
    wishlist_items = WishlistItem.objects.filter(discord_user_id=user_id)
    return [
        {
            "pokemon_name": item.pokemon_name,
            "set_name": item.set_name,
            "card_id": item.card_id
        }
        for item in wishlist_items
    ]


user_wishlist_cache = {}  # {message_id: {user_id, pokemon_name, set_name, card_id}}

@bot.command(name='wishlist')
async def view_wishlist(ctx):
    user = ctx.author
    wishlist = await get_user_wishlist(user.id)

    if not wishlist:
        await ctx.send("Your wishlist is currently empty.")
        return

    await ctx.send(f"{user.mention}, here’s your wishlist! React with ❌ on any to remove:")

    for item in wishlist:
        content = f"{item['pokemon_name']} (Set: {item['set_name']}, ID: {item['card_id']})"
        msg = await ctx.send(content)
        await msg.add_reaction("❌")

        # Cache full card info per message
        user_wishlist_cache[msg.id] = {
            "user_id": user.id,
            "pokemon_name": item['pokemon_name'],
            "set_name": item['set_name'],
            "card_id": item['card_id']
        }

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.emoji) != "❌":
        return

    msg = reaction.message
    data = user_wishlist_cache.get(msg.id)

    if not data or user.id != data["user_id"]:
        return

    success = await remove_from_user_wishlist(
        user.id,
        data["pokemon_name"],
        data["set_name"],
        data["card_id"]
    )

    if success:
        await msg.edit(content=f"✅ Removed: {data['pokemon_name']} (Set: {data['set_name']}, ID: {data['card_id']})")
        del user_wishlist_cache[msg.id]
    else:
        await msg.channel.send("⚠️ Couldn’t remove that item. It may have already been deleted.", delete_after=5)


@sync_to_async
def remove_from_user_wishlist(user_id, pokemon_name, set_name, card_id):
    try:
        wishlist_item = WishlistItem.objects.get(
            discord_user_id=user_id,
            pokemon_name=pokemon_name,
            set_name=set_name,
            card_id=card_id
        )
        wishlist_item.delete()
        return True
    except WishlistItem.DoesNotExist:
        return False


@bot.command(name='remove_wishlist')
async def remove_wishlist(ctx, *, card_info: str):
    user = ctx.author

    parts = [part.strip() for part in card_info.split(',')]

    if len(parts) != 3:
        await ctx.send("Invalid format! Please use: `!remove_wishlist <pokemon_name>, <set_name>, <id>`.")
        return

    pokemon_name, set_name, card_id = parts

    success = await remove_from_user_wishlist(user.id, pokemon_name, set_name, card_id)

    if success:
        await ctx.send(f"{pokemon_name} (Set: {set_name}, ID: {card_id}) has been removed from your wishlist.")
    else:
        await ctx.send(f"{pokemon_name} (Set: {set_name}, ID: {card_id}) was not found in your wishlist.")

@sync_to_async
def clear_user_wishlist(user_id):
    WishlistItem.objects.filter(discord_user_id=user_id).delete()

@bot.command(name='clear_wishlist')
async def clear_wishlist(ctx):
    user = ctx.author

    await clear_user_wishlist(user.id)
    await ctx.send(f"🧹 Your wishlist has been cleared, {user.mention}.")

@bot.command(name='commands')
async def show_commands(ctx):
    command_list = """
📜 **Available Commands:**

🔹 `!add_wishlist <pokemon_name>, <set_name>, <card_id>`  
➤ Adds a specific Pokémon card to your wishlist.  
Example: `!add_wishlist Charizard, Base, base1-4`

🔹 `!remove_wishlist <pokemon_name>, <set_name>, <card_id>`  
➤ Removes a specific card from your wishlist.  
Example: `!remove_wishlist Charizard, Base, base1-4`

🔹 `!wishlist`  
➤ View your current wishlist.

🔹 `!commands`  
➤ Show this list of commands.
    """
    await ctx.send(command_list)

bot.run(TOKEN)

