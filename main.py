import requests
import pandas as pd
from telegram import Bot
import time
from datetime import datetime

# ================== 직접 입력하세요 ==================
TELEGRAM_TOKEN = "8214918290:AAGM9H4CAfAo4_LlOzXDDs9ne4IUSX4o70c"
TELEGRAM_CHAT_ID = "7640801313"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "ADAUSDT"]
INTERVAL = "5m"
CE_PERIOD = 1
CE_MULTIPLIER = 2
# ======================================================

bot = Bot(token=TELEGRAM_TOKEN)

def send_signal_message(symbol, signal_type, close_price, stop_loss):
    emoji = "📈" if signal_type == "롱" else "📉"
    message = (
        f"{emoji} {symbol} {signal_type} 신호 발생!\n"
        f"종가: {close_price:.4f} USDT\n"
        f"손절선: {stop_loss:.4f} USDT\n\n"
        "안전한 매매를 위해 신호를 확인하시고 대응 바랍니다."
    )
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        print(f"텔레그램 알림 전송 성공: {signal_type} 신호 - {symbol}")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def get_binance_klines(symbol, interval, limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
        ])
        # Convert to proper types
        df["open_time"] = pd.to_datetime(df["open_time"], unit='ms')
        df["close_time"] = pd.to_datetime(df["close_time"], unit='ms')
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df
    except Exception as e:
        print(f"[{symbol}] 캔들 데이터 가져오기 실패: {e}")
        return None

def chandelier_exit(df, period=1, multiplier=2):
    # ATR 계산
    high = df['high']
    low = df['low']
    close = df['close']

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()

    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()

    long_stop = highest_high - (atr * multiplier)
    short_stop = lowest_low + (atr * multiplier)

    return long_stop, short_stop

def check_signals(df, long_stop, short_stop):
    signals = []
    close = df['close']
    for i in range(1, len(df)):
        prev_close = close.iloc[i-1]
        curr_close = close.iloc[i]
        prev_long_stop = long_stop.iloc[i-1]
        curr_long_stop = long_stop.iloc[i]
        prev_short_stop = short_stop.iloc[i-1]
        curr_short_stop = short_stop.iloc[i]

        # 롱 신호 : 종가가 롱 손절선 아래에서 위로 돌파
        if prev_close < prev_long_stop and curr_close > curr_long_stop:
            signals.append(("롱", curr_close, curr_long_stop))

        # 숏 신호 : 종가가 숏 손절선 위에서 아래로 돌파
        elif prev_close > prev_short_stop and curr_close < curr_short_stop:
            signals.append(("숏", curr_close, curr_short_stop))

    return signals

def main_loop():
    print("BingX->Binance CE 지표 알림 봇 시작")
    while True:
        for symbol in SYMBOLS:
            df = get_binance_klines(symbol, INTERVAL)
            if df is None or len(df) < CE_PERIOD + 2:
                print(f"[{symbol}] 데이터 부족 또는 오류")
                continue

            long_stop, short_stop = chandelier_exit(df, period=CE_PERIOD, multiplier=CE_MULTIPLIER)
            signals = check_signals(df, long_stop, short_stop)

            for signal_type, close_price, stop_loss in signals:
                send_signal_message(symbol, signal_type, close_price, stop_loss)

        print(f"전체 심볼 순환 완료 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(5 * 60)  # 5분 대기

if __name__ == "__main__":
    main_loop()
