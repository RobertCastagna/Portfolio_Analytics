from ib_insync import *
import pandas as pd
from functools import reduce
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
import datetime

def merge_dfs(left, right):
    return pd.merge(left, right, on='date', how='outer')

def get_positions(account):
    positions = ib.portfolio(account)
    tickers = []
    for position in positions:
        tickers.append([position.contract.symbol, position.position, position.marketPrice])
    return tickers

def get_historical_data(tickers):
    price_list = []
    for ticker in tickers:
        contract = Stock(ticker, 'SMART', 'USD')
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr='3 M',
            barSizeSetting='1 day',
            whatToShow='MIDPOINT',
            useRTH=True,
            formatDate=1
        )

        df = util.df(bars)
        df = df[['date','close']]
        df.rename({'close': ticker}, axis=1, inplace=True)
        price_list.append(df)

    prices = reduce(merge_dfs, price_list).set_index('date')
    return prices


if __name__ == "__main__":

    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)
    paper_acct = ib.managedAccounts()[0]

    #  -------------------------- (Efficient Frontier Calculation) -------------------------------- #
    # Step 1: Gather data
    position_data = get_positions(paper_acct)
    for pos in position_data:
        tickers = [pos[0] for pos in position_data]

    prices = get_historical_data(tickers)

    # Step 2: Calculate daily returns
    daily_returns = prices.pct_change()
        
    # Step 3: Calculate expected returns and covariance
    expected_returns = daily_returns.mean()
    cov_matrix = daily_returns.cov()
    corr_matrix = daily_returns.corr()

    # Step 4: Generate random portfolios
    num_assets = len(expected_returns)
    num_portfolios = 10000

    # Arrays to store results
    results = np.zeros((3, num_portfolios))
    weights_record = []

    risk_free_rate = 0.042 # 10-year US Treasury bond yield

    for i in range(num_portfolios):
        weights = np.random.random(num_assets)
        weights /= np.sum(weights)  # Normalize to sum to 1
        weights_record.append(weights)
        
        # Portfolio return
        portfolio_return = np.dot(weights, expected_returns)
        
        # Portfolio volatility
        portfolio_stddev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Sharpe Ratio, adjusted for the risk-free rate
        sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_stddev
        
        # Store results (return, volatility, Sharpe ratio)
        results[0,i] = portfolio_return
        results[1,i] = portfolio_stddev
        results[2,i] = sharpe_ratio

    # Convert results to a DataFrame for easier plotting
    df_results = pd.DataFrame(results.T, columns=['Return', 'Volatility', 'Sharpe Ratio'])
    df_weights = pd.DataFrame(weights_record, columns=tickers) 
    df_final = pd.concat([df_results, df_weights], axis=1)

    # Current Porfolio Weights and Performance for Efficient Frontier Scatter Plot
    current_positions = pd.DataFrame(position_data, columns=['Ticker', 'Position', 'Price'])
    current_positions['Total Value'] = current_positions['Position'] * current_positions['Price']
    total_portfolio_value = current_positions['Total Value'].sum()

    # Calculate the weights of each holding
    current_positions['Weight'] = current_positions['Total Value'] / total_portfolio_value

    # Extract the tickers and weights for the current portfolio
    current_tickers = current_positions['Ticker'].tolist()
    current_weights = current_positions.set_index('Ticker')['Weight'].reindex(tickers).fillna(0).values

    # Calculate the expected return and volatility for the current portfolio
    current_portfolio_return = np.dot(current_weights, expected_returns)
    current_portfolio_volatility = np.sqrt(np.dot(current_weights.T, np.dot(cov_matrix, current_weights)))

    # Calculate the Sharpe Ratio for the current portfolio
    current_portfolio_sharpe = (current_portfolio_return - risk_free_rate) / current_portfolio_volatility



    #  -------------------------- (Plotting) -------------------------------- #
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Efficient Frontier', 'Correlation Matrix'),
        column_widths=[0.6, 0.4],
        specs=[[{"type": "scatter"}, {"type": "heatmap"}]],
        horizontal_spacing=0.15
        )

    # Efficient Frontier Scatter Plot
    fig.add_trace(
        go.Scatter(
            name='Efficient Frontier',
            x=df_results['Volatility'], 
            y=df_results['Return'], 
            mode='markers', 
            marker=dict(
                size=5,
                color=df_results['Sharpe Ratio'], 
                colorscale='Viridis', 
                colorbar=dict(
                    title='Sharpe Ratio',
                    xanchor='left',  # Anchor the color bar to the left
                    x=0.52  # Adjust this value to move the color bar closer to the subplot
                ),
                showscale=True),
            text=df_results['Sharpe Ratio']
        ),
        row=1, col=1  # Position in first column
    )
    # Plot the current portfolio on the efficient frontier plot
    fig.add_trace(
        go.Scatter(
            x=[current_portfolio_volatility],
            y=[current_portfolio_return],
            mode='markers',
            marker=dict(
                size=10,
                color='red'
            ),
            name='Current Portfolio'
        ),
        row=1, col=1
    )

    # Correlation Matrix Heatmap
    fig.add_trace(
        go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='Plasma',
            colorbar=dict(
                title='Correlation',
                xanchor='left',  # Anchor the color bar to the left
                x=1  # Position to the far right of the second subplot
            )
        ),
        row=1, col=2  # Position in second column
    )

    # Update layout for the entire figure
    fig.update_layout(
        legend=dict(
        x=0.4,  # Adjust these values to position the legend
        y=0.2
    ),
        height=700,  
        width=1500, 
        title_text='Portfolio Analysis: Efficient Frontier & Correlation Matrix',
        margin=dict(t=100, b=100, l=100, r=100)  # Adjust margins to give more space
    )

    # Update x-axis and y-axis titles for the Efficient Frontier subplot
    fig.update_xaxes(title_text='Volatility (Standard Deviation)', row=1, col=1)
    fig.update_yaxes(title_text='Expected Return', row=1, col=1)

    # Update the correlation matrix subplot
    fig.update_traces(
        selector=dict(type='heatmap'),
        colorbar=dict(
            title='Correlation',  # Set a more descriptive title
            titleside='right',
            titlefont=dict(size=14),
            x=1  # Adjust the position to prevent overlap with the plot
        ),
        row=1, col=2
    )

    fig.show()

    # Generate the table for the Optimal Portfolio
    max_sharpe_port = df_final.iloc[df_final['Sharpe Ratio'].idxmax()].to_frame().T 
    avg_of_top5_sharpes = df_final.sort_values('Sharpe Ratio', ascending=False).iloc[:5].mean().to_frame().T
    print('Average of top 5 highest sharpe ratio portfolio position sizings: \n', avg_of_top5_sharpes, '\n')
    


    # ----------------------------  (Portfolio Statistics) -------------------------------- #

    print('Portfolio Statistics')
    # portfolio return
    pos_sizes = [position_data[i][1]*position_data[i][2] for i in range(len(position_data))]
    weights = [pos/sum(pos_sizes) for pos in pos_sizes]
    portfolio_return = np.dot(weights, expected_returns)

    # market return
    spy_data = get_historical_data(['SPY'])
    spy_daily_return = spy_data.pct_change()
    spy_expected_return = spy_daily_return.mean()

    # portfolio's beta
    covariance = daily_returns.apply(lambda x: x.cov(spy_daily_return['SPY']))
    spy_variance = spy_daily_return['SPY'].var()
    beta_values = covariance / spy_variance
    portfolio_beta = np.dot(weights, beta_values)
    print('Portfolio Beta: ', np.round(portfolio_beta,3))

    # jensens alpha
    expected_return = risk_free_rate + portfolio_beta * (spy_expected_return['SPY'] - risk_free_rate)
    print('Jensen\'s Alpha: ', np.round(expected_return,3))

    # treynor ratio
    treynor_ratio = (portfolio_return - risk_free_rate) / portfolio_beta
    print('Treynor Ratio: ', np.round(treynor_ratio,3))
    
    # Portfolio volatility
    portfolio_stddev = np.sqrt(np.dot(pd.Series(weights).T, np.dot(cov_matrix, weights)))
    print('Portfolio Volatility: ', np.round(portfolio_stddev, 3))
    
    # Sharpe Ratio, adjusted for the risk-free rate
    sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_stddev
    print('Sharpe Ratio: ', np.round(sharpe_ratio, 3))
