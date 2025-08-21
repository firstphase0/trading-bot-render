# Strategy module implementing enhanced logic and backtest for accurate evaluation.
import logging, traceback
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class Position:
    entry_index: int
    entry_price: float
    size: float
    stop_price: float
    take_price: Optional[float]
    direction: int

def ensure_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'ema21' not in df.columns:
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    if 'ema50' not in df.columns:
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    if 'atr' not in df.columns:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14, min_periods=1).mean()
    if 'rsi' not in df.columns:
        delta = df['close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.ewm(span=14, adjust=False).mean()
        ma_down = down.ewm(span=14, adjust=False).mean()
        rs = ma_up / (ma_down + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))
    if 'vol_avg' not in df.columns:
        df['vol_avg'] = df['volume'].rolling(20, min_periods=1).mean()
    return df

def enhanced_strategy_logic(df: pd.DataFrame,
                            i: int,
                            higher_tf_close: Optional[float] = None,
                            config: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, float]]:
    try:
        cfg = {
            'ema_fast': 'ema21',
            'ema_slow': 'ema50',
            'rsi_low': 30,
            'rsi_high': 70,
            'min_vol_mult': 1.1,
            'atr_stop_mult': 1.5,
            'atr_take_mult': 3.0,
            'trend_weight': 0.4,
            'rsi_weight': 0.15,
            'vol_weight': 0.15,
            'candle_weight': 0.2,
            'min_confidence': 0.5,
        }
        if config:
            cfg.update(config)

        row = df.iloc[i]
        prev = df.iloc[i-1]

        signal = 0
        confidence = 0.0

        # Trend filter
        ema_fast = row[cfg['ema_fast']]
        ema_slow = row[cfg['ema_slow']]
        trend_long = row['close'] > ema_fast > ema_slow
        trend_short = row['close'] < ema_fast < ema_slow
        if trend_long:
            confidence += cfg['trend_weight']
        if trend_short:
            confidence += cfg['trend_weight']

        # RSI
        if row['rsi'] < cfg['rsi_low']:
            confidence += cfg['rsi_weight']
        if row['rsi'] > cfg['rsi_high']:
            confidence += cfg['rsi_weight']

        # Volume spike
        if row['volume'] > cfg['min_vol_mult'] * row['vol_avg']:
            confidence += cfg['vol_weight']

        # Candles
        body = abs(row['close'] - row['open'])
        prev_body = abs(prev['close'] - prev['open'])
        is_bull_engulf = (row['close'] > row['open']) and (row['open'] < prev['close']) and (row['close'] > prev['open']) and (body > prev_body)
        is_bear_engulf = (row['close'] < row['open']) and (row['open'] > prev['close']) and (row['close'] < prev['open']) and (body > prev_body)
        if is_bull_engulf:
            confidence += cfg['candle_weight']
        if is_bear_engulf:
            confidence += cfg['candle_weight']

        if higher_tf_close is not None:
            if row['close'] > higher_tf_close:
                confidence += 0.05

        if is_bull_engulf and (row['rsi'] < cfg['rsi_high']) and trend_long:
            signal = 1
        elif is_bear_engulf and (row['rsi'] > cfg['rsi_low']) and trend_short:
            signal = -1
        else:
            if (row['close'] > prev['high']) and (row['volume'] > row['vol_avg']):
                signal = 1
                confidence += 0.05
            if (row['close'] < prev['low']) and (row['volume'] > row['vol_avg']):
                signal = -1
                confidence += 0.05

        confidence = min(1.0, confidence)
        if confidence < cfg['min_confidence']:
            signal = 0

        stop_atr_mult = cfg['atr_stop_mult']
        take_atr_mult = cfg['atr_take_mult']

        return signal, {'confidence': confidence, 'stop_atr_mult': stop_atr_mult, 'take_atr_mult': take_atr_mult}
    except Exception as e:
        logger.error("Strategy logic error: %s", e)
        logger.debug(traceback.format_exc())
        return 0, {'confidence': 0.0, 'stop_atr_mult': 1.5, 'take_atr_mult': 3.0}

