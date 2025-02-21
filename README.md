# Telegram Kripto Ödeme Botu

Bu bot, kullanıcıların kripto para ile ödeme yaparak özel bir Telegram grubuna katılmalarını sağlar. Coinbase Commerce API kullanılarak güvenli ödeme işlemleri gerçekleştirilir.

## Özellikler

- Coinbase üzerinden güvenli kripto para ödemeleri
- 30 günlük otomatik abonelik sistemi
- Çoklu kripto para desteği (BTC, ETH, USDC)
- Otomatik grup davet sistemi
- Abonelik süresi takibi
- SQLite veritabanı ile veri yönetimi

## Gereksinimler

- Python 3.8+
- Telegram Bot Token
- Coinbase Commerce API Anahtarları
- Özel Telegram Grup ID'si

## Kurulum

1. Repository'yi klonlayın:
```bash
git clone https://github.com/username/telegram_crypto_payment.git
cd telegram_crypto_payment
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. `.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```

4. `.env` dosyasını düzenleyin:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_GROUP_ID=your_group_id
COINBASE_API_KEY=your_api_key
COINBASE_API_SECRET=your_api_secret
```

5. Bot'u çalıştırın:
```bash
python bot.py
```

## Kullanım

Bot aşağıdaki komutları destekler:

- `/start` - Bot'u başlat ve bilgi al
- `/payment` - Yeni ödeme oluştur
- `/help` - Yardım menüsünü görüntüle

## Güvenlik

- Tüm API anahtarları `.env` dosyasında saklanır
- SQLite veritabanı kullanılır
- Coinbase güvenli ödeme altyapısı
- Otomatik süre kontrolleri

## Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.