import logging
from telegram import Chat, ChatMember, ChatMemberUpdated, Update,InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes,ChatMemberHandler,CallbackQueryHandler,ConversationHandler,MessageHandler,filters
import requests
import json
from decimal import Decimal, getcontext
from datetime import datetime, timedelta, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor

####  ============ utils ======================== #
def special_format(number):
    number = float(number)
    if number >= 1_000_000_000:  # Billions
        formatted = f"{number / 1_000_000_000:.1f}B"
    elif number >= 1_000_000:  # Millions
        formatted = f"{number / 1_000_000:.1f}M"
    elif number >= 1_000:  # Thousands
        formatted = f"{number / 1_000:.1f}K"
    elif number >= 0.000000001:  # Handle very small numbers (up to 9 decimal places)
        formatted = f"{number:.9f}".rstrip('0').rstrip('.')
    elif number > 0:  # Handle very small numbers using scientific notation
        formatted = f"{number:.9e}"
    else:  # Handle zero or negative numbers if needed
        formatted = f"{number:.9f}".rstrip('0').rstrip('.')
    return formatted

def calculate_age(date_created):
    birthdate = datetime.fromtimestamp(date_created / 1000, tz=timezone.utc)
    
    # Current time in UTC
    now = datetime.now(timezone.utc)
    
    # Calculate the total number of days between now and birthdate
    delta_days = (now - birthdate).days
    # Determine the most appropriate unit
    if delta_days >= 365.25:
        age_years = int(delta_days // 365.25)
        return f"{age_years} years"
    elif delta_days >= 30.44:
        age_months = int(delta_days // 30.44)
        return f"{age_months} mo"
    elif delta_days >= 7:
        age_weeks = delta_days // 7
        return f"{age_weeks} wk"
    else:
        return f"{delta_days} d"

def get_token_pools(address, page="1"):
    url = (f"https://api.dexscreener.com/latest/dex/tokens/{address}")
    response = requests.get(url)
    with open('g.json','w')as file:
        json.dump(response.json(),file,indent =4)
    return response.json()

def all_time_high(token_address,date_created):
    current_datetime = datetime.now()
    timestamp_seconds = int(current_datetime.timestamp())
    splited = token_address.split('::')
    used_address =splited[0]
    print(timestamp_seconds)
    print(date_created)

    url = f"https://public-api.birdeye.so/defi/history_price?address={used_address}%3A%3A{splited[-2]}%3A%3A{splited[-1]}&address_type=token&type=1D&time_from={date_created}&time_to={timestamp_seconds}"

    headers = {
        "accept": "application/json",
        "x-chain": "sui",
        "X-API-KEY": "0dfb9c6c2e2540629463db7a61891f70"
    }
    response = requests.get(url, headers=headers)
    data = response.json()['data']['items']
    with open('h.json','w')as file:
        json.dump(data,file,indent =4)
    
    max_entry = max(data, key=lambda x: x["value"])
    return max_entry["value"], max_entry["unixTime"]

def get_holders(token_address:str):
    gg = token_address.split('::')
    print(gg)
    using_address =gg[0]
    url = f"https://api.blockberry.one/sui/v1/coins/{using_address}%3A%3A{gg[-2]}%3A%3A{gg[-1]}/holders?page=0&size=10&orderBy=DESC&sortBy=AMOUNT"

    headers = {
        "accept": "*/*",
        "x-api-key": "RQHohI3MlLTjDAcbDTjXGk1S0Iv2Wf"
    }
    response = requests.get(url, headers=headers)
    data =response.json()
    total_percentage = sum(holder['percentage'] for holder in data['content'])
    with open('ho.json','w')as file:
        json.dump(data,file,indent =4)
    values = []
    addresses = []
    count =0
    for items in data['content']:
        if count <5:
            addresses.append(f"https://suivision.xyz/account/{items['holderAddress']}")
            values.append(round(items['percentage'],1))
            count +=1
    # print(' | '.join(map(str,values)))
    output = " | ".join([f"<a href='{url}'>{num}</a>" for num, url in zip(values, addresses)])
    return output,total_percentage

def get_holders_count(token_address):
    splited = token_address.split('::')
    used_address =splited[0]
    url = f"https://api.blockberry.one/sui/v1/coins/{used_address}%3A%3A{splited[-2]}%3A%3A{splited[-1]}"

    headers = {
        "accept": "*/*",
        "x-api-key": "RQHohI3MlLTjDAcbDTjXGk1S0Iv2Wf"
    }

    response = requests.get(url, headers=headers)

    data = response.json()['holdersCount']
    return data

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


## =========== bot =================++#
async def is_user_admin(update:Update,context:ContextTypes.DEFAULT_TYPE):
    ## check if usser is admin
    chat_id = update.effective_chat.id
    user_id = update.message.from_user.id
    admins = await context.bot.get_chat_administrators(chat_id)
    return any(admin.user.id == user_id for admin in admins)

async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.my_chat_member.new_chat_member.status == 'member':
        chat_id = update.my_chat_member.chat.id
        group_name = update.my_chat_member.chat.title
        logger.info(f"Bot added to group '{group_name}' (Chat ID: {chat_id})")
        welcome_message = (
            f'''
🚀✨ Thanks for adding me to this group, lets explore together
'''   
        )
        await context.bot.send_message(chat_id=chat_id, text=welcome_message)
        #then it automatically creates a new key on the database
executor = ThreadPoolExecutor(max_workers=4)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    message = update.message.text
    if message.startswith('0x'):
        try:
            # Offload blocking I/O operations to a separate thread
            data = await asyncio.get_event_loop().run_in_executor(executor, get_token_pools, message)
            value = data['pairs'][0]

            # Collect all the values asynchronously
            async def get_values():
                pair_address = value.get('pairAddress', "N/A")
                name = value.get('baseToken', {}).get('name', "N/A")
                symbol = value.get('baseToken', {}).get('symbol', "N/A")
                price_in_usd = value.get('priceUsd', "N/A")
                fdv = value.get('marketCap', "N/A")
                website = f"<a href='{value.get('info', {}).get('websites', [{}])[0].get('url', '')}'>WEB</a>" if value.get('info', {}).get('websites') else "N/A"
                twitter = f"<a href='{value.get('info', {}).get('socials', [{}])[0].get('url', '')}'>X</a>" if value.get('info', {}).get('socials') else "N/A"
                telegram = f"<a href='{value.get('info', {}).get('socials', [{}])[1].get('url', '')}'>TG</a>" if value.get('info', {}).get('socials') else "N/A"
                pair_created = calculate_age(value.get('pairCreatedAt', "N/A"))
                hr_24 = value.get('priceChange', {}).get('h24', "N/A")
                hr_1 = value.get('priceChange', {}).get('h1', "N/A")
                vol_in_usd = value.get('volume', {}).get('h24', "N/A")
                tnx_buy_1hr = value.get('txns', {}).get('h1', {}).get('buys', "N/A")
                tnx_sell_1hr = value.get('txns', {}).get('h1', {}).get('sells', "N/A")
                vol_in_usd_1hr = value.get('volume', {}).get('h1', "N/A")
                liquidity = value.get('liquidity', {}).get('usd', "N/A")
                dex_id = value.get('dexId', "N/A")
                date_to_use = value.get('pairCreatedAt', 0) // 1000

                highest_value, corresponding_unix_time = await asyncio.get_event_loop().run_in_executor(executor, all_time_high, message, date_to_use)
                ath = (float(highest_value) * float(fdv)) / float(price_in_usd) if highest_value and fdv and price_in_usd else "N/A"
                dex_chart = f"<a href='https://dexscreener.com/sui/{pair_address}'>DEXSCRENEER</a>"
                blue_dex = f"<a href='https://dex.bluemove.net/swap/0x2::sui::SUI/{pair_address}'>BLUEMOVE</a>"
                birdeye = f"<a href='https://birdeye.so/token/{message}'>BIRDEYE</a>"
                hog = f"<a href='https://hop.ag/swap/SUI-{symbol}'>HOP</a>"
                holders, top_holders = await asyncio.get_event_loop().run_in_executor(executor, get_holders, message)
                time_for_ath = calculate_age(int(corresponding_unix_time * 1000)) if corresponding_unix_time else "N/A"
                holders_count = await asyncio.get_event_loop().run_in_executor(executor, get_holders_count, message)

                return {
                    "pair_address": pair_address, "name": name, "symbol": symbol, "price_in_usd": price_in_usd, 
                    "fdv": fdv, "website": website, "twitter": twitter, "telegram": telegram, "pair_created": pair_created, 
                    "hr_24": hr_24, "hr_1": hr_1, "vol_in_usd": vol_in_usd, "tnx_buy_1hr": tnx_buy_1hr, 
                    "tnx_sell_1hr": tnx_sell_1hr, "vol_in_usd_1hr": vol_in_usd_1hr, "liquidity": liquidity, 
                    "dex_id": dex_id, "ath": ath, "dex_chart": dex_chart, "blue_dex": blue_dex, "birdeye": birdeye, 
                    "hog": hog, "holders": holders, "time_for_ath": time_for_ath, "holders_count": holders_count,
                    "top_holders": top_holders
                }

            values = await get_values()
            message_content = (
                f"🟢<b>{values['name']} [{special_format(values['fdv'])}/{values['hr_24']}%]</b> ${values['symbol']}\n"
                f"💧SUI @ {values['dex_id']}\n"
                f"💰USD: <code>${special_format(values['price_in_usd'])}</code>\n"
                f"💎FDV: <code>${special_format(values['fdv'])}</code>\n"
                f"💦Liq: <code>${special_format(values['liquidity'])}</code>\n"
                f"📊Vol: <code>${special_format(values['vol_in_usd'])} Age: {values['pair_created']}</code>\n"
                f"🌋ATH: <code>${special_format(values['ath'])} @ {values['time_for_ath']}</code> \n"
                f"📉 1H: <code><a href ='#'>{special_format(values['hr_1'])}% | ${special_format(values['vol_in_usd_1hr'])} | 🅑 {values['tnx_buy_1hr']} | 🅢 {values['tnx_sell_1hr']}</a></code>\n"
                f"💬{values['telegram']} | {values['twitter']} | {values['website']}\n\n"
                f"TOP: <code>{values['holders']}</code>\n\n"
                f"HOLDERS: <code>{special_format(int(values['holders_count']))} | TOP 10: {round(values['top_holders'], 2)}%</code>\n\n"
                f"<code>{message}</code>\n\n"
                f"{values['hog']} | {values['blue_dex']} | {values['birdeye']} | {values['dex_chart']}"
            )
            await context.bot.send_message(chat_id, text=message_content, parse_mode='HTML', disable_web_page_preview=True)

        except Exception as e:
            print(e)
            await context.bot.send_message(chat_id=chat_id, text='An Error Occurred')

async def scan(update:Update,context = ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    the_args = context.args[0]
    print(the_args)
    try:
        if the_args:
            # Offload blocking I/O operations to a separate thread
            data = await asyncio.get_event_loop().run_in_executor(executor, get_token_pools, the_args)
            value = data['pairs'][0]
            # Collect all the values asynchronously
            async def get_values():
                pair_address = value.get('pairAddress', "N/A")
                name = value.get('baseToken', {}).get('name', "N/A")
                symbol = value.get('baseToken', {}).get('symbol', "N/A")
                price_in_usd = value.get('priceUsd', "N/A")
                fdv = value.get('marketCap', "N/A")
                website = f"<a href='{value.get('info', {}).get('websites', [{}])[0].get('url', '')}'>WEB</a>" if value.get('info', {}).get('websites') else "N/A"
                twitter = f"<a href='{value.get('info', {}).get('socials', [{}])[0].get('url', '')}'>X</a>" if value.get('info', {}).get('socials') else "N/A"
                telegram = f"<a href='{value.get('info', {}).get('socials', [{}])[1].get('url', '')}'>TG</a>" if value.get('info', {}).get('socials') else "N/A"
                pair_created = calculate_age(value.get('pairCreatedAt', "N/A"))
                hr_24 = value.get('priceChange', {}).get('h24', "N/A")
                hr_1 = value.get('priceChange', {}).get('h1', "N/A")
                vol_in_usd = value.get('volume', {}).get('h24', "N/A")
                tnx_buy_1hr = value.get('txns', {}).get('h1', {}).get('buys', "N/A")
                tnx_sell_1hr = value.get('txns', {}).get('h1', {}).get('sells', "N/A")
                vol_in_usd_1hr = value.get('volume', {}).get('h1', "N/A")
                liquidity = value.get('liquidity', {}).get('usd', "N/A")
                dex_id = value.get('dexId', "N/A")
                date_to_use = value.get('pairCreatedAt', 0) // 1000

                highest_value, corresponding_unix_time = await asyncio.get_event_loop().run_in_executor(executor, all_time_high, the_args, date_to_use)
                ath = (float(highest_value) * float(fdv)) / float(price_in_usd) if highest_value and fdv and price_in_usd else "N/A"
                dex_chart = f"<a href='https://dexscreener.com/sui/{pair_address}'>DEXSCRENEER</a>"
                blue_dex = f"<a href='https://dex.bluemove.net/swap/0x2::sui::SUI/{pair_address}'>BLUEMOVE</a>"
                birdeye = f"<a href='https://birdeye.so/token/{the_args}'>BIRDEYE</a>"
                hog = f"<a href='https://hop.ag/swap/SUI-{symbol}'>HOP</a>"
                holders, top_holders = await asyncio.get_event_loop().run_in_executor(executor, get_holders, the_args)
                time_for_ath = calculate_age(int(corresponding_unix_time * 1000)) if corresponding_unix_time else "N/A"
                holders_count = await asyncio.get_event_loop().run_in_executor(executor, get_holders_count, the_args)

                return {
                    "pair_address": pair_address, "name": name, "symbol": symbol, "price_in_usd": price_in_usd, 
                    "fdv": fdv, "website": website, "twitter": twitter, "telegram": telegram, "pair_created": pair_created, 
                    "hr_24": hr_24, "hr_1": hr_1, "vol_in_usd": vol_in_usd, "tnx_buy_1hr": tnx_buy_1hr, 
                    "tnx_sell_1hr": tnx_sell_1hr, "vol_in_usd_1hr": vol_in_usd_1hr, "liquidity": liquidity, 
                    "dex_id": dex_id, "ath": ath, "dex_chart": dex_chart, "blue_dex": blue_dex, "birdeye": birdeye, 
                    "hog": hog, "holders": holders, "time_for_ath": time_for_ath, "holders_count": holders_count,
                    "top_holders": top_holders
                }

            values = await get_values()
            message_content = (
                f"🟢<b>{values['name']} [{special_format(values['fdv'])}/{values['hr_24']}%]</b> ${values['symbol']}\n"
                f"💧SUI @ {values['dex_id']}\n"
                f"💰USD: <code>${special_format(values['price_in_usd'])}</code>\n"
                f"💎FDV: <code>${special_format(values['fdv'])}</code>\n"
                f"💦Liq: <code>${special_format(values['liquidity'])}</code>\n"
                f"📊Vol: <code>${special_format(values['vol_in_usd'])} Age: {values['pair_created']}</code>\n"
                f"🌋ATH: <code>${special_format(values['ath'])} @ {values['time_for_ath']}</code> \n"
                f"📉 1H: <code><a href ='#'>{special_format(values['hr_1'])}% | ${special_format(values['vol_in_usd_1hr'])} | 🅑 {values['tnx_buy_1hr']} | 🅢 {values['tnx_sell_1hr']}</a></code>\n"
                f"💬{values['telegram']} | {values['twitter']} | {values['website']}\n\n"
                f"TOP: <code>{values['holders']}</code>\n\n"
                f"HOLDERS: <code>{special_format(int(values['holders_count']))} | TOP 10: {round(values['top_holders'], 2)}%</code>\n\n"
                f"<code>{the_args}</code>\n\n"
                f"{values['hog']} | {values['blue_dex']} | {values['birdeye']} | {values['dex_chart']}"
            )
            await context.bot.send_message(chat_id, text=message_content, parse_mode='HTML', disable_web_page_preview=True)

    except Exception as e:
        print('heree',e)
TOKEN_KEY_ = '8137029737:AAHegPYrIqn64szuBQuLsxO6oLs_h0OqGMQ'
def main():
    app = ApplicationBuilder().token(TOKEN_KEY_).build()
    app.add_handler(ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("scan", scan))

    # app.add_handler()
    app.run_polling()

if __name__ == '__main__':
    main()
