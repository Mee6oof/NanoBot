##########################################
# NanoBot                                #
# Version 1.3-beta                       #
# Copyright (c) Nanomotion, 2017         #
# See the LICENSE.txt file for more info #
##########################################

import logging
logging.basicConfig(format='[%(asctime)s] (%(levelname)s) %(name)s: %(message)s', level=logging.INFO, datefmt='%m/%d/%Y %I:%M:%S %p')
import importlib
import discord
import asyncio
import traceback
import youtube_dl
import time
import uuid
import sys
import os
from discord.ext import commands
from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.tools import argparser
import colorama
import urllib.request
import ast
import timeit
import argparse
# import atexit

colorama.init(autoreset=True)
class color:
    BLUE = colorama.Fore.WHITE + colorama.Back.BLUE
    YELLOW = colorama.Fore.WHITE + colorama.Back.YELLOW
    RED = colorama.Fore.WHITE + colorama.Back.RED
    GREEN = colorama.Fore.WHITE + colorama.Back.GREEN

def queue_get_all(q):
    items = []
    maxItemsToRetreive = 10
    for numOfItemsRetrieved in range(0, maxItemsToRetreive):
        try:
            if numOfItemsRetrieved == maxItemsToRetreive:
                break
            items.append(q.get_nowait())
        except:
            break
    return items

cmds_this_session = []
admin_ids = ["233325229395410964", "236251438685093889", "294210459144290305", "233366211159785473"]
songs_played = []
start_time = "null"
version = "1.3-beta"
_uuid = uuid.uuid1()
queue = {}
errors = 0
exc_msg = ":warning: An error occurred:\n```py\n{}\n```\nNeed help? Join the NanoBot support server at https://discord.gg/eDRnXd6"
DEVELOPER_KEY = str(os.getenv('GAPI_TOKEN'))
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Change logging level to logging.DEBUG instead of logging.INFO", action="store_true")
    parser.add_argument("-ver", "--version", help="Prints the application version", action="store_true")
    parser.add_argument("-sptest", "--speedtest", help="Pings gateway.discord.gg", action="store_true")
    parser.add_argument("-m", "--maintenance", help="Runs the bot in maintenance mode", action="store_true")
    parser.add_argument("-gtoken", "--gapi-token", help="Runs the bot with a custom Google API token")
    parser.add_argument("-nc", "--no-color", help="Runs the bot without logging colors", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(version)
        sys.exit(0)
    elif args.speedtest:
        x = os.system('ping gateway.discord.gg')
        sys.exit(x)
    elif args.verbose:
        logging.basicConfig(format='[%(asctime)s] (%(levelname)s) %(name)s: %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.DEBUG("Logging level set to DEBUG")
    elif args.maintenance:
        x = os.system('start maintenance.py')
        sys.exit(x)
    if args.gapi_token:
        DEVELOPER_KEY = args.gapi_token
    if args.no_color:
        color.BLUE = ""
        color.YELLOW = ""
        color.RED = ""
        color.GREEN = ""

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* by **{0.uploader}** requested by {1.mention} '
        duration = self.player.duration
        if duration:
            fmt = fmt + '`[length: {0[0]}m {0[1]}s]`'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)

class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set() # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        global errors
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, ':notes: Now playing ' + str(self.current))
            try:
                self.current.player.start()
                await self.play_next_song.wait()
            except Exception as e:
                self.bot.say(exc_msg.format(e))
                print(color.RED + "ERROR: " + str(e))

