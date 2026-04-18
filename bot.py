import os
import discord
import asyncio
from mcstatus import JavaServer

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1495136829228322928

server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last_players = set()
channel = None


async def monitor():
    global last_players, channel

    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            status = server.status()

            # 🔥 récupération des joueurs actuels
            if status.players.sample:
                current_players = {p.name for p in status.players.sample}
            else:
                current_players = set()

            print("Joueurs actuels =", current_players)

            # ➕ joueurs qui rejoignent
            joined = current_players - last_players
            # ➖ joueurs qui partent
            left = last_players - current_players

            # 🔔 message join
            if joined:
                await channel.send(
                    "🟢 **Joueur(s) connecté(s)** : " + ", ".join(joined)
                )

            # 🔴 message leave
            if left:
                await channel.send(
                    "🔴 **Joueur(s) déconnecté(s)** : " + ", ".join(left)
                )

            last_players = current_players

        except Exception as e:
            print("Erreur :", e)

        await asyncio.sleep(30)


@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")
    client.loop.create_task(monitor())

    try:
        ch = await client.fetch_channel(CHANNEL_ID)
        await ch.send("✅ bot online")
    except Exception as e:
        print("Erreur on_ready :", e)


client.run(TOKEN)
