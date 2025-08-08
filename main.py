import os
import time
from telegram import Bot
import requests

# 환경변수로부터 토큰, 챗 ID 불러오기
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = Bot(token=TOKEN)

# 감시할 코인 리스트 및 심볼 (빙엑스 API 예시)
COINS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT']

# 빙엑스 API에서 가격 데이터 받아오는 함수 (예시)
def fetch_price(symbol):
    url = f'https://api.bingx.com/api/v1/market/ticker?symbol={symbol}'
    response = requests.get(url)
    data = response.json()
    return float(data['data']['lastPrice'])

# ATR 계산 함수 (간단화한 버전)
def calculate_atr(prices, length=1):
    if len(prices) < length + 1:
        return 0
    trs = []
    for i in range(1, length + 1):
        tr = abs(prices[-i] - prices[-i - 1])
        trs.append(tr)
    return sum(trs) / length

# CE 신호 판단 함수 (간략화)
def check_chandelier_exit(prices, atr_mult=2):
    highest = max(prices)
    atr = calculate_atr(prices, length=1)
    long_stop = highest - atr_mult * atr
    last_price = prices[-1]
    if last_price > long_stop:
        return 'LONG'
    else:
        return 'SHORT'

def main():
    price_history = {coin: [] for coin in COINS}
    alert_state = {coin: None for coin in COINS}

    while True:
        for coin in COINS:
            price = fetch_price(coin)
            price_history[coin].append(price)

            # 최근 22개 가격만 유지
            if len(price_history[coin]) > 22:
                price_history[coin].pop(0)

            if len(price_history[coin]) >= 2:
                signal = check_chandelier_exit(price_history[coin])
                if alert_state[coin] != signal:
                    alert_state[coin] = signal
                    message = f'[{coin}] Chandelier Exit 신호: {signal}\n현재가: {price}'
                    bot.send_message(chat_id=CHAT_ID, text=message)
                    print(message)
        time.sleep(300)  # 5분 간격

if __name__ == '__main__':
    main()
