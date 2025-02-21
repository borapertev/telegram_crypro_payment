import os
import logging
import aiohttp
from datetime import datetime, timedelta
import secrets
import json

# Loglama ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ManualUSDTProcessor:
    def __init__(self):
        self.minimum_payment = float(os.getenv('MINIMUM_PAYMENT_USD', 30))
        self.subscription_days = int(os.getenv('SUBSCRIPTION_DAYS', 30))
        self.wallet_address = os.getenv('USDT_WALLET_ADDRESS', 'YOUR_WALLET_ADDRESS')
        self.pending_payments = {}  # payment_id -> payment_info

    async def create_payment(self, user_id: int, username: str) -> dict:
        """Yeni bir ödeme oluştur"""
        try:
            # Benzersiz bir ödeme ID'si oluştur
            payment_id = secrets.token_hex(12)
            
            # Ödeme bilgilerini kaydet
            payment_info = {
                'user_id': user_id,
                'username': username,
                'amount': self.minimum_payment,
                'payment_id': payment_id,
                'status': 'pending',
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=20)
            }
            
            self.pending_payments[payment_id] = payment_info
            
            return {
                'payment_id': payment_id,
                'wallet_address': self.wallet_address,
                'amount': self.minimum_payment,
                'currency': 'USDT (TRC-20)',
                'expires_at': payment_info['expires_at']
            }
            
        except Exception as e:
            logger.error(f"Ödeme oluşturma hatası: {str(e)}", exc_info=True)
            return None

    def check_payment_status(self, payment_id: str) -> dict:
        """Ödeme durumunu kontrol et"""
        if payment_id in self.pending_payments:
            payment = self.pending_payments[payment_id]
            if datetime.now() > payment['expires_at']:
                payment['status'] = 'expired'
            return {
                'status': payment['status'],
                'expires_at': payment['expires_at']
            }
        return {'status': 'not_found'}

class NowPaymentsProcessor:
    def __init__(self):
        self.api_key = os.getenv('NOWPAYMENTS_API_KEY')
        self.api_url = os.getenv('NOWPAYMENTS_API_URL', 'https://api.nowpayments.io/v1')
        self.headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        logger.info(f"NowPayments API URL: {self.api_url}")

    async def create_payment(self, amount_usd: float) -> dict:
        """Yeni bir ödeme oluştur"""
        try:
            logger.info(f"Ödeme oluşturma başlatıldı - Miktar: {amount_usd} USD")
            
            # Önce fiyat tahmini al
            async with aiohttp.ClientSession() as session:
                estimate_url = f"{self.api_url}/estimate"
                logger.info(f"Fiyat tahmini alınıyor: {estimate_url}")
                
                async with session.get(
                    estimate_url,
                    headers=self.headers,
                    params={
                        "amount": str(amount_usd),
                        "currency_from": "usd",
                        "currency_to": "btc"
                    }
                ) as response:
                    estimate_response = await response.text()
                    logger.info(f"Fiyat tahmini yanıtı: {estimate_response}")
                    
                    if response.status == 200:
                        estimate_data = json.loads(estimate_response)
                        estimated_amount = estimate_data.get('estimated_amount')
                        logger.info(f"Tahmini BTC miktarı: {estimated_amount}")
                    else:
                        logger.error(f"Fiyat tahmini hatası: {estimate_response}")
                        return {
                            'success': False,
                            'error': 'Fiyat tahmini alınamadı'
                        }

            # Ödeme oluştur
            payment_id = secrets.token_hex(8)
            payment_data = {
                "price_amount": str(amount_usd),
                "price_currency": "usd",
                "pay_currency": "btc",
                "order_id": payment_id,
                "order_description": "Telegram Grup Erişimi",
                "case": "success"
            }
            logger.info(f"Ödeme isteği gönderiliyor: {json.dumps(payment_data)}")
            
            async with aiohttp.ClientSession() as session:
                payment_url = f"{self.api_url}/payment"
                logger.info(f"Ödeme URL: {payment_url}")
                
                async with session.post(
                    payment_url,
                    headers=self.headers,
                    json=payment_data
                ) as response:
                    payment_response = await response.text()
                    logger.info(f"Ödeme yanıtı: {payment_response}")
                    
                    if response.status == 201:
                        data = json.loads(payment_response)
                        expires_at = datetime.now() + timedelta(minutes=20)
                        result = {
                            'success': True,
                            'payment_id': data.get('payment_id'),
                            'wallet_address': data.get('pay_address'),
                            'amount_btc': data.get('pay_amount'),
                            'amount_usd': amount_usd,
                            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S')
                        }
                        logger.info(f"Ödeme başarıyla oluşturuldu: {json.dumps(result)}")
                        return result
                    else:
                        logger.error(f"Ödeme oluşturma hatası: {payment_response}")
                        error_msg = json.loads(payment_response).get('message', 'Ödeme oluşturulamadı')
                        return {
                            'success': False,
                            'error': error_msg
                        }
        except Exception as e:
            logger.error(f"Ödeme oluşturma hatası: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Bir hata oluştu'
            }

    async def check_payment(self, payment_id: str) -> dict:
        """Ödeme durumunu kontrol et"""
        try:
            logger.info(f"Ödeme kontrolü başlatıldı - Payment ID: {payment_id}")
            
            async with aiohttp.ClientSession() as session:
                payment_url = f"{self.api_url}/payment/{payment_id}"
                logger.info(f"Ödeme kontrol URL: {payment_url}")
                
                async with session.get(
                    payment_url,
                    headers=self.headers
                ) as response:
                    payment_response = await response.text()
                    logger.info(f"Ödeme kontrol yanıtı: {payment_response}")
                    
                    if response.status == 200:
                        data = json.loads(payment_response)
                        result = {
                            'success': True,
                            'status': data.get('payment_status'),
                            'paid': data.get('payment_status') in ['confirmed', 'finished', 'partially_paid'],
                            'amount_btc': data.get('pay_amount'),
                            'amount_usd': data.get('price_amount'),
                            'actual_amount': data.get('actually_paid'),
                            'created_at': data.get('created_at'),
                            'updated_at': data.get('updated_at')
                        }
                        logger.info(f"Ödeme durumu alındı: {json.dumps(result)}")
                        return result
                    else:
                        logger.error(f"Ödeme kontrol hatası: {payment_response}")
                        error_msg = json.loads(payment_response).get('message', 'Ödeme bulunamadı')
                        return {
                            'success': False,
                            'error': error_msg
                        }
        except Exception as e:
            logger.error(f"Ödeme kontrol hatası: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Bir hata oluştu'
            }
