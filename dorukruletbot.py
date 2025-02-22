import telebot
from telebot import types
import random
from threading import Timer
from PIL import Image, ImageDraw, ImageFont
import os

# Bot Token
TOKEN = '7912106541:AAHZI3rwpZCbGXt508FqaY9kE-gdIsZFNU8'
bot = telebot.TeleBot(TOKEN)

# Kullanıcı bakiyeleri ve bahisler
user_balances = {}
user_names = {}
bets = {}
active_games = set()  # Aktif oyunları takip etmek için
registrations = set()  # Kayıt olan kullanıcıları takip etmek için

# Rulet görselleri klasör yolu
roulette_images_folder = '/storage/emulated/0/Rulet/'

# Rulet sayılarının renkleri
roulette_colors = {
    0: 'green', 1: 'red', 2: 'black', 3: 'red', 4: 'black', 5: 'red', 6: 'black', 
    7: 'red', 8: 'black', 9: 'red', 10: 'black', 11: 'black', 12: 'red', 13: 'black', 
    14: 'red', 15: 'black', 16: 'red', 17: 'black', 18: 'red', 19: 'red', 20: 'black', 
    21: 'red', 22: 'black', 23: 'red', 24: 'black', 25: 'red', 26: 'black', 27: 'red', 
    28: 'black', 29: 'black', 30: 'red', 31: 'black', 32: 'red', 33: 'black', 34: 'red', 
    35: 'black', 36: 'red', '00': 'green', '000': 'green'
}

def format_amount(amount):
    """Bakiye formatlama fonksiyonu."""
    suffixes = {10**12: 'T', 10**9: 'B', 10**6: 'M', 10**3: 'k'}
    for divisor, suffix in suffixes.items():
        if amount >= divisor:
            return f"{amount // divisor}{suffix} 🪙 DTC"
    return f"{amount} 🪙 DTC"

def get_username(user_id):
    """Kullanıcı adını alma fonksiyonu."""
    return user_names.get(user_id, f"ID-{user_id}")

# Start komutu ile kullanıcı kaydı
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in registrations:
        bot.send_message(user_id, (
            "Rulet oyununa hoş geldiniz! Lütfen kendinize bir isim belirleyin.\n"
            "İsim belirlemek için /changename [yeni isim] komutunu kullanabilirsiniz.\n"
            "Örnek: /changename Ahmet"
        ))
        registrations.add(user_id)
        user_balances[user_id] = 10000000000  # Başlangıç bonusu

# Kullanıcı adını değiştirme komutu
@bot.message_handler(commands=['changename'])
def change_name(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        new_name = message.text.split(maxsplit=1)[1]
        user_names[user_id] = new_name
        bot.send_message(chat_id, f"İsminiz '{new_name}' olarak değiştirildi.")
    except IndexError:
        bot.send_message(chat_id, "Lütfen yeni isminizi belirtin. Kullanım: /changename [yeni isim]")

# Bakiye sorgulama komutu
@bot.message_handler(commands=['balance'])
def check_balance(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    balance = user_balances.get(user_id, 10000000000)  # Varsayılan bakiye
    max_win = max([amount for _, amount in bets.get(user_id, [])], default=0)
    win_rate = "N/A"  # Kazanma oranı hesaplanabilir
    balance_text = (
        f"👤 Kullanıcı: {get_username(user_id)}\n"
        f"💰 Bakiye: {format_amount(balance)}\n"
        f"🏆 En Yüksek Kazanç: {format_amount(max_win)}\n"
        f"📊 Kazanma Oranı: {win_rate}\n"
    )
    bot.send_message(chat_id, balance_text)

# Para gönderme komutu
@bot.message_handler(commands=['send'])
def send_money(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        parts = message.text.split()
        target_id = int(parts[1])
        amount = int(parts[2])
        target_name = get_username(target_id)

        if user_balances[user_id] >= amount:
            user_balances[user_id] -= amount
            user_balances[target_id] = user_balances.get(target_id, 0) + amount
            bot.send_message(
                chat_id,
                f"💸 {get_username(user_id)}, {target_name}'ye {format_amount(amount)} gönderdi.\n"
                f"✅ Yeni bakiyeniz: {format_amount(user_balances[user_id])}"
            )
        else:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /send [ID] [miktar]")

# Liderlik tablosu komutu
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    chat_id = message.chat.id
    sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_text = "🏆 Liderlik Tablosu 🏆\n"
    for idx, (user_id, balance) in enumerate(sorted_users):
        leaderboard_text += f"{idx + 1}. {get_username(user_id)}: {format_amount(balance)}\n"
    bot.send_message(chat_id, leaderboard_text)

# Rulet başlatma komutu
@bot.message_handler(commands=['rulet'])
def start_rulet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if chat_id in active_games:
        bot.send_message(chat_id, "❌ Şu anda zaten bir oyun açık. Lütfen sonuçların açıklanmasını bekleyin.")
        return

    if user_id not in registrations:
        bot.send_message(chat_id, "❌ Lütfen önce /start komutunu kullanarak kayıt olun.")
        return

    active_games.add(chat_id)
    user_balances.setdefault(user_id, 10000000000)  # Varsayılan bakiye (10B 🪙 DTC)

    # Çark görselini gönder
    try:
        image_path = f"{roulette_images_folder}rulet.çark.jpg"
        with open(image_path, 'rb') as image_file:
            bot.send_photo(chat_id, image_file, caption="🎰 Rulet oyunu başladı! Bahislerinizi yapın.")
    except FileNotFoundError:
        bot.send_message(chat_id, "❌ Çark görseli bulunamadı.")
        active_games.remove(chat_id)
        return

    bot.send_message(chat_id, "⏳ Bahis yapmak için 25 saniyeniz var!")
    Timer(25, roulette_game, args=[chat_id]).start()

# Yeşil bahis komutu
@bot.message_handler(commands=['green'])
def green_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        bet_amount = int(message.text.split()[1])
        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return
        user_balances[user_id] -= bet_amount
        bets.setdefault(user_id, []).append(('green', bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: 🟢 Yeşil için {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /green [miktar]")

# Kırmızı bahis komutu
@bot.message_handler(commands=['red'])
def red_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        bet_amount = int(message.text.split()[1])
        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return
        user_balances[user_id] -= bet_amount
        bets.setdefault(user_id, []).append(('red', bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: 🔴 Kırmızı için {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /red [miktar]")

# Siyah bahis komutu
@bot.message_handler(commands=['black'])
def black_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        bet_amount = int(message.text.split()[1])
        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return
        user_balances[user_id] -= bet_amount
        bets.setdefault(user_id, []).append(('black', bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: ⚫ Siyah için {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /black [miktar]")

# Tek sayı bahis komutu
@bot.message_handler(commands=['number'])
def number_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        parts = message.text.split()
        bet_amount = int(parts[1])
        bet_number = parts[2]

        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return

        if bet_number.isdigit() and 0 <= int(bet_number) <= 36 or bet_number in ['00', '000']:
            user_balances[user_id] -= bet_amount
            bets.setdefault(user_id, []).append((bet_number, bet_amount))
            bot.send_message(chat_id, f"💵 {get_username(user_id)}: {bet_number} numarasına {format_amount(bet_amount)} bahis yaptınız.")
        else:
            bot.send_message(chat_id, "❌ Geçersiz sayı. Lütfen 0-36, 00 veya 000 arasında bir sayı girin.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /number [miktar] [sayı]")

# Çoklu sayı bahis komutu
@bot.message_handler(commands=['multinumber'])
def multinumber_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        parts = message.text.split()
        bet_amount = int(parts[1])
        bet_numbers = parts[2:]

        if bet_amount * len(bet_numbers) > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return

        invalid_numbers = [n for n in bet_numbers if not (n.isdigit() and 0 <= int(n) <= 36 or n in ['00', '000'])]
        if invalid_numbers:
            bot.send_message(chat_id, f"❌ Geçersiz sayılar: {', '.join(invalid_numbers)}. Lütfen 0-36, 00 veya 000 arasında sayılar girin.")
            return

        for bet_number in bet_numbers:
            user_balances[user_id] -= bet_amount
            bets.setdefault(user_id, []).append((bet_number, bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: {', '.join(bet_numbers)} numaralarına {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /multinumber [miktar] [sayı(lar)]")

# Rulet oyunu
def roulette_game(chat_id):
    global bets
    result = random.choice([i for i in range(37)] + ['00', '000'])

    bot.send_message(chat_id, "⏳ Bahisler kapandı! Sonuçlar hesaplanıyor...")

    # Sonuç sembolü ve rengi
    result_color = roulette_colors[result]
    result_symbol = '🟢' if result_color == 'green' else '🔴' if result_color == 'red' else '⚫'

    # Sonuç görseli ve kazananları gönder
    winners = []
    losers = []
    for user_id, bets_list in bets.items():
        total_winnings = 0
        for bet_type, bet_amount in bets_list:
            if bet_type == str(result):  # Sayı bahsi
                if result == '00':
                    winnings = bet_amount * 144
                elif result == '000':
                    winnings = bet_amount * 216
                else:
                    winnings = bet_amount * 36
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'red' and result_color == 'red':  # Kırmızı bahis
                winnings = bet_amount * 2
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'black' and result_color == 'black':  # Siyah bahis
                winnings = bet_amount * 2
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'green' and result_color == 'green':  # Yeşil bahis
                if result == 0:
                    winnings = bet_amount * 72
                elif result == '00':
                    winnings = bet_amount * 144
                elif result == '000':
                    winnings = bet_amount * 216
                else:
                    winnings = bet_amount * 36
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'even' and isinstance(result, int) and result % 2 == 0 and result != 0:  # Çift sayı bahis
                winnings = bet_amount * 2
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'odd' and isinstance(result, int) and result % 2 != 0:  # Tek sayı bahis
                winnings = bet_amount * 2
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'first12' and isinstance(result, int) and 1 <= result <= 12:  # 1-12 bölgesi bahis
                winnings = bet_amount * 3
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'second12' and isinstance(result, int) and 13 <= result <= 24:  # 13-24 bölgesi bahis
                winnings = bet_amount * 3
                user_balances[user_id] += winnings
                total_winnings += winnings
            elif bet_type == 'third12' and isinstance(result, int) and 25 <= result <= 36:  # 25-36 bölgesi bahis
                winnings = bet_amount * 3
                user_balances[user_id] += winnings
                total_winnings += winnings

        if total_winnings > 0:
            winners.append(f"✅ {get_username(user_id)}: {format_amount(total_winnings)} kazandı")
        else:
            losers.append(f"❌ {get_username(user_id)}: {format_amount(sum([amount for _, amount in bets_list]))} kaybetti")

    # Sonuç mesajı
    result_text = (
        f"🎰 Rulet sonucu: {result} ({result_color}) {result_symbol}\n"
        f"🏆 Kazananlar:\n" + "\n".join(winners) + "\n"
        f"💔 Kaybedenler:\n" + "\n".join(losers)
    )

    # Sonuç görseli gönder
    try:
        image_path = f"{roulette_images_folder}rulet.{result}.jpg"
        with open(image_path, 'rb') as image_file:
            bot.send_photo(chat_id, image_file, caption=result_text)
    except FileNotFoundError:
        bot.send_message(chat_id, result_text)

    bets.clear()
    active_games.remove(chat_id)

# Yardım komutu
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "🎰 Rulet Oyunu Komutları 🎰\n"
        "/start - Oyuna kayıt olun.\n"
        "/changename [isim] - İsminizi değiştirin.\n"
        "/balance - Bakiyenizi kontrol edin.\n"
        "/send [ID] [miktar] - Para gönderin.\n"
        "/leaderboard - Liderlik tablosunu görüntüleyin.\n"
        "/rulet - Rulet oyununu başlatın.\n"
        "/green [miktar] - Yeşil için bahis yapın.\n"
        "/red [miktar] - Kırmızı için bahis yapın.\n"
        "/black [miktar] - Siyah için bahis yapın.\n"
        "/number [miktar] [sayı] - Tek sayı için bahis yapın.\n"
        "/multinumber [miktar] [sayılar] - Çoklu sayı için bahis yapın.\n"
    )
    bot.send_message(message.chat.id, help_text)

# Botu başlat
bot.polling()
