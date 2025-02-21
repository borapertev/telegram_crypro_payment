import os
import logging
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, JobQueue
from payment_processor import NowPaymentsProcessor
import html
import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Loglama ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

# Global değişkenler
payment_processor = NowPaymentsProcessor()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot başlatıldığında çalışacak komut"""
    keyboard = [
        [InlineKeyboardButton("💰 Ödeme Yap", callback_data='payment')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 Telegram VIP Grup Üyelik Botu\n\n"
        "💎 VIP Gruba 30 günlük erişim için:\n"
        "1. 'Ödeme Yap' butonuna tıklayın\n"
        "2. Belirtilen BTC adresine ödemeyi yapın\n"
        "3. Ödeme sonrası otomatik olarak gruba ekleneceksiniz\n"
        "4. Üyeliğiniz 30 gün boyunca aktif kalacak\n\n"
        "💡 Ödeme sonrası grup bağlantısı otomatik gönderilecektir.\n"
        "❓ Sorun yaşarsanız /help yazabilirsiniz.",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yardım komutu"""
    await update.message.reply_text(
        "📚 Komut Listesi:\n\n"
        "/start - Botu başlat\n"
        "/payment - Ödeme yap\n"
        "/check_payment <payment_id> - Ödeme durumunu kontrol et\n"
        "/help - Bu yardım mesajını göster"
    )

async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ödeme başlatma komutu"""
    keyboard = [
        [InlineKeyboardButton("💳 Ödeme Bilgilerini Al", callback_data='get_payment_info')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💰 Bitcoin (BTC) ile Ödeme\n\n"
        f"💵 Ödeme Tutarı: ${os.getenv('MINIMUM_PAYMENT_USD')} USD\n"
        "⏱ Süre: 20 dakika\n"
        "🔗 Ağ: Bitcoin Network\n\n"
        "📝 Ödeme bilgilerini almak için aşağıdaki butona tıklayın:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Buton callback işleyicisi"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'payment':
        keyboard = [
            [InlineKeyboardButton("💳 Ödeme Bilgilerini Al", callback_data='get_payment_info')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "💰 Bitcoin (BTC) ile Ödeme\n\n"
            f"💵 Ödeme Tutarı: ${os.getenv('MINIMUM_PAYMENT_USD')} USD\n"
            "⏱ Süre: 20 dakika\n"
            "🔗 Ağ: Bitcoin Network\n\n"
            "📝 Ödeme bilgilerini almak için aşağıdaki butona tıklayın:",
            reply_markup=reply_markup
        )
    
    elif query.data == 'get_payment_info':
        try:
            amount = float(os.getenv('MINIMUM_PAYMENT_USD'))
            result = await payment_processor.create_payment(amount)
            
            if result['success']:
                context.user_data['payment_id'] = result['payment_id']
                message = (
                    f"🔹 Ödeme Bilgileri:\n\n"
                    f"💵 Tutar: ${result['amount_usd']} USD\n"
                    f"₿ BTC Miktarı: {result['amount_btc']} BTC\n"
                    f"📝 Ödeme ID: `{result['payment_id']}`\n"
                    f"🏦 Bitcoin Cüzdan Adresi:\n`{result['wallet_address']}`\n\n"
                    f"❗️ Önemli Notlar:\n"
                    f"• Tam olarak {result['amount_btc']} BTC gönderiniz\n"
                    f"• Bitcoin ağını kullanın\n"
                    f"• Ödeme ID'nizi saklayın\n"
                    f"• Ödeme sonrası /check_payment komutunu kullanın"
                )
                
                await query.message.reply_text(
                    text=message,
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text(
                    "❌ Ödeme bilgileri oluşturulurken bir hata oluştu.\n"
                    f"Hata: {result.get('error', 'Bilinmeyen hata')}"
                )
        except Exception as e:
            logging.error(f"Ödeme oluşturma hatası: {str(e)}")
            await query.message.reply_text(
                "❌ Bir hata oluştu. Lütfen daha sonra tekrar deneyin."
            )

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ Lütfen ödeme ID'nizi girin.\n"
            "Örnek: /check_payment <payment_id>"
        )
        return
    
    payment_id = args[0]
    result = await payment_processor.check_payment(payment_id)
    
    if result['success'] and result['paid']:
        user_id = update.effective_user.id
        
        try:
            # Kullanıcıyı veritabanına ekle
            add_member(user_id)
            
            await update.message.reply_text(
                "✅ Ödemeniz onaylandı!\n\n"
                "Gruba katılmak için aşağıdaki bağlantıyı kullanın:\n"
                f"{os.getenv('TELEGRAM_GROUP_INVITE_LINK')}\n\n"
                "⚠️ Üyeliğiniz 30 gün boyunca aktif kalacaktır.\n"
                "📅 Süre sonunda otomatik olarak gruptan çıkarılacaksınız."
            )
            
        except Exception as e:
            logging.error(f"Üye ekleme hatası: {str(e)}")
            await update.message.reply_text(
                "✅ Ödemeniz onaylandı fakat bir hata oluştu.\n"
                "Lütfen yönetici ile iletişime geçin."
            )
    else:
        await update.message.reply_text(
            "❌ Ödeme bulunamadı veya henüz onaylanmadı.\n"
            "Lütfen birkaç dakika bekleyip tekrar deneyin."
        )

async def create_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()  # Önce callback'i yanıtlayalım
        
        payment_processor = NowPaymentsProcessor()
        result = await payment_processor.create_payment(float(os.getenv('MINIMUM_PAYMENT_USD')))
        
        if result and result.get('success'):
            text = f"Adres: {result['wallet_address']}\nMiktar: {result['amount_btc']} BTC"
            
            keyboard = [[
                InlineKeyboardButton(
                    "Kontrol", 
                    callback_data=f"check_{result['payment_id']}"
                )
            ]]
            
            try:
                # Yeni mesaj gönderme denemesi
                await query.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as msg_error:
                logging.error(f"Mesaj gönderme hatası: {msg_error}")
                # Alternatif mesaj gönderme denemesi
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await query.message.reply_text("Ödeme oluşturulamadı")
            
    except Exception as e:
        logging.error(f"Ödeme hatası: {e}")
        try:
            await update.effective_chat.send_message("Hata oluştu")
        except:
            pass

async def test_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sadece adminler için test komutu"""
    try:
        # Admin kontrolü
        admin_id = os.getenv('ADMIN_ID')
        user_id = str(update.effective_user.id)
        
        logging.info(f"Test komutu çalıştırıldı - User ID: {user_id}, Admin ID: {admin_id}")
        
        if user_id != admin_id:
            logging.warning(f"Yetkisiz test denemesi - User ID: {user_id}")
            await update.message.reply_text("Bu komut sadece yöneticiler içindir.")
            return
        
        # Test mesajı
        text = (
            "🧪 TEST MODU\n\n"
            "Adres: TEST_BTC_ADDRESS\n"
            "Miktar: 0.001 BTC"
        )
        
        keyboard = [[
            InlineKeyboardButton(
                "Test Kontrol", 
                callback_data="test_check"
            )
        ]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mesajı gönder
        sent_message = await update.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )
        
        logging.info(f"Test mesajı gönderildi - Message ID: {sent_message.message_id}")
        
    except Exception as e:
        logging.error(f"Test hatası: {str(e)}", exc_info=True)
        await update.message.reply_text(f"Test sırasında hata oluştu: {str(e)}")

async def test_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test ödeme kontrolü için callback"""
    try:
        query = update.callback_query
        await query.answer()
        
        group_id = os.getenv('TELEGRAM_GROUP_ID')
        user_id = update.effective_user.id
        
        logging.info(f"Test kontrol başladı - User ID: {user_id}, Group ID: {group_id}")
        
        try:
            # Kullanıcıyı veritabanına ekle
            add_member(user_id)
            
            await query.message.reply_text(
                "✅ Test başarılı!\n\n"
                "Gruba katılmak için aşağıdaki bağlantıyı kullanın:\n"
                f"{os.getenv('TELEGRAM_GROUP_INVITE_LINK')}\n\n"
                "⚠️ Üyeliğiniz 30 gün boyunca aktif kalacaktır.\n"
                "📅 Süre sonunda otomatik olarak gruptan çıkarılacaksınız."
            )
            
        except Exception as group_error:
            logging.error(f"Grup işlemi hatası: {str(group_error)}")
            await query.message.reply_text(
                "⚠️ Bir hata oluştu.\n"
                "Lütfen grup yöneticisi ile iletişime geçin."
            )
            return
        
        logging.info(f"Test kontrol başarılı - User ID: {user_id}")
        
    except Exception as e:
        logging.error(f"Test kontrol hatası: {str(e)}", exc_info=True)
        await query.message.reply_text(
            "❌ Test sırasında hata oluştu.\n"
            "Lütfen daha sonra tekrar deneyin."
        )

# Mesaj gönderme fonksiyonunu güvenli hale getirme
def send_safe_message(bot, chat_id, text):
    try:
        # HTML parse_mode kullanarak ve karakterleri escape ederek gönder
        escaped_text = html.escape(text)
        return bot.send_message(
            chat_id=chat_id,
            text=escaped_text,
            parse_mode='HTML'
        )
    except Exception as e:
        # Hata durumunda parse_mode olmadan tekrar dene
        return bot.send_message(
            chat_id=chat_id,
            text=text
        )

# Veritabanı işlemleri için yardımcı fonksiyonlar
def init_db():
    """Veritabanını oluştur"""
    conn = sqlite3.connect('members.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT,
            expire_date TEXT,
            is_active INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_member(user_id: int):
    """Yeni üye ekle"""
    conn = sqlite3.connect('members.db')
    c = conn.cursor()
    
    join_date = datetime.now()
    expire_date = join_date + timedelta(days=30)
    
    c.execute('''
        INSERT OR REPLACE INTO members (user_id, join_date, expire_date, is_active)
        VALUES (?, ?, ?, ?)
    ''', (user_id, join_date.isoformat(), expire_date.isoformat(), 1))
    
    conn.commit()
    conn.close()

async def check_expired_members(context: ContextTypes.DEFAULT_TYPE):
    """Süresi dolan üyelikleri kontrol et"""
    try:
        conn = sqlite3.connect('members.db')
        c = conn.cursor()
        
        now = datetime.now()
        
        # Süresi dolan aktif üyeleri bul
        c.execute('''
            SELECT user_id FROM members 
            WHERE expire_date < ? AND is_active = 1
        ''', (now.isoformat(),))
        
        expired_members = c.fetchall()
        
        for member in expired_members:
            user_id = member[0]
            try:
                # Veritabanında pasif yap
                c.execute('''
                    UPDATE members SET is_active = 0
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Kullanıcıya bildirim gönder
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="⚠️ VIP üyelik süreniz dolmuştur. Yenilemek için /start komutunu kullanabilirsiniz."
                    )
                except:
                    logging.warning(f"Kullanıcıya mesaj gönderilemedi: {user_id}")
                
                logging.info(f"Üyelik süresi dolan kullanıcı pasif yapıldı: {user_id}")
                
            except Exception as e:
                logging.error(f"Üye işlemi hatası - User ID: {user_id}, Hata: {str(e)}")
        
        conn.commit()
        
    except Exception as e:
        logging.error(f"Üyelik kontrolü hatası: {str(e)}")
    finally:
        conn.close()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Üyelik durumunu kontrol et"""
    try:
        user_id = update.effective_user.id
        conn = sqlite3.connect('members.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT join_date, expire_date, is_active 
            FROM members 
            WHERE user_id = ?
        ''', (user_id,))
        
        member = c.fetchone()
        
        if member:
            join_date = datetime.fromisoformat(member[0])
            expire_date = datetime.fromisoformat(member[1])
            is_active = member[2]
            
            remaining_days = (expire_date - datetime.now()).days
            
            if is_active and remaining_days > 0:
                await update.message.reply_text(
                    f"✅ VIP üyeliğiniz aktif!\n\n"
                    f"📅 Başlangıç: {join_date.strftime('%d.%m.%Y')}\n"
                    f"⏳ Kalan süre: {remaining_days} gün\n"
                    f"📌 Bitiş: {expire_date.strftime('%d.%m.%Y')}"
                )
            else:
                await update.message.reply_text(
                    "❌ VIP üyeliğiniz aktif değil.\n"
                    "Yenilemek için /start komutunu kullanabilirsiniz."
                )
        else:
            await update.message.reply_text(
                "❌ VIP üyelik kaydınız bulunmamaktadır.\n"
                "Üyelik için /start komutunu kullanabilirsiniz."
            )
            
    except Exception as e:
        logging.error(f"Durum kontrolü hatası: {str(e)}")
        await update.message.reply_text("Durum kontrolü sırasında bir hata oluştu.")
    finally:
        conn.close()

def main() -> None:
    """Bot başlatma fonksiyonu"""
    # Daha uzun timeout değerleri ile application oluştur
    application = (
        Application.builder()
        .token(os.getenv('TELEGRAM_BOT_TOKEN'))
        .connect_timeout(30.0)  # 30 saniye
        .read_timeout(30.0)     # 30 saniye
        .write_timeout(30.0)    # 30 saniye
        .build()
    )
    
    # Komut işleyicileri
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("payment", payment))
    application.add_handler(CommandHandler("check_payment", check_payment))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^payment$'))
    application.add_handler(CallbackQueryHandler(create_payment, pattern='^get_payment_info$'))
    application.add_handler(CallbackQueryHandler(check_payment, pattern='^check_[0-9]+$'))
    application.add_handler(CallbackQueryHandler(test_check_callback, pattern='^test_check$'))
    
    # Test komutu
    application.add_handler(CommandHandler("test", test_payment))
    
    # Üyelik durumunu kontrol et komutu
    application.add_handler(CommandHandler("status", status_command))
    
    # Üyelik kontrolü için komut ekle
    application.add_handler(CommandHandler("check_expired", check_expired_members))
    
    # Veritabanını başlat
    init_db()
    
    # Job queue ayarları
    if application.job_queue:
        # Her 24 saatte bir kontrol
        application.job_queue.run_repeating(
            check_expired_members,
            interval=timedelta(hours=24),
            first=timedelta(minutes=1)
        )
        logging.info("Job queue başarıyla başlatıldı")
    else:
        logging.warning("Job queue başlatılamadı!")
    
    # Botu başlat
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        pool_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0
    )

if __name__ == '__main__':
    main()
