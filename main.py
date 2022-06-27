import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html,callback_context
from dash.dependencies import Input,Output
import datetime
from datetime import date,datetime
# from jupyter_dash import JupyterDash

#---refreshing from NSE.com
#---extract data from NSE Option Chain---
def option_chain(symbol='NIFTY'):
    symbol = symbol
    print(symbol)
    url = 'https://www.nseindia.com/api/option-chain-indices?symbol={}'.format(symbol)

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.67 Safari/537.36',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9'
    }
    session = requests.Session()
    request = session.get(url,headers=headers)
    cookies = dict(request.cookies)
    response = session.get(url,headers=headers,cookies=cookies).json()
    rawdata = pd.DataFrame(response)
    rawop = pd.DataFrame(rawdata['records']['data']).fillna(0)
    return rawop

#---function to enable sort dict---
def myFunc(e):
    return e['label']

#---get spot price from option chain data----
def spot_price():
    print('spot price -',data_df[data_df['underlyingValue']>0]['underlyingValue'].iloc[1])

def plot_chart(dataframe,x_ax,y_ax1,y_ax2=''):
    chart_df = pd.DataFrame(dataframe)
    ax = chart_df.plot(x=x_ax,y=y_ax1,kind='bar',figsize=(14,7))
    if len(y_ax2) != 0:
        ax1 = ax.twinx()
        ax = chart_df.plot(x=x_ax,y=y_ax2,kind='line',ax=ax1,color='red')

def select_exp_date():
    date_list = pd.to_datetime(data_df['expiryDate'], infer_datetime_format=True).sort_values()
    date_list.drop_duplicates('first',True)
    selection_list = list(map(str,date_list.dt.strftime('%d-%b-%Y')))
    first_expiry = selection_list[0]
    today_expiry = date.today().strftime('%d-%b-%Y')
    if today_expiry == first_expiry:
        return selection_list[1]
    else: return selection_list[0]

#---get the In the Money strike price based on the spot price---
def get_itm(spot, diff = 50):
    l_strike = spot - (spot%diff)
    u_strike = l_strike+diff
    if spot - l_strike < u_strike - spot: itm_value = l_strike
    elif spot - l_strike > u_strike - spot: itm_value = u_strike
    else: itm_value = l_strike
    return itm_value

#----download data from NSE Option Chain and convert to usable dataframe and download as csv---
def data_download():
    rawop = option_chain()
    titles = []
    title_val = rawop[rawop['PE'] !=0]['PE'].iloc[0]
    for i,t in enumerate(title_val):
        titles.append(t)
    if titles[len( titles)-1] != 'Type': titles.append('Type')
    data_df = pd.DataFrame(columns=titles)
    dataval_zero = {}
    loop_types = ['CE','PE']
    for loop_val in loop_types:
        for i,dataval in enumerate(rawop[loop_val]):
            if dataval !=0:
                dataval.update({'Type':loop_val})
                data_df = data_df.append(dataval,ignore_index=True)
            else:
                dataval_zero.update({'strikePrice':rawop['strikePrice'][i],'expiryDate':rawop['expiryDate'][i],'Type':loop_val})
                data_df = data_df.append(dataval_zero,ignore_index=True)
    data_df['timestamp'] = datetime.now()
    data_df['timeXvalue'] = data_df['timestamp'].apply(lambda x: x.strftime('%H:%M'))
    data_df.to_csv('option_data.csv',index=False)

#---get the option data saved and read it to data frame for further processing
def get_option_data():
    data_df = pd.read_csv('option_data.csv')
    return data_df


# ---get the list of expiry dates for filter dropdown---
def expiry_date_unq_list(data_frame):
    data_df = pd.DataFrame(data_frame)
    exp_list = []
    data_df['timeSortField'] = pd.to_datetime(data_df['expiryDate'])
    data_df.sort_values('timeSortField', inplace=True)
    for ed in data_df['expiryDate']:
        if ed not in exp_list: exp_list.append(ed)

    exp_list.sort()
    dropdown_list = []
    for i, ed in enumerate(exp_list):
        vd = datetime.strptime(ed, "%d-%b-%Y")
        dropdown_dict = {}
        dropdown_dict.update({'label': vd})
        dropdown_dict.update({'value': ed})
        dropdown_list.append(dropdown_dict)

    return dropdown_list