class Music:

    # TODO: "!!repeat" command for audio

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx, *, channel : discord.Channel): # !!join
        global errors
        """Joins a voice channel."""
        tmp = await bot.send_message(ctx.message.channel, ":clock2: Connecting to voice channel `" + str(channel.name) + "`...")
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await bot.edit_message(tmp, ':no_entry_sign: Already in a voice channel!')
            errors += 1
        except TimeoutError:
            await bot.edit_message(tmp, ':no_entry_sign: Connection timed out.')
            errors += 1
        except discord.Forbidden:
            await bot.edit_message(tmp, ':no_entry_sign: I don\'t have permission to join that channel!')
            errors += 1
        except discord.InvalidArgument:
            await bot.edit_message(tmp, ':no_entry_sign: Not a valid voice channel!')
            errors += 1
        except Exception as e:
            print(color.RED + "ERROR: " + str(e))
            await bot.edit_message(tmp, ':no_entry_sign: Couldn\'t connect to voice channel.')
            errors += 1
            try:
                await bot.send_message(discord.User(id="236251438685093889"), ":warning: An error occurred in `join`: ```" + traceback.format_exc()[:1800] + "```")
            except Exception as e:
                logging.warn("Failed to create direct message: " + str(e))
                errors += 1
        else:
            await bot.edit_message(tmp, ':notes: Ready to play audio in `' + channel.name + '`')

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx): # !!summon
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        tmp = await bot.send_message(ctx.message.channel, ":clock2: Please wait...")
        if summoned_channel is None:
            await bot.edit_message(tmp, ':no_entry_sign: You are not in a voice channel!')
            return False
        else:
            tmp = await bot.edit_message(tmp, ":clock2: Connecting to voice channel `" + str(summoned_channel.name) + "`...")

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            await bot.edit_message(tmp, ":notes: Ready to play music in `" + str(summoned_channel.name) + "`!")
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, song : str): # !!play
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        global songs_played
        global errors
        songs_played.append(song)
        tmp = await bot.send_message(ctx.message.channel, ":clock2: Please wait...")
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                pass

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
        except OSError as e:
            print(color.RED + "ERROR: " + e)
            await bot.edit_message(tmp, ":gun: A fatal error occurred: `{0}: {1}` Please report this at https://discord.gg/eDRnXd6.".format(str(type(e).__name__), str(e)[:1900]))
        except Exception as e:
            e = str(e)
            print(color.RED + "ERROR: " + e)
            errors += 1
            fmt = ':warning: An error occurred: ```py\n' + e[:1900] + '\n```'
            if e.startswith("ERROR: Unsupported URL") or e.startswith("hostname"):
                fmt = ':warning: That URL is not supported. Visit https://goo.gl/5yKXrN for a list of supported sites.'
            elif e.startswith("ERROR: Unable to download webpage") or e.startswith("ERROR: Incomplete"):
                fmt = ':warning: The requested video could not be downloaded.'
            elif e.startswith("[WinError 6] The handle is invalid"):
                fmt = ':warning: Access denied to video!'
            await bot.edit_message(tmp, fmt)
        else:
            player.volume = 0.6
            try:
                entry = VoiceEntry(ctx.message, player)
            except Exception as e:
                print(color.RED + "ERROR: " + str(e))
                errors += 1
                await bot.edit_message(tmp, ':gun: A fatal error occurred: `{}`'.format(str(e)[:1900]))
            else:
                await bot.edit_message(tmp, ':notes: Added ' + str(entry) + ' to the queue.')
                await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value : int): # !!volume
        """Sets the volume of the currently playing song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say(':speaker: :notes: Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx): # !!pause
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()
            await self.bot.say(":pause_button: Paused the player.")

    @commands.command(pass_context=True, no_pm=True)
    async def queue(self, ctx): # !!queue
        """Shows all songs waiting to be played."""
        state = self.get_voice_state(ctx.message.server)
        songs = queue_get_all(state.songs)
        msg = ":notes: Songs in queue:\n"
        num = 1
        if len(songs) == 0:
            await self.bot.say(":speaker::no_entry_sign: No songs in queue.")
        else:
            for song in songs:
                msg += str(num) + ". " + str(song) + "\n"
                num += 1
            await self.bot.say(msg[:2000])

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx): # !!resume
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()
            await self.bot.say(":notes: Resumed the player.")

    @commands.command(pass_context=True, no_pm=True, aliases=['leave', 'disconnect'])
    async def stop(self, ctx): # !!stop
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        await self.bot.say(":octagonal_sign: Stopped the player. Leaving the voice channel...")
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx): # !!skip
        """Vote to skip a song. The song requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say(':no_entry_sign: Not playing any music right now.')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say(':fast_forward: Skipping song...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= 3:
                await self.bot.say(':fast_forward: Skip vote passed, skipping song...')
                state.skip()
            else:
                await self.bot.say(':fast_forward: Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say(':warning: You have already voted to skip this song!')

    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx): # !!playing
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Not playing anything. Type `!!play <query>` to play a song.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current, skip_count))

class Moderation:

    # TODO: Add moderator commands

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def prune(self, ctx, limit : int): # !!prune
        """Bulk-deletes the specified amount of messages."""
        global errors
        if ctx.message.author == ctx.message.server.owner:
            if not limit > 1:
                await self.bot.say(":no_entry_sign: You can only bulk-delete more than 1 message!")
            elif not limit < 101:
                await self.bot.say(":no_entry_sign: You can only bulk-delete less than 101 messages!")
            else:
                counter = 0
                msgs = []
                await self.bot.say('Deleting messages... :clock2:')
                try:
                    async for log in self.bot.logs_from(ctx.message.channel, limit=limit):
                        msgs.append(log)
                        counter += 1
                    await self.bot.delete_messages(msgs)
                except Exception as e:
                    errors += 1
                    print(color.RED + "ERROR: " + str(e))
                    await self.bot.say(exc_msg.format(str(e)))
                    try:
                        await bot.send_message(discord.User(id="236251438685093889"), ":warning: An error occurred in `" + str(event) + "`: ```" + traceback.format_exc()[:1800] + "```")
                    except Exception as e:
                        errors += 1
                        logging.warn("Failed to create direct message: " + str(e))
                else:
                    await self.bot.say(':zap: Deleted {} messages.'.format(counter))
        else:
            await self.bot.say(":no_entry_sign: You don't have permission to do that!")

    @commands.command(pass_context=True)
    async def prune2(self, ctx, *, messages : int): # !!prune2
        """Individually deletes the specified amount of messages."""
        global errors
        if ctx.message.author == ctx.message.server.owner:
            counter = 0
            await self.bot.say('Deleting messages... :clock2:')
            try:
                async for log in self.bot.logs_from(message.channel, limit=messages):
                    await self.bot.delete_message(log)
                    counter += 1
            except Exception as e:
                errors += 1
                print(color.RED + "ERROR: " + str(e))
                await bot.send_message(message.channel, exc_msg.format(e))
            else:
                await bot.send_message(message.channel, 'Deleted {} messages.'.format(counter))
        else:
            await bot.send_message(message.channel, ':warning: No permission! You must be the server owner.')

class Admin:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, hidden=True)
    async def eval(self, ctx, *, _eval : str): # !!eval
        if not str(ctx.message.author.id) in admin_ids:
            await self.bot.say(":warning: You need to be **NanoBot Owner** to do that.")
        else:
            res = "null"
            err = 0
            embed = discord.Embed()
            try:
                if "exit" in _eval.lower():
                    err = 1
                    res = "PermissionError: Request denied."
                else:
                    res = eval(_eval)
                    logging.info("Evaluated " + str(_eval))
            except Exception as e:
                res = str(e)
                err = 1
            if err == 1:
                embed = discord.Embed(color=0xFF0000)
            else:
                embed = discord.Embed(color=0x00FF00)
            if len(str(res)) > 899:
                res = str(res)[:880] + "\n\n(result trimmed)"
            embed.title = "NanoBot Eval"
            embed.set_footer(text="Code Evaluation")
            '''embed.set_image(url=ctx.message.server.me.avatar_url)'''
            embed.add_field(name=":inbox_tray: Input", value="```py\n" + str(_eval) + "```")
            if err == 1:
                embed.add_field(name=":outbox_tray: Error", value="```py\n" + str(res)[:900] + "```")
            else:
                embed.add_field(name=":outbox_tray: Output", value="```py\n" + str(res)[:900] + "```")
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True, hidden=True)
    async def exec(self, ctx, *, _eval : str): # !!exec
        if not str(ctx.message.author.id) in admin_ids:
            await self.bot.say(":warning: You need to be **NanoBot Owner** to do that.")
        else:
            res = "null"
            err = 0
            embed = discord.Embed()
            try:
                if "exit" in _eval.lower():
                    err = 1
                    res = "PermissionError: Request denied."
                else:
                    res = exec(_eval)
                    logging.info("Executed " + str(_eval))
            except Exception as e:
                res = str(e)
                err = 1
            if err == 1:
                embed = discord.Embed(color=0xFF0000)
            else:
                embed = discord.Embed(color=0x00FF00)
            if len(str(res)) > 899:
                res = str(res)[:880] + "\n\n(result trimmed)"
            embed.title = "NanoBot Exec"
            embed.set_footer(text="Code Execution")
            '''embed.set_image(url=ctx.message.server.me.avatar_url)'''
            embed.add_field(name=":inbox_tray: Input", value="```py\n" + str(_eval) + "```")
            if err == 1:
                embed.add_field(name=":outbox_tray: Error", value="```py\n" + str(res)[:900] + "```")
            else:
                embed.add_field(name=":outbox_tray: Output", value="```py\n" + str(res)[:900] + "```")
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True, hidden=True)
    async def setplaying(self, ctx, *, game : str): # !!setplaying
        if not str(ctx.message.author.id) in admin_ids:
            await self.bot.say(":warning: You need to be **NanoBot Owner** to do that.")
        else:
            try:
                await self.bot.change_presence(game=discord.Game(name=game))
                logging.info("Set game to " + str(game))
            except Exception as e:
                await self.bot.say(":warning: Failed to set playing: `" + str(e)[:1900] + "`")

    @commands.command(pass_context=True, hidden=True)
    async def reload(self, ctx, *, module : str): # !!reload
        global errors
        if not str(ctx.message.author.id) in admin_ids:
            await self.bot.say(":warning: You need to be **NanoBot Owner** to do that.")
        else:
            try:
                logging.info('Reloading ' + module + '...')
                exec('importlib.reload(' + module + ')')
                await self.bot.say('Reloaded module `' + module + '`')
                logging.info('Successfully reloaded ' + module)
            except Exception as e:
                errors += 1
                await self.bot.say(':warning: Failed to reload module: `' + str(e) + '`')
                logging.warn('Failed to reload ' + module)

    @commands.command(pass_context=True, hidden=True)
    async def setstatus(self, ctx, *, status : str): # !!setstatus
        global errors
        if not str(ctx.message.author.id) in admin_ids:
            await self.bot.say(":warning: You need to be **NanoBot Owner** to do that.")
        else:
            try:
                if status == "online":
                    await self.bot.change_presence(status=discord.Status.online)
                    await self.bot.say("Changed status to `online` <:online:313956277808005120>")
                elif status == "idle" or status == "away":
                    await self.bot.change_presence(status=discord.Status.idle)
                    await self.bot.say("Changed status to `idle` <:away:313956277220802560>")
                elif status == "dnd":
                    await self.bot.change_presence(status=discord.Status.dnd)
                    await self.bot.say("Changed status to `dnd` <:dnd:313956276893646850>")
                elif status == "offline" or status == "invisible":
                    await self.bot.change_presence(status=discord.Status.offline)
                    await self.bot.say("Changed status to `offline` <:offline:313956277237710868>")
                elif status == "streaming":
                    await self.bot.change_presence(game=discord.Game(name="Type !!help", type=1))
                    await self.bot.say("Changed status to `streaming` <:streaming:313956277132853248>")
                else:
                    await self.bot.say(":warning: Invalid status `" + status + "`. Possible values:\n```py\n['online', 'idle', 'away', 'dnd', 'offline', 'invisible', 'streaming']```")
                logging.info("Set status to " + str(status))
            except Exception as e:
                errors += 1
                await self.bot.say(":warning: Failed to set status: `" + str(e)[:1900] + "`")

    @commands.command(pass_context=True, hidden=True)
    async def sendmsg(self, ctx): # !!sendmsg
        if str(ctx.message.author.id) in admin_ids:
            f = open("msg.txt", "r")
            await self.bot.say(f.read())
            f.close()

    @commands.command(pass_context=True, hidden=True)
    async def restart(self, ctx): # !!restart
        if str(ctx.message.author.id) in admin_ids:
            await self.bot.say(":wave: Restarting...")
            await self.bot.change_presence(status=discord.Status.idle)
            sys.exit(0)
            exit()

class YouTube:

    def __init__(self, bot):
        self.bot = bot

    def search(q, max_results=10):
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

        # Call the search.list method to retrieve results matching the specified
        # query term.
        search_response = youtube.search().list(
            q=q,
            part="id,snippet",
            maxResults=max_results
        ).execute()

        videos = []

        # Add each result to the appropriate list, and then display the lists of
        # matching videos, channels, and playlists.
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                videos.append({"id":search_result["id"]["videoId"], "title":search_result["snippet"]["title"], "description":search_result['snippet']['description'], "uploader":search_result['snippet']['channelTitle'], "thumbnail":search_result['snippet']['thumbnails']['default']['url']})

        return videos

    @commands.command(pass_context=True)
    async def yt(self, ctx, *, query : str): # !!yt
        """Searches YouTube for videos with the specified query."""
        await self.bot.send_typing(ctx.message.channel)
        q = ""
        try:
            q = YouTube.search(query)
        except HttpError as e:
            await self.bot.say(":warning: Error `{status}` occurred: ```json\n{content}\n```".format(status=e.resp.status, content=e.content))
        else:
            q = q[0]
            embed = discord.Embed(color=discord.Color.red())
            embed.title = "YouTube Search Result"
            embed.add_field(name="Title", value=q['title'][:1020])
            embed.add_field(name="Uploader", value=q['uploader'][:1020])
            embed.add_field(name="URL", value="https://youtube.com/watch?v=" + q['id'])
            embed.set_thumbnail(url=q['thumbnail'])
            embed.add_field(name="Description", value=q['description'][:1000])
            await self.bot.send_message(ctx.message.channel, embed=embed)
            #await self.bot.say("https://youtube.com/watch?v=" + q['id'])

class General:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def invite(self, ctx): # !!invite
        """Shows a link to invite NanoBot to your server."""
        await self.bot.say(ctx.message.author.mention + ", you can invite me to your server with this link: http://bot.nanomotion.xyz/invite :wink:")

    @commands.command(pass_context=True, no_pm=True)
    async def user(self, ctx, *, user : discord.User): # !!user
        """Gets the specified user's info."""
        await self.bot.send_typing(ctx.message.channel)
        stp = user.status
        if str(user.status) == "online":
            stp = "<:online:313956277808005120>"
        elif str(user.status) == "offline":
            stp = "<:offline:313956277237710868>"
        elif str(user.status) == "idle":
            stp = "<:away:313956277220802560>"
        elif str(user.status) == "dnd" or str(user.status) == "do_not_disturb":
            stp = "<:dnd:313956276893646850>"
        else:
            stp = ":question:"
        stp2 = ""
        for role in user.roles:
            if role.name == user.roles[len(user.roles) - 1].name:
               stp2 = stp2 + role.mention
            else:
                stp2 = stp2 + role.mention + ", "
        embed = discord.Embed(color=user.color)
        embed.title=user.name + "'s Info"
        embed.set_footer(text=user.name + "#" + user.discriminator)
        embed.add_field(name="Account Created At", value=user.created_at)
        embed.add_field(name="Roles", value=stp2)
        embed.add_field(name="Status", value=str(user.status) + " " + stp)
        embed.add_field(name="Nickname", value=user.display_name)
        try:
            embed.add_field(name="Playing", value=user.game.name)
        except:
            embed.add_field(name="Playing", value="(Nothing)")
        embed.set_thumbnail(url=user.avatar_url)
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True)
    async def dog(self, ctx): # !!dog
        """Gets a random dog from http://random.dog"""
        await self.bot.send_typing(ctx.message.channel)
        dog = urllib.request.urlopen('https://random.dog/woof')
        dog = str(dog.read())
        dog = dog[2:]
        dog = dog[:len(dog) - 1]
        print("https://random.dog/" + str(dog))
        await self.bot.say("Here is your random dog: https://random.dog/" + str(dog))

    @commands.command(pass_context=True)
    async def cat(self, ctx): # !!cat
        """Gets a random cat from http://random.cat"""
        await self.bot.send_typing(ctx.message.channel)
        cat = urllib.request.urlopen('https://random.cat/meow')
        cat = str(cat.read())
        cat = cat[11:]
        cat = cat[:len(cat) - 3]
        cat = cat.replace("\\", "")
        print(cat)
        await self.bot.say("Here is your random cat: " + str(cat))

    @commands.command(pass_context=True, aliases=['github', 'githubstatus', 'ghstats'])
    async def ghstatus(self, ctx): # !!ghstatus
        """Shows GitHub status (From https://status.github.com)"""
        await self.bot.send_typing(ctx.message.channel)
        st = urllib.request.urlopen('https://status.github.com/api/last-message.json')
        st = str(st.read())
        st = st[2:]
        st = st[:len(st) - 1]
        st = ast.literal_eval(st)
        status = st['status']
        desc = st['body']
        timestamp = st['created_on']
        color = discord.Color.default()
        if status == "good":
            color = discord.Color.green()
        elif status == "minor":
            color = discord.Color.gold()
        elif status == "major":
            color = discord.Color.red()
        embed = discord.Embed(color=color)
        embed.title="GitHub Status"
        embed.set_footer(text="Last updated " + timestamp)
        embed.add_field(name="Status", value=status)
        embed.add_field(name="Description", value=desc)
        embed.set_thumbnail(url="https://maxcdn.icons8.com/iOS7/PNG/75/Logos/github_copyrighted_filled-75.png")
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True, no_pm=True, aliases=['botinfo'])
    async def info(self, ctx): # !!info
        """Shows bot info."""
        global start_time
        global version
        global errors
        elapsed_time = time.gmtime(time.time() - start_time)
        stp = str(elapsed_time[7] - 1) + " days, " + str(elapsed_time[3]) + " hours, " + str(elapsed_time[4]) + " minutes"
        await self.bot.send_typing(ctx.message.channel)
        embed = discord.Embed(color=ctx.message.server.me.color)
        embed.title = "NanoBot Status"
        embed.set_footer(text="NanoBot#2520")
        embed.set_thumbnail(url=ctx.message.server.me.avatar_url)
        embed.add_field(name="Owner", value="Der ✓#4587")
        embed.add_field(name="Version", value=version)
        embed.add_field(name="Session UUID", value="```\n" + str(_uuid) + "\n```")
        embed.add_field(name="Commands Processed", value=str(len(cmds_this_session)))
        embed.add_field(name="Songs Played", value=str(len(songs_played)))
        embed.add_field(name="Uptime", value=stp)
        embed.add_field(name="Errors", value=str(errors) + " (" + str(round(errors/len(cmds_this_session) * 100)) + "%)")
        embed.add_field(name="Servers", value=str(len(self.bot.servers)))
        embed.add_field(name="Users", value=str(sum(1 for _ in self.bot.get_all_members())))
        embed.add_field(name="Voice Sessions", value=str(len(self.bot.voice_clients)))
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True, no_pm=True, aliases=['server', 'guildinfo', 'serverinfo'])
    async def guild(self, ctx): # !!guild
        """Shows guild info."""
        await self.bot.send_typing(ctx.message.channel)
        server = ctx.message.server
        owner = server.owner.name + "#" + str(server.owner.discriminator)
        stp2 = ""
        for role in server.roles:
            if role.name == server.roles[len(server.roles) - 1].name:
               stp2 = stp2 + role.mention
            else:
                stp2 = stp2 + role.mention + ", "
        embed = discord.Embed(color=discord.Color.default())
        embed.title = "Guild Info"
        embed.set_footer(text="NanoBot#2520")
        embed.set_thumbnail(url=server.icon_url)
        embed.add_field(name="Name", value=server.name)
        embed.add_field(name="ID", value=str(server.id))
        embed.add_field(name="Roles", value=stp2)
        embed.add_field(name="Owner", value=owner)
        embed.add_field(name="Members", value=server.member_count)
        embed.add_field(name="Channels", value=len(server.channels))
        embed.add_field(name="Region", value=server.region)
        embed.add_field(name="Custom Emoji", value=len(server.emojis))
        embed.add_field(name="Created At", value=server.created_at)
        await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command(pass_context=True)
    async def ping(self, ctx, *, times=1): # !!ping
        """Pong!"""
        global errors
        try:
            times = int(times)
        except:
            await self.bot.say(":warning: Times is an optional argument that must be an `int`.")
        else:
            await self.bot.send_typing(ctx.message.channel)
            start = time.time()
            res = os.system("ping gateway.discord.gg -n " + str(times))
            _time = round(((time.time() - start) * 1000) / (times * 2))
            embed = discord.Embed()
            if res == 0 or res is None:
                if _time <= 125:
                    embed = discord.Embed(color=discord.Color.green())
                elif _time <= 250:
                    embed = discord.Embed(color=discord.Color.gold())
                else:
                    embed = discord.Embed(color=discord.Color.red())
                    errors += 1
                embed.title = "NanoBot Status"
                embed.add_field(name=":outbox_tray: Output", value="Connection took " + str(_time) + "ms")
                embed.set_footer(text="gateway.discord.gg")
            else:
                embed = discord.Embed(color=discord.Color.red())
                embed.title = "NanoBot Status"
                embed.add_field(name=":outbox_tray: Error", value="Ping returned error code `" + str(res) + "` in " + str(_time) + "ms")
                errors += 1
                embed.set_footer(text="gateway.discord.gg")
            await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command()
    async def hello(self): # !!hello
        """Hello, world!"""
        await bot.send_message(message.channel, ':wave: Hi, I\'m NanoBot! I can make your Discord server better with all of my features! Type `!!help` for more info, or go to http://bot.nanomotion.xyz')

bot = commands.Bot(command_prefix=commands.when_mentioned_or('!!'), description='A music, fun, and moderation bot for Discord.')
bot.add_cog(Music(bot))
bot.add_cog(Moderation(bot))
bot.add_cog(Admin(bot))
bot.add_cog(General(bot))
bot.add_cog(YouTube(bot))

@bot.event
async def on_server_join(server): # When the bot joins a server
    logging.warn(color.GREEN + "Joined server " + str(server.id)+ " (" + str(server.name) + ")")
    await bot.send_message(server.default_channel, ':wave: Hi, I\'m NanoBot! Thanks for adding me to your server. Type `!!help` for help and tips on what I can do.')

@bot.event
async def on_server_leave(server): # When the bot leaves a server
    logging.warn(color.RED + "Left server " + str(server.id) + " (" + str(server.name) + ")")

@bot.event
async def on_member_join(member): # When a member joins a server
    if str(member.server.id) == "294215057129340938":
        await bot.send_message(member.server.get_channel("314136139755945984"), ":wave: Welcome " + str(member.mention) + " to the server!")

@bot.event
async def on_command_error(error, ctx): # When a command error occurrs
    global exc_msg
    global errors
    if isinstance(error, discord.ext.commands.errors.CommandNotFound):
        pass
    if isinstance(error, discord.ext.commands.errors.CheckFailure):
        await bot.send_message(ctx.message.channel, ":no_entry_sign: {}, you don't have permission to use this command.".format(ctx.message.author.mention))
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        if ctx.command.name == "play":
            await bot.send_message(ctx.message.channel, ":warning: {}, `query/url` is a required argument that is missing.".format(ctx.message.author.mention))
        elif ctx.command.name == "join":
            await bot.send_message(ctx.message.channel, ":warning: {}, `channel` is a required argument that is missing.".format(ctx.message.author.mention))
        elif ctx.command.name == "yt":
            await bot.send_message(ctx.message.channel, ":warning: {}, `query` is a required argument that is missing.".format(ctx.message.author.mention))
        elif ctx.command.name == "volume":
            await bot.send_message(ctx.message.channel, ":warning: {}, `volume` is a required argument that is missing.".format(ctx.message.author.mention))
        elif ctx.command.name == "prune" or ctx.command.name == "prune2":
            await bot.send_message(ctx.message.channel, ":warning: {}, `amount` is a required argument that is missing.".format(ctx.message.author.mention))
        else:
            await bot.send_message(ctx.message.channel, ":warning: {}, you are missing required arguments.".format(ctx.message.author.mention))
    elif isinstance(error, discord.ext.commands.errors.BadArgument):
        await bot.send_message(ctx.message.channel, ":warning: {}, you passed an invalid argument.".format(ctx.message.author.mention))
    elif isinstance(error, discord.Forbidden):
        pass
    elif isinstance(error, discord.ext.commands.errors.NoPrivateMessage):
        await bot.send_message(ctx.message.channel, ":no_entry_sign: This command can't be used in private messages.")
    else:
        if ctx.command:
            errors += 1
            logging.warn(color.YELLOW + "Command error: " + str(error))
            await bot.send_message(ctx.message.channel, ":warning: An error occured while processing this command: `{}`".format(error))

@bot.event
async def on_message(message): # When a message is sent
    if message.content.startswith('!!') and not message.content.startswith('!!!'):
        global cmds_this_session
        logging.info(message.author.name + "#" + str(message.author.discriminator) + " (ID: " + str(message.author.id) + ") entered command " + message.content)
        cmds_this_session.append(message.content)
        if message.content == "!!help":
            f = open('help.txt', 'r')
            await bot.send_message(message.channel, f.read())
            f.close()
        else:
            await bot.process_commands(message)

@bot.event
async def on_ready():
    global start_time
    print(color.BLUE + 'Logged in as')
    print(color.BLUE + bot.user.name)
    print(color.BLUE + bot.user.id)
    print('------')
    await bot.change_presence(game=discord.Game(name='Type !!help'))
    start_time = time.time()
    os.makedirs('data', exist_ok=True)
    # atexit.register(os.system, "start bot.py")

bot.run(os.getenv('NANOBOT_TOKEN'))