def dynamic_position_sizing(account_balance: float,
                             atr: float,
                             risk_per_trade: float = 0.01,
                             price: float = 1.0,
                             atr_stop_mult: float = 1.5,
                             tick_value: float = 1.0) -> float:
    stop_distance = max(atr * atr_stop_mult, 1e-8)
    risk_amount = account_balance * risk_per_trade
    size = risk_amount / (stop_distance * tick_value)
    return float(size)

def enhanced_backtest_strategy(df, initial_balance: float = 10000.0,
                               risk_per_trade: float = 0.01,
                               slippage: float = 0.0005,
                               commission: float = 0.0002,
                               spread: float = 0.0):
    df = df.copy().reset_index(drop=True)
    df = ensure_indicators(df)
    balance = initial_balance
    position = None
    cash = balance
    equity_list = []
    position_list = []
    unreal_list = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        signal, meta = enhanced_strategy_logic(df, i)
        # check existing position for stop/take using bar extremes
        if position is not None:
            if position.direction == 1:
                if row['low'] <= position.stop_price:
                    exit_price = position.stop_price * (1 + slippage)
                    pnl = (exit_price - position.entry_price) * position.size
                    fee = abs(exit_price * position.size) * commission
                    cash += position.size * exit_price - fee
                    balance = cash
                    position = None
                elif row['high'] >= (position.take_price or 1e18):
                    exit_price = (position.take_price or row['close']) * (1 - slippage)
                    pnl = (exit_price - position.entry_price) * position.size
                    fee = abs(exit_price * position.size) * commission
                    cash += position.size * exit_price - fee
                    balance = cash
                    position = None
            else:
                if row['high'] >= position.stop_price:
                    exit_price = position.stop_price * (1 - slippage)
                    pnl = (position.entry_price - exit_price) * position.size
                    fee = abs(exit_price * position.size) * commission
                    cash += position.size * (position.entry_price + pnl) - fee
                    balance = cash
                    position = None
                elif row['low'] <= (position.take_price or -1e18):
                    exit_price = (position.take_price or row['close']) * (1 + slippage)
                    pnl = (position.entry_price - exit_price) * position.size
                    fee = abs(exit_price * position.size) * commission
                    cash += position.size * (position.entry_price + pnl) - fee
                    balance = cash
                    position = None

        # entry
        if (position is None) and (signal != 0):
            atr = row['atr']
            size = dynamic_position_sizing(balance, atr, risk_per_trade=risk_per_trade, price=row['close'], atr_stop_mult=meta['stop_atr_mult'])
            if size <= 0:
                size = 0.0
            if signal == 1:
                stop_price = row['close'] - meta['stop_atr_mult'] * atr - spread / 2
                take_price = row['close'] + meta['take_atr_mult'] * atr
                entry_price = row['close'] * (1 + slippage + spread / 2)
            else:
                stop_price = row['close'] + meta['stop_atr_mult'] * atr + spread / 2
                take_price = row['close'] - meta['take_atr_mult'] * atr
                entry_price = row['close'] * (1 - slippage - spread / 2)

            notional = entry_price * size
            fee = notional * commission
            if notional + fee <= cash:
                cash -= notional + fee
                position = Position(entry_index=i, entry_price=entry_price, size=size, stop_price=stop_price, take_price=take_price, direction=signal)

        # unrealized pnl
        unreal = 0.0
        if position is not None:
            if position.direction == 1:
                unreal = (row['close'] - position.entry_price) * position.size
            else:
                unreal = (position.entry_price - row['close']) * position.size

        equity = cash + unreal
        equity_list.append(equity)
        position_list.append(1 if position is not None else 0)
        unreal_list.append(unreal)

    import pandas as pd
    out = pd.DataFrame({
        'balance': equity_list,
        'position': position_list,
        'unrealized_pnl': unreal_list
    }, index=df.index[1:len(df)])
    return out