#---organize the data to enable charting---
def chart_data(data_frame,expiry):
    data_df = pd.DataFrame(data_frame)
    data_df = data_df[data_df['timestamp']==data_df['timestamp'].max()]
    sort_df = data_df.sort_values(['strikePrice'],ascending=True)
    exp_date = expiry
    spot_price = data_df[data_df['underlyingValue']>0]['underlyingValue'].iloc[0]
    refresh_time = data_df['timeXvalue'].iloc[0]
    refresh_test = datetime.strptime(data_df['timestamp'].iloc[0], "%Y-%m-%d %H:%M:%S.%f")
    refresh_date = refresh_test.strftime('%d-%b-%Y time:%H:%M')
    itm_strike = get_itm(spot_price)
    chart_range = 1500
    lower_range = itm_strike - chart_range
    upper_range = itm_strike + chart_range
    sort_df = sort_df[(sort_df['expiryDate']==exp_date)&(sort_df['strikePrice']>lower_range)&(sort_df['strikePrice']<upper_range)]
    sort_df['strikeXaxis'] = list(map(str,sort_df['strikePrice']))
    ce_df = sort_df[sort_df['Type']=='CE']
    pe_df = sort_df[sort_df['Type']=='PE']
    ce_df.set_index(['strikePrice','expiryDate'],inplace=True)
    pe_df.set_index(['strikePrice','expiryDate'],inplace=True)
    chart_df = ce_df.join(pe_df,lsuffix='-CE',rsuffix='-PE')
    return chart_df, spot_price, refresh_time,itm_strike,refresh_date

app = dash.Dash(__name__)
server = app.server

#---sort the filter dropdown values----
data_df = get_option_data()
exp_drop_list = expiry_date_unq_list(data_df)
exp_drop_list.sort(key=myFunc)

for i in exp_drop_list:
    i['label'] = i['label'].strftime('%d-%b-%Y')

default_value = exp_drop_list[0]['label']

##### <---------------- App Layout--------------------------------->

app.layout = html.Div([
    html.H1('OI Analytics Dashboard'),

    html.Div([
        html.Button('Refresh', id='btn-data_refresh', n_clicks=0),
        html.Div(id='refresh-data')
    ]),

    html.Div([
        html.H3('Select Date'),
        dcc.Dropdown(exp_drop_list, id='expiry-date', value=default_value)
    ]),

    html.Div([
        dcc.Graph(id='oi-chart'),
        dcc.Graph(id='oi_change-chart')
    ])

])

##### <---------------- Callback--------------------------------->

@app.callback(
    Output(component_id='oi-chart', component_property='figure'),
    Output(component_id='oi_change-chart', component_property='figure'),
    Output(component_id='refresh-data', component_property='children'),
    Input(component_id='expiry-date', component_property='value'),
    Input(component_id='btn-data_refresh', component_property='n_clicks'))
def update_figure(slected_expiry, n_clicks):
    # ---data refresh on button click-
    changed_id = [p['prop_id'] for p in callback_context.triggered][0]
    if 'btn-data_refresh' in changed_id: data_download()

    # ---updating chart---------------

    df = get_option_data()
    chart_df, spot_price, refresh_time, itm_strike, refresh_date = chart_data(df, slected_expiry)

    # ---OI Chart---
    x = list(chart_df['strikeXaxis-CE'])
    y1 = list(chart_df['openInterest-PE'])
    y2 = list(chart_df['openInterest-CE'])
    fig = go.Figure(data=[
        go.Bar(name='PE-OI', x=x, y=y1, marker_color='rgb(51,153,102)'),
        go.Bar(name='CE-OI', x=x, y=y2, marker_color='rgb(255,0,102)')
    ])

    fig.update_layout(barmode='group', height=600, plot_bgcolor='rgb(255,255,255)')
    fig.update_xaxes(tickangle=-90, title_text='Strike Price')

    # ---OI Change Chart---
    x = list(chart_df['strikeXaxis-CE'])
    y1 = list(chart_df['changeinOpenInterest-PE'])
    y2 = list(chart_df['changeinOpenInterest-CE'])
    fig1 = go.Figure(data=[
        go.Bar(name='PE-OI Change', x=x, y=y1, marker_color='rgb(51,153,102)'),
        go.Bar(name='CE-OI Change', x=x, y=y2, marker_color='rgb(255,0,102)')
    ])
    fig1.update_layout(barmode='group', height=600, plot_bgcolor='rgb(255,255,255)')
    fig1.update_xaxes(tickangle=-90, title_text='Strike Price')

    # ---update the refresh data points-----
    refresh_data_points = 'Spot Price: {}| ITM Strike Price: {}| Last Refresh: {}'.format(spot_price, itm_strike,
                                                                                          refresh_date)

    return fig, fig1, refresh_data_points

if __name__ == '__main__':
    app.run_server(debug=True)