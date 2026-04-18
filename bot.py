import os
import discord
import asyncio
from datetime import datetime
from mcstatus import JavaServer

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = 1495136829228322928

server = JavaServer.lookup("confdesenclumes.ddns.net:25565")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

last_players = set()
channel = None

last_daily = None
server_offline = False
monitoring = False  # 🔥 état ON/OFF


async def monitor():
    global last_players, channel, last_daily, server_offline, monitoring

    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    while monitoring:
        try:
            status = server.status()

            # 🟢 serveur revenu
            if server_offline:
                await channel.send("🟢 Serveur Minecraft de nouveau en ligne")
                server_offline = False

            if status.players.sample:
                current_players = {p.name for p in status.players.sample}
            else:
                current_players = set()

            current_count = len(current_players)

            joined = current_players - last_players
            left = last_players - current_players

            if joined:
                await channel.send(
                    f"🟢 **Joueur(s) connecté(s)** : {', '.join(joined)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            if left:
                await channel.send(
                    f"🔴 **Joueur(s) déconnecté(s)** : {', '.join(left)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            last_players = current_players

            # 🕛 message quotidien
            now = datetime.now()
            if now.hour == 12 and (last_daily is None or last_daily != now.date()):
                await channel.send("🟢 Bot toujours actif (check quotidien)")
                last_daily = now.date()

        except Exception as e:
            print("Erreur serveur Minecraft :", e)

            if not server_offline:
                await channel.send("🔴 Serveur Minecraft inaccessible ou hors ligne")
                server_offline = True

        await asyncio.sleep(10)


# 🔥 COMMANDE /start
@tree.command(name="start", description="Démarrer le monitoring Minecraft")
async def start(interaction: discord.Interaction):
    global monitoring

    if monitoring:
        await interaction.response.send_message("⚠️ Monitoring déjà actif", ephemeral=True)
        return

    monitoring = True
    client.loop.create_task(monitor())

    await interaction.response.send_message("🟢 Monitoring démarré")


# 🔥 COMMANDE /stop
@tree.command(name="stop", description="Arrêter le monitoring Minecraft")
async def stop(interaction: discord.Interaction):
    global monitoring

    if not monitoring:
        await interaction.response.send_message("⚠️ Monitoring déjà arrêté", ephemeral=True)
        return

    monitoring = False
    await interaction.response.send_message("🔴 Monitoring arrêté")


# 🧪 COMMANDE /test
@tree.command(name="test", description="Tester si le bot et le serveur fonctionnent")
async def test(interaction: discord.Interaction):
    try:
        status = server.status()

        if status.players.sample:
            players = [p.name for p in status.players.sample]
        else:
            players = []

        await interaction.response.send_message(
            f"🟢 Bot OK\n"
            f"🌐 Serveur OK\n"
            f"👥 Joueurs : {status.players.online}\n"
            f"📋 Liste : {', '.join(players) if players else 'aucun'}"
        )

    except Exception:
        await interaction.response.send_message(
            "🟢 Bot OK\n🔴 Serveur Minecraft inaccessible"
        )


@client.event
async def on_ready():
    print(f"Bot connecté : {client.user}")

    await tree.sync()

    try:
        ch = await client.fetch_channel(CHANNEL_ID)
        await ch.send("✅ bot online (commands ready)")
    except Exception as e:
        print("Erreur on_ready :", e)


client.run(TOKEN)
