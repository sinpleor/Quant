
import backtrader as bt

class MeanReversionStrategy(bt.Strategy):
    params = (
        ('short_period', 5),
        ('long_period', 10),
        ('threshold', 0.00),  # 2% threshold for mean reversion
    )

    def __init__(self):
        # 短期均线和长期均线
        self.short_sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.short_period)
        self.long_sma = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.long_period)

    def next(self):
        # 均线差异百分比
        sma_diff = (self.short_sma[0] - self.long_sma[0]) / self.long_sma[0]

        if not self.position:  # 当前没有持仓
            if sma_diff < -self.params.threshold:  # 短期均线低于长期均线一定阈值
                self.buy(size=self.broker.get_cash() // self.data.close[0])  # 全仓买入
        elif sma_diff > self.params.threshold:  # 短期均线高于长期均线一定阈值
            self.sell(size=self.position.size)  # 全部卖出