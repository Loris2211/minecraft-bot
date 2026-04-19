async def monitor():
    global last_players, channel, last_daily, server_offline, monitoring

    await client.wait_until_ready()
    channel = await client.fetch_channel(CHANNEL_ID)

    while monitoring:
        try:
            status = server.status()

            # 🟢 retour en ligne
            if server_offline:
                await channel.send("@everyone 🟢 Serveur Minecraft de nouveau en ligne")
                server_offline = False

            current_players = {p.name for p in (status.players.sample or [])}
            current_count = len(current_players)

            joined = current_players - last_players
            left = last_players - current_players

            # 🟢 JOIN -> @everyone
            if joined:
                await channel.send(
                    f"@everyone 🟢 **Joueur(s) connecté(s)** : {', '.join(joined)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            # 🔴 LEAVE -> @everyone
            if left:
                await channel.send(
                    f"@everyone 🔴 **Joueur(s) déconnecté(s)** : {', '.join(left)}\n"
                    f"👥 Joueurs actuellement : {current_count}"
                )

            last_players = current_players

            # 🕛 check quotidien -> @here
            now = datetime.now()
            if now.hour == 12 and (last_daily is None or last_daily != now.date()):
                await channel.send("@here 🟢 Bot toujours actif (check quotidien)")
                last_daily = now.date()

        except Exception as e:
            print("Erreur serveur Minecraft :", e)

            if not server_offline:
                await channel.send("@everyone 🔴 Serveur Minecraft inaccessible ou hors ligne")
                server_offline = True

        await asyncio.sleep(10)
