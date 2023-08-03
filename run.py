import asyncio
from time import time, sleep
from random import choice, randrange
from telethon import TelegramClient
from telethon.tl.types import InputPeerChannel, InputMessagesFilterPinned, InputUser
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest
from telethon.errors.rpcerrorlist import SlowModeWaitError, FloodWaitError, \
     FilePart0MissingError, ForbiddenError, ChannelPrivateError, UserBannedInChannelError, \
     ChatWriteForbiddenError, UserPrivacyRestrictedError, UserNotMutualContactError, UserKickedError, UserIdInvalidError
from telethon.errors.rpcbaseerrors import BadRequestError
from telethon.sync import TelegramClient, events
from telethon.events import NewMessage

from telegram import Bot
from telegram.constants import PARSEMODE_MARKDOWN_V2
from telegram.utils.helpers import escape_markdown
from pymongo import MongoClient, server_api

INVITE_USER_DESTINATION_GROUP = '@AM_FORUM'
NOTIFY_USER_ID = 5372828517
NOTIFY_BOT_TOKEN = '5975443199:AAGtqc-QftD22JshcJkG7sF6iC5mHcUseHY'

market_bot = Bot(NOTIFY_BOT_TOKEN)

MONGO_URI = 'mongodb+srv://49Y47:TYO6G03MikDnII2a@alcatraz.4y0rkar.mongodb.net/?retryWrites=true&w=majority'
mongo_client = MongoClient(MONGO_URI, server_api=server_api.ServerApi('1'))

ScrapUsersCollection = mongo_client['ALCATRAZ']['SCRAPS']

API_ID, API_HASH = 3488972, '7e420060c082dc2b6b4facfbaf29137f'
api_id_and_hash = {    
    3488972: '7e420060c082dc2b6b4facfbaf29137f',
    20562103: '383748abd39cddfccaa9e39fc20d54f0',
    21900015: 'a1bf6ef405c3017a80f7546e3a697ded',
}

PHANTOM_BASE = -1001984235241 # Group From Which Advertisements Have Been Selected
PHANTOM_BASE_LINK = 'https://t.me/PhantomAds_2hOoisIE'

MAX_REGULAR_GROUPS = 30
MAX_SLOWMODE_GROUPS = 70

REGULAR_INTERVAL_PER_AD = 9 # SECONDS [ ❗️ Desired interval 3 seconds ]
SLOWMODE_INTERVAL_PER_AD = 52 # SECONDS [Working Perfect]

REGULAR_GROUPS_CYCLE = MAX_REGULAR_GROUPS * REGULAR_INTERVAL_PER_AD # SECONDS
SLOWMODE_GROUPS_CYCLE = MAX_SLOWMODE_GROUPS * SLOWMODE_INTERVAL_PER_AD # SECONDS

blacklisted_channels = [
    1691470900, # AM_FORUMS
    1901994892, # AM_BOTS
    1984235241, # Phantom Ads
]

PhoneNumbersList = [
    '+97691369776',

    '+3547652023',

    '+905393838325',
    '+260975114951',
    '+244936948974',
    '+263714561105',
    '+5926307350',
    '+923006985020',
    '+244930027465',
    '+37258510286',
    '+27813237219',
    '+9609590487',
    '+244924533066',
    '+244950784076',
    '+244940127129',
    '+244930305672',
    '+244929553988',
    '+244945712361',
    '+244935826729',
    '+244921198511',
    '+244945952319',
    '+244940250551',
    '+244952114340',
    '+244922838225',
    '+244931390058',
]

workers_pool = {}
for phone_number in PhoneNumbersList:    
    workers_pool[phone_number] = {
        'RegularDialogs': [],
        'RegularDialogsCount': 0,
        'RegularDialogsIndex': 0,
        'RegularNextDrop': time(),
        'RegularLastCycle': time(),

        'SlowModeDialogs': [],
        'SlowModeDialogsCount': 0,
        'SlowModeDialogsIndex': 0,
        'SlowModeNextDrop': time(),
        'SlowModeLastCycle': time(),

        'DialogsDetails': {},

        'Advertisements': [],

        'AnsweredChats': [],

        'NextUserInvite': 0
    }

async def fetch_dialogs(client: TelegramClient, phone_number):
    print(f"Retrieving Dialogs of bot {phone_number} ...")
    for dialog in await client.get_dialogs():
        entity = await client.get_input_entity(dialog)
    
        if isinstance(entity, InputPeerChannel):
            channel_id = entity.channel_id
            if channel_id in blacklisted_channels:
                continue
            
            slowmode_enabled = dialog.entity.slowmode_enabled
            
            if not slowmode_enabled and workers_pool[phone_number]['RegularDialogsCount'] < MAX_REGULAR_GROUPS:
                workers_pool[phone_number]['RegularDialogsCount'] += 1
                workers_pool[phone_number]['RegularDialogs'].append(entity)
            elif workers_pool[phone_number]['SlowModeDialogsCount'] < MAX_SLOWMODE_GROUPS:
                workers_pool[phone_number]['SlowModeDialogsCount'] += 1
                workers_pool[phone_number]['SlowModeDialogs'].append(entity)
            else:
                continue

            workers_pool[phone_number]['DialogsDetails'][channel_id] = dialog.title
            
