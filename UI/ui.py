import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import talib
from matplotlib import font_manager
from tkinter import Tk, StringVar, ttk, Radiobutton, simpledialog
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from datetime import datetime
import backtrader as bt

from My_system.My.backtest import MeanReversionStrategy

start_date = '20190401'
stock_list = ak.stock_info_a_code_name()
stock_dict = dict(zip(stock_list['code'], stock_list['name']))
stock_dict['sh000001'] = '上证指数'

root = Tk()
root.title("LAM")
root.geometry("1000x700")

selected_stock = StringVar()
selected_stock.set('sh000001')

# 创建下拉菜单选择器
label = ttk.Label(root, text="请选择股票代码：")
label.pack(pady=10)

combo = ttk.Combobox(root, textvariable=selected_stock, values=list(stock_dict.keys()))
combo.pack(pady=10)

# 设置中文字体
font_path = "C:/Windows/Fonts/msyh.ttc"
my_font = font_manager.FontProperties(fname=font_path)
plt.rcParams['font.family'] = my_font.get_name()
plt.rcParams['axes.unicode_minus'] = False

# 初始化图形区域
fig, (ax, ax_volume) = plt.subplots(2, 1, figsize=(10, 8), dpi=100, gridspec_kw={'height_ratios': [3, 2]})
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill='both', expand=True)

# 添加工具栏以支持交互功能
toolbar_frame = ttk.Frame(root)
toolbar_frame.pack(fill='x', padx=10, pady=5)
toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
toolbar.update()

# 设置图表展示的选项
plot_option = StringVar(value='kline')

radio_kline = Radiobutton(root, text="显示K线和成交量图", variable=plot_option, value='kline')
radio_macd = Radiobutton(root, text="显示MACD图", variable=plot_option, value='macd')
radio_kline.pack(pady=5)
radio_macd.pack(pady=5)


def zoom_factory(ax, base_scale=1.2):
    def zoom(event):
        if event.inaxes == ax:
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()

            xdata = event.xdata
            ydata = event.ydata

            if event.step > 0:
                scale_factor = base_scale
            elif event.step < 0:
                scale_factor = 1 / base_scale
            else:
                scale_factor = 1

            new_xlim = [xdata - (xdata - cur_xlim[0]) / scale_factor,
                        xdata + (cur_xlim[1] - xdata) / scale_factor]
            new_ylim = [ydata - (ydata - cur_ylim[0]) / scale_factor,
                        ydata + (cur_ylim[1] - ydata) / scale_factor]

            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            ax.figure.canvas.draw()

    ax.figure.canvas.mpl_connect('scroll_event', zoom)

zoom_factory(ax)
zoom_factory(ax_volume)

def set_start_date():
    global start_date
    new_start_date = simpledialog.askstring("设置开始日期", "请输入开始日期：")
    if new_start_date:
        try:
            datetime.strptime(new_start_date, '%Y%m%d')
            start_date = new_start_date
        except ValueError:
            messagebox.showerror("错误", "日期格式不正确，请输入正确格式。")


def get_stock_data(stock_code, start_date, end_date):
    try:
        if stock_code.startswith('sh'):
            data = ak.stock_zh_index_daily(symbol=stock_code)
        elif stock_code.startswith('9') or stock_code.startswith('8'):
            adjusted_code = f"bj{stock_code}"
            data = ak.stock_zh_a_daily(symbol=adjusted_code, adjust="")  # 不复权数据
        elif stock_code.startswith('3'):
            adjusted_code = f"sz{stock_code}"
            data = ak.stock_zh_a_daily(symbol=adjusted_code, adjust="")  # 不复权数据
        else:
            adjusted_code = f"sz{stock_code}" if stock_code.startswith('0') else f"sh{stock_code}"
            data = ak.stock_zh_a_daily(symbol=adjusted_code, adjust="")  # 不复权数据

        # 数据预处理
        data['date'] = pd.to_datetime(data['date'])  # 确保 'date' 列存在并转换为 datetime
        data.set_index('date', inplace=True)  # 设置日期为索引

        # 过滤日期范围
        filtered_data = data.loc[start_date:end_date]

        # 转换数据类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in filtered_data.columns:
                filtered_data[col] = filtered_data[col].astype(float)  # 确保数据为浮点型

        filtered_data['stock_code'] = stock_code  # 添加股票代码列（可选）
        return filtered_data
    except KeyError as ke:
        print(f"无法获取股票数据 {stock_code}: 缺少列 {ke}")
        return pd.DataFrame()
    except Exception as e:
        print(f"无法获取股票数据 {stock_code}: {e}")
        return pd.DataFrame()


