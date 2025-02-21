import sqlite3
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = 'crypto_payment.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Veritabanı tablolarını oluştur"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Kullanıcılar tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    subscription_start_date TEXT,
                    subscription_end_date TEXT,
                    created_at TEXT
                )
            ''')
            
            # Ödemeler tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    telegram_id INTEGER,
                    amount REAL,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
                )
            ''')
            
            conn.commit()

    def _connect(self):
        """Veritabanı bağlantısı oluştur"""
        return sqlite3.connect(self.db_name)

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Kullanıcı bilgilerini getir"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM users WHERE telegram_id = ?',
                    (telegram_id,)
                )
                user = cursor.fetchone()
                
                if user:
                    return {
                        'telegram_id': user[0],
                        'username': user[1],
                        'subscription_start_date': user[2],
                        'subscription_end_date': user[3],
                        'created_at': user[4]
                    }
                return None
        except Exception as e:
            logger.error(f"Kullanıcı bilgisi alınırken hata: {e}")
            return None

    def update_subscription(self, telegram_id: int, username: str, days: int) -> bool:
        """Kullanıcı aboneliğini güncelle veya oluştur"""
        try:
            now = datetime.now()
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Mevcut kullanıcıyı kontrol et
                user = self.get_user(telegram_id)
                
                if user:
                    # Mevcut abonelik varsa üzerine ekle
                    current_end = datetime.fromisoformat(user['subscription_end_date']) \
                        if user['subscription_end_date'] else now
                    
                    if current_end < now:
                        current_end = now
                    
                    new_end = current_end + timedelta(days=days)
                    
                    cursor.execute('''
                        UPDATE users 
                        SET username = ?,
                            subscription_end_date = ?
                        WHERE telegram_id = ?
                    ''', (username, new_end.isoformat(), telegram_id))
                else:
                    # Yeni kullanıcı oluştur
                    end_date = now + timedelta(days=days)
                    cursor.execute('''
                        INSERT INTO users (
                            telegram_id, username,
                            subscription_start_date,
                            subscription_end_date,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        telegram_id, username,
                        now.isoformat(),
                        end_date.isoformat(),
                        now.isoformat()
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Abonelik güncellenirken hata: {e}")
            return False

    def add_payment(self, payment_id: str, telegram_id: int,
                   amount: float, status: str = 'pending') -> bool:
        """Yeni ödeme kaydı ekle"""
        try:
            now = datetime.now().isoformat()
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments (
                        payment_id, telegram_id, amount,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (payment_id, telegram_id, amount, status, now))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ödeme eklenirken hata: {e}")
            return False

    def update_payment_status(self, payment_id: str,
                            status: str, completed_at: str = None) -> bool:
        """Ödeme durumunu güncelle"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                if completed_at:
                    cursor.execute('''
                        UPDATE payments
                        SET status = ?, completed_at = ?
                        WHERE payment_id = ?
                    ''', (status, completed_at, payment_id))
                else:
                    cursor.execute('''
                        UPDATE payments
                        SET status = ?
                        WHERE payment_id = ?
                    ''', (status, payment_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ödeme durumu güncellenirken hata: {e}")
            return False

    def get_expired_subscriptions(self) -> list:
        """Süresi dolmuş abonelikleri getir"""
        try:
            now = datetime.now().isoformat()
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT telegram_id, username, subscription_end_date
                    FROM users
                    WHERE subscription_end_date < ?
                ''', (now,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Süresi dolmuş abonelikler alınırken hata: {e}")
            return []