async def fetch_advertisements(client: TelegramClient, phone_number):
    workers_pool[phone_number]['Advertisements'] = await client.get_messages(PHANTOM_BASE, limit=100, filter=InputMessagesFilterPinned())

async def main(phone_number):
    client = TelegramClient(f"Sessions/{phone_number}", API_ID, API_HASH)
    async with client:
        try:
            await client.get_input_entity(PHANTOM_BASE)
        except ValueError:
            await client(JoinChannelRequest(PHANTOM_BASE_LINK))
        
        await fetch_dialogs(client, phone_number)
        await fetch_advertisements(client, phone_number)

if input("Create New Session Files ? [Yes / No] [Default: No] ").upper().startswith('Y'):
    for phone_number in PhoneNumbersList:
        print(f"Logging in {phone_number} ...")
        client = TelegramClient(f"Sessions/{phone_number}", API_ID, API_HASH)
        with client:
            pass

loop = asyncio.get_event_loop()

tasks = [main(phone_number) for phone_number in PhoneNumbersList]
loop.run_until_complete(asyncio.gather(*tasks))

async def invite_user(client: TelegramClient, phone_number):
    w = 75
    workers_pool[phone_number]['NextUserInvite'] = time() + randrange(3600, 7200)
    user = ScrapUsersCollection.find_one({'Invited': {'$ne': True}, f'access_hash.{phone_number}': {'$exists': True}})
    if user:
        user_id = user.get('_id')

        access_hash = user.get('access_hash', {}).get(phone_number)

        invite_banned_numbers = ['+97691369776']
        if phone_number in invite_banned_numbers:
            return

        try:
            await client(InviteToChannelRequest(INVITE_USER_DESTINATION_GROUP, [InputUser(user_id=user_id, access_hash=access_hash)]))
            print(f"🔵 {phone_number} > Successfully invited {user_id} to {INVITE_USER_DESTINATION_GROUP}")
            ScrapUsersCollection.update_one({'_id': user_id}, {'$set': {'Invited': True}}, upsert=True)
            
            msg = f"{escape_markdown(INVITE_USER_DESTINATION_GROUP, version=2)} \[[User](tg://user?id={user_id}) invited by `{phone_number}`\]\n"
            msg += f"Members Left: {ScrapUsersCollection.count_documents({'Invited': {'$ne': True}})}"
            market_bot.send_message(chat_id=NOTIFY_USER_ID, text=msg, parse_mode=PARSEMODE_MARKDOWN_V2)
        except ChannelPrivateError:
            print(f"🟡 {phone_number} > Failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}".ljust(w) + f"[ChannelPrivateError]")
        except ChatWriteForbiddenError:
            print(f"🟡 {phone_number} > Failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}".ljust(w) + f"[ChatWriteForbiddenError: You can't write in this chat]")
        except UserKickedError:
            print(f"🟡 {phone_number} > Failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}".ljust(w) + f"[UserKickedError]")
        except UserNotMutualContactError:
            print(f"🟡 {phone_number} > Failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}".ljust(w) + f"[UserNotMutualContactError]")
        except UserPrivacyRestrictedError:
            print(f"🟡 {phone_number} > Failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}".ljust(w) + f"[UserPrivacyRestrictedError]")
            ScrapUsersCollection.update_one({'_id': user_id}, {'$set': {'Invited': True, 'UserPrivacyRestrictedError': True}}, upsert=True)
        except UserIdInvalidError:
            print(f"🟡 {phone_number} > Failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}".ljust(w) + f"[UserIdInvalidError]")
            ScrapUsersCollection.update_one({'_id': user_id}, {'$set': {'Invited': True, 'UserIdInvalidError': True}}, upsert=True)
        except FloodWaitError as e:
            print(f"🟡 {phone_number} > Failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}".ljust(w) + f"[FloodWaitError: {e.seconds} seconds]")
            workers_pool[phone_number]['NextUserInvite'] += e.seconds
        except Exception as e:
            msg = f"{phone_number} failed to invite {user_id} to {INVITE_USER_DESTINATION_GROUP}\n\nError: {e}"
            market_bot.send_message(chat_id=NOTIFY_USER_ID, text=msg)
    
async def advertise(client: TelegramClient, dialog: InputPeerChannel, phone_number, index, cycle_label = None, cycle_time = None):
    w = 75
    channel_name = workers_pool[phone_number]['DialogsDetails'].get(dialog.channel_id)
    extra_sleep = 0

    active_workers = len([1 for phone_number in PhoneNumbersList if workers_pool[phone_number]['RegularNextDrop'] + 30 > time()])
    active_chats = workers_pool[phone_number]['RegularDialogsCount'] + workers_pool[phone_number]['SlowModeDialogsCount']

    try:
        if cycle_time is not None:
            await client.send_message('me', f"Cycle {cycle_label} completed in {cycle_time / 60:.2f} Minutes")

        await client.send_message(dialog, choice(workers_pool[phone_number]['Advertisements']))
        print(f"✅ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}")
    except FloodWaitError as e:
        print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + f"[FloodWaitError: {e}]")
        extra_sleep = e.seconds
    except ForbiddenError:
        print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + "[ForbiddenError]")
    except ValueError:
        print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + "[ValueError]")
    except ChannelPrivateError:
        print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + "[ChannelPrivateError]")
    except SlowModeWaitError as e:
        pass
        # print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + "[SlowModeWaitError: {e}]")
    except FilePart0MissingError as e:
        print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + f"[FilePart0MissingError: {e}]")
    except UserBannedInChannelError: 
        print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + "[UserBannedInChannelError: Possibly limited due to spam]")
        if 'REGULAR' in cycle_label:
            workers_pool[phone_number]['RegularDialogsCount'] -= 1
            try:
                workers_pool[phone_number]['RegularDialogs'].remove(dialog)
            except:
                pass
        elif 'SLOWMODE' in cycle_label:
            workers_pool[phone_number]['SlowModeDialogsCount'] -= 1
            try:
                workers_pool[phone_number]['SlowModeDialogs'].remove(dialog)
            except:
                pass
    except BadRequestError as brerror:
        if "TOPIC_CLOSED" in str(brerror):
            print(f"❌ [Active Workers: {active_workers}, Active Chats: {active_chats}] Advertisement {index}: {phone_number} > [{dialog.channel_id}] {channel_name}".ljust(w) + "[Topic Closed]")
    
    if extra_sleep:
        await asyncio.sleep(extra_sleep)

async def start_advertiser(phone_number):
    # API_ID, API_HASH = choice(list(api_id_and_hash.items()))
    client = TelegramClient(f"Sessions/{phone_number}", API_ID, API_HASH)

    @client.on(events.NewMessage(incoming=True))
    async def forward_incoming_messsages(event: NewMessage.Event):
        if event.is_private and event.message.peer_id.user_id not in workers_pool[phone_number]['AnsweredChats']:
            print(event)
            workers_pool[phone_number]['AnsweredChats'].append(event.message.peer_id.user_id)

            await event.message.reply("Please contact me to my main Account: @alcatraz1998orti or when I see the message I will contact you from that account.")
            await client.forward_messages(PHANTOM_BASE_LINK, event.message)

    async with client:
        while True:
            current_time = time()

            try:
                c = workers_pool[phone_number]['RegularDialogsCount']
                if c and current_time >= workers_pool[phone_number]['RegularNextDrop']:
                    i = workers_pool[phone_number]['RegularDialogsIndex']

                    cycle_time = None
                    cycle_count, cycle_remainder = divmod(i, c)
                    if cycle_remainder == 0:
                        cycle_time = time() - workers_pool[phone_number]['RegularLastCycle']
                        workers_pool[phone_number]['RegularLastCycle'] = time()

                    await advertise(client, workers_pool[phone_number]['RegularDialogs'][i%c], phone_number, i, f"REGULAR#{c}-{cycle_count}", cycle_time)
                    workers_pool[phone_number]['RegularNextDrop'] = current_time + (REGULAR_GROUPS_CYCLE / c)
                    workers_pool[phone_number]['RegularDialogsIndex'] += 1
                    print(f"Next regular advertisement in {REGULAR_GROUPS_CYCLE / c:.2f} seconds ...")

                c = workers_pool[phone_number]['SlowModeDialogsCount']
                if c and current_time >= workers_pool[phone_number]['SlowModeNextDrop']:
                    i = workers_pool[phone_number]['SlowModeDialogsIndex']

                    cycle_time = None
                    cycle_count, cycle_remainder = divmod(i, c)
                    if cycle_remainder == 0:
                        cycle_time = time() - workers_pool[phone_number]['SlowModeLastCycle']
                        workers_pool[phone_number]['SlowModeLastCycle'] = time()

                    await advertise(client, workers_pool[phone_number]['SlowModeDialogs'][i%c], phone_number, i, f"SLOWMODE#{c}-{cycle_count}", cycle_time)
                    workers_pool[phone_number]['SlowModeNextDrop'] = current_time + (SLOWMODE_GROUPS_CYCLE / c)
                    workers_pool[phone_number]['SlowModeDialogsIndex'] += 1
                    print(f"Next slow-mo advertisement in {SLOWMODE_GROUPS_CYCLE / c:.2f} seconds ...")

                if current_time >= workers_pool[phone_number]['NextUserInvite']:
                    await invite_user(client, phone_number)

                await asyncio.sleep(0.1)
            except asyncio.CancelledError as e:
                print(f"Asyncio.CancelledError: {e}")
            except Exception as e:
                print(f"Error in session {phone_number}: {e}")
        
tasks = [start_advertiser(phone_number) for phone_number in PhoneNumbersList]
loop.run_until_complete(asyncio.gather(*tasks))

# for phone_number in PhoneNumbersList:
#     loop.create_task(start_advertiser(phone_number))
    
# loop.run_forever()