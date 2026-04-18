import os
import discord
import asyncio
from mcstatus import JavaServer

# 🔐 TOKEN (Railway variable d’environnement)
TOKEN = os.getenv("TOKEN")

# 🎮 Salon Discord
CHANNEL_ID = 1495136829228322928

# 🌍 Serveur Minecraft
server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

last = None
channel = None


async def monitor():
    global last, channel

    await client.wait_until_ready()

    # 🔥 récupère le salon une seule fois
    channel = await client.fetch_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            print("🔎 Check serveur Minecraft...")

            # 🧠 sécurité sur le status Minecraft
            try:
                status = server.status()
                current = status.players.online
                print("👥 Joueurs =", current)

            except Exception as e:
                print("❌ MC ERROR :", e)
                current = -1

            # 📢 envoi si changement
            if last is not None and current != last:
                await channel.send(f"🔔 Joueurs : {last} → {current}")

            last = current

        except Exception as e:
            print("❌ Monitor error :", e)

        await asyncio.sleep(30)


@client.event
async def on_ready():
    print(f"✅ Bot connecté : {client.user}")

    # lancement boucle
    client.loop.create_task(monitor())

    # message test
    try:
        ch = await client.fetch_channel(CHANNEL_ID)
        await ch.send("✅ bot online")
    except Exception as e:
        print("❌ on_ready error :", e)


client.run(TOKEN)
