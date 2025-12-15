import discord
import asyncio

# Initialize Client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# VPS Prices Configuration
vps_prices = {
    "64GB RAM": 8000,
    "32GB RAM": 4000,
    "16GB RAM": 2000,
    "8GB RAM": 1000,
    "4GB RAM": 500
}

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # --- VPS Hosting (!vps) ---
    if message.content == '!vps':
        embed = discord.Embed(
            title='🖥️ VPS Hosting Plans (LKR)',
            description='🎟️ Create a ticket to purchase!',
            color=0x3498db
        )
        embed.add_field(name='💠 64GB RAM', value=f"Rs. {vps_prices['64GB RAM']}", inline=False)
        embed.add_field(name='💠 32GB RAM', value=f"Rs. {vps_prices['32GB RAM']}", inline=False)
        embed.add_field(name='💠 16GB RAM', value=f"Rs. {vps_prices['16GB RAM']}", inline=False)
        embed.add_field(name='💠 8GB RAM', value=f"Rs. {vps_prices['8GB RAM']}", inline=False)
        embed.add_field(name='💠 4GB RAM', value=f"Rs. {vps_prices['4GB RAM']}", inline=False)
        embed.set_footer(text='Trapo Cloud Hosting™ | Visit trapo.cloud')
        await message.channel.send(embed=embed)

    # --- Game Server Hosting (!gameserver) ---
    elif message.content == '!gameserver':
        embed = discord.Embed(
            title='🎮 Game Server Hosting (LKR)',
            description='🎟️ Create a ticket to purchase!',
            color=0xe67e22
        )
        embed.add_field(name='💠 64GB RAM', value=f"Rs. {vps_prices['64GB RAM'] + 100}", inline=False)
        embed.add_field(name='💠 32GB RAM', value=f"Rs. {vps_prices['32GB RAM'] + 100}", inline=False)
        embed.add_field(name='💠 16GB RAM', value=f"Rs. {vps_prices['16GB RAM'] + 100}", inline=False)
        embed.add_field(name='💠 8GB RAM', value=f"Rs. {vps_prices['8GB RAM'] + 100}", inline=False)
        embed.add_field(name='💠 4GB RAM', value=f"Rs. {vps_prices['4GB RAM'] + 100}", inline=False)
        embed.set_footer(text='Trapo Cloud Hosting™ | Visit trapo.cloud')
        await message.channel.send(embed=embed)

    # --- Discord Bot Hosting (!dcbot) ---
    elif message.content == '!dcbot':
        embed = discord.Embed(
            title='🤖 Discord Bot Hosting Plans (LKR)',
            description='🎟️ Create a ticket to purchase!',
            color=0x9b59b6
        )
        embed.add_field(name='🟢 Starter', value='💲 Rs. 100\n🧠 RAM: 256MB', inline=False)
        embed.add_field(name='🔵 Coder', value='💲 Rs. 200\n🧠 RAM: 512MB', inline=False)
        embed.add_field(name='🟣 Developer', value='💲 Rs. 600\n🧠 RAM: 1GB', inline=False)
        embed.set_footer(text='CodeOn Hosting™ | Visit codeon.codes')
        await message.channel.send(embed=embed)

    # --- Web Hosting (!web) ---
    elif message.content == '!web':
        embed = discord.Embed(
            title='🌐 Web Hosting Plans (LKR)',
            description='🎟️ Create a ticket to purchase!',
            color=0x2ecc71
        )
        embed.add_field(name='Lite', value='💲 Rs. 99\n💾 SSD: 1GB', inline=False)
        embed.add_field(name='Plus', value='💲 Rs. 199\n💾 SSD: 5GB', inline=False)
        embed.add_field(name='Elite', value='💲 Rs. 399\n💾 SSD: 10GB', inline=False)
        embed.set_footer(text='Trapo Cloud Hosting™ | Visit trapo.cloud')
        await message.channel.send(embed=embed)

# PASTE YOUR TOKEN BELOW inside the quotes
client.run('MTQ0NDkwODI3Njg2ODMyMTM3MQ.Gjkusi.JMgpQa1kLxg2izTEVnxARi4_rAlaNiIRlDODu0')