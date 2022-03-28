import os
import pandas as pd
import re
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objs as go

df = pd.read_csv('해양경찰청_해상조난사고 상세데이터 현황_20201231.csv', encoding='cp949', parse_dates=['발생일시'])
df['위도'] = df['위도'].apply(lambda x : int(x.split('|')[0])) + df['위도'].apply(lambda x : int(x.split('|')[1])/60) + df['위도'].apply(lambda x : int(x.split('|')[2])/3600)
df['경도'] = df['경도'].apply(lambda x : int(x.split('|')[0])) + df['경도'].apply(lambda x : int(x.split('|')[1])/60) + df['경도'].apply(lambda x : int(x.split('|')[2])/3600)

app = dash.Dash(__name__, title="marine")
server=app.server

app.layout = html.Div([
    html.Div([
        html.H1('2021년 해양조난사고 현황 🚢')
    ],id='header'),
    html.Div([
        html.Div([
            html.H4("관할해경서"),
            dcc.Dropdown(id='user',
                         multi=False,
                         searchable=True,
                         value='평택',
                         placeholder='Select Region',
                         options=[{'label': c, 'value': c} for c in (df['관할해경서'].unique())], className="dropdown")
        ], className="create_container three"),
        html.Div([
            html.H4("사고건수"),
            html.Div(id='accident')
        ], className="create_container three"),
        html.Div([
            html.H4("발생인원"),
            html.Div(id='person')
        ], className="create_container three"),
    ], id='third-container'),
    
    html.Div([
        html.Div([
            dcc.Graph(id='line_chart', config={'displayModeBar': 'hover'})
        ], className='create_container two'),
        html.Div([
            dcc.Graph(id='pie_chart', config={'displayModeBar': 'hover'})
        ], className='create_container two'),
    ], id='second-container'),
    
    html.Div([
        html.Div([
            dcc.Graph(id='map_chart', config={'displayModeBar': 'hover'})
        ], className="create_container map"),
    ], id="forth-container")
], id='main')

@app.callback(Output('map_chart', 'figure'),
              Input('user', 'value'))
def map(user):
    terr_list = df[['관할해경서', '위도', '경도']]
    dict_of_locations = terr_list.set_index('관할해경서')[['위도', '경도']].T.to_dict('dict')
    marine = df.groupby(['관할해경서', '발생해역', '발생원인','선 종','위도', '경도'])[
        ['사고선박수']].sum().reset_index()
    
    if user:
        zoom_long = dict_of_locations[user]['경도']
        zoom_lat = dict_of_locations[user]['위도']

    return {
        'data': [go.Scattermapbox(
            lon=marine['경도'],
            lat=marine['위도'],
            mode='markers',
            marker=go.scattermapbox.Marker(size=marine['사고선박수']*10,
                                           color=marine['사고선박수'],
                                           colorscale='HSV',
                                           showscale=False,
                                           sizemode='area',
                                           opacity=0.3),
            hoverinfo='text',
            hovertext='사고선박수 : ' + (marine['사고선박수'].astype(str)) + '<br />' +
            '발생해역 : ' + (marine['발생해역']) + '<br />' +
            '발생원인 : ' + (marine['발생원인']) + '<br />' +
            '선종 : ' + (marine['선 종'])

        )],
        'layout': go.Layout(
            mapbox=dict(
                accesstoken=os.environ.get('MARINE'),
                center=go.layout.mapbox.Center(lat=zoom_lat, lon=zoom_long),
                style='dark',
                zoom=8
            ),
            margin=dict(r=0, l=0, t=0, b=0),
            autosize=True,
            hovermode='x',
            paper_bgcolor='#010915',
            plot_bgcolor='#010915',
        )
    }

@app.callback(Output('accident', 'children'),
              Input('user', 'value'))
def map(user):
    total = df.melt(id_vars=['관할해경서'], value_vars='사고선박수').groupby(['관할해경서'])['value'].sum().reset_index()
    counts = total[total['관할해경서'] == user]['value'].iloc[-1]
    return [
        html.P(f"{counts}건")
    ]
    
@app.callback(Output('person', 'children'),
              Input('user', 'value'))
def map(user):
    total = df.melt(id_vars=['관할해경서'], value_vars='발생인원').groupby(['관할해경서'])['value'].sum().reset_index()
    counts = total[total['관할해경서'] == user]['value'].iloc[-1]
    return [
        html.P(f"{counts:,.0f}명")
    ]

@app.callback(Output('line_chart', 'figure'),
              Input('user', 'value'))
def update(user) :
    gdf = df[df['관할해경서'] == user].sort_values(by='발생일시').reset_index(drop=True)
    gdf['발생일시'] = gdf['발생일시'].dt.date
    gdf['발생일시']= pd.to_datetime(gdf['발생일시'])
    gdf['month'] = gdf['발생일시'].dt.month
    gdf = gdf.groupby(['month'])['발생인원'].sum().reset_index()
    return {
        'data' : [go.Scatter(
            x = gdf['month'],
            y = gdf['발생인원'],
            mode='markers+lines',
            line=dict(shape='spline', smoothing=1, width=3, color='dimgray'),
            marker=dict(color='white', size=10, symbol='circle',
                        line=dict(color='dimgray', width=2)),
        )],
        'layout' : go.Layout(
            title={'text': '월별 사고발생건수_' + (user)},
            paper_bgcolor='#010915',
            plot_bgcolor='#010915',
            font=dict(color='white'),
            xaxis=dict(showline=True, showgrid=True,
                       linecolor='white', dtick=1),
            yaxis=dict(showline=True, showgrid=True,
                       linecolor='white'),
        )
    }

@app.callback(Output('pie_chart', 'figure'),
              [Input('user', 'value')])
def pie(user):
    test = df.groupby(['관할해경서','발생원인'])['발생유형'].count().reset_index()
    test = test.pivot_table(index='관할해경서', columns='발생원인', values='발생유형', aggfunc=sum).reset_index().fillna(0)
    type1 = test[test['관할해경서'] == user]['관리소홀'].sum()
    type2 = test[test['관할해경서'] == user]['기상악화'].sum()
    type3 = test[test['관할해경서'] == user]['배터리 방전'].sum()
    type4 = test[test['관할해경서'] == user]['안전부주의'].sum()
    type5 = test[test['관할해경서'] == user]['운항부주의'].sum()
    type6 = test[test['관할해경서'] == user]['적재불량'].sum()
    type7 = test[test['관할해경서'] == user]['정비불량'].sum()
    type8 = test[test['관할해경서'] == user]['화기취급부주의'].sum()
    type9 = test[test['관할해경서'] == user]['기타 '].sum()
    colors = ['white', 'orange', 'green', 'pink', 'gold', 'mediumturquoise', 'darkorange', 'lightgreen']
    return {
        'data': [go.Pie(
            labels=['관리소홀', '기상악화', '배터리방전', '안전부주의', '운항부주의', '적재불량', '정비불량', '화기취급부주의', '기타'],
            values=[type1, type2, type3, type4, type5, type6, type7, type8, type9],
            marker=dict(colors=colors),
            hoverinfo='label+value+percent',
            textinfo='label+value',
            rotation=45,
        )],
        'layout': go.Layout(
            title={'text': '사고발생별 원인'},
            paper_bgcolor='#010915',
            plot_bgcolor='#010915',
            font=dict(color='white'),
            xaxis=dict(showline=True, showgrid=True,
                       linecolor='white', dtick=1),
            yaxis=dict(showline=True, showgrid=True,
                       linecolor='white'),
        )
    }

if __name__ == "__main__":
    app.run_server(debug=True)