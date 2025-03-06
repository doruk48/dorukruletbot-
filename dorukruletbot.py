import telebot
from telebot import types
import random
from threading import Timer
from datetime import datetime, timedelta
import json
import os
import uuid  # Uniq oyun ID'leri oluşturmak için

# .data klasörünü oluştur (eğer yoksa)
if not os.path.exists('.data'):
    os.makedirs('.data')

# .data klasörüne bakiye bilgilerini kaydet
def save_balances():
    try:
        file_path = os.path.join('.data', 'balances.json')
        with open(file_path, 'w') as file:
            json.dump(user_balances, file)
        print("Bakiye bilgileri kaydedildi.")
    except Exception as e:
        print("Bakiye kaydedilirken hata oluştu:", e)

# .data klasöründen bakiye bilgilerini yükle
def load_balances():
    try:
        file_path = os.path.join('.data', 'balances.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        print("Bakiye dosyası bulunamadı, yeni bir dosya oluşturulacak.")
    except Exception as e:
        print("Bakiye yüklenirken hata oluştu:", e)
    return {}

# Kullanıcı bakiyeleri
user_balances = load_balances()
user_names = {}
active_games = {}
bets = {}  # Bahisleri tutmak için
registrations = set()
statistics = user_balances.get('statistics', {})

# Bot Token
TOKEN = '7912106541:AAHZI3rwpZCbGXt508FqaY9kE-gdIsZFNU8'
bot = telebot.TeleBot(TOKEN)

# Rulet sayılarının renkleri
roulette_colors = {
    0: 'green', 1: 'red', 2: 'black', 3: 'red', 4: 'black', 5: 'red', 6: 'black', 
    7: 'red', 8: 'black', 9: 'red', 10: 'black', 11: 'black', 12: 'red', 13: 'black', 
    14: 'red', 15: 'black', 16: 'red', 17: 'black', 18: 'red', 19: 'red', 20: 'black', 
    21: 'red', 22: 'black', 23: 'red', 24: 'black', 25: 'red', 26: 'black', 27: 'red', 
    28: 'black', 29: 'black', 30: 'red', 31: 'black', 32: 'red', 33: 'black', 34: 'red', 
    35: 'black', 36: 'red'
}

# Yeni seviye eşikleri ve emojiler
LEVELS = {
    100000000: "Çırak 🛠️",        # 100M 🪙
    1000000000: "Kalfa 🔧",       # 1B 🪙
    10000000000: "Usta 🛡️",       # 10B 🪙
    100000000000: "Süper Oyuncu 🚀",  # 100B 🪙
    1000000000000: "Şampiyon 🏆",    # 1T 🪙
    10000000000000: "Efsane 🐉",     # 10T 🪙
    100000000000000: "Godlike 👑",   # 100T 🪙
    1000000000000000: "Trilyoner 💎"  # 1Q 🪙
}

def format_amount(amount):
    """Bakiye formatlama fonksiyonu."""
    suffixes = {10**12: 'T', 10**9: 'B', 10**6: 'M', 10**3: 'k'}
    for divisor, suffix in suffixes.items():
        if amount >= divisor:
            return f"{amount / divisor:,.2f}{suffix} 🪙"
    return f"{amount:,.2f} 🪙"

def get_level(balance):
    """Bakiye seviyesini belirleme fonksiyonu."""
    for threshold, level in sorted(LEVELS.items(), reverse=True):
        if balance >= threshold:
            return level
    return "Acemi 🪙"

def get_username(user_id):
    """Kullanıcı adını alma fonksiyonu."""
    return user_names.get(user_id, f"ID-{user_id}")

def get_image_url(result):
    """Görsel URL'sini oluşturma fonksiyonu."""
    base_url = "https://github.com/doruk48/rulet_images/blob/main/Rulet.{}.jpg?raw=true"
    return base_url.format(result)

def send_result_message(chat_id, result, winners, losers):
    """Sonuç mesajını gönderme fonksiyonu."""
    result_color = roulette_colors[result]
    result_symbol = '🟢' if result_color == 'green' else '🔴' if result_color == 'red' else '⚫'
    result_text = f"🏆 Rulet sonucu: {result} ({result_color}) {result_symbol}\n"
    
    if winners:
        result_text += "✅ Kazananlar:\n" + "\n".join(f"✅ {winner}" for winner in winners)
    if losers:
        result_text += "\n❌ Kaybedenler:\n" + "\n".join(f"❌ {loser}" for loser in losers)
    
    image_url = get_image_url(result)
    try:
        bot.send_photo(chat_id, image_url, caption=result_text)
    except Exception as e:
        bot.send_message(chat_id, result_text)
        print(f"Error sending image: {e}")

# Start komutu ile kullanıcı kaydı
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in registrations:
        bot.send_message(user_id, (
            "🎰 Rulet oyununa hoş geldiniz! Lütfen kendinize bir isim belirleyin.\n"
            "İsim belirlemek için /changename [yeni isim] komutunu kullanabilirsiniz.\n"
            "Örnek: /changename Ahmet"
        ))
        registrations.add(user_id)
        user_balances[user_id] = 10000000000  # Başlangıç bonusu
        statistics[user_id] = {
            'total_bets': 0,
            'total_wins': 0,
            'total_losses': 0,
            'max_win': 0,
            'win_rate': 0
        }
        bot.send_message(user_id, f"🎉 Tebrikler! 10B 🪙 başlangıç bonusu kazandınız. Şimdi rulet oynamaya başlayabilirsiniz.")

# Günlük bonus verileri
daily_bonus = {}

def get_daily_bonus_amount(day):
    """Günlük bonus miktarını belirleme fonksiyonu."""
    if day == 7:
        return 1000000000  # 7. gün 1B 🪙
    return day * 100000000  # Diğer günler 100M, 200M, 300M, ..., 600M 🪙

@bot.message_handler(commands=['daily'])
def daily_bonus_command(message):
    user_id = message.from_user.id
    today = datetime.now().date()

    if user_id in daily_bonus:
        last_claim_date = daily_bonus[user_id]['last_claim_date']
        streak = daily_bonus[user_id]['streak']

        # Eğer kullanıcı bugün bonusunu zaten aldıysa
        if last_claim_date == today:
            bot.send_message(message.chat.id, "❌ Bugünkü bonusunuzu zaten aldınız. Yarın tekrar deneyin!")
            return

        # Eğer kullanıcı bir gün atladıysa, streak sıfırlanır
        if last_claim_date + timedelta(days=1) != today:
            streak = 0
    else:
        streak = 0

    # Streak'i güncelle
    streak += 1
    if streak > 7:
        streak = 1  # 7 gün tamamlandığında streak sıfırlanır

    # Bonus miktarını belirle
    bonus_amount = get_daily_bonus_amount(streak)
    user_balances[user_id] += bonus_amount

    # Günlük bonus verilerini güncelle
    daily_bonus[user_id] = {
        'last_claim_date': today,
        'streak': streak
    }

    # Kullanıcıya bilgi ver
    bot.send_message(message.chat.id, (
        f"🎉 Günlük bonusunuz: {format_amount(bonus_amount)}\n"
        f"🔥 Streak: {streak} gün\n"
        f"💰 Yeni bakiyeniz: {format_amount(user_balances[user_id])}"
    ))

# Kullanıcı adını değiştirme komutu
@bot.message_handler(commands=['changename'])
def change_name(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    try:
        new_name = message.text.split(maxsplit=1)[1]
        user_names[user_id] = new_name
        bot.send_message(chat_id, f"✅ İsminiz '{new_name}' olarak değiştirildi.")
    except IndexError:
        bot.send_message(chat_id, "❌ Lütfen yeni isminizi belirtin. Kullanım: /changename [yeni isim]")

# Bakiye sorgulama komutu
@bot.message_handler(commands=['balance'])
def check_balance(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Varsayılan bakiye ve bahis verileri
    balance = user_balances.get(user_id, 10000000000)  # Varsayılan bakiye
    user_stats = statistics.get(user_id, {
        'total_bets': 0,
        'total_wins': 0,
        'total_losses': 0,
        'max_win': 0,
        'win_rate': 0
    })
    total_bets = user_stats['total_bets']
    total_wins = user_stats['total_wins']
    total_losses = user_stats['total_losses']
    max_win = user_stats['max_win']
    win_rate = user_stats['win_rate']
    level = get_level(balance)  # Kullanıcı seviyesi

    # Formatlanmış metin
    balance_text = (
        f"🎰 *Rulet Botu - Bakiye Bilgileri* 🎰\n\n"
        f"👤 *Kullanıcı:* {get_username(user_id)}\n"
        f"💰 *Bakiye:* `{format_amount(balance)}`\n"
        f"🏅 *Seviye:* `{level}`\n\n"
        f"📊 *İstatistikler:*\n"
        f"• 🎲 *Toplam Bahis:* `{total_bets}`\n"
        f"• 🏆 *En Yüksek Kazanç:* `{format_amount(max_win)}`\n"
        f"• 💹 *Toplam Kazanç:* `{format_amount(total_wins)}`\n"
        f"• 📉 *Toplam Kayıp:* `{format_amount(total_losses)}`\n"
        f"• 📈 *Kazanma Oranı:* `{win_rate:.2f}%`\n\n"
        f"🔮 *Tavsiye:* Bakiye yönetimi ve stratejik bahislerle kazanma şansınızı artırabilirsiniz!"
    )

    # Mesajı gönder
    bot.send_message(chat_id, balance_text, parse_mode="Markdown")

@bot.message_handler(commands=['level'])
def check_level(message):
    user_id = message.from_user.id
    balance = user_balances.get(user_id, 0)
    level = get_level(balance)

    # Bir sonraki seviye için gereken miktarı bul
    next_level_threshold = None
    for threshold, lvl in sorted(LEVELS.items()):
        if balance < threshold:
            next_level_threshold = threshold
            break

    # İlerleme yüzdesini hesapla
    if next_level_threshold:
        progress = (balance / next_level_threshold) * 100
    else:
        progress = 100  # En yüksek seviyede

    # Seviye bilgisi mesajı
    level_text = f"🎚️ *Seviye Bilgisi*\n\n"
    level_text += f"👤 Kullanıcı: {get_username(user_id)}\n"
    level_text += f"🏅 Mevcut Seviye: {level}\n"
    if next_level_threshold:
        level_text += f"📊 İlerleme: %{progress:.2f}\n"
        level_text += f"🔜 Sonraki Seviye: {next_level_threshold / 1e12:.2f}T 🪙 kazanmanız gerekiyor.\n"
    else:
        level_text += "🎉 Tebrikler! En yüksek seviyedesiniz.\n"

    # Seviye atlama ödülü kontrolü
    if user_id in daily_bonus:  # Eğer kullanıcı daha önce bonus aldıysa
        last_level = daily_bonus[user_id].get('last_level', None)
        if last_level != level:  # Eğer kullanıcı yeni bir seviyeye ulaştıysa
            bonus_amount = next_level_threshold * 0.1  # Ödül: Bir sonraki seviye eşiğinin %10'u
            user_balances[user_id] += bonus_amount
            level_text += f"\n🎁 *Tebrikler! Yeni seviyeye ulaştınız ve {format_amount(bonus_amount)} bonus kazandınız!* 🎁\n"
            daily_bonus[user_id]['last_level'] = level  # Son seviyeyi güncelle

    bot.send_message(message.chat.id, level_text, parse_mode="Markdown")

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

    game_id = str(uuid.uuid4())  # Benzersiz oyun ID'si oluştur
    active_games[chat_id] = game_id
    user_balances.setdefault(user_id, 10000000000)  # Varsayılan bakiye (10B 🪙)

    bot.send_message(chat_id, f"🎰 Rulet oyununa hoş geldiniz! Bakiyeniz: {format_amount(user_balances[user_id])}\nOyun ID: {game_id}")
    
    # Çark görselini gönder
    try:
        image_url = get_image_url("çark")
        wheel_message = bot.send_photo(chat_id, image_url)
    except Exception as e:
        bot.send_message(chat_id, "❌ Çark görseli bulunamadı.")
        del active_games[chat_id]
        return

    bets[game_id] = {}  # Bahisleri temizle
    bot.send_message(chat_id, "⏳ Bahis yapmak için 25 saniyeniz var!")

    # 25 saniye sonra roulette_game fonksiyonunu çağır
    Timer(25.0, roulette_game, args=[chat_id, game_id, wheel_message.message_id]).start()

# Yeşil bahis komutu
@bot.message_handler(commands=['green'])
def green_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    game_id = active_games.get(chat_id)
    if not game_id:
        bot.send_message(chat_id, "❌ Aktif bir rulet oyunu bulunmamaktadır. Lütfen önce /rulet komutu ile bir oyun başlatın.")
        return

    try:
        bet_amount = int(message.text.split()[1])
        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return
        user_balances[user_id] -= bet_amount
        bets[game_id].setdefault(user_id, []).append(('green', bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: 🟢 Yeşil için {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /green [bahis miktarı]")

# Kırmızı bahis komutu
@bot.message_handler(commands=['red'])
def red_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    game_id = active_games.get(chat_id)
    if not game_id:
        bot.send_message(chat_id, "❌ Aktif bir rulet oyunu bulunmamaktadır. Lütfen önce /rulet komutu ile bir oyun başlatın.")
        return

    try:
        bet_amount = int(message.text.split()[1])
        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return
        user_balances[user_id] -= bet_amount
        bets[game_id].setdefault(user_id, []).append(('red', bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: 🔴 Kırmızı için {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /red [bahis miktarı]")

# Siyah bahis komutu
@bot.message_handler(commands=['black'])
def black_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    game_id = active_games.get(chat_id)
    if not game_id:
        bot.send_message(chat_id, "❌ Aktif bir rulet oyunu bulunmamaktadır. Lütfen önce /rulet komutu ile bir oyun başlatın.")
        return

    try:
        bet_amount = int(message.text.split()[1])
        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return
        user_balances[user_id] -= bet_amount
        bets[game_id].setdefault(user_id, []).append(('black', bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: ⚫ Siyah için {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /black [bahis miktarı]")

# Tek sayı bahisi komutu
@bot.message_handler(commands=['number'])
def number_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    game_id = active_games.get(chat_id)
    if not game_id:
        bot.send_message(chat_id, "❌ Aktif bir rulet oyunu bulunmamaktadır. Lütfen önce /rulet komutu ile bir oyun başlatın.")
        return

    try:
        parts = message.text.split()
        bet_amount = int(parts[1])
        bet_number = parts[2]

        if bet_amount > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return

        if bet_number.isdigit() and 0 <= int(bet_number) <= 36:
            user_balances[user_id] -= bet_amount
            bets[game_id].setdefault(user_id, []).append((bet_number, bet_amount))
            bot.send_message(chat_id, f"💵 {get_username(user_id)}: {bet_number} numarasına {format_amount(bet_amount)} bahis yaptınız.")
        else:
            bot.send_message(chat_id, "❌ Geçersiz sayı. Lütfen 0-36 arasında bir sayı girin.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /number [bahis miktarı] [sayı]")

# Çoklu sayı bahisi komutu
@bot.message_handler(commands=['multinumber'])
def multinumber_bet(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    game_id = active_games.get(chat_id)
    if not game_id:
        bot.send_message(chat_id, "❌ Aktif bir rulet oyunu bulunmamaktadır. Lütfen önce /rulet komutu ile bir oyun başlatın.")
        return

    try:
        parts = message.text.split()
        bet_amount = int(parts[1])
        bet_numbers = parts[2:]

        if bet_amount * len(bet_numbers) > user_balances[user_id]:
            bot.send_message(chat_id, "❌ Yetersiz bakiye!")
            return

        invalid_numbers = [n for n in bet_numbers if not (n.isdigit() and 0 <= int(n) <= 36)]
        if invalid_numbers:
            bot.send_message(chat_id, f"❌ Geçersiz sayılar: {', '.join(invalid_numbers)}. Lütfen 0-36 arasında sayılar girin.")
            return

        for bet_number in bet_numbers:
            user_balances[user_id] -= bet_amount
            bets[game_id].setdefault(user_id, []).append((bet_number, bet_amount))
        bot.send_message(chat_id, f"💵 {get_username(user_id)}: {', '.join(bet_numbers)} numaralarına {format_amount(bet_amount)} bahis yaptınız.")
    except (IndexError, ValueError):
        bot.send_message(chat_id, "❌ Geçersiz komut. Kullanım: /multinumber [bahis miktarı] [sayı(lar)]")

# Rulet oyunu
def roulette_game(chat_id, game_id, wheel_message_id):
    global bets  # Global olarak deklarasyon

    # Çark görselini sil
    try:
        bot.delete_message(chat_id, wheel_message_id)
    except Exception as e:
        print("Çark görseli silinirken bir hata oluştu:", e)

    # Rulet sonucunu belirle
    result = random.choice([i for i in range(37)])
    result_color = roulette_colors[result]
    result_symbol = '🟢' if result_color == 'green' else '🔴' if result_color == 'red' else '⚫'

    # Kazananları ve kaybedenleri belirle
    winners = []
    losers = []
    for user_id, bets_list in bets.get(game_id, {}).items():
        total_winnings = 0
        total_losses = 0
        for bet in bets_list:
            bet_type, bet_amount = bet  # Bahis türü ve miktarı
            if isinstance(bet_type, list):  # Çoklu sayı bahsi
                if str(result) in bet_type:
                    winnings = bet_amount * 36
                    user_balances[user_id] += winnings
                    total_winnings += winnings
                else:
                    total_losses += bet_amount
            elif bet_type == str(result):  # Tek sayı bahsi
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
                winnings = bet_amount * 36
                user_balances[user_id] += winnings
                total_winnings += winnings
            else:
                total_losses += bet_amount

        # Kazanan ve kaybeden mesajlarını hazırla
        if total_winnings > 0:
            winners.append(f"✅ {get_username(user_id)}: {format_amount(total_winnings)} kazandı")
            statistics[user_id]['total_wins'] += total_winnings
            if total_winnings > statistics[user_id]['max_win']:
                statistics[user_id]['max_win'] = total_winnings
        if total_losses > 0:
            losers.append(f"❌ {get_username(user_id)}: {format_amount(total_losses)} kaybetti")
            statistics[user_id]['total_losses'] += total_losses

        statistics[user_id]['total_bets'] += len(bets_list)
        if statistics[user_id]['total_bets'] > 0:
            statistics[user_id]['win_rate'] = (statistics[user_id]['total_wins'] / statistics[user_id]['total_bets']) * 100

    # Sonuç mesajını hazırla
    result_message = f"🎰 *Rulet Sonucu* 🎰\n\n"
    result_message += f"🔢 **Sonuç:** {result_symbol} {result} ({result_color.capitalize()})\n\n"

    if winners:
        result_message += "🏆 **Kazananlar:**\n" + "\n".join(winners) + "\n\n"
    if losers:
        result_message += "😢 **Kaybedenler:**\n" + "\n".join(losers)

        # Kazanan sayının görselini ve sonuç mesajını gönder
    try:
        image_url = get_image_url(result)  # Kazanan sayının görsel URL'si
        bot.send_photo(chat_id, image_url, caption=result_message, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, "❌ Görsel yüklenirken bir hata oluştu.")

    # Bahisleri temizle ve aktif oyunları güncelle
    del bets[game_id]
    del active_games[chat_id]
@bot.message_handler(commands=['leaderboard'])
def leaderboard(message):
    if not user_balances:
        bot.send_message(message.chat.id, "Henüz hiç kullanıcı yok!", parse_mode="Markdown")
        return

    # Kullanıcıları bakiye sırasına göre sırala
    sorted_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)
    top_users = sorted_users[:10]  # İlk 10 kullanıcıyı al

    # Liderlik tablosu başlığı
    leaderboard_text = "🏆 *Liderlik Tablosu* 🏆\n\n"
    leaderboard_text += "🌟 *En Zengin Oyuncular* 🌟\n\n"

    # İlk 3 kullanıcı için özel gösterişli rakamlar
    if len(top_users) >= 1:
        user_id, balance = top_users[0]
        username = get_username(user_id)
        level = get_level(balance)
        leaderboard_text += (
            f"🥇 🆔 [{username}](tg://user?id={user_id}) - `{format_amount(balance)}`\n"
            f"   🏅 Seviye: *{level}*\n\n"
        )

    if len(top_users) >= 2:
        user_id2, balance2 = top_users[1]
        username2 = get_username(user_id2)
        level2 = get_level(balance2)
        leaderboard_text += (
            f"🥈 🆔 [{username2}](tg://user?id={user_id2}) - `{format_amount(balance2)}`\n"
            f"   🏅 Seviye: *{level2}*\n\n"
        )

    if len(top_users) >= 3:
        user_id3, balance3 = top_users[2]
        username3 = get_username(user_id3)
        level3 = get_level(balance3)
        leaderboard_text += (
            f"🥉 🆔 [{username3}](tg://user?id={user_id3}) - `{format_amount(balance3)}`\n"
            f"   🏅 Seviye: *{level3}*\n\n"
        )

    # Diğer kullanıcılar (4'ten 10'a kadar)
    for i, (user_id, balance) in enumerate(top_users[3:], start=4):
        username = get_username(user_id)
        level = get_level(balance)
        leaderboard_text += (
            f"{i}️⃣ 🆔 [{username}](tg://user?id={user_id}) - `{format_amount(balance)}`\n"
            f"   🏅 Seviye: *{level}*\n\n"
        )

    # Alt bilgi
    leaderboard_text += "🔝 Daha yükseğe çıkmak için rulet oynamaya devam edin!"

    # Mesajı gönder (Markdown formatında)
    bot.send_message(message.chat.id, leaderboard_text, parse_mode="Markdown")
# Yardım komutu
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "🎰 *Rulet Botu Komutları* 🎰\n\n"
        "/start - Botu başlatır ve kayıt olmanızı sağlar.\n"
        "/changename [yeni isim] - İsminizi değiştirir.\n"
        "/balance - Bakiyenizi ve istatistiklerinizi gösterir.\n"
        "/rulet - Rulet oyununu başlatır.\n"
        "/moneys [miktar] - Yanıtladığınız kullanıcıya para gönderir.\n"
        "/green [miktar] - Yeşile bahis yapar.\n"
        "/red [miktar] - Kırmızıya bahis yapar.\n"
        "/black [miktar] - Siyaha bahis yapar.\n"
        "/number [miktar] [sayı] - Belirli bir sayıya bahis yapar.\n"
        "/multinumber [miktar] [sayı(lar)] - Birden fazla sayıya bahis yapar.\n"
        "/leaderboard - Liderlik tablosunu gösterir.\n"
        "/daily - Günlük bonusunuzu alın.\n"
        "/level - Mevcut seviyenizi ve bir sonraki seviyeye ne kadar kaldığını gösterir.\n"
        "/help - Tüm komutları ve nasıl kullanılacaklarını gösterir."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# Botu çalıştır
bot.polling()
