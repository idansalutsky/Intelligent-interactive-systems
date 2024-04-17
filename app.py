import gradio as gr
import yfinance as yf  
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from numpy.linalg import inv
import pathlib
import matplotlib.pyplot as plt

def plot_portfolio_cumulative_return_daily(df, portfolio_weights):
    returns = df.pct_change()
    weighted_returns = returns * portfolio_weights
    portfolio_returns = weighted_returns.sum(axis=1)
    portfolio_cumulative_return = (1 + portfolio_returns).cumprod() - 1
    sp500 = yf.download('^GSPC', start=df.index.min(), end=df.index.max())
    sp500_returns = sp500['Adj Close'].pct_change()
    sp500_cumulative_return = (1 + sp500_returns).cumprod() - 1

    # Create the plot
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)

    # Plot portfolio cumulative returns
    ax.plot(portfolio_cumulative_return.index, portfolio_cumulative_return, label='Portfolio Cumulative Return', color='blue')

    # Plot S&P 500 cumulative returns
    ax.plot(sp500_cumulative_return.index, sp500_cumulative_return, label='S&P 500 Cumulative Return', color='red')

    ax.set_title('Portfolio Cumulative Return vs. S&P 500 Cumulative Return (Daily)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Return')
    ax.legend()

    fig.tight_layout()
    return fig


def generate_portfolios(age, investment_size, volatility, risk_flag, selected_sectors,button_ignore, num_stocks):
    try:
      payload = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
      df = pd.DataFrame(payload[0])
      #tickers_symbols = df.values.tolist()
      stock_symbols = df[df['GICS Sector'].isin(selected_sectors)]['Symbol'].tolist()

      fig = plt.figure(figsize=(10, 6))
      empty_df_html = pd.DataFrame().to_html(index=False)
      if len(stock_symbols) < num_stocks:
          return (empty_df_html,"Not enough stocks in those sectors please add sectors",empty_df_html,fig)

      if (age > 50 and volatility > 0.5 and not risk_flag):
          return (empty_df_html,"Its high risk for your age decrease the risk or check the Activate risk button",empty_df_html,fig)


      End_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
      Start_date = '2021-01-01'
      end_training_date = '2023-01-01'
      Start_training_date_future_predictions = '2022-01-01'


      data= yf.download(stock_symbols, start=Start_date, end=End_date)
      close = data['Adj Close'].dropna(axis=1).dropna()
      stock_symbols = close.columns.tolist()
      returns = close.pct_change(1).dropna()

      ################ Calculations related to past predictions results

      old_portfolio = weighted_portfolio(returns,stock_symbols,volatility,Start_date,end_training_date)
      old_portfolio, old_num_stocks_symbols = shrink_portfolio(old_portfolio,stock_symbols,num_stocks)
      old_portfolio_returns_df, old_asset_returns = calculate_portfolio_return(close[close.index > end_training_date][old_num_stocks_symbols],old_portfolio)
      old_results_df, old_exact_sum = calculate_portfolio_allocation(old_num_stocks_symbols, old_portfolio, investment_size, close[old_num_stocks_symbols])

      fig = plot_portfolio_cumulative_return_daily(close[close.index > end_training_date][old_num_stocks_symbols],old_portfolio)


      header_html_portfolio = f"<h2>Should you trust us? </h2>"
      ration = old_portfolio_returns_df['Portfolio Total Return'].iloc[0] - old_portfolio_returns_df['S&P 500 Total Return'].iloc[0]
      ration = np.round(ration,2)
      header_html_portfolio_small = f"<h3>Portfolio return per year (%) - calculated based on data from 2021 to 2022 and evaluated from 2023 to present. Excess return of {ration} % for our portfolio relative to the s&p500</h3>"
      instructions_html_portfolio = "<p style='font-size: medium;'>The portfolio is formulated using stock returns from 2021 to 2022 and assessed from 2023 to the present day. It aligns with your chosen sectors and volatility preferences, employing the following portfolio allocations.</p>"
      portfolio_returns_df_html = header_html_portfolio + header_html_portfolio_small  + old_portfolio_returns_df.to_html(index=False) + instructions_html_portfolio #transposed_old_results_df.to_html(index=False)

      ################ Calculations related to future predictions

      portfolio = weighted_portfolio(returns,stock_symbols,volatility,Start_training_date_future_predictions,End_date)
      portfolio, num_stocks_symbols = shrink_portfolio(portfolio,stock_symbols,num_stocks)
      portfolio_returns_df, asset_returns = calculate_portfolio_return(close[num_stocks_symbols],portfolio)

      results_df, exact_sum = calculate_portfolio_allocation(num_stocks_symbols, portfolio, investment_size, close[close.index > end_training_date][num_stocks_symbols])
      one_year_ago_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
      results_df[f'1Y stock return (%) ({one_year_ago_date} - {End_date})'] = np.round(np.array(asset_returns.tolist()) * 100, 1)
      results_df_html = results_df.to_html(index=False, escape=False)

      # Iterate over each row in the DataFrame to add hyperlinks
      for index, row in results_df.iterrows():
          ticker = row['Symbol']  # Assuming 'Ticker' is the column name containing stock tickers
          hyperlink = '<a href="https://finance.yahoo.com/quote/{}">{}</a>'.format(ticker, ticker)
          results_df_html = results_df_html.replace('<td>{}</td>'.format(ticker), '<td>{}</td>'.format(hyperlink))

      # Add instructions in smaller letters
      instructions_html = "<p style='font-size: medium;'>Click on each stock symbol to view more information about the company.</p>"
      header_html = "<h2>Our future predictions</h2>"
      small_header_html = "<h3>Portfolio Summary formulated from 2022 to the present day, leveraging the same sectors and volatility parameters you have chosen.</h3>"  # Smaller header HTML
      results_df_html =  header_html + small_header_html + results_df_html + instructions_html

      return (results_df_html , exact_sum,portfolio_returns_df_html ,fig)

    except Exception as e:
        error_message = str(e)
        return (np.nan, error_message, np.nan, np.nan)


def shrink_portfolio(portfolio,stock_symbols,num_stocks):
    if len(stock_symbols) == num_stocks:
            return portfolio
    else:
          sorted_indices = np.argsort(portfolio)

          num_stocks_weights_indices = sorted_indices[-num_stocks:][::-1] # num_stocks biggest weights indices
          num_stocks_weights = portfolio[num_stocks_weights_indices] # num_stocks biggest weights values
          num_stocks_symbols = [stock_symbols[i] for i in num_stocks_weights_indices] #num_stocks biggest weights symbols

          non_selected_sum = np.sum(portfolio[sorted_indices[:-num_stocks]])
          num_stocks_weights /= (1 - non_selected_sum) # normalize weights to 1
          portfolio_updated = num_stocks_weights

          return portfolio_updated, num_stocks_symbols


def weighted_portfolio(returns,stock_symbols,volatility,start_training_date,end_training_date):
    min_var_portfolio,C,C_inv = min_variance(returns[(returns.index < end_training_date)&(returns.index >= start_training_date)])
    best_basket_portfolio = best_basket(returns[(returns.index < end_training_date)&(returns.index >= start_training_date)],C,C_inv)

    portfolio = (1-volatility)*min_var_portfolio + volatility*best_basket_portfolio

    return portfolio

def min_variance(returns):
    C = returns.cov()
    C_inv = np.linalg.inv(C)
    e = np.ones(C.shape[0])
    min_var = np.matmul(C_inv, e) / np.matmul(np.matmul(e.T, C_inv), e)
    return min_var,C,C_inv

def best_basket(returns,C,C_inv):
    #C = returns.cov().to_numpy()
    e = np.ones((np.shape(C)[0],1), dtype=int)
    #C_inv = inv(C)
    mean_returns = np.array(returns.mean().values)
    divider = e.T@C_inv@mean_returns
    best_basket = C_inv@mean_returns / divider
    return best_basket

def get_sp500_cumulative_return(start_date, end_date):
    sp500_data = yf.download('^GSPC', start=start_date, end=end_date)
    sp500_returns = sp500_data['Adj Close'].pct_change()
    cumulative_return = (1 + sp500_returns).prod() - 1
    cumulative_return_percentage = np.round(cumulative_return * 100, 2)
    return cumulative_return_percentage

def calculate_portfolio_return(close_prices_df, weights):
    annual_returns = close_prices_df.groupby(close_prices_df.index.year).apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)

    # Calculate the weighted returns for each asset
    weighted_annual_returns = annual_returns * weights

    # Calculate the overall portfolio return
    portfolio_return_per_year = weighted_annual_returns.sum(axis=1)
    overall_return = np.prod(portfolio_return_per_year+1) - 1
    portfolio_return_per_year = np.round(portfolio_return_per_year * 100, 2)

    years = close_prices_df.index.year.unique().tolist()

    # Create a DataFrame with a single row containing the portfolio return for each year
    portfolio_return_per_year_df = pd.DataFrame([portfolio_return_per_year], columns=years)
    portfolio_return_per_year_df['Portfolio Total Return'] = np.round(overall_return * 100 , 2)
    portfolio_return_per_year_df['S&P 500 Total Return'] = get_sp500_cumulative_return(close_prices_df.index.min(), close_prices_df.index.max())

    Start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    last_year_close_prices_df = close_prices_df[close_prices_df.index>Start_date]
    last_year_asset_returns = last_year_close_prices_df.iloc[-1] / last_year_close_prices_df.iloc[0] - 1

    return portfolio_return_per_year_df, last_year_asset_returns


def calculate_portfolio_allocation(symbols, weights, investment_amount, close_stocks_df):
    # Calculate percent of portfolio for each symbol
    portfolio_allocation = [round(weight * 100, 2) for weight in weights]

    # Get the last row of the close_stocks_df to get the current stock prices
    last_prices = close_stocks_df.iloc[-1]

    # Calculate number of shares and value of shares for each symbol
    num_shares = []
    exact_values = []
    for symbol, stock_weight in zip(symbols, weights):
        stock_price = last_prices[symbol]
        shares = int(np.floor((stock_weight * investment_amount) / stock_price))
        exact_value = shares * stock_price
        num_shares.append(shares)
        exact_values.append(exact_value)

    exact_sum = np.round(sum(exact_values),2)
    # Create a DataFrame with the results
    results_df = pd.DataFrame({
        'Symbol': symbols,
        'Shares to buy': num_shares,
        'Purchase amount in USD': np.round(np.array(exact_values), 2),
        'Portfolio Allocation (%)': portfolio_allocation,
    }).sort_values(by='Portfolio Allocation (%)', ascending=False)

    return results_df,exact_sum

interface = gr.Interface(
    title='Stock Guide',
    description="This app utilizes interactive features to gather information from users, such as their level of volatility tolerance,\
     preferred sectors, amount of investment, and desired number of stocks in the portfolio. Using this information, \
     the app generates a selection of stocks that align with the user's criteria. By providing tailored portfolio suggestions and educational resources,\
     the app aims to empower users to make informed investment decisions that align with their financial objectives. We're here to create the best investment portfolio for you.\
     Let's start by asking you a few questions to understand your financial goals and preferences. The results are only a hypothesis and do not constitute a recommendation. Created by Idan Salutsky & Tomer Eichler",
    fn=generate_portfolios,

    inputs=[
        gr.Number(label="Age", minimum=18, maximum=120, show_label=True, container=True),
        gr.Number(label="Investment Size (USD)", info="We would like to know the amount of money that the investor would like to invest in order to correctly allocate investments in the portfolio.", show_label=True, container=True),
        gr.Slider(label="Volatility of the investment Portfolio", minimum=0, maximum=1, show_label=True, container=True, info="Your volatility choice reflects how much risk and potential return you're comfortable with. Higher volatility means embracing market fluctuations for potentially greater returns, while lower volatility prioritizes stability and risk mitigation. Understanding and aligning your volatility preference with your financial goals helps tailor your portfolio to suit your needs. Low volatility - [0-0.2], medium - [0.2-0.8], high - [0.8-1]"),
        gr.Checkbox(label="Activate risk", info="If you are over 50 years old and have chosen a volatility level greater than 0.5, you must understand that this is a high risk for your age, if you want to continue press the button"),
        gr.CheckboxGroup(choices=['Industrials', 'Health Care', 'Information Technology',
       'Utilities', 'Financials', 'Materials', 'Consumer Discretionary',
       'Real Estate', 'Communication Services', 'Consumer Staples',
       'Energy'], label="Choose Sectors from the GICS Sectors", info="Choose your preferred sectors"),
        gr.Button(value="Click for learning about GICS Sectors !", link="https://en.wikipedia.org/wiki/Global_Industry_Classification_Standard"),
        gr.Number(label="Number of Stocks", minimum=1, maximum=20, info="Deciding on the number of stocks in your portfolio is critical for achieving a balance between risk and return. More stocks increase diversification but demand more research and monitoring. Conversely, fewer stocks lead to concentration, potentially amplifying individual stock impacts.  Balancing diversification and concentration aligns with your objectives and ensures effective risk management in your investment portfolio. (maximum 20)"),
    ],

    outputs=[
        gr.HTML(),
        gr.Textbox(label="Total budget used"),
        gr.HTML(),
        gr.Plot(),
    ],
)
interface.launch()
