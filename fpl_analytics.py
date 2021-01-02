import streamlit as st 
import requests
import pandas as pd
import numpy as np
st.set_page_config(
    page_title='FPL Analytics',
    layout="centered"
    )

@st.cache
def load_data():
    url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    r = requests.get(url)
    json = r.json()
    elements_df = pd.DataFrame(json['elements'])
    elements_types_df = pd.DataFrame(json['element_types'])
    teams_df = pd.DataFrame(json['teams'])
    slim_elements_df = elements_df[['second_name','team','element_type','selected_by_percent','now_cost','value_season','total_points','form','ict_index','dreamteam_count','in_dreamteam']]
    slim_elements_df['position'] = slim_elements_df.element_type.map(elements_types_df.set_index('id').singular_name)
    slim_elements_df['team'] = slim_elements_df.team.map(teams_df.set_index('id').name)
    slim_elements_df['value'] = slim_elements_df.value_season.astype(float)
    slim_elements_df['total_points'] = slim_elements_df.total_points.astype(float)
    slim_elements_df['ict_index'] = slim_elements_df.ict_index.astype(float)
    slim_elements_df.sort_values('value',ascending=False,inplace=True)
    return slim_elements_df,elements_df

main_df,mapping_df = load_data()

def format_transfer_df(transfer_data,elements_df):
    transfer_history_df = pd.DataFrame(transfer_data)
    transfer_history_df['element_in_cost'] = transfer_history_df['element_in_cost']/10
    transfer_history_df['element_out_cost'] = transfer_history_df['element_out_cost']/10
    transfer_history_df['element_in_name'] = transfer_history_df.element_in.map(elements_df.set_index('id').second_name)
    transfer_history_df['element_out_name']= transfer_history_df.element_out.map(elements_df.set_index('id').second_name)
    transfer_history_df = transfer_history_df[['element_in_name','element_in_cost','element_out_name','element_out_cost','event']]
    transfer_history_df.columns = ['player in','player in cost','player out','player out cost','gameweek']
    transfer_history_df['gain or loss'] = transfer_history_df['player out cost'].astype(float) - transfer_history_df['player in cost'].astype(float)
    return transfer_history_df

def format_current_team_df(current_team_data,slim_elements_df,elements_df):
    team_df = pd.DataFrame(current_team_data)
    team_df['second_name'] = team_df.element.map(elements_df.set_index('id').second_name)
    team_df = team_df.merge(slim_elements_df,how='left',on='second_name')
    team_df = team_df[['team','second_name','position_y','selected_by_percent','now_cost','value','form','ict_index','dreamteam_count','in_dreamteam']]
    team_df['now_cost'] = team_df['now_cost'] / 10
    team_df.columns = ['team','name','position','selected by (%)','cost','value','form','ict score','dreamteam appearances','in dreamteam']
    team_df.sort_values('value',ascending=False,inplace=True)
    return team_df

st.title('FPL Team Insights')
st.write('Analyse your team - [How to find my team id?](https://www.reddit.com/r/FantasyPL/comments/4tki9s/fpl_id/) ')
team_id = st.text_input('Enter your team id:')

#validating input
valid_team_id = False
if len(team_id) > 0:
    # Endpoints to call for manager data
    manager_info_url = 'https://fantasy.premierleague.com/api/entry/{}/'.format(team_id)

    manager_data = requests.get(manager_info_url).json()
    try:
        if manager_data['detail'] == 'Not found.':
            st.write('Invalid team id found, please refer to the help above.')
            
    except:
        current_game_week = manager_data['current_event']
        manager_details_df = pd.DataFrame.from_dict({
            'id':manager_data['id'],
            'name':manager_data['player_first_name'] + ' ' + manager_data['player_last_name'],
            'region':manager_data['player_region_name'],
            'overall points':manager_data['summary_overall_points'],
            'overall rank':manager_data['summary_overall_rank'],
            'current gameweek':current_game_week
        },orient='index',columns=['Manager Data'])
        st.write(manager_details_df)
        valid_team_id = True

if valid_team_id:
    team_checkbox = st.button('Analyse my team')

    if team_checkbox:
        #endpoints for team data
        transfer_url = 'https://fantasy.premierleague.com/api/entry/{}/transfers/'.format(team_id)
        picks_url = 'https://fantasy.premierleague.com/api/entry/{}/event/{}/picks/'.format(team_id,current_game_week)
        history_url = 'https://fantasy.premierleague.com/api/entry/{}/history/'.format(team_id)

        st.subheader('Transfer History')
        transfer_data = requests.get(transfer_url).json()
        transfer_history_df = format_transfer_df(transfer_data,mapping_df)
        st.write(transfer_history_df)

        st.subheader('Current Team Data')
        current_team_data = requests.get(picks_url).json()['picks']
        team_df = format_current_team_df(current_team_data,main_df,mapping_df)
        st.write(team_df)

        st.subheader('Player Recommendation')
        top_100_df = main_df
        recommendation_df = top_100_df[~top_100_df['second_name'].isin(team_df['name'])]
        recommendation_df = recommendation_df[['team','second_name','position','selected_by_percent','now_cost','value','form','ict_index','dreamteam_count','in_dreamteam']]
        recommendation_df.columns = ['team','name','position','selected by (%)','cost','value','form','ict score','dreamteam appearances','in dreamteam']
        recommendation_df['cost'] = recommendation_df['cost']/10

        st.write('Goalkeepers')
        goalkeeper_df = recommendation_df[recommendation_df['position'] == 'Goalkeeper'].head(10)
        st.write(goalkeeper_df)

        st.write('Defenders')
        defender_df = recommendation_df[recommendation_df['position'] == 'Defender'].head(10)
        st.write(defender_df)
        
        st.write('Midfielders')
        midfielder_df = recommendation_df[recommendation_df['position'] == 'Midfielder'].head(10)
        st.write(midfielder_df)

        st.write('Forwards')
        forward_df = recommendation_df[recommendation_df['position'] == 'Forward'].head(10)
        st.write(forward_df)

st.title('General FPL Statistics')
st.write('This is intended to give you an overall feel for the entire league')

general_df = main_df.loc[main_df.value>0]
general_df['now_cost'] = general_df['now_cost']/10

pivot = general_df.pivot_table(index='position',values='value',aggfunc=np.mean).reset_index()
pivot.sort_values('value',ascending=False,inplace=True)
st.subheader('Average value by position')
st.write(pivot)

st.subheader('Average value by team')
team_pivot = general_df.pivot_table(index='team',values=['value','total_points','ict_index'],aggfunc=np.mean).reset_index()
team_pivot.sort_values('ict_index',ascending=False,inplace=True)
team_pivot.columns = ['team','average ict index','average points','average value']
st.write(team_pivot)

fwd_df = general_df.loc[general_df.position == 'Forward']
mid_df = general_df.loc[general_df.position == 'Midfielder']
def_df = general_df.loc[general_df.position == 'Defender']
goal_df = general_df.loc[general_df.position == 'Goalkeeper']