def plot_kline(df):
    ax.clear()
    ax_volume.clear()
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='black', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc)
    mpf.plot(df, type='candle', ax=ax, volume=ax_volume, mav=(12, 26), style=s)
    stock_name = stock_dict[selected_stock.get()]
    ax.set_title(f'{stock_name} ({selected_stock.get()}) 行情数据', fontsize=16, fontproperties=my_font)
    canvas.draw()


def plot_macd(df):
    ax.clear()
    ax_volume.clear()
    ax_volume.axis('off')
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='black', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc)
    df['EMA12'] = talib.EMA(df['close'], timeperiod=12)
    df['EMA26'] = talib.EMA(df['close'], timeperiod=26)
    df['DIF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = talib.EMA(df['DIF'], timeperiod=9)
    df['MACD'] = 2 * (df['DIF'] - df['DEA'])
    df.dropna(subset=['DIF', 'DEA', 'MACD'], inplace=True)
    macd_plot_data = [
        mpf.make_addplot(df['DIF'], ax=ax, color='blue', width=1.5, label='DIF'),
        mpf.make_addplot(df['DEA'], ax=ax, color='orange', width=1.5, label='DEA'),
        mpf.make_addplot(df['MACD'], ax=ax, type='bar', color='dimgray', width=0.8, label='MACD')
    ]
    mpf.plot(df, addplot=macd_plot_data, style=s, ax=ax)
    stock_name = stock_dict[selected_stock.get()]
    ax.set_title(f'{stock_name} ({selected_stock.get()}) MACD 数据', fontsize=16, fontproperties=my_font)
    ax.legend(loc='upper left')
    canvas.draw()


def update_plot():
    ts_code = selected_stock.get()
    end_date = datetime.now().strftime('%Y-%m-%d')
    try:
        df = get_stock_data(ts_code, start_date, end_date)
        if df.empty:
            messagebox.showerror("错误", "获取的股票数据为空！")
            return
        if plot_option.get() == 'kline':
            plot_kline(df)
        elif plot_option.get() == 'macd':
            plot_macd(df)
    except Exception as e:
        messagebox.showerror("错误", f"无法获取股票数据：{str(e)}")


def run_backtest():
    ts_code = selected_stock.get()
    end_date = datetime.now().strftime('%Y-%m-%d')
    try:
        df = get_stock_data(ts_code, start_date, end_date)
        if df.empty:
            messagebox.showwarning("警告", "数据为空，无法进行回测。")
            return

        cerebro = bt.Cerebro()

        cerebro.addstrategy(MeanReversionStrategy)
        # 将 pandas DataFrame 转换为 backtrader 数据源
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)

        # 运行回测
        cerebro.run()
        plt.close('all')  # 关闭所有现有图形窗口，避免重复生成
        cerebro.plot()

    except Exception as e:
        messagebox.showerror("错误", f"无法获取股票数据进行回测：{str(e)}")


set_date_button = ttk.Button(root, text="开始日期", command=set_start_date)
set_date_button.pack(pady=10)
# 更新按钮
update_button = ttk.Button(root, text="更新图表", command=update_plot)
update_button.pack(pady=10)

backtest_button = ttk.Button(root, text="运行回测", command=run_backtest)
backtest_button.pack(pady=10)

update_plot()

root.mainloop()
