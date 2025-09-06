from cmath import phase
from ctypes import sizeof
from distutils.command.build import build
from doctest import OutputChecker
from operator import contains
from pickle import TRUE
from this import d
from turtle import width
from unicodedata import decimal
from bokeh.plotting import figure, ColumnDataSource, output_notebook, show, output_file, save
from bokeh.models import HoverTool, WheelZoomTool, PanTool, BoxZoomTool, ResetTool, TapTool, SaveTool, LabelSet, Range1d, Span, BoxAnnotation, Div, FactorRange
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn
from bokeh.palettes import brewer, Spectral5, GnBu3, Pastel2, viridis
from bokeh.transform import factor_cmap
from bokeh.layouts import column, gridplot, layout
from bokeh.io import export_png, curdoc
from cv2 import drawFrameAxes
from selenium import webdriver
from decimal import *
from collections.abc import Mapping
from pandas.io.formats.style import Styler
import math
import os
import pandas as pd
import matplotlib as mpl
from sqlalchemy import false
import seaborn as sns
import numpy as np
import chromedriver_binary  # Adds chromedriver binary to path
import operator
from collections import OrderedDict
import difflib
from math import pi
import pandas as pd
from bokeh.palettes import Category20c, GnBu
from bokeh.plotting import figure, show
from bokeh.transform import cumsum
import pandas as pd
import holoviews as hv
hv.extension('bokeh') 

pd.options.mode.chained_assignment = None  # default='warn'
pd.set_option('display.max_colwidth', 0)

global batterScatter
global bowlerScatter

global filterVenues
filterVenues = []

global filterTeams
filterTeams = []

global bestPlayerTeams
bestPlayerTeams = []

global venueFilter
venueFilter = ''

global venueTitle
venueTitle = ''

global filePath
filePath = "~/Downloads/tests_male_csv2/"

global runsRangeColumns
runsRangeColumns = []

global savePngs
savePngs = True

global saveHtml
saveHtml = True

global showImages
showImages = True

global innsProgressionSR
innsProgressionSR = 25

global playerBPI
playerBPI = 15

global teamBPI
teamBPI = 74

global ppStart
ppStart = 0.0

global ppEnd 
ppEnd = 30.0

global moStart 
moStart = 30.0

global moEnd 
moEnd = 60.0

global deathStart
deathStart = 60.0

global deathEnd
deathEnd = 450.0

global maxInnings
maxInnings = 4

global matchupColumns
matchupColumns = []

global matchupTotals
matchupTotals = pd.DataFrame()

global batterMatchups
batterMatchups = pd.DataFrame()

global bowlerMatchups
bowlerMatchups = pd.DataFrame()

global matchupPlot
matchupPlot = ''

global calculateNBSRFlag
calculateNBSRFlag = False

bowlerTypeMapping = {
    'LF': 'Left arm Fast', 
    'LM': 'Left arm Medium', 
    'LS': 'Left arm Slow', 
    'LC': 'Left arm Chinaman', 
    'LO': 'Left arm Orthodox', 
    'RF': 'Right arm Fast', 
    'RM': 'Right arm Medium', 
    'RS': 'Right arm Slow', 
    'RL': 'Right arm Leg Break', 
    'RO': 'Right arm Off Break'
}

teams_mapping = {
    'Chennai Super Kings': 'CSK',
    'Mumbai Indians': 'MI',
    'Kolkata Knight Riders': 'KKR',
    'Gujarat Titans': 'GT',
    'Lucknow Super Giants': 'LSG',
    'Punjab Kings': 'PBKS',
    'Kings XI Punjab': 'PBKS',
    'Royal Challengers Bangalore': 'RCB',
    'Delhi Capitals': 'DC',
    'Delhi Daredevils': 'DC',
    'Sunrisers Hyderabad': 'SRH',
    'Rajasthan Royals': 'RR',
    'Rising Pune Supergiants': 'RPSG',
    'Rising Pune Supergiant': 'RPSG',
    'Gujarat Lions': 'GL',
    'Deccan Chargers': 'DCh',
    'Kochi Tuskers Kerala': 'KTK'
}

venue_replacements = {
    'Arun Jaitley Stadium': 'Feroz Shah Kotla',
    'Arun Jaitley Stadium, Delhi': 'Feroz Shah Kotla',
    'Brabourne Stadium': 'Brabourne Stadium, Mumbai',
    'Dr DY Patil Sports Academy': 'Dr DY Patil Sports Academy, Mumbai',
    'M.Chinnaswamy Stadium': 'M Chinnaswamy Stadium',
    'MA Chidambaram Stadium': 'MA Chidambaram Stadium, Chepauk, Chennai',
    'MA Chidambaram Stadium, Chepauk': 'MA Chidambaram Stadium, Chepauk, Chennai',
    'Maharashtra Cricket Association Stadium': 'Maharashtra Cricket Association Stadium, Pune',
    'Punjab Cricket Association IS Bindra Stadium': 'Punjab Cricket Association IS Bindra Stadium, Mohali',
    'Punjab Cricket Association Stadium, Mohali': 'Punjab Cricket Association IS Bindra Stadium, Mohali',
    'Rajiv Gandhi International Stadium': 'Rajiv Gandhi International Stadium, Uppal',
    'Sheikh Zayed Stadium': 'Zayed Cricket Stadium, Abu Dhabi',
    'Wankhede Stadium': 'Wankhede Stadium, Mumbai',
    'Eden Gardens': 'Eden Gardens, Kolkata'
}

stadia_replacements = {
    'Barsapara Cricket Stadium, Guwahati': 'Barsapara Cricket Stadium',
    'Arun Jaitley Stadium': 'Feroz Shah Kotla',
    'Arun Jaitley Stadium, Delhi': 'Feroz Shah Kotla',
    'Feroz Shah Kotla, Delhi': 'Feroz Shah Kotla',
    'Brabourne Stadium, Mumbai': 'Brabourne Stadium',
    'Himachal Pradesh Cricket Association Stadium, Dharamsala': 'Himachal Pradesh Cricket Association Stadium',
    'Dr DY Patil Sports Academy, Mumbai': 'Dr DY Patil Sports Academy',
    'M.Chinnaswamy Stadium, Bengaluru': 'M Chinnaswamy Stadium',
    'MA Chidambaram Stadium, Chepauk, Chennai': 'MA Chidambaram Stadium',
    'MA Chidambaram Stadium, Chepauk': 'MA Chidambaram Stadium',
    'MA Chidambaram Stadium, Chennai': 'MA Chidambaram Stadium',
    'Maharashtra Cricket Association Stadium, Pune': 'Maharashtra Cricket Association Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association Stadium, Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association Stadium, Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Rajiv Gandhi International Stadium, Uppal, Hyderabad': 'Rajiv Gandhi International Stadium',
    'Rajiv Gandhi International Stadium, Uppal': 'Rajiv Gandhi International Stadium',
    'Rajiv Gandhi International Stadium, Hyderabad': 'Rajiv Gandhi International Stadium',
    'Sheikh Zayed Stadium': 'Zayed Cricket Stadium',
    'Sheikh Zayed Stadium, Abu Dhabi': 'Zayed Cricket Stadium',
    'Zayed Cricket Stadium, Abu Dhabi': 'Zayed Cricket Stadium',
    'Wankhede Stadium, Mumbai': 'Wankhede Stadium',
    'Eden Gardens, Kolkata': 'Eden Gardens',
    'Narendra Modi Stadium, Ahmedabad': 'Narendra Modi Stadium',
    'Sardar Patel Stadium, Motera': 'Sardar Patel Stadium',
    'Sawai Mansingh Stadium, Jaipur': 'Sawai Mansingh Stadium',
    'Vidarbha Cricket Association Stadium, Jamtha': 'Vidarbha Cricket Association Stadium',
    'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow': 'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium',
    'Barsapara Cricket Stadium,Guwahati': 'Barsapara Cricket Stadium',
    'Arun Jaitley Stadium,Delhi': 'Feroz Shah Kotla',
    'Feroz Shah Kotla,Delhi': 'Feroz Shah Kotla',
    'Brabourne Stadium,Mumbai': 'Brabourne Stadium',
    'Himachal Pradesh Cricket Association Stadium,Dharamsala': 'Himachal Pradesh Cricket Association Stadium',
    'Dr DY Patil Sports Academy,Mumbai': 'Dr DY Patil Sports Academy',
    'M.Chinnaswamy Stadium,Bengaluru': 'M Chinnaswamy Stadium',
    'MA Chidambaram Stadium,Chepauk': 'MA Chidambaram Stadium',
    'MA Chidambaram Stadium,Chennai': 'MA Chidambaram Stadium',
    'Maharashtra Cricket Association Stadium,Pune': 'Maharashtra Cricket Association Stadium',
    'Punjab Cricket Association IS Bindra Stadium,Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association Stadium,Mohali': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association Stadium,Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Punjab Cricket Association IS Bindra Stadium,Chandigarh': 'Punjab Cricket Association IS Bindra Stadium',
    'Rajiv Gandhi International Stadium,Uppal': 'Rajiv Gandhi International Stadium',
    'Rajiv Gandhi International Stadium,Hyderabad': 'Rajiv Gandhi International Stadium',
    'Sheikh Zayed Stadium': 'Zayed Cricket Stadium',
    'Sheikh Zayed Stadium,Abu Dhabi': 'Zayed Cricket Stadium',
    'Zayed Cricket Stadium,Abu Dhabi': 'Zayed Cricket Stadium',
    'Wankhede Stadium,Mumbai': 'Wankhede Stadium',
    'Eden Gardens,Kolkata': 'Eden Gardens',
    'Narendra Modi Stadium,Ahmedabad': 'Narendra Modi Stadium',
    'Sardar Patel Stadium,Motera': 'Sardar Patel Stadium',
    'Sawai Mansingh Stadium,Jaipur': 'Sawai Mansingh Stadium',
    'Vidarbha Cricket Association Stadium,Jamtha': 'Vidarbha Cricket Association Stadium',
    'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium,Lucknow': 'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium',
    'Kensington Oval Barbados': 'Kensington Oval Bridgetown'
}

sumColumns = ['runs', 'wickets', 'ballsFaced', 'dots', '1s', '2s', '3s', '4s', 
                    '6s', 'ppRuns', 'ppBalls', 'ppWickets', 'ppdots', 'pp1s', 'pp2s', 'pp3s', 'pp4s', 'pp6s', 'ppExtras',
                    'moRuns', 'moBalls', 'moWickets', 'modots', 'mo1s', 'mo2s', 'mo3s', 'mo4s', 'mo6s', 'moExtras', 
                    'deathRuns', 'deathBalls', 'deathWickets', 'deathdots', 'death1s', 'death2s', 'death3s', 
                    'death4s', 'death6s', 'deathExtras', 'overallRuns', 'overallBalls', 'overallWickets', 'overalldots', 'overall1s',
                    'overall2s', 'overall3s', 'overall4s', 'overall6s', 'overallExtras', 'teamRunsExclBatter', 'teamBallsExclBatter', 'teamWicketsExclBatter',
                    'ppTeamRuns', 'ppTeamBalls', 'ppTeamWickets', 'moTeamRuns', 'moTeamBalls', 'moTeamWickets', 'deathTeamRuns', 'deathTeamBalls', 'deathTeamWickets',
                    'overallTeamRuns', 'overallTeamBalls', 'overallTeamWickets']

runsRangeColumns.sort()
runsRangeColumns = [*set(runsRangeColumns)]

global statMode
global timePeriod

def sortVenues(inningsTotals):

    inningsTotals = inningsTotals[inningsTotals['venue'].notna()]
    #inningsTotals = inningsTotals[inningsTotals['sortedVenues'].notna()]
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('.', ' ')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Darren', 'Daren')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Gros Islet', 'St Lucia')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Zahur', 'Zohur')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Jamaica', 'Kingston')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('P Sara Oval', 'P Saravanamuttu Stadium')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Vidarbha C A  Ground', 'Vidarbha Cricket Association Stadium')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Sardar Patel Stadium', 'Narendra Modi Stadium')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Arun Jaitley Stadium', 'Feroz Shah Kotla')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Himachal Pradesh Cricket Association Stadium', 'HPCA Stadium')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Maharashtra Cricket Association Stadium', 'MCA Stadium')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium', 'BRSABV Ekana Cricket Stadium')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Kensington Oval Barbados', 'Kensington Oval Bridgetown')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Brian Lara Stadium Tarouba Trinidad', 'Brian Lara Stadium Tarouba')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Daren Sammy National Cricket Stadium St Lucia St Lucia', 'Daren Sammy National Cricket Stadium St Lucia')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace('Providence Stadium Guyana', 'Providence Stadium')
    inningsTotals['venue'] = inningsTotals['venue'].str.replace("Queen's Park Oval Port of Spain Trinidad", "Queen's Park Oval Port of Spain")
    inningsTotals['venue'] = inningsTotals['venue'].str.replace("Warner Park Basseterre St Kitts", "Warner Park Basseterre")
    inningsTotals['venue'] = inningsTotals['venue'].str.replace("Central Broward Regional Park Stadium Turf Ground Lauderhill", "Central Broward Regional Park Stadium Turf Ground")
    inningsTotals['city'] = inningsTotals['city'].str.replace('Dharmasala', 'Dharamsala')
    inningsTotals['city'] = inningsTotals['city'].str.replace('Bridgetown', 'Barbados')
    inningsTotals = inningsTotals.sort_values(by='venue', ascending=True)

    if 'sortedVenues' not in inningsTotals.columns:
        venues = inningsTotals['venue'].tolist()
        tempVenues = venues.copy()
    else:
        venues = inningsTotals['sortedVenues'].tolist()
        tempVenues = venues.copy()

    for i in range(len(inningsTotals.index)-1, 1, -1):

        #overlap = ''.join(sorted(set(venues[i]) & set(venues[i-1]), key = venues[i].index))
        if venues[i-1] in venues[i] and venues[i-1] != venues[i]:
            tempVenues = list(map(lambda x: x.replace(tempVenues[i], tempVenues[i-1]), tempVenues))

    inningsTotals['sortedVenues'] = tempVenues

    return inningsTotals

def buildVenueNotes(venuesDf, tempVenuesDf, venue):

    print(venue)
    tempDf = tempVenuesDf.copy()
    tempDf = tempDf[tempDf['venue'].isin(venue)]
    tempDict = {}

    global timePeriod
    print(tempDf)
    print(timePeriod)
    print(tempDf['year'])

    if '-' in timePeriod:
        years = timePeriod.split('-')
        minYear = years[0]
        maxYear = years[1]
        print(minYear)
        print(maxYear)
        tempDf = tempDf[tempDf['year'].astype(int) >= int(minYear)]
        tempDf = tempDf[tempDf['year'].astype(int) <= int(maxYear)]

    print(tempDf)
    tempDict['venue'] = venueTitle

    #tempDict['city'] = tempDf['city'].unique().tolist()[0]

    if len(tempDf['city'].unique().tolist()) == 1:
        tempDict['city'] = tempDf['city'].unique().tolist()[0]
    else:
        tempDict['city'] =  ''

    minYear = tempDf['year'].min()
    maxYear = tempDf['year'].max()

    if minYear != maxYear:
        tempDict['timePeriod'] = str(minYear) + '-' + str(maxYear)
    else:
        tempDict['timePeriod'] = minYear

    tempDict['matches'] = len(tempDf.index)

    tempDict['wonBattingFirst'] = len(tempDf[tempDf['wonBattingFirst'] == 'yes'])
    tempDict['wonFieldingFirst'] = len(tempDf[tempDf['wonFieldingFirst'] == 'yes'])
    tempDict['draws'] = len(tempDf[tempDf['outcome'] == 'draw'])

    wonBatFirstDf = tempDf.copy()
    wonBatFirstDf = wonBatFirstDf[wonBatFirstDf['wonBattingFirst'] == 'yes']

    if not wonBatFirstDf.empty:

        if wonBatFirstDf['innings1Runs'].sum() > 0:
            tempDict['avgWinningScore'] = math.ceil(wonBatFirstDf['innings1Runs'].mean())

        tempDict['lowestTotalDefended'] = wonBatFirstDf['innings1Runs'].min()

    wonFieldFirstDf = tempDf.copy()
    wonFieldFirstDf = wonFieldFirstDf[wonFieldFirstDf['wonFieldingFirst'] == 'yes']

    if not wonFieldFirstDf.empty:

        if wonFieldFirstDf['innings1Runs'].sum() > 0:
            tempDict['avgChasingScore'] = math.ceil(wonFieldFirstDf['innings1Runs'].mean())

    wonChasingDf = tempDf.copy()
    wonChasingDf = wonChasingDf[wonChasingDf['outcome'] != 'draw']
    wonChasingDf = wonChasingDf[wonChasingDf['winner'] != wonChasingDf['innings4Team']]
    tempDict['highestTotalChased'] = wonFieldFirstDf['innings4Runs'].max()

    tempDict['noResults'] = len(tempDf[tempDf['outcome'] == 'no result'])

    if len(tempDf.index) > 0:
        tempDict['winTossWinMatch'] = round(100*len(tempDf[tempDf['winTossWinMatch'] == 'yes'])/len(tempDf.index), 2)
    else:
        tempDict['winTossWinMatch'] = 0

    if tempDict['matches'] > 0:
        tempDict['batFirstWinPercent'] = round(100*tempDict['wonBattingFirst']/tempDict['matches'])
        tempDict['chaseWinPercent'] = round(100*tempDict['wonFieldingFirst']/tempDict['matches'])
    else:
        tempDict['batFirstWinPercent'] = 0
        tempDict['chaseWinPercent'] = 0

    #tempDfCopy = tempDf.copy()
    #tempDfCopy = tempDfCopy[tempDfCopy['outcome'] != 'no result']
    tempDf = tempDf[tempDf['outcome'] != 'no result']
    updateVenueDict(tempDict, tempDf, 'innings', '')

    calculateTypeStats(tempDict, tempDf)
    venuesDf = venuesDf.append(tempDict, ignore_index=True)

    wonBatFirstTotals = pd.DataFrame()
    if not wonBatFirstDf.empty:
        batFirstDict = {}
        updateVenueDict(batFirstDict, wonBatFirstDf, 'innings', '')
        calculateTypeStats(batFirstDict, wonBatFirstDf)
        wonBatFirstTotals = wonBatFirstTotals.append(batFirstDict, ignore_index=True)

    wonFieldFirstTotals = pd.DataFrame()

    if not wonFieldFirstDf.empty:
        fieldFirstDict = {}
        updateVenueDict(fieldFirstDict, wonFieldFirstDf, 'innings', '')
        calculateTypeStats(fieldFirstDict, wonFieldFirstDf)
        wonFieldFirstTotals = wonFieldFirstTotals.append(fieldFirstDict, ignore_index=True)

    return venuesDf, wonBatFirstTotals, wonFieldFirstTotals

def calculateTypeStats(tempDict, tempDf):

    batTypes = ['LHB', 'RHB']
    bowlTypes = ['pace', 'spin']
    paceTypes = ['LF', 'LM', 'LS', 'RF', 'RM', 'RS']
    spinTypes = ['LC', 'LO', 'RL', 'RO']
    phases = ['pp', 'mo', 'death', 'overall', 'mo1', 'mo2', 'mo3']

    for phase in phases:

        updateVenueDict(tempDict, tempDf, 'innings', phase)
        updateTypePercent(tempDict, 'innings', phase)    

    for batType in batTypes:

        updateVenueDict(tempDict, tempDf, 'innings', batType)
        updateTypePercent(tempDict, 'innings', batType)

    for bowlType in bowlTypes:

        updateVenueDict(tempDict, tempDf, 'innings', bowlType)
        updateTypePercent(tempDict, 'innings', bowlType)

    for paceType in paceTypes:

        updateVenueDict(tempDict, tempDf, 'innings', paceType)
        updateTypePercent(tempDict, 'innings', paceType)

    for spinType in spinTypes:

        updateVenueDict(tempDict, tempDf, 'innings', spinType)
        updateTypePercent(tempDict, 'innings', spinType)

def createVenueNotes(inningsTotals, batterTotals, bowlerTotals):

    venues = inningsTotals['venue'].unique().tolist()
    venuesDf = pd.DataFrame()
    #filterVenues = ['Sinhalese Sports Club Ground']   
    filterCities = ['Bridgetown', 'Barbados']
    filterCities = []

    tempVenuesDf = inningsTotals.copy()
    tempVenuesDf['year'] = tempVenuesDf['date1'].str[:4]

    tempVenuesDf.to_excel('tempVenuesDf.xlsx')

    if len(filterCities) > 0:
        tempVenuesDf = tempVenuesDf[tempVenuesDf['city'].isin(filterCities)] 

    if len(filterVenues) > 0:
        tempVenuesDf = tempVenuesDf[tempVenuesDf['venue'].isin(filterVenues)] 

    print(filterCities)
    print(filterVenues)
    tempVenuesDf.to_excel('tempVenuesDf1.xlsx')

    if venueFilter != '':
        venues = tempVenuesDf['venue'].dropna().unique().tolist()
        print(venues)

        for venue in venues:

            venueList = [venue]
            venuesDf, wonBatFirstTotals, wonFieldFirstTotals = buildVenueNotes(venuesDf, tempVenuesDf, venueList)

    elif len(filterVenues) > 0:

        venues = tempVenuesDf['venue'].dropna().unique().tolist()
        venuesDf, wonBatFirstTotals, wonFieldFirstTotals = buildVenueNotes(venuesDf, tempVenuesDf, venues)

    else: 

        venues = tempVenuesDf['venue'].dropna().unique().tolist()
        venuesDf, wonBatFirstTotals, wonFieldFirstTotals = buildVenueNotes(venuesDf, tempVenuesDf, venues)

    venuesDf.to_excel(f"venueNotes {statMode} {venueTitle} {timePeriod}.xlsx")
    
    visualizeVenueNotes(venuesDf, batterTotals, bowlerTotals, wonBatFirstTotals, wonFieldFirstTotals)

def updateTypePercent(tempDict, prefix, suffix):

    for i in range(1, int(maxInnings)+1):

        innsRunsLabel = prefix + str(i) + str(suffix) + 'Runs'
        innsRunsPctLabel = prefix + str(i) + str(suffix) + 'RunsPct'
        if int(tempDict[prefix + str(i) + 'Runs']) > 0:
            tempDict[innsRunsPctLabel] = round(100*int(tempDict[innsRunsLabel])/int(tempDict[prefix + str(i) + 'Runs']), 2)
        else:
            tempDict[innsRunsPctLabel] = 0

        innsBallsLabel = prefix + str(i) + str(suffix) + 'Balls'
        innsBallsPctLabel = prefix + str(i) + str(suffix) + 'BallsPct'
        if int(tempDict[prefix + str(i) + 'Balls']) > 0:
            tempDict[innsBallsPctLabel] = round(100*int(tempDict[innsBallsLabel])/int(tempDict[prefix + str(i) + 'Balls']), 2)
        else:
            tempDict[innsBallsPctLabel] = 0

        innsWicketsLabel = prefix + str(i) + str(suffix) + 'Wickets'
        innsWicketsPctLabel = prefix + str(i) + str(suffix) + 'WicketsPct'
        if int(tempDict[prefix + str(i) + 'Wickets']) > 0:
            tempDict[innsWicketsPctLabel] = round(100*int(tempDict[innsWicketsLabel])/int(tempDict[prefix + str(i) + 'Wickets']), 2)
        else:
            tempDict[innsWicketsPctLabel] = 0

def updateVenueDict(tempDict, tempDf, prefix, suffix):

    for i in range(1, int(maxInnings)+1):

        innsRunsLabel = prefix + str(i) + str(suffix) + 'Runs'
        innsWicketsLabel = prefix + str(i) + str(suffix) + 'Wickets'
        innsBallsLabel = prefix + str(i) + str(suffix) + 'Balls'

        innsLabel = prefix + str(i) + str(suffix)

        if innsRunsLabel in tempDf.columns:
            tempDict[innsRunsLabel] = tempDf[innsRunsLabel].sum()
            tempDict[innsRunsLabel + 'High'] = tempDf[innsRunsLabel].max()
            tempDict[innsRunsLabel + 'Low'] = tempDf[innsRunsLabel].min()
        else:
            tempDict[innsRunsLabel] = 0
            tempDict[innsRunsLabel + 'High'] = 0
            tempDict[innsRunsLabel + 'Low'] = 0

        if innsRunsLabel in tempDf.columns and innsBallsLabel in tempDf.columns and tempDf[innsBallsLabel].sum() > 0:
            tempDict[innsBallsLabel] = tempDf[innsBallsLabel].sum()
            tempDict[innsLabel + 'RunRate'] = round(6*tempDf[innsRunsLabel].astype(float).sum()/tempDf[innsBallsLabel].astype(float).sum(), 2)
        else:
            tempDict[innsBallsLabel] = 0
            tempDict[innsLabel + 'RunRate'] = 0

        if innsRunsLabel in tempDf.columns and innsWicketsLabel in tempDf.columns and innsBallsLabel in tempDf.columns and tempDf[innsWicketsLabel].astype(float).sum() > 0:
            tempDict[innsWicketsLabel] = tempDf[innsWicketsLabel].sum()
            tempDict[innsLabel + 'Average'] = round(tempDf[innsRunsLabel].sum()/tempDf[innsWicketsLabel].sum(), 2)
            tempDict[innsLabel + 'BPD'] = round(tempDf[innsBallsLabel].sum()/tempDf[innsWicketsLabel].sum(), 2)
        else:
            tempDict[innsWicketsLabel] = 0
            tempDict[innsLabel + 'Average'] = 0
            tempDict[innsLabel + 'BPD'] = 0

        if innsRunsLabel in tempDf.columns and innsWicketsLabel in tempDf.columns and innsBallsLabel in tempDf.columns: 
            
            if tempDf[innsWicketsLabel].astype(float).sum() > 0 and tempDf[innsRunsLabel].astype(float).sum() > 0 and tempDf[innsBallsLabel].astype(float).sum() > 0:
                tempDict[innsLabel + 'AvgScore'] = str(math.ceil(tempDf[innsRunsLabel].astype(float).mean())) + '-' + str(math.ceil(tempDf[innsWicketsLabel].astype(float).mean())) + ' (' + str(math.ceil(tempDf[innsBallsLabel].astype(float).mean())) + ')'
            elif tempDf[innsWicketsLabel].astype(float).sum() == 0 and tempDf[innsRunsLabel].astype(float).sum() > 0 and tempDf[innsBallsLabel].astype(float).sum() > 0:
                tempDict[innsLabel + 'AvgScore'] = str(math.ceil(tempDf[innsRunsLabel].astype(float).mean())) + '-0 (' + str(math.ceil(tempDf[innsBallsLabel].astype(float).mean())) + ')'
            else:
                tempDict[innsLabel + 'AvgScore'] = 0

def visualizeVenueNotes(venuesDf, batterTotals, bowlerTotals, wonBatFirstTotals, wonFieldFirstTotals):

    filterCities = []

    tempVenuesDf = venuesDf.copy()
    tempVenuesDf.reset_index(drop=True)
    tempVenuesDf = tempVenuesDf.fillna('')
    if len(filterCities) > 0:
        tempVenuesDf = tempVenuesDf[tempVenuesDf['city'].isin(filterCities)]
    #tempVenuesDf = tempVenuesDf[tempVenuesDf['city'] == 'Manchester']
    tempVenuesDf = tempVenuesDf[tempVenuesDf['venue'] != 'Brabourne Stadium']
    #tempVenuesDf = tempVenuesDf[tempVenuesDf['venue'].isin(filterVenues)]

    global statMode
    tempVenuesDf.to_excel(f"tempDF {statMode} {venueTitle} {timePeriod}.xlsx")

    matchResults = pd.read_excel('matchResults.xlsx')

    for venue in tempVenuesDf['venue'].unique().tolist():

        tempDf = tempVenuesDf.copy()
        tempDf = tempDf[tempDf['venue'] == venue]

        textTitle = str(venue) + ' ' + str(timePeriod) + ' Venue Notes'
        excelTitle = textTitle + '.xlsx'
        htmlTitle = textTitle + '.html'
        pngTitle = textTitle + '.png'

        matchColumns = ['venue', 'city', 'timePeriod', 'matches', 'wonBattingFirst', 'wonFieldingFirst', 'draws', 'winTossWinMatch', 'batFirstWinPercent', 'chaseWinPercent', 'lowestTotalDefended', 'highestTotalChased', 'avgWinningScore', 'avgChasingScore']
        table1 = buildTable(tempDf, matchColumns, 'Match Numbers - Tests', 'total')

        inns1Columns = ['venue', 'innings1AvgScore', 'innings1RunsHigh', 'innings1RunsLow', 'innings1Average', 'innings1BPD', 'innings1RunRate']
        inns2Columns = ['venue', 'innings2AvgScore', 'innings2RunsHigh', 'innings2RunsLow', 'innings2Average', 'innings2BPD', 'innings2RunRate']
        inns3Columns = ['venue', 'innings3AvgScore', 'innings3RunsHigh', 'innings3RunsLow', 'innings3Average', 'innings3BPD', 'innings3RunRate']
        inns4Columns = ['venue', 'innings4AvgScore', 'innings4RunsHigh', 'innings4RunsLow', 'innings4Average', 'innings4BPD', 'innings4RunRate']

        innsColumns = ['AvgScore', 'RunsHigh', 'RunsLow', 'Average', 'BPD', 'RunRate']
        wicketsColumns = ['paceBallsPct', 'paceWicketsPct', 'spinBallsPct', 'spinWicketsPct']
        paceColumns = ['paceBallsPct', 'paceWicketsPct', 'paceAverage', 'paceBPD', 'paceRunRate']
        spinColumns = ['spinBallsPct', 'spinWicketsPct', 'spinAverage', 'spinBPD', 'spinRunRate']

        table2 = buildTable(tempDf, inns1Columns, 'Innings 1', 'total')
        table3 = buildTable(tempDf, inns2Columns, 'Innings 2', 'total')
        table4 = buildTable(tempDf, inns3Columns, 'Innings 3', 'total')
        table5 = buildTable(tempDf, inns4Columns, 'Innings 4', 'total')

        table6 = buildTable(tempDf, innsColumns, 'Innings-wise Numbers', 'innings')
        table7 = buildTable(tempDf, wicketsColumns, 'Pace vs Spin', 'innings')
        table8 = buildTable(tempDf, paceColumns, 'Pace Numbers', 'innings')
        table9 = buildTable(tempDf, spinColumns, 'Spin Numbers', 'innings')

        ppColumns = ['ppAverage', 'ppBPD', 'ppRunRate', 'ppAvgScore']
        moColumns = ['moAverage', 'moBPD', 'moRunRate', 'moAvgScore']
        deathColumns = ['deathAverage', 'deathBPD', 'deathRunRate', 'deathAvgScore']

        table10 = buildTable(tempDf, ppColumns, 'Power Play', 'innings')
        table11 = buildTable(tempDf, moColumns, 'Middle Overs', 'innings')
        table12 = buildTable(tempDf, deathColumns, 'Death Overs', 'innings')

        bowlingTypes, bowlingTypesDf = getBestBowlingTypes(tempDf)

        batterTotals = batterTotals[batterTotals['striker'] != 'Team Average']
        
        #matchIds = ['1381217', '1381218']
        matchIds = []
        filterPlayers = []
        global bestPlayerTeams
        if len(bestPlayerTeams) > 0:
            filterPlayers = getFilterPlayers(bestPlayerTeams)

        colors = ['red', 'yellow', 'yellow', 'green']
        statMode = 'batting'
        bestBatters = getBestPlayers(batterTotals, 'striker', 'overallRuns', 10, matchIds, filterPlayers)
        bestBatters.to_excel('bestBatters.xlsx')
        battersTable = buildTableFromDf(bestBatters, 'Most Runs')
        bestBatters.rename(columns={'name': 'striker'}, inplace = True)
        bestBatters['overallAvgScore'] = bestBatters['striker'] + ' ' + bestBatters['batRuns'].astype(str) + ' (' + bestBatters['batInns'].astype(str) + ')'
        bestBatterScatter = buildPlot(bestBatters['batAvg'].tolist(), bestBatters['batSR'].tolist(), 0, operator.ge, 0, operator.ge, 'or', 'Average', 'Strike Rate', bestBatters, 'Batter Scatter', 'overall', colors)
        bestBatters.rename(columns={'striker': 'name'}, inplace = True)

        statMode = 'bowling'
        bestBowlers = getBestPlayers(bowlerTotals, 'bowler', 'overallWickets', 10, matchIds, filterPlayers)
        bestBowlers.to_excel('bestBowlers.xlsx')
        bowlersTable = buildTableFromDf(bestBowlers, 'Most Wickets')
        bestBowlers.rename(columns={'name': 'bowler'}, inplace = True)
        bestBowlers['overallAvgScore'] = bestBowlers['bowler'] + ' ' + bestBowlers['bowlWickets'].astype(str) + ' (' + bestBowlers['bowlInns'].astype(str) + ')'
        bestBowlerScatter = buildPlot(bestBowlers['bowlAvg'].tolist(), bestBowlers['bowlBPD'].tolist(), 0, operator.ge, 0, operator.ge, 'or', 'Average', 'Strike Rate', bestBowlers, 'Bowler Scatter', 'overall', colors)
        bestBowlers.rename(columns={'bowler': 'name'}, inplace = True)

        allTeamsBestBatters = getBestPlayers(batterTotals, 'striker', 'overallRuns', 10, [], [])
        allTeamsBestBattersTable = buildTableFromDf(allTeamsBestBatters, 'Most Runs')

        allTeamsBestBowlers = getBestPlayers(bowlerTotals, 'bowler', 'overallWickets', 10, [], [])
        allTeamsBestBowlersTable = buildTableFromDf(allTeamsBestBowlers, 'Most Wickets')

        if not bowlerMatchups.empty:
            matchups = buildMatchupTable(bowlerMatchups, matchIds, filterPlayers)
            matchupTables = []

            for df in matchups:

                title = 'Matchups'
                teams = df['batting_team'].unique().tolist()
                if len(teams) == 1:
                    title = 'Matchups - ' + teams[0] + ' Batters'

                df = df.drop('batting_team', axis=1)
                matchupTables.append(buildTableFromDf(df, title))

        playerStats = pd.merge(bestBatters, bestBowlers, on='name', how='outer')
        playerStats = playerStats.sort_values(by='batRuns', ascending=False)
        playerStats = playerStats.fillna('')

        playerStatsTable = buildTableFromDf(playerStats, 'Player Stats')

        pieChartDf = tempDf.copy()
        pieChartDf = pieChartDf[['wonBattingFirst', 'wonFieldingFirst', 'draws']]
        #pieChartDict = pieChartDf.T.to_dict(orient='records')
        pieChartTitle = venueTitle + ' - ' + str(tempDf['matches'].iloc[0]) + ' Tests (' + str(timePeriod) + ')'
        matchResultsPieChart = buildPieChart(pieChartDf, pieChartTitle)

        hLineChartDf = tempDf.copy()
        hLineChartColumns = ['highestTotalChased', 'innings4AvgScore', 'innings3AvgScore', 'innings2AvgScore', 'innings1AvgScore']
        finalColumns = []

        for column in hLineChartColumns:

            if column in hLineChartDf.columns:
                finalColumns.append(column)

        hLineChartDf = hLineChartDf[finalColumns]
        avgScoresLineChart = buildHLineChart(hLineChartDf)

        #phaseWiseStrat = buildHbarStack(wonBatFirstTotals, wonFieldFirstTotals)
        phaseWiseStrat = buildHbarStackTests(venuesDf)
        sankeyDiagrams = buildSankeyDiagram(bowlingTypesDf, tempDf, venueTitle)

        bowlTypesScatterPlots = []

        for innings in range (1, maxInnings+1):
            
            innsColumns = ['Type']
            innsLabel = 'innings' + str(int(innings))
            innsAvgLabel = innsLabel + 'Average'
            innsBPDLabel = innsLabel + 'BPD'

            for column in bowlingTypesDf.columns:

                if innsLabel in column:

                    innsColumns.append(column)

            innsBowlTypesDf = bowlingTypesDf.copy()
            innsBowlTypesDf = innsBowlTypesDf[innsColumns]
            innsBowlTypesDf = innsBowlTypesDf[innsBowlTypesDf[innsLabel + 'BPD'] > 0]
            innsBowlTypesDf.rename(columns={'Type': 'bowler'}, inplace = True)

            if innsAvgLabel in innsBowlTypesDf.columns and innsBPDLabel in innsBowlTypesDf.columns:
                colors = ['red', 'yellow', 'yellow', 'green']
                bowlingTypesScatter = buildPlot(innsBowlTypesDf[innsAvgLabel].tolist(), innsBowlTypesDf[innsBPDLabel].tolist(), 50, operator.le, 150, operator.le, 'or', 'Average', 'Strike Rate', innsBowlTypesDf, 'Innings ' + str(innings), 'overall', colors)
                bowlTypesScatterPlots.append(bowlingTypesScatter)

        lastNMatchesTable = buildLastNMatchesTable(5, str(venue), '', 'Venue')

        matchInnsTotals = pd.read_excel(f"Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")

        tempMatchResults = pd.merge(matchResults, matchInnsTotals, on='matchId', how='outer')
        tempMatchResults.drop([i for i in tempMatchResults.columns if '_x' in i], axis=1, inplace=True)

        renameDict = {}
        for column in tempMatchResults.columns:

            if '_y' in column:
                renameDict[column] = column.replace('_y', '')

        tempMatchResults.rename(columns=renameDict, inplace=True)

        tempMatchResults.to_excel('tempMatchResults.xlsx')

        #team1Table = buildLastNMatchesTable(5, str(venue), bestPlayerTeams[0], bestPlayerTeams[0])
        #team2Table = buildLastNMatchesTable(5, str(venue), bestPlayerTeams[1], bestPlayerTeams[1])

        teamMatchesTable = getTeamMatchesTable(bestPlayerTeams, matchResults)

        output_file(filename = htmlTitle)

        grid = layout([
            [table1],
            [table6],
            [table8, table9],
            [table10, table11, table12],
            [bowlingTypes[0], bowlingTypes[1]],
            [battersTable, bowlersTable], 
            [allTeamsBestBattersTable, allTeamsBestBowlersTable],
            [lastNMatchesTable],
            teamMatchesTable
        ], sizing_mode='stretch_width')

        plotGrid = layout([
            [matchResultsPieChart, avgScoresLineChart],
            [phaseWiseStrat],
            [sankeyDiagrams[0], bowlTypesScatterPlots[0]],
            [sankeyDiagrams[1], bowlTypesScatterPlots[1]],
            [sankeyDiagrams[2], bowlTypesScatterPlots[2]],
            [sankeyDiagrams[3], bowlTypesScatterPlots[3]],
            [batterScatter, bowlerScatter]
        ], sizing_mode='scale_both', width=1200, height=1200)

        show(grid)
        #export_png(grid, filename=pngTitle, width=1200, height=1200)

        htmlTitle = 'Plots ' + htmlTitle
        output_file(filename = htmlTitle)

        show(plotGrid)
        pngTitle = 'Plots ' + pngTitle
        #export_png(plotGrid, filename=pngTitle, width=1200, height=1200)

def getTeamMatchesTable(teams, matchResults):

    tables = []

    for team in teams:

        tempMatchResults = matchResults.copy()
        tempMatchResults = tempMatchResults.sort_values(by=['date1'], ascending=False)
        tempMatchResults = tempMatchResults[(tempMatchResults['team1'] == team) | (tempMatchResults['team2'] == team)]
        tempMatchResults = tempMatchResults.head(5)

        tempDf = pd.DataFrame()

        for index, row in tempMatchResults.iterrows():

            tempDict = {}
            tempDict['Date'] = row['date1']
            tempDict['Venue'] = row['venue']
            tempDict['Opponent'] = row['team2'] if row['team1'] == team else row['team1']
            tempDict['Result'] = 'W' if row['winner'] == team else 'L'
            tempDict['Result'] = 'Draw' if row['outcome'] == 'draw' else 'W' if row['winner'] == team else 'L'
            tempDf = tempDf.append(tempDict, ignore_index=True)

        print(tempDf)
        table = buildTableFromDf(tempDf, 'Past Results ' + team)
        tables.append(table)

    if len(teams) == 2:

        h2hResults = matchResults.copy()
        h2hResults = h2hResults.sort_values(by=['date1'], ascending=False)
        h2hResults = h2hResults[((h2hResults['team1'] == teams[0]) & (h2hResults['team2'] == teams[1]) | (h2hResults['team1'] == teams[1]) & (h2hResults['team2'] == teams[0]))]
        h2hResults = h2hResults.head(5)

        tempDf = pd.DataFrame()

        for index, row in h2hResults.iterrows():

            tempDict = {}
            tempDict['Date'] = row['date1']
            tempDict['Venue'] = row['venue']
            tempDict['Winner'] = 'Draw' if row['outcome'] == 'draw' else row['winner']
            tempDf = tempDf.append(tempDict, ignore_index=True)

        print(tempDf)
        table = buildTableFromDf(tempDf, 'Head to Head')
        tables.append(table)

    return tables

def buildLastNMatchesTable(n, venue, team, title):

    matchResults = pd.read_excel(f"Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")
    matchResults.to_excel('tempMatchResultsTable.xlsx')
    print(filterVenues)
    #matchResults = matchResults[matchResults['venue'].isin(filterVenues)]

    if team != '':
        matchResults = matchResults[(matchResults['team1'] == team) | (matchResults['team2'] == team)]
    else:
        matchResults = matchResults[matchResults['venue'].isin(filterVenues)]

    matchResults.to_excel(title + 'tempMatchResultsTable1.xlsx')

    matchResults = matchResults.sort_values(by=['date1'], ascending=False)
    matchResults = matchResults.head(n)
    matchResults.to_excel('tempMatchResultsTable2.xlsx')

    tempDf = pd.DataFrame()

    for index, row in matchResults.iterrows():

        tempDict = {}
        tempDict['Date'] = row['date1']
        tempDict['Winner'] = 'Draw' if row['outcome'] == 'draw' else row['winner']
        teams = [row['team1'], row['team2']]
        scores = ''

        for innings in range (1, maxInnings+1):

            innsLabel = 'innings' + str(innings)

            if row[innsLabel + 'Team'] in teams:

                if innings > 1:
                    scores += ', '
                
                innsBattingTeam = teams[0] if row[innsLabel + 'Team'] == teams[1] else teams [1]
                innsBattingRuns = str(int(row[innsLabel + 'Runs']))
                innsBattingWickets = str(int(row[innsLabel + 'Wickets']))
                innsScore = innsBattingTeam + ' ' + innsBattingRuns + '-' + innsBattingWickets
                scores += innsScore

        #tempDict['Match Scores'] = row['innings2Team'] + ' ' + str(int(row['innings1Runs'])) + '-' + str(int(row['innings1Wickets'])) + ', ' + row['innings1Team'] + ' ' + str(int(row['innings2Runs'])) + '-' + str(int(row['innings2Wickets']))
        #tempDict['Match Scores'] = tempDict['Match Scores'] + ', ' + row['innings4Team'] + ' ' + str(int(row['innings3Runs'])) + '-' + str(int(row['innings3Wickets'])) + ', ' + row['innings3Team'] + ' ' + str(int(row['innings4Runs'])) + '-' + str(int(row['innings4Wickets']))

        tempDict['Match Scores'] = scores

        tempDf = tempDf.append(tempDict, ignore_index=True)

    table = buildTableFromDf(tempDf, 'Past Results ' + title)
    return table

def getFilterPlayers(teams):

    matchIndex = pd.read_excel('matchIndex.xlsx')
    players = []

    for team in teams:

        tempIndex = matchIndex.copy()
        tempIndex = tempIndex[tempIndex['team'] == team]
        tempIndex = tempIndex.sort_values(by='date1', ascending=False)

        matchIds = tempIndex['matchId'].unique().tolist()
        matchIds = matchIds[:5]

        tempIndex = tempIndex[tempIndex['matchId'].isin(matchIds)]
        teamPlayers = tempIndex['player'].unique().tolist()
        players = players + teamPlayers

    print(players)
    return players

def buildSankeyDiagram(df, pvsDf, venueTitle):

    bowlTypes = ['Pace', 'Spin']
    paceTypes = ['Left arm Fast', 'Left arm Medium', 'Left arm Slow', 'Right arm Fast', 'Right arm Medium', 'Right arm Slow']
    spinTypes = ['Left arm Orthodox', 'Left arm Chinaman', 'Right arm Leg Break', 'Right arm Off Break']
    sankeys = []

    for innings in range (1, maxInnings+1):

        diagramDf = pd.DataFrame()
        diagramDict = {}
        innsLabel = 'innings' + str(innings)
        wktsPctLabel = innsLabel + 'WicketsPct'
        wktsLabel = innsLabel + 'Wickets'
        avgLabel = innsLabel + 'Average'
        bpdLabel = innsLabel + 'BPD'
        rrLabel = innsLabel + 'RunRate'

        for type in bowlTypes:

            tempDf = df.copy()
            typeLabel = ''
            
            if type == 'Pace':
                tempDf = tempDf[tempDf['Type'].isin(paceTypes)]
                typeLabel = 'pace'
            if type == 'Spin':
                tempDf = tempDf[tempDf['Type'].isin(spinTypes)]
                typeLabel = 'spin'

            typeWktsPct = innsLabel + typeLabel + 'WicketsPct'
            typeWkts = innsLabel + typeLabel + 'Wickets'
            typeAvg = innsLabel + typeLabel + 'Average'
            typeBpd = innsLabel + typeLabel + 'BPD'
            typeRR = innsLabel + typeLabel + 'RunRate'
            typeValue = ''

            if typeWkts in pvsDf.columns and typeWktsPct in pvsDf.columns and typeAvg in pvsDf.columns and typeBpd in pvsDf.columns and typeRR in pvsDf.columns:
                
                for index, row in pvsDf.iterrows():

                    typeLabel = type + ' (Avg ' + str(row[typeAvg]) + ', SR ' + str(row[typeBpd]) + ', ER ' + str(row[typeRR]) + ')'
                    #typeLabel = type + ' (ER ' + str(row[typeRR]) + ')'
                    typeValue = row[typeWktsPct]

            diagramDict['source'] = 'Bowler Wickets'
            diagramDict['target'] = typeLabel
            diagramDict['value'] = typeValue
            diagramDf = diagramDf.append(diagramDict, ignore_index=True)

            for index, row in tempDf.iterrows():

                diagramDict = {}
                diagramDict['source'] = typeLabel

                label = row['Type'] + ' (Avg ' + str(row[avgLabel]) + ', SR ' + str(row[bpdLabel]) + ', ER ' + str(row[rrLabel]) + ')'
                label = row['Type'] + ' ' + str(int(row[wktsLabel])) + ' Wkts @ ' + str(row[avgLabel])

                diagramDict['target'] = label
                diagramDict['value'] = row[wktsPctLabel]
                diagramDf = diagramDf.append(diagramDict, ignore_index=True)

            diagramDf = diagramDf[diagramDf['value'] > 0]

        title = venueTitle + ' ' + timePeriod + ' - Innings ' + str(innings) + ' - Percent Wickets Taken by Bowling Type'
        diagramDf.to_excel(title + ' diagramDf.xlsx')
        edges = diagramDf.copy()
        sankey = hv.Sankey(edges, label=title)
        sankey.opts(label_position='left', edge_color='target', node_color='index', cmap='tab20', width=700, height=500)
        fig = hv.render(sankey)
        fig.toolbar_location=None
        sankeys.append(fig)

        renderer = hv.renderer('bokeh')
        renderer.save(sankey, title)
    return sankeys

def buildHbarStackTests(venuesDf):

    innsValues = []
    innsValuesList = []

    for innings in range(1, maxInnings+1):

        innsPhases = {}
        for index, row in venuesDf.iterrows():

            p1AvgScore = 'innings' + str(innings) + 'ppAvgScore'
            p2AvgScore = 'innings' + str(innings) + 'moAvgScore'
            p3AvgScore = 'innings' + str(innings) + 'deathAvgScore'

            columns = [p1AvgScore, p2AvgScore, p3AvgScore]

            for column in columns:

                if column in venuesDf.columns:
                    innsPhases[column] = row[column]
                else:
                    innsPhases[column] = 0

        innsValues.append(list(innsPhases.values()))
        innsValuesList = innsValuesList + list(innsPhases.values())

    print('#### innsValuesList ####')
    print(innsValuesList)

    print('#### innsValues ####')
    print(innsValues)

    xValue1 = int(ppEnd)
    xValue2 = int(moEnd) - int(ppEnd)
    xValue3 = int(deathEnd) - int(moEnd)

    xValue1 = 30
    xValue2 = 30
    xValue3 = 30

    source = ColumnDataSource(data=dict(
        y=['4', '3', '2', '1'],
        x1=[xValue1, xValue1, xValue1, xValue1],
        x2=[xValue2, xValue2, xValue2, xValue2],
        x3=[xValue3, xValue3, xValue3, xValue3],
        innsValues=innsValues,
        xLabels=[15, 45, 75, 105]
    ))

    labels = {
        'x': [15, 45, 75, 15, 45, 75, 15, 45, 75, 15, 45, 75],
        'y': ['1', '1', '1', '2', '2', '2', '3', '3', '3', '4', '4', '4'],
        'labels': innsValuesList
    }

    p = figure(width=400, height=100, y_range = source.data["y"], title='Phase-wise Batting Strategy', toolbar_location=None)

    colors = ['#5a8691', '#55ae6a', '#ffa600']

    xAxisLabel = f"Powerplay (0-{str(int(ppEnd))})       Middle Overs ({str(int(moStart))}-{str(int(moEnd))})       Death Overs ({str(int(deathStart))}-{str(int(deathEnd))})"
    xAxisLabel = 'Overs'

    p.hbar_stack(['x1', 'x2', 'x3'], y='y', height=0.5, color=colors, source=source)
    p.xaxis.axis_label = xAxisLabel
    p.yaxis.axis_label = "Innings"

    setLabels = LabelSet(x="x", y="y", text="labels", source=ColumnDataSource(labels), text_align='center', text_color='white', y_offset=-4)
    p.add_layout(setLabels)

    return p

def buildHbarStack(wonBatFirstDf, wonFieldFirstDf):

    inns1Phases = {}
    for index, row in wonBatFirstDf.iterrows():

        #inns1Phases['innings1ppAvgScore'] = row['innings1ppAvgScore']
        #inns1Phases['innings1moAvgScore'] = row['innings1moAvgScore']
        #inns1Phases['innings1deathAvgScore'] = row['innings1deathAvgScore']

        for column in ['innings1ppAvgScore', 'innings1mo1AvgScore', 'innings1mo2AvgScore', 'innings1mo3AvgScore', 'innings1deathAvgScore']:

            if column in wonBatFirstDf.columns:
                inns1Phases[column] = row[column]
            else:
                inns1Phases[column] = 0

    inns1Values = list(inns1Phases.values())

    inns2Phases = {}
    for index, row in wonFieldFirstDf.iterrows():

        #inns2Phases['innings2ppAvgScore'] = row['innings2ppAvgScore']
        #inns2Phases['innings2moAvgScore'] = row['innings2moAvgScore']
        #inns2Phases['innings2deathAvgScore'] = row['innings2deathAvgScore']

        for column in ['innings2ppAvgScore', 'innings2mo1AvgScore', 'innings2mo2AvgScore', 'innings2mo3AvgScore', 'innings2deathAvgScore']:

            if column in wonBatFirstDf.columns:
                inns2Phases[column] = row[column]
            else:
                inns2Phases[column] = 0

    inns2Values = list(inns2Phases.values())

    xValue1 = int(ppEnd)
    xValue2 = int(moEnd) - int(ppEnd)
    xValue3 = int(deathEnd) - int(moEnd)

    xValue1 = 6
    xValue2 = 3
    xValue3 = 3
    xValue4 = 3
    xValue5 = 5

    source = ColumnDataSource(data=dict(
        y=['2', '1'],
        x1=[xValue1, xValue1],
        x2=[xValue2, xValue2],
        x3=[xValue3, xValue3],
        x4=[xValue4, xValue4],
        x5=[xValue5, xValue5],
        innsValues=[inns1Values, inns2Values],
        xLabels=[3, 7.5, 10.5, 13.5, 17.5]
    ))

    labels = {
        'x': [3, 7.5, 10.5, 13.5, 17.5, 3, 7.5, 10.5, 13.5, 17.5],
        'y': ['1', '1', '1', '1', '1', '2', '2', '2', '2', '2'],
        'labels': inns1Values + inns2Values
    }

    p = figure(width=400, height=100, y_range = source.data["y"], title='Phase-wise Batting Strategy', toolbar_location=None)

    colors = ['#5a8691', '#55ae6a', '#ffa600', '#5a8691', '#55ae6a']

    xAxisLabel = f"Powerplay (0-{str(int(ppEnd))})       Middle Overs ({str(int(moStart))}-{str(int(moEnd))})       Death Overs ({str(int(deathStart))}-{str(int(deathEnd))})"
    xAxisLabel = 'Overs'

    p.hbar_stack(['x1', 'x2', 'x3', 'x4', 'x5'], y='y', height=0.5, color=colors, source=source)
    p.xaxis.axis_label = xAxisLabel
    p.yaxis.axis_label = "Innings"

    setLabels = LabelSet(x="x", y="y", text="labels", source=ColumnDataSource(labels), text_align='center', text_color='white', y_offset=-4)
    p.add_layout(setLabels)

    return p

def buildHLineChartStacked(hLineChartStackedDf):

    tempDict = hLineChartStackedDf.to_dict('records')[0]

    innings = ['1', '2', '3', '4']
    values = ['high', 'low', 'average']

    high = []
    low = []
    average = []

    for inning in innings:

        innsLabel = 'innings' + str(inning) + 'Runs'
        high.append(tempDict[innsLabel + 'High'])
        low.append(tempDict[innsLabel + 'Low'])

        tempValues = tempDict['innings' + str(inning) + 'AvgScore'].split(' ')
        scores = tempValues[0].split('-')
        value = scores[0]
        strValue = str(tempValues[0])
        average.append(value)

    data = {'innings': innings,
        'high': high,
        'low': low,
        'average': average}

    x = [ (inning, value) for inning in innings for value in values]
    counts = sum(zip(data['high'], data['low'], data['average']), ()) # like an hstack

    source = ColumnDataSource(data=dict(x=x, counts=counts))

    p = figure(x_range=FactorRange(*x), height=350, title="Runs by Innings",
            toolbar_location=None, tools="")

    p.vbar(x='x', top='counts', width=0.9, source=source)

    p.y_range.start = 0
    p.x_range.range_padding = 0.1
    p.xaxis.major_label_orientation = 1
    p.xgrid.grid_line_color = None

    show(p)

def buildHLineChart(hLineChartDf):

    values = []
    right = []
    labels = []
    strValues = []

    i = 1

    for index, row in hLineChartDf.iterrows():

        for column in hLineChartDf.columns:

            if column in ('innings1AvgScore', 'innings2AvgScore', 'innings3AvgScore', 'innings4AvgScore'):
                tempValues = row[column].split(' ')
                scores = tempValues[0].split('-')
                value = scores[0]
                strValue = str(tempValues[0])
            else:
                if row[column] == '':
                    value = 0
                else:
                    value = int(row[column])

                strValue = str(value)

            values.append(value)
            labels.append(column)
            right.append(value)
            strValues.append(strValue)

            i = i + 1

    source = ColumnDataSource(dict(x=values, y=labels, right=right, strValues=strValues))

    labelSet = LabelSet(x=50, y='y', text='strValues', level='glyph',
                  text_align='center', source=source, text_color='white', y_offset=-4)

    # instantiating the figure object
    graph = figure(y_range = source.data["y"], height=350, toolbar_location=None)

    # height / thickness of the bars 
    height = 0.4
    
    # plotting the graph
    graph.hbar(source=source, y='y',
            right = 'right',
            height = height, fill_color='#5b296d')

    graph.add_layout(labelSet)
    
    # displaying the model
    return graph

def buildPieChart(pieChartDf, venueTitle):

    x = {}

    for index, row in pieChartDf.iterrows():

        for column in pieChartDf.columns:
            x[column] = row[column]

    print(x)
    data = pd.Series(x).reset_index(name='value').rename(columns={'index': 'result'})
    data['angle'] = data['value']/data['value'].sum() * 2*pi
    #data['color'] = Category20c[len(x)]

    df = pd.DataFrame()
    df['angle'] = data['value'] / data['value'].sum() * 2 * pi
    value = list(data["value"])
    #df["cumulative_angle"] = [(sum(value[0:i + 1]) - (item / 2)) / sum(value) * 2 * pi for i, item in enumerate(value)]

    # Calculate cumulative angle
    cumulative_angle = []

    # Calculate the total sum of 'value' once to avoid recomputation
    total_sum = sum(value)

    for i, item in enumerate(value):
        if total_sum != 0:
            angle = (sum(value[0:i + 1]) - (item / 2)) / total_sum * 2 * pi
        else:
            angle = 0  # Handle the case where the denominator is zero
        cumulative_angle.append(angle)

    df["cumulative_angle"] = cumulative_angle

    df['cos'] = np.cos(df['cumulative_angle']) * 0.3
    df['sin'] = np.sin(df['cumulative_angle']) * 0.3
    if len(df.index) > 3:
        df["color"] = GnBu[len(df.index)]
    elif len(df.index) == 3:
        df["color"] = ['#003f5c', '#bc5090', '#ffa600']
    elif len(df.index) == 2:
        df["color"] = ['#003f5c', '#bc5090']
    else:
        df["color"] = ["steelblue"]
    df["percentage"] = data["value"] / data["value"].sum()
    df['percentage'] = df['percentage'].astype(float).map(lambda n: '{:.1%}'.format(n))
    df["percentage"] = df['percentage'].astype(str)
    df['result'] = data['result']
    df['value'] = data['value']
    df['label'] = df['result'].map(str) + ' ' + df['value'].map(str)
    #df["label"] = df["label"].str.pad(35, side="left")
    
    data["value"] = data['value'].astype(str)

    source = ColumnDataSource(df)

    p = figure(toolbar_location=None, x_range=(-1.0, 1.0), y_range=(-1.0, 1.0),
           tooltips=[("percentage", "@percentage")], tools="hover", title=venueTitle, height=350)
    pie_chart = p.wedge(x=0, y=0, radius=0.5,
                        start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                        line_color="white", fill_color='color', source=source)

    labels = LabelSet(x="cos", y="sin", y_offset=0, text='label', text_align="center", angle=0, source=source,render_mode='canvas', text_color='white', text_font_size="10pt")

    p.add_layout(labels)

    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None

    return p

def buildMatchupTable(matchupDf, matchIds, matchPlayers):

    tempDf = matchupDf.copy()

    if len(matchIds) > 0:
        matchIndex = pd.read_excel('matchIndex.xlsx')
        matchIndex = matchIndex[matchIndex['matchId'].astype(str).isin(matchIds)]
        matchPlayers = matchIndex['player'].unique().tolist()
        tempDf = tempDf[(tempDf['striker'].isin(matchPlayers)) | (tempDf['bowler'].isin(matchPlayers))]
    elif len(matchPlayers) > 0:
        tempDf = tempDf[(tempDf['striker'].isin(matchPlayers)) | (tempDf['bowler'].isin(matchPlayers))]

    print('#### matchupTable ####')
    print(tempDf)

    if tempDf.empty:
        tempDf = matchupDf.copy()

    tempDf[['mStriker', 'mBowler']] = tempDf['matchup'].str.split(' vs ', 1, expand=True)

    matchupDfs = []

    batTypes = ['LHB', 'RHB']
    bowlTypes = ['LF', 'LM', 'LS', 'LC', 'LO', 'RF', 'RM', 'RS', 'RL', 'RO']

    ppMatchup = tempDf.copy()
    ppMatchup = ppMatchup[ppMatchup['mStriker'].isin(matchPlayers)]
    ppMatchup = ppMatchup[ppMatchup['mBowler'].isin(matchPlayers)]

    teams = ppMatchup['batting_team'].unique().tolist()

    for team in teams:

        tempMatchupDf = ppMatchup.copy()
        tempMatchupDf = tempMatchupDf[tempMatchupDf['batting_team'] == team]
        matchupDfs.append(tempMatchupDf)

    ppMatchup = tempDf.copy()
    ppMatchup = ppMatchup[ppMatchup['mStriker'].isin(matchPlayers)]
    ppMatchup = ppMatchup[ppMatchup['mBowler'].isin(bowlTypes)]
    #matchupDfs.append(ppMatchup)

    ppMatchup = tempDf.copy()
    ppMatchup = ppMatchup[ppMatchup['mStriker'].isin(batTypes)]
    ppMatchup = ppMatchup[ppMatchup['mBowler'].isin(matchPlayers)]
    #matchupDfs.append(ppMatchup)

    ppMatchup = tempDf.copy()
    ppMatchup = ppMatchup[ppMatchup['mStriker'].isin(batTypes)]
    ppMatchup = ppMatchup[ppMatchup['mBowler'].isin(bowlTypes)]
    #matchupDfs.append(ppMatchup)

    columns = []
    renameDict = {}

    columns = ['matchup', 'batting_team', 'overallRuns', 'overallBalls', 'overallWickets', 'overallER']

    for column in columns: 

        if 'overall' in column:
            renameDict[column] = column.replace('overall', '')

    updatedMatchups = []
    for df in matchupDfs:
        df = df[columns]
        df.rename(columns=renameDict, inplace = True)
        df = df.round(2)
        df = df[(df['Balls'] >= 6) | (df['Wickets'] >= 1)]
        df = df.sort_values(by='ER', ascending=False)
        updatedMatchups.append(df)

    return updatedMatchups

def getBestPlayers(df, column, sortColumn, n, matchIds, matchPlayers):

    tempDf = df.copy()
    tempDf = tempDf[tempDf['teamAvgExclBatter'] > 0]
    tempDf = tempDf[tempDf[column] != 'Player Average']
    tempDf = tempDf[tempDf[column] != 'Team Average']

    if len(matchIds) > 0:
        matchIndex = pd.read_excel('matchIndex.xlsx')
        matchIndex = matchIndex[matchIndex['matchId'].astype(str).isin(matchIds)]
        matchPlayers = matchIndex['player'].unique().tolist()
        tempDf = tempDf[tempDf[column].isin(matchPlayers)]
    elif len(matchPlayers) > 0:
        tempDf = tempDf[tempDf[column].isin(matchPlayers)]
    else:
        tempDf = tempDf[tempDf['overallInns'] >= 1]

    if tempDf.empty:
        tempDf = df.copy()
        tempDf = tempDf[tempDf['teamAvgExclBatter'] > 0]
        tempDf = tempDf[tempDf[column] != 'Player Average']
        tempDf = tempDf[tempDf[column] != 'Team Average']
        tempDf = tempDf[tempDf['overallInns'] >= 1]

    columns = []
    renameDict = {}

    if column == 'striker':
        columns = [column, 'batting_team', 'overallInns', 'overallRuns', 'overallAvg', 'overallSR', 'overallBPD']
        sortAscending = False
        renameDict[column] = 'name'
        prefix = 'bat'

    if column == 'bowler':
        columns = [column, 'bowling_team', 'overallInns', 'overallWickets', 'overallAvg', 'overallBPD', 'overallER']
        tempDf = tempDf[tempDf['overallWickets'] >= 1]
        sortAscending = False
        renameDict[column] = 'name'
        prefix = 'bowl'

    for column in columns: 

        if 'overall' in column:
            renameDict[column] = column.replace('overall', prefix)

    tempDf = tempDf[columns]
    tempDf = tempDf.sort_values(by=sortColumn, ascending=sortAscending)
    tempDf.rename(columns=renameDict, inplace = True)
    tempDf = tempDf.head(n)
    tempDf = tempDf.round(2)

    return tempDf

def getBestBowlingTypes(tempDf):

    paceTypes = ['LF', 'LM', 'LS', 'RF', 'RM', 'RS']
    spinTypes = ['LC', 'LO', 'RL', 'RO']
    bowlerTypes = ['LF', 'LM', 'LS', 'LC', 'LO', 'RF', 'RM', 'RS', 'RL', 'RO']

    ballsPctColumns = []
    wicketsPctColumns = []
    wicketsColumns = []
    averageColumns = []
    bpdColumns = []
    runRateColumns = []
    allColumns = []
    finalColumns = []
    renameDict = {}

    tables = []

    for bowlerType in bowlerTypes:

        for i in range(1, int(maxInnings)+1):

            if ('innings' + str(i) + bowlerType + 'BallsPct') in tempDf.columns:

                ballsPctColumns.append('innings' + str(i) + bowlerType + 'BallsPct')
                wicketsPctColumns.append('innings' + str(i) + bowlerType + 'WicketsPct')
                wicketsColumns.append('innings' + str(i) + bowlerType + 'Wickets')
                averageColumns.append('innings' + str(i) + bowlerType + 'Average')
                bpdColumns.append('innings' + str(i) + bowlerType + 'BPD')
                runRateColumns.append('innings' + str(i) + bowlerType + 'RunRate')

                allColumns.append('innings' + str(i) + bowlerType + 'BallsPct')
                allColumns.append('innings' + str(i) + bowlerType + 'WicketsPct')
                allColumns.append('innings' + str(i) + bowlerType + 'Wickets')
                allColumns.append('innings' + str(i) + bowlerType + 'Average')
                allColumns.append('innings' + str(i) + bowlerType + 'BPD')
                allColumns.append('innings' + str(i) + bowlerType + 'RunRate')

    for i in range(1, int(maxInnings)+1):

        innsColumns = ['Type']       

        innsColumns.append('innings' + str(i) + 'BallsPct')
        innsColumns.append('innings' + str(i) + 'WicketsPct')
        innsColumns.append('innings' + str(i) + 'Wickets')
        innsColumns.append('innings' + str(i) + 'Average')
        innsColumns.append('innings' + str(i) + 'BPD')
        innsColumns.append('innings' + str(i) + 'RunRate')

        renameDict['innings' + str(i) + 'BallsPct'] = 'BallsPct'
        renameDict['innings' + str(i) + 'WicketsPct'] = 'WicketsPct'
        renameDict['innings' + str(i) + 'Wickets'] = 'Wickets'
        renameDict['innings' + str(i) + 'Average'] = 'Average'
        renameDict['innings' + str(i) + 'BPD'] = 'BPD'
        renameDict['innings' + str(i) + 'RunRate'] = 'RunRate'

        finalColumns.append(innsColumns)

    bowlerTypesDf = tempDf.copy()
    bowlerTypesDf = bowlerTypesDf[allColumns]

    innsBowlingColumns = [ballsPctColumns, wicketsPctColumns, wicketsColumns, averageColumns, bpdColumns, runRateColumns]
    innsBowlingLabels = ['BallsPct', 'WicketsPct', 'Wickets', 'Average', 'BPD', 'RunRate']

    innsBowlingTypes = pd.DataFrame()
    
    for i in range(0, len(innsBowlingColumns)):

        columns = innsBowlingColumns[i]
        label = innsBowlingLabels[i]
        
        tempDf = bowlerTypesDf.copy()
        tempDf = tempDf[columns]

        for i in range(1, int(maxInnings)+1):

            tempDf = tempDf.T
            tempDf = tempDf.sort_values(by=tempDf.columns[0], ascending=True).T
            topFiveDf = tempDf.head(10)
            columns = topFiveDf.columns
            columns = [sub.replace('innings', '') for sub in columns]
            columns = [sub[1:] for sub in columns]

            table = buildTable(topFiveDf, columns, 'Best Bowling Types', 'innings')
            #tables.append(table)

            #topFiveDf = topFiveDf[columns]
            topFiveDf = topFiveDf.T
            topFiveDf.reset_index(inplace = True)
            topFiveDf.rename(columns={topFiveDf.columns[0]: 'Type', topFiveDf.columns[1]: 'innings' + str(i) + label}, inplace = True)
            topFiveDf = topFiveDf[topFiveDf['Type'].str.contains('innings' + str(i))]
            topFiveDf['Type'] = topFiveDf['Type'].str[8:]
            topFiveDf['Type'] = topFiveDf['Type'].str[:2]

            if not innsBowlingTypes.empty:
                innsBowlingTypes = pd.merge(innsBowlingTypes, topFiveDf, how='outer', on='Type')
            else:
                innsBowlingTypes = topFiveDf.copy()

    
    innsBowlingTypes.replace(bowlerTypeMapping, inplace=True)

    for i in range(0, len(finalColumns)):

        tempDf = innsBowlingTypes.copy()
        columns = finalColumns[i]
        tempDf = tempDf[columns]
        tempDf = tempDf[tempDf['innings' + str(i+1) + 'BallsPct'] > 0]
        tempDf = tempDf.sort_values(by='innings' + str(i+1) + 'Average', ascending=True)

        tempDf.rename(columns=renameDict, inplace = True)

        table = buildTableFromDf(tempDf, 'Innings ' + str(i+1))
        tables.append(table)

    return tables, innsBowlingTypes

def buildTableFromDf(tempDf, title):

    columns = []

    for column in tempDf.columns:
        columns.append(TableColumn(field=column, title=column, width=1))

    data = tempDf.to_dict('list')
    source = ColumnDataSource(data)

    tableHeight = (len(tempDf.index) + 1)*25

    data_table = DataTable(source=source, columns=columns, index_position=None, autosize_mode='fit_columns', height=tableHeight)

    div = Div(text=title, align='center')

    grid = layout([[div],[data_table]], sizing_mode='stretch_width')

    return grid

def buildTable(tempDf, filterColumns, title, type):

    matchDict = {}
    columns = []

    if type == 'innings':

        inningsDf = pd.DataFrame()

        for i in range(1, maxInnings+1):

            innsDict = {}
            innsDict[type] = i

            for column in filterColumns:

                tempColumn = 'innings' + str(i) + str(column)

                if tempColumn in tempDf.columns:
                    innsDict[column] = tempDf[tempColumn].tolist()[0]

            inningsDf = inningsDf.append(innsDict, ignore_index=True)

        filterColumns.insert(0, 'innings')

        for column in filterColumns:
        
            columnTitle = column
            columns.append(TableColumn(field=column, title=columnTitle, width=1))

        inningsDf['innings'] = inningsDf['innings'].astype(int)
        inningsDf['innings'] = inningsDf['innings'].astype(str)
        #data = inningsDf.set_index('innings').to_dict('list')
        data = inningsDf.to_dict('list')
        source = ColumnDataSource(data) 
        
        #, autosize_mode='fit_viewport'
        data_table = DataTable(source=source, columns=columns, index_position=None, autosize_mode='fit_columns', height=125)

        div = Div(text=title, align='center')

        grid = layout([[div],[data_table]], sizing_mode='stretch_width')

        return grid

    if type == 'total':

        for column in filterColumns:

            if column in tempDf.columns:
                matchDict[column] = tempDf[column]
                columnTitle = column

                if 'innings' in column:
                    columnTitle = column[8:]
                    
                columns.append(TableColumn(field=column, title=columnTitle, width=1))

        data = matchDict
        source = ColumnDataSource(data) 
        
        #, autosize_mode='fit_viewport'
        data_table = DataTable(source=source, columns=columns, index_position=None, autosize_mode='fit_columns', height=100)

        div = Div(text=title, align='center')

        grid = layout([[div],[data_table]], sizing_mode='stretch_width')

        return grid

def processMultipleFiles(mode, startDate, endDate):

    global statMode
    statMode = mode

    global timePeriod

    if startDate[:4] == endDate[:4]:
        timePeriod = startDate[:4]
    else:
        timePeriod = startDate[:4] + '-' + endDate[:4]

    fileNames = getValidFileNames(startDate, endDate)
    #fileNames = []

    indiaFileNames = ['1243388.csv', 	'1243390.csv', 	'1243391.csv', 	'1243392.csv', 	'1262758.csv', 	'1262759.csv', 	'1262760.csv', 	'1273727.csv', 	'1273739.csv', 	'1273744.csv', 	'1278673.csv', 	'1278680.csv', 	'1278681.csv', 	'1278684.csv', 	'1278687.csv', 	'1278688.csv', 	'1278689.csv', 	'1278690.csv', 	'1278691.csv', 	'1303308.csv', 	'1276904.csv', 	'1276905.csv', 	'1317903.csv', 	'1317904.csv', 	'1317906.csv', 	'1317907.csv', 	'1327272.csv', 	'1327276.csv', 	'1327277.csv', 	'1327279.csv', 	'1327503.csv', 	'1327507.csv', 	'1298157.csv', 	'1298164.csv', 	'1298169.csv', 	'1298176.csv', 	'1298178.csv', 	'1322276.csv', 	'1348640.csv', 	'1348642.csv', 	'1348651.csv', 	'1381218.csv', 	'1381221.csv', 	'1384637.csv', 	'1399113.csv', 	'1243389.csv', 	'1273748.csv', 	'1273753.csv', 	'1278671.csv', 	'1278672.csv', 	'1278679.csv', 	'1278685.csv', 	'1278686.csv', 	'1303307.csv', 	'1276906.csv', 	'1317905.csv', 	'1327270.csv', 	'1327504.csv', 	'1327505.csv', 	'1327506.csv', 	'1327508.csv', 	'1298150.csv', 	'1322277.csv', 	'1348641.csv', 	'1348649.csv', 	'1348650.csv', 	'1381217.csv', 	'1381219.csv', 	'1381220.csv', 	'1384634.csv', 	'1399117.csv', 	'1399120.csv']
    indiaFileNames = ['1243388.csv', 	'1243390.csv', 	'1243391.csv', 	'1243392.csv', 	'1262758.csv', 	'1262759.csv', 	'1262760.csv', 	'1273727.csv', 	'1273739.csv', 	'1273744.csv', 	'1278673.csv', 	'1278680.csv', 	'1278681.csv', 	'1278684.csv', 	'1278687.csv', 	'1278688.csv', 	'1278689.csv', 	'1278690.csv', 	'1278691.csv', 	'1303308.csv', 	'1276904.csv', 	'1276905.csv', 	'1317903.csv', 	'1317904.csv', 	'1317906.csv', 	'1317907.csv', 	'1327272.csv', 	'1327276.csv', 	'1327277.csv', 	'1327279.csv', 	'1327503.csv', 	'1327507.csv', 	'1298157.csv', 	'1298164.csv', 	'1298169.csv', 	'1298176.csv', 	'1298178.csv', 	'1322276.csv', 	'1348640.csv', 	'1348642.csv', 	'1348651.csv', 	'1381218.csv', 	'1381221.csv', 	'1384637.csv',  '1243389.csv', 	'1273748.csv', 	'1273753.csv', 	'1278671.csv', 	'1278672.csv', 	'1278679.csv', 	'1278685.csv', 	'1278686.csv', 	'1303307.csv', 	'1276906.csv', 	'1317905.csv', 	'1327270.csv', 	'1327504.csv', 	'1327505.csv', 	'1327506.csv', 	'1327508.csv', 	'1298150.csv', 	'1322277.csv', 	'1348641.csv', 	'1348649.csv', 	'1348650.csv', 	'1381217.csv', 	'1381219.csv', 	'1381220.csv', 	'1384634.csv']
    #indiaFileNames = ['1243388.csv']
    indiaFileNames = ['1384634.csv', 	'1381220.csv', 	'1381219.csv', 	'1381217.csv', 	'1348650.csv', 	'1348649.csv', 	'1348641.csv', 	'1322277.csv', 	'1298150.csv', 	'1327508.csv', 	'1327506.csv', 	'1327505.csv', 	'1327504.csv', 	'1327270.csv', 	'1384637.csv', 	'1381221.csv', 	'1381218.csv', 	'1348651.csv', 	'1348642.csv', 	'1348640.csv', 	'1322276.csv', 	'1298178.csv', 	'1298176.csv', 	'1298169.csv', 	'1298164.csv', 	'1298157.csv', 	'1327507.csv', 	'1327503.csv', 	'1327279.csv', 	'1327277.csv', 	'1327276.csv', 	'1327272.csv', ]
    indiaFileNames = []
    fileNames.extend(indiaFileNames)
    print('#### fileNames ####')
    print(fileNames)

    masterDf = pd.DataFrame()
    nbsrDf = pd.DataFrame()
    nthBallSRDf = pd.DataFrame()
    innsProgressionDf = pd.DataFrame()
    inningsTotals = pd.DataFrame()

    for fileName in fileNames:
        if fileName != 'all_matches.csv':
            returnList = readFile(fileName, nbsrDf, startDate, endDate, inningsTotals)

            if returnList is not None:
                tempDf = returnList[0]
                nbsrDf = returnList[1]
                inningsTotals = returnList[2]
                if not tempDf.empty:
                    masterDf = pd.concat([masterDf, tempDf])

    if calculateNBSRFlag == True:
        #start here
        nbsrColumns = int((len(nbsrDf.columns) - 1) / 3)

        innsProgressionDf['striker'] = nbsrDf['playerName']
        initializeInningsProgression(innsProgressionDf, nbsrDf)

        processRangeStatistics(innsProgressionDf, nbsrDf, nbsrColumns)

        calculateTotalStatistics(innsProgressionDf)

        innsProgressionDf['ballsPerInns'] = innsProgressionDf['totalBalls'] / innsProgressionDf['totalInns']
        innsProgressionDf.to_excel(f"innsProgression {statMode} {venueTitle} {timePeriod}.xlsx")

        nthBallSRDf['playerName'] = nbsrDf['playerName']
        nthBallSRDf['ball1SR'] = 100*nbsrDf['ball1SR']
        calculateNthBallSR(nthBallSRDf, nbsrDf, nbsrColumns)

        nbsrDf.to_excel(f"nbsr {statMode} {venueTitle} {timePeriod}.xlsx")
        nthBallSRDf.to_excel(f"nthballSr {statMode} {venueTitle} {timePeriod}.xlsx")
        #end here

    #masterDf = pd.read_excel(f"MasterDF {statMode} {venueTitle} {timePeriod}.xlsx")
    masterDf['venue'] = masterDf['venue'].replace(venue_replacements)
    masterDf['year'] = masterDf['start_date'].str[:4]
    #masterDf.to_excel(f"MasterDF {statMode} {venueTitle} {timePeriod}.xlsx")
    masterDf.to_excel(f"{statMode} {venueTitle} {timePeriod}.xlsx")

    matchResults = pd.read_excel('matchResults.xlsx')

    matchResults = matchResults[matchResults['date1'] >= startDate]
    matchResults = matchResults[matchResults['date1'] <= endDate]

    global filterTeams
    print(filterTeams)

    print(matchResults.columns)

    if len(filterTeams) > 0:
        matchResults = matchResults[matchResults['team1'].isin(filterTeams)]
        matchResults = matchResults[matchResults['team2'].isin(filterTeams)]

    if venueFilter != '':
        matchResults = matchResults[matchResults['venue'] == venueFilter]

    tempMatchResults = pd.DataFrame()

    if not inningsTotals.empty:
        tempMatchResults = pd.merge(matchResults, inningsTotals, on='matchId', how='outer')
        #tempMatchResults = pd.merge(inningsTotals, matchResults, on='matchId', how='outer')

    inningsTotals.to_excel(f"Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")

    #tempMatchResults = pd.read_excel(f"Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")

    if not tempMatchResults.empty:
        tempMatchResults = sortVenues(tempMatchResults)
        tempMatchResults = sortVenues(tempMatchResults)

    tempMatchResults.to_excel(f"Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")

    matchInnsTotals = pd.read_excel(f"Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")
    matchResults = pd.read_excel('matchResults.xlsx')

    tempMatchResults = pd.merge(matchResults, matchInnsTotals, on='matchId', how='outer')
    tempMatchResults.drop([i for i in tempMatchResults.columns if '_x' in i], axis=1, inplace=True)

    renameDict = {}
    for column in tempMatchResults.columns:

        if '_y' in column:
            renameDict[column] = column.replace('_y', '')

    tempMatchResults.rename(columns=renameDict, inplace=True)

    tempMatchResults.to_excel('tempMatchResults.xlsx')
    #tempMatchResults.to_excel('matchResults.xlsx')

    batterNames = masterDf['striker'].unique()
    bowlerNames = masterDf['bowler'].unique()
    masterDf = masterDf.sort_values(by='start_date', ascending=True)
 
    venueNames = masterDf['year'].unique().tolist()

    venue = timePeriod
    venueDf = masterDf.copy()

    venueDf.to_excel(f"Overall Stats {statMode} {venueTitle} {timePeriod}.xlsx")

    batterTotals = processVenueStatistics(venueDf, statMode, venue)
    batterTotals.to_excel(f"batterTotals {statMode} {venueTitle} {timePeriod}.xlsx")

    matchupTotals.to_excel('matchupTotalsPreAgg.xlsx')
    matchupTotals.drop_duplicates(subset=['match_id', 'matchup'], inplace=True)

    if not matchupTotals.empty:
        matchupTotalsAgg = matchupTotals.copy()
        global matchupPlot
        matchupPlot = 'Matchups'
        matchupTotalsAgg = processVenueStatistics(matchupTotalsAgg, statMode, venue)
        matchupTotalsAgg.to_excel(f"matchupTotalsAgg {statMode} {venueTitle} {timePeriod}.xlsx")
        matchupPlot = ''
        global batterMatchups
        global bowlerMatchups

        if statMode == 'batting':
            batterMatchups = matchupTotalsAgg.copy()
        
        if statMode == 'bowling':
            bowlerMatchups = matchupTotalsAgg.copy()

    if calculateNBSRFlag == True:
        teamInnsProgression, topOrderBatters = saveInnsProgressionFile(innsProgressionDf, batterTotals) #

    teamInnsProgression = pd.DataFrame()
    topOrderBatters = pd.DataFrame()

    venueDf.to_excel(f"Overall Stats {statMode} {venueTitle} {timePeriod}.xlsx")

    overallBatterTotals = pd.DataFrame()

    venueNames = []

    for venue in venueNames:

        timePeriod = venue

        venueDf = masterDf.copy()
        venueDf = venueDf[venueDf['year'] == venue]

        venueDf.to_excel(f"Overall Stats {statMode} {venueTitle} {timePeriod}.xlsx")

        batterTotals = processVenueStatistics(venueDf, statMode, venue)

        overallBatterTotals = pd.concat([overallBatterTotals, batterTotals])

        if calculateNBSRFlag == True:
            teamInnsProgression, topOrderBatters = saveInnsProgressionFile(innsProgressionDf, batterTotals)

        venueDf.to_excel(f"Overall Stats {statMode} {venueTitle} {timePeriod}.xlsx")

    overallBatterTotals.to_excel(f"Overall Totals {statMode} {venueTitle} {timePeriod}.xlsx")
    
    return teamInnsProgression, topOrderBatters, batterTotals, tempMatchResults

def getValidFileNames(startDate, endDate):

    #filterCities = ['Ahmedabad', 'Bangalore', 'Bengaluru', 'Chennai', 'Mumbai', 'Pune', 'Lucknow', 'Dharamsala', 'Kolkata', 'Delhi', 'Dharmasala']
    filterCities = ['Bridgetown', 'Barbados']
    filterCities = []

    dir_list = os.listdir(os.path.expanduser(filePath))

    matchIndex = pd.DataFrame()
    matchIndex = buildMatchIndex()

    validMatches = matchIndex.copy()
    validMatches = validMatches[validMatches['date1'] >= startDate]
    validMatches = validMatches[validMatches['date1'] <= endDate]

    global filterTeams
    print(filterTeams)

    print(validMatches.columns)
    print('#### venueFilter ####')
    print(venueFilter)
    print('#### filterVenues ####')
    print(filterVenues)

    if len(filterTeams) > 0:
        validMatches = validMatches[validMatches['team1'].isin(filterTeams)]
        validMatches = validMatches[validMatches['team2'].isin(filterTeams)]

    if venueFilter != '':
        validMatches = validMatches[validMatches['venue'] == (venueFilter)]
    elif len(filterVenues) > 0:
        validMatches = validMatches[validMatches['venue'].isin(filterVenues)]

    if len(filterCities) > 0:
        validMatches = validMatches[validMatches['city'].isin(filterCities)]

    teams = ['New Zealand', 'England', 'Bangladesh', 'India', 'Pakistan', 'Australia', 'Afghanistan', 'South Africa', 'West Indies', 'Sri Lanka', 'Ireland', 'Zimbabwe', 'Netherlands']
    #validMatches = validMatches[(validMatches['event'] == 'Indian Premier League') | (validMatches['team1'].isin(teams) & validMatches['team2'].isin(teams))]
    #validMatches = validMatches[(validMatches['event'] == 'Indian Premier League') | (validMatches['team1'] == 'India') | (validMatches['team2'] == 'India')]
    #validMatches = validMatches[(validMatches['event'] != 'Asian Games Men\'s Cricket Competition')]
    #validMatches = validMatches[(validMatches['team1'].isin(teams)) & (validMatches['team2'].isin(teams))] 

    #tempMatchResults[(tempMatchResults['team1'] == team) | (tempMatchResults['team2'] == team)]

    fileNames = validMatches['matchFile'].unique().tolist()
    print(fileNames)
    #fileNames = ['1148680.csv']

    #for fileName in dir_list:
        #if fileName.__contains__('.csv') and not fileName.__contains__('_info.csv'):
            #fileNames.append(fileName)

    return fileNames

def buildMatchIndex():

    fileNames = []
    matchIds = []
    dir_list = os.listdir(os.path.expanduser(filePath))

    fileNames = ['1317148_info.csv']

    if os.path.isfile('matchIndex.xlsx'):
        matchIndex = pd.read_excel('matchIndex.xlsx', index_col=[0])
    else:
        matchIndex = pd.DataFrame()

    if not matchIndex.empty:
        matchIds = matchIndex['matchId'].astype(str).unique().tolist()
    else:
        matchIds = []

    dir_list = [item for item in dir_list if item.__contains__('.csv') and not item.__contains__('_info.csv')]
    dir_list = [item.replace('.csv', '') for item in dir_list]

    fileNames = list(set(dir_list) - set(matchIds))
    fileNames = [item + '_info.csv' for item in fileNames]

    #fileNames = ['1317148_info.csv']

    updatedDict = {}

    for key in stadia_replacements.keys():

        newKey = rf"\b{key}\b"
        updatedDict[newKey] = stadia_replacements[key]

    for fileName in fileNames:

        matchDf = pd.read_csv(fileName, sep='delimiter', header=None)
        matchDf = matchDf.replace('info,', '', regex=True)
        matchDf = matchDf.replace(updatedDict, regex=True)
        matchDf.rename(columns={ matchDf.columns[0]: "Column1" }, inplace = True)

        for key, value in updatedDict.items():
            matchDf['Column1'] = matchDf['Column1'].str.replace(key, value, regex=True)

        venueStr = matchDf[matchDf['Column1'].str.contains("venue")]
        venue = venueStr['Column1'].values[0]
        actualVenue = venue[6:]
        actualVenue = actualVenue.replace(',', '')
        tempVenueStr = 'venue,' + actualVenue

        matchDf['Column1'] = matchDf['Column1'].str.replace(venue, tempVenueStr, regex=True)
        matchDf = matchDf['Column1'].str.split(',', expand=True)

        columns = matchDf[matchDf.columns[0]].unique().tolist()
        columns.remove('version')
        columns.remove('registry')

        matchId = fileName.replace('_info.csv', '')
        matchFile = matchId + '.csv'

        rowDict = {}    

        rowDict['matchId'] = matchId
        rowDict['matchFile'] = matchFile

        matchDetailsDf = pd.DataFrame()

        for column in columns:

            columnDf = matchDf[matchDf[matchDf.columns[0]] == column]
            columnDf = columnDf.dropna(axis=1)

            if len(columnDf.columns) == 2 and len(columnDf.index) == 1:
                tempDf = columnDf.transpose()
                tempDf = tempDf[1:]
                tempDf.rename(columns={tempDf.columns[0]: column}, inplace = True)

                rowDict[column] = tempDf[column].iloc[0]
            
            elif len(columnDf.columns) == 2:

                counter = 1

                for value in columnDf[columnDf.columns[1]]:

                    key = column + str(counter)
                    rowDict[key] = value

                    counter = counter + 1

            else:

                if 'date1' in rowDict.keys():
                    rowDict['date'] = rowDict['date1']

                for index, row in columnDf.iterrows():

                    tempDict = rowDict.copy()

                    tempDict['team'] = row[columnDf.columns[1]]
                    tempDict['player'] = row[columnDf.columns[2]]

                    matchDetailsDf = matchDetailsDf.append(tempDict, ignore_index=True)

        matchDetailsDf.drop_duplicates(subset=['matchId', 'team', 'player'], inplace=True)
        matchIndex = pd.concat([matchIndex, matchDetailsDf], ignore_index=True)
        matchIndex = matchIndex.drop_duplicates()

    allColumns = matchIndex.columns
    dateColumns = [s for s in allColumns if "date" in s]
    matchIndex['year'] = matchIndex['date1'].astype(str).str[:4]
    matchIndex[dateColumns] = matchIndex[dateColumns].astype(str).replace("/", "-", regex=True)
    matchIndex['venue'] = matchIndex['venue'].astype(str).replace("\"", "", regex=True)

    matchIndex = matchIndex.sort_values(by=['date1', 'matchId'], ascending=True)
    #matchIndex = matchIndex.reset_index()

    for index, row in matchIndex.iterrows():

        winTossWinMatch = 'no result'

        if row["outcome"] == "tie":
            row['winner'] == row['eliminator']

        if row["toss_winner"] == row["winner"]:
            winTossWinMatch = "yes"
        elif row["outcome"] == "no result":
            winTossWinMatch = "no result"
        else:
            winTossWinMatch = "no"

        if row['toss_decision'] == 'bat':
            batFirst = row['toss_winner']
            bowlFirst = row['team1'] if row['toss_winner'] == row['team2'] else row['team2']
        if row['toss_decision'] == 'field':
            bowlFirst = row['toss_winner']
            batFirst = row['team1'] if row['toss_winner'] == row['team2'] else row['team2']

        winningTeam = row["winner"]

        wonBattingFirst = ''
        wonFieldingFirst = ''

        if winningTeam != '':

            wonBattingFirst = 'yes' if batFirst == winningTeam else 'no'
            wonFieldingFirst = 'yes' if bowlFirst == winningTeam else 'no'

        matchIndex.at[index,'winTossWinMatch'] = winTossWinMatch
        matchIndex.at[index,'wonBattingFirst'] = wonBattingFirst
        matchIndex.at[index,'wonFieldingFirst'] = wonFieldingFirst
        matchIndex.at[index,'batFirst'] = batFirst
        matchIndex.at[index,'bowlFirst'] = bowlFirst

    stadiumReplacements = getStadiumReplacements(matchIndex)
    stadiumReplacements = {}
    for key, value in stadiumReplacements.items():
        matchIndex['venue'] = matchIndex['venue'].str.replace(key, value, regex=True)
    matchIndex.to_excel('matchIndex.xlsx')
    matchResults = matchIndex.drop_duplicates(subset='matchId', keep="last")
    matchResults.to_excel('matchResults.xlsx')

    return matchIndex

def getStadiumReplacements(matchIndex):

    stadiumReplacements = {}

    tempDf = matchIndex.copy()
    venueDf = tempDf.sort_values(by='venue')
    matchIndex = matchIndex.sort_values(by='venue')

    venues = matchIndex['venue']

    for i in range(len(venues)-1, 1, -1):

        if venues[i-1] in venues[i]:

            tempKey = venues[i-1]
            key = rf"^{tempKey}$"
            stadiumReplacements[tempKey] = venues[i]

            venues[i-1] = venues[i]

    stadiumReplacements = OrderedDict(sorted(stadiumReplacements.items()))
    matchIndex['venue'] = venues
    return stadiumReplacements

def initializeInningsProgression(innsProgressionDf, nbsrDf):
    noOfRows = len(innsProgressionDf['striker'])
    innsProgressionDf['totalRuns'] = pd.Series(0, index=range(noOfRows))
    innsProgressionDf['totalBalls'] = pd.Series(0, index=range(noOfRows))
    innsProgressionDf['totalSR'] = pd.Series(0, index=range(noOfRows))
    innsProgressionDf['totalInns'] = nbsrDf['ball1BallsFaced']

def saveInnsProgressionFile(innsProgressionDf, batterTotals):

    if statMode == 'batting':
        masterDataDf = pd.merge(innsProgressionDf, batterTotals, on='striker', how='inner')
        playerColumns = ['striker', 'overallAvg', 'totalSR', 'ballsPerInns', 'pp%BallsFaced', 'mo%BallsFaced', 'death%BallsFaced',
                        '1-10SR', '11-20SR', '21-30SR', '31-40SR', '41-50SR', '51-60SR', 'overallWPI', 'overallER', 'ppRPI', 'ppWPI', 'ppER',
                        'moRPI', 'moWPI', 'moER', 'deathRPI', 'deathWPI', 'deathER']
        teamColumns = ['striker', 'ballsPerInns', 'overallRPI', 'overallWPI', 'overallER', 'ppRPI', 'ppWPI', 'ppER',
                        'moRPI', 'moWPI', 'moER', 'deathRPI', 'deathWPI', 'deathER']
    else:
        batterTotals = batterTotals.drop('striker', axis=1)
        batterTotals.rename(columns = {'bowler':'striker'}, inplace = True)
        masterDataDf = pd.merge(innsProgressionDf, batterTotals, on='striker', how='inner')

        playerColumns = ['striker', 'ballsPerInns', 'overallRPI', 'overallWPI', 'pp%BallsFaced', 'mo%BallsFaced', 'death%BallsFaced',
                        'ppER', 'ppWPI', 'ppAvgScore', 'moER', 'moWPI', 'moAvgScore', 'deathER', 'deathWPI', 'deathAvgScore',
                        'ppRPI', 'moRPI', 'deathRPI', 'overallER']
        teamColumns = ['striker', 'ballsPerInns', 'overallRPI', 'overallWPI', 'overallER', 'ppRPI', 'ppWPI', 'ppER',
                        'moRPI', 'moWPI', 'moER', 'deathRPI', 'deathWPI', 'deathER']
        teamInnsProgressionColumns = ['striker', 'overallRPI', 'overallWPI', 'overallER']
        teamOverERColumns = ['1-6SR', '7-12SR', '13-18SR', '19-24SR', '25-30SR', '31-36SR', '37-42SR', '43-48SR', '49-54SR',
                                '55-60SR', '61-66SR', '67-72SR', '73-78SR', '79-84SR', '85-90SR', '91-96SR', '97-102SR', 
                                '103-108SR', '109-114SR', '115-120SR', '120-126SR']

    masterDataDf.to_excel(f"MD {statMode} {venueTitle} {timePeriod}.xlsx")

    masterDataDf = masterDataDf[masterDataDf['overallInns'] >= masterDataDf['overallInns'].mean()/2]

    if statMode == 'batting':
        masterDataDf = masterDataDf[masterDataDf['runs'] >= masterDataDf['runs'].mean()/4]
        innsProgression = masterDataDf.copy()
        #innsProgression = innsProgression[innsProgression['runs'] >= 400]
        innsProgression = masterDataDf[playerColumns]
        teamInnsProgression = masterDataDf[teamColumns]
        innsProgression = innsProgression[(innsProgression['totalSR'] >= innsProgressionSR)]
        innsProgression = innsProgression[innsProgression['ballsPerInns'] < teamBPI]
        #innsProgression = innsProgression[(innsProgression['ballsPerInns'] >= innsProgression['ballsPerInns'].mean()/12)]
        teamInnsProgression = teamInnsProgression[teamInnsProgression['ballsPerInns'] > teamBPI]
    else:
        masterDataDf = masterDataDf[masterDataDf['wickets'] >= masterDataDf['wickets'].mean()/4]
        innsProgression = masterDataDf.copy()
        #innsProgression = innsProgression[innsProgression['wickets'] >= 10]
        innsProgression = masterDataDf[playerColumns]
        teamInnsProgression = masterDataDf[teamColumns]
        #innsProgression = innsProgression[(innsProgression['ballsPerInns'] >= innsProgression['ballsPerInns'].mean()/6)]
        innsProgression = innsProgression[innsProgression['ballsPerInns'] < teamBPI]
        teamInnsProgression = teamInnsProgression[teamInnsProgression['ballsPerInns'] > teamBPI]
    
    topOrderBatters = innsProgression[innsProgression['death%BallsFaced'] < 25].sort_values(by='pp%BallsFaced', ascending=False)
    lowerOrderBatters = innsProgression[innsProgression['death%BallsFaced'] >= 25].sort_values(by='death%BallsFaced', ascending=True)

    topOrderBatters = topOrderBatters.append(lowerOrderBatters).set_index('striker').round(2)

    teamInnsProgression = teamInnsProgression[teamInnsProgression['ballsPerInns'] > teamBPI]
    teamInnsProgression = teamInnsProgression.set_index('striker').round(2)
    teamInnsProgression = teamInnsProgression.drop('ballsPerInns', axis=1)

    if statMode == 'batting':
        teamInnsProgression = teamInnsProgression.sort_values(by='overallRPI', ascending=False)
    else:
        teamInnsProgression = teamInnsProgression.sort_values(by='overallRPI', ascending=True)

    topOrderBatters = topOrderBatters[topOrderBatters['ballsPerInns'] < teamBPI]
        

    teamInnsProgression.to_excel(f"Teams Innings Progression {statMode} {venueTitle} {timePeriod}.xlsx")
    topOrderBatters.to_excel(f"Players Innings Progression {statMode} {venueTitle} {timePeriod}.xlsx")

    rpiColumns = ['overallRPI', 'ppRPI', 'moRPI', 'deathRPI']
    wpiColumns = ['overallWPI', 'ppWPI', 'moWPI', 'deathWPI']
    erColumns = ['overallER', 'ppER', 'moER', 'deathER']

    ballsFacedColumns = ['ballsPerInns', 'pp%BallsFaced', 'mo%BallsFaced', 'death%BallsFaced']
    srColumns = ['totalSR', '1-10SR', '11-20SR', '21-30SR', '31-40SR', '41-50SR', '51-60SR']

    rgColumns = []
    grColumns = []

    colors = ["#FF7F7F", "#FFBFAF", "#FFDF9F", "#FFEF7F", "#DDFF7F", "#9FFF9F", "#7FDFAF", "#5FBFBF", "#3F9FFF", "#1F7FFF", "#007FFF"]

    cmRG = sns.color_palette("RdYlGn", as_cmap=True)
    #cmRG = sns.color_palette("Spectral", as_cmap=True)
    cmGR = sns.color_palette("RdYlGn_r", as_cmap=True)
    #cmGR = sns.color_palette("Spectral_r", as_cmap=True)

    if statMode == 'batting':
        rgColumns = rpiColumns + erColumns
        grColumns = wpiColumns 
    
    if statMode == 'bowling':
        rgColumns = wpiColumns
        grColumns = rpiColumns + erColumns

    teamInnsProgression.rename(index=teams_mapping,inplace=True)

    fileName = statMode + ' ' + str(timePeriod) + ' team '
    styleColumns(teamInnsProgression, cmRG, rgColumns, cmGR, grColumns, fileName)

    topOrderBatters = topOrderBatters.fillna(0)

    topOrderBatters['topOrderPercent'] = topOrderBatters['pp%BallsFaced'] + topOrderBatters['mo%BallsFaced']

    lowerOrderBatters = topOrderBatters[topOrderBatters['topOrderPercent'] < 75]
    top3Batters = topOrderBatters[topOrderBatters['topOrderPercent'] >= 75]
    topOrderBatters = topOrderBatters.drop('topOrderPercent', axis=1)

    if statMode == 'batting':
        batterColumns = ['overallAvg', 'totalSR', 'ballsPerInns', 'pp%BallsFaced', 'mo%BallsFaced', 'death%BallsFaced', '1-10SR', '11-20SR', '21-30SR', '31-40SR', '41-50SR', '51-60SR']
        topOrderBatters = topOrderBatters[batterColumns]
        top3Batters = top3Batters[batterColumns]
        lowerOrderBatters = lowerOrderBatters[batterColumns]

    if statMode == 'batting':
        batterColumns = ['overallAvg', 'totalSR', 'ballsPerInns', '1-10SR', '11-20SR', '21-30SR', '31-40SR', '41-50SR', '51-60SR']
        rpiColumns = ['overallAvg']
        wpiColumns = []
        erColumns = []
        ballsFacedColumns = ['ballsPerInns', 'pp%BallsFaced', 'mo%BallsFaced', 'death%BallsFaced']
        srColumns = ['totalSR', '1-10SR', '11-20SR', '21-30SR', '31-40SR', '41-50SR', '51-60SR']

        rgColumns = rpiColumns + erColumns + ballsFacedColumns + srColumns
        grColumns = wpiColumns 
    
    if statMode == 'bowling':
        batterColumns = ['overallRPI', 'overallER', 'overallWPI', 'ballsPerInns', 'ppRPI', 'ppER', 'ppWPI', 'moRPI', 'moER', 'moWPI', 'deathRPI', 'deathER', 'deathWPI']
        topOrderBatters = topOrderBatters[batterColumns]
        top3Batters = top3Batters[batterColumns]
        lowerOrderBatters = lowerOrderBatters[batterColumns]

        rpiColumns = ['overallRPI', 'ppRPI', 'moRPI', 'deathRPI']
        wpiColumns = ['overallWPI', 'ppWPI', 'moWPI', 'deathWPI']
        erColumns = ['overallER', 'ppER', 'moER', 'deathER']
        ballsFacedColumns = ['ballsPerInns']

        rgColumns = wpiColumns + ballsFacedColumns 
        grColumns = rpiColumns + erColumns

    fileName = statMode + ' ' + str(timePeriod) +  ' player '

    #avgBallsPerInns = math.floor(topOrderBatters['ballsPerInns'].mean())

    styleColumns(top3Batters, cmRG, rgColumns, cmGR, grColumns, fileName + ' Top Order Batters')
    styleColumns(lowerOrderBatters, cmRG, rgColumns, cmGR, grColumns, fileName + 'Middle and Lower Order Batters')
    styleColumns(topOrderBatters, cmRG, rgColumns, cmGR, grColumns, fileName + ' total ')

    return teamInnsProgression, topOrderBatters

def styleColumns(df, rgMap, rgColumns, grMap, grColumns, type):

    fileName = type + ' ' + statMode + '_styled'

    f=open(fileName + '.html',"w")

    #.applymap(lambda x: "background-color: white" if x==0 else "background-color: white")\

    s = df.style\
        .background_gradient(cmap=rgMap, subset=rgColumns)\
        .background_gradient(cmap=grMap, subset=grColumns)\
        .set_properties(**{'text-align': 'center'}) \
        .set_table_styles([{
            'selector': 'thead th',
            'props': [('text-align', 'center')]
        }, 
        {
            'selector': '',
            'props': [('border', '1px solid grey')]
        }]) \
        .set_precision(2)\
        .set_table_attributes('style="border-collapse: collapse"')\
        .set_table_attributes('style="text-align: left"')
                                        
    f.write(s.render()) # df is the styled dataframe
    f.close()

    s.to_excel(fileName  + ' ' + str(timePeriod) + ' ' +  '_styled.xlsx')

def processRangeStatistics(innsProgressionDf, nbsrDf, nbsrColumns):

    if statMode == 'batting':
        step = 10
    else:
        step = 5

    for ballCounter in range(1, nbsrColumns, step):
        startRange = ballCounter
        endRange = min(ballCounter + step - 1, nbsrColumns)

        rangeColName = str(startRange) + '-' + str(endRange) if endRange <= nbsrColumns else str(startRange) + '+'
        rangeRunsCol = rangeColName + 'Runs'
        rangeBallsCol = rangeColName + 'Balls'
        rangeSRCol = rangeColName + 'SR'

        rangeRuns = nbsrDf[[f'ball{i}Runs' for i in range(startRange, endRange + 1)]].sum(axis=1)
        rangeBalls = nbsrDf[[f'ball{i}BallsFaced' for i in range(startRange, endRange + 1)]].sum(axis=1)
        rangeSR = 100 * rangeRuns.divide(rangeBalls, fill_value=0)

        innsProgressionDf[rangeRunsCol] = rangeRuns
        innsProgressionDf[rangeBallsCol] = rangeBalls
        innsProgressionDf[rangeSRCol] = rangeSR


def calculateTotalStatistics(innsProgressionDf):
    innsProgressionDf['totalRuns'] = innsProgressionDf.filter(like='Runs').sum(axis=1)
    innsProgressionDf['totalBalls'] = innsProgressionDf.filter(like='Balls').sum(axis=1)
    innsProgressionDf['totalSR'] = 100 * innsProgressionDf['totalRuns'].divide(innsProgressionDf['totalBalls'], fill_value=0)


def calculateNthBallSR(nthBallSRDf, nbsrDf, nbsrColumns):
    for ballCounter in range(2, nbsrColumns):
        runsColumnName = 'ball' + str(ballCounter) + 'Runs'
        ballsFacedColumnName = 'ball' + str(ballCounter) + 'BallsFaced'
        nbsrColumnName = 'ball' + str(ballCounter) + 'SR'

        prevrunsColumnName = 'ball' + str(ballCounter - 1) + 'Runs'
        prevballsFacedColumnName = 'ball' + str(ballCounter - 1) + 'BallsFaced'
        prevnbsrColumnName = 'ball' + str(ballCounter - 1) + 'SR'

        nbsrDf[runsColumnName] = nbsrDf[[runsColumnName, prevrunsColumnName]].sum(axis=1).where(
            nbsrDf[runsColumnName] > 0, 0)
        nbsrDf[ballsFacedColumnName] = nbsrDf[[ballsFacedColumnName, prevballsFacedColumnName]].sum(axis=1).where(
            nbsrDf[ballsFacedColumnName] > 0, 0)
        nbsrDf[nbsrColumnName] = 100 * nbsrDf[runsColumnName] / nbsrDf[ballsFacedColumnName]

        nthBallSRDf[nbsrColumnName] = nbsrDf[nbsrColumnName]

def calculateTotals(venueDf, batterNames):

    if statMode == 'batting':
        filter = 'striker'
        if matchupPlot == 'Matchups':
            filter = 'matchup'
        playerFilter = 'runs'
        playerThreshold = 0
    
    if statMode == 'bowling':
        filter = 'bowler'
        if matchupPlot == 'Matchups':
            filter = 'matchup'
        playerFilter = 'wickets'
        playerThreshold = 1

    batterTotals = pd.DataFrame()

    for batter in batterNames:

        playerDf = venueDf.copy()
        playerDf = venueDf[venueDf[filter] == batter]
        playerDf.sort_values(by=['start_date'], inplace=True)

        if playerDf[playerFilter].sum() >= playerThreshold and not playerDf.empty:
            playerTotal = calculatePhaseInnings(playerDf)
            playerTotal = calculateOverallTotals(playerTotal, venueDf)
            batterTotals = pd.concat([batterTotals, playerTotal])

    return batterTotals

def processVenueStatistics(venueDf, statMode, venue):
    venueDf.to_excel(f"Overall Stats {statMode} {venueTitle} {timePeriod}.xlsx")
    inningsTotals = []

    for innings in venueDf['innings'].unique():

        inningsTotals.append(pd.DataFrame())

    if statMode == 'batting':
        filter = 'striker'

        if matchupPlot == 'Matchups':
            filter = 'matchup'

        batterNames = venueDf[filter].unique()
        batterTotals = calculateTotals(venueDf, batterNames)

        if matchupPlot == 'Matchups':
            print('#### BATTERNAMES ####')
            print(batterNames)
            batterTotals.to_excel('MatchupTotalsTemp.xlsx')

        for innings in venueDf['innings'].drop_duplicates().sort_values():

            inningsDf = venueDf.copy()
            inningsDf = inningsDf[inningsDf['innings'] == innings]

            inningsTotal = calculateTotals(inningsDf, batterNames)

            inningsDf = inningsTotals[int(innings)-1]
            inningsTotals[int(innings)-1] = pd.concat([inningsDf, inningsTotal])

        inningsTotals = []
        if len(inningsTotals) > 0:

            inningsAverages = pd.DataFrame()
            i = 1
            for inningsDf in inningsTotals:

                if (not inningsDf.empty) and i < 3:
                    inningsAverage = calculateOverallPeriodAverage(inningsDf, venue, 'Innings ' + str(i))
                    inningsAverages = pd.concat([inningsAverages, inningsAverage])
                    i = i + 1

            if not inningsAverages.empty:
                inningsAverages.to_excel(f"Innings Averages {statMode} {venueTitle} {timePeriod}.xlsx")

        return calculateOverallPeriodAverage(batterTotals, venue, '')

    if statMode == 'bowling':
        filter = 'bowler'

        if matchupPlot == 'Matchups':
            filter = 'matchup'

        bowlerNames = venueDf[filter].unique()
        bowlerTotals = calculateTotals(venueDf, bowlerNames)

        for innings in venueDf['innings'].drop_duplicates().sort_values():

            inningsDf = venueDf.copy()
            inningsDf = inningsDf[inningsDf['innings'] == innings]

            inningsTotal = calculateTotals(inningsDf, bowlerNames)

            inningsDf = inningsTotals[int(innings)-1]
            inningsTotals[int(innings)-1] = pd.concat([inningsDf, inningsTotal])

        inningsTotals = []
        if len(inningsTotals) > 0:

            inningsAverages = pd.DataFrame()
            i = 1
            for inningsDf in inningsTotals:

                if (not inningsDf.empty) and i < 3:
                    inningsAverage = calculateOverallPeriodAverage(inningsDf, venue, 'Innings ' + str(i))
                    inningsAverages = pd.concat([inningsAverages, inningsAverage])
                    i = i + 1
                
            if not inningsAverages.empty:
                inningsAverages.to_excel(f"Innings Averages{statMode} {venueTitle} {timePeriod}.xlsx")

        return calculateOverallPeriodAverage(bowlerTotals, venue, '')

    venueDf.to_excel(f"Overall Stats {statMode} {venueTitle} {timePeriod}.xlsx")

def calculatePeriodAverage(df):

    teamDf = df.copy()
    teamDf = teamDf[teamDf['overallBPI'] >= 100]
    teamDf = calcPALabel(teamDf, 'Team Average')

    batterDf = df.copy()
    batterDf = batterDf[batterDf['overallBPI'] < 100]
    batterDf = calcPALabel(batterDf, 'Player Average')

    returndf = pd.concat([teamDf, batterDf])

    return returndf

def calculateOverallPeriodAverage(batterTotals, venue, innings):

    allColumns = ['innings', 'striker', 'bowler', 'matchup', 'batting_team', 'bowling_team', 'runs', 'wickets',
        'ballsFaced', 'inningsAvg', 'inningsSR', 'dots', '1s', '2s', '3s', '4s',
        '6s', 'dotPercent', 'boundaryPercent', 'ppInns', 'ppRuns', 'ppBalls', 'ppWickets',
        'ppAvg', 'ppSR', 'ppdots', 'pp1s', 'pp2s', 'pp3s', 'pp4s', 'pp6s', 'ppExtras', 'ppER', 
        'ppdotPercent', 'ppboundaryPercent', 'moInns', 'moRuns', 'moBalls', 'moWickets',
        'moAvg', 'moSR', 'modots', 'mo1s', 'mo2s', 'mo3s', 'mo4s', 'mo6s', 'moExtras', 'moER',
        'modotPercent', 'moboundaryPercent','deathInns', 'deathRuns', 'deathBalls',
        'deathWickets', 'deathAvg', 'deathSR', 'deathdots', 'death1s',
        'death2s', 'death3s', 'death4s', 'death6s', 'deathExtras', 'deathER', 'deathdotPercent',
        'deathboundaryPercent', 'overallInns', 'overallRuns', 'overallBalls',
        'overallWickets', 'overallAvg', 'overallSR', 'overalldots', 'overall1s',
        'overall2s', 'overall3s', 'overall4s', 'overall6s', 'overallExtras', 'overallER', 'overalldotPercent',
        'overallboundaryPercent', 'teamRunsExclBatter', 'teamBallsExclBatter',
        'avgDiff', 'srDiff', 'teamAvgExclBatter', 'teamSRExclBatter', 'ppTeamAvg', 'ppTeamSR', 'ppAvgDiff', 'ppSRDiff',
        'moTeamAvg', 'moTeamSR', 'moAvgDiff', 'moSRDiff', 'deathTeamAvg', 'deathTeamSR', 'deathAvgDiff', 'deathSRDiff',
        'ppTeamRuns', 'ppTeamBalls', 'ppTeamWickets', 'moTeamRuns', 'moTeamBalls', 'moTeamWickets', 'deathTeamRuns', 'deathTeamBalls', 'deathTeamWickets',
        'overallTeamRuns', 'overallTeamBalls', 'overallTeamWickets']

    if not batterTotals.empty:

        batterTotals = calculatePeriodAverage(batterTotals)

        yearColumn = []

        for i in range(0, len(batterTotals.index)):

            yearColumn.append(str(venue))

        batterTotals['year'] = yearColumn

        if str(innings) != '':
            venue = venue + ' Innings ' + str(innings)

        global runsRangeColumns
        runsRangeColumns.sort()
        runsRangeColumns = [*set(runsRangeColumns)]
        runsRangeColumns.sort()

        allColumns = [item for item in batterTotals.columns if item not in runsRangeColumns]
        runsRangeColumns = [item for item in runsRangeColumns if item in batterTotals.columns]

        if statMode == 'batting':
            allColumns.extend(runsRangeColumns)

        batterTotals = batterTotals[allColumns]

        if statMode == 'batting':
            batterTotals = getRangePcts(batterTotals, runsRangeColumns)

        batterTotals.to_excel(f"Batter Totals {statMode} {venueTitle} {timePeriod}.xlsx")

        teamTotals = batterTotals.copy()
        if 'teamRunsExclBatter' in teamTotals.columns:
            teamTotals = teamTotals[teamTotals['teamRunsExclBatter'] == 0]
        #plotDifferences(teamTotals, venue)

        playerTotals = batterTotals.copy() 
        if 'teamRunsExclBatter' in playerTotals.columns:
            playerTotals = playerTotals[playerTotals['teamRunsExclBatter'] > 0]

        if matchupPlot != 'Matchups':
            plotDifferences(playerTotals, venue)

        return batterTotals

def getRangePcts(batterTotals, runsRangeColumns):

    for column in runsRangeColumns:

        if column[:2] == 'pp':
            inns = batterTotals['ppInns']
        if column[:2] == 'mo':
            inns = batterTotals['moInns']
        if column[:2] == 'de':
            inns = batterTotals['deathInns']
        if column[:2] == 'ov':
            inns = batterTotals['overallInns']

        batterTotals[column + 'Pct'] = 100*batterTotals[column]/inns

    return batterTotals.round(2)

def calcPALabel(df, label):

    if statMode == 'batting':
        tempDict = {'striker': label}

    if statMode == 'bowling':
        tempDict = {'bowler': label}

    sumColumns = ['runs', 'wickets', 'ballsFaced', 'dots', '1s', '2s', '3s', '4s', 
                    '6s', 'ppInns', 'ppRuns', 'ppBalls', 'ppWickets', 'ppdots', 'pp1s', 'pp2s', 'pp3s', 'pp4s', 'pp6s', 'ppExtras',
                    'moInns', 'moRuns', 'moBalls', 'moWickets', 'modots', 'mo1s', 'mo2s', 'mo3s', 'mo4s', 'mo6s', 'moExtras', 
                    'deathInns', 'deathRuns', 'deathBalls', 'deathWickets', 'deathdots', 'death1s', 'death2s', 'death3s', 
                    'death4s', 'death6s', 'deathExtras', 'overallInns', 'overallRuns', 'overallBalls', 'overallWickets', 'overalldots', 'overall1s',
                    'overall2s', 'overall3s', 'overall4s', 'overall6s', 'overallExtras', 'teamRunsExclBatter', 'teamBallsExclBatter', 'teamWicketsExclBatter',
                    'ppTeamRuns', 'ppTeamBalls', 'ppTeamWickets', 'moTeamRuns', 'moTeamBalls', 'moTeamWickets', 'deathTeamRuns', 'deathTeamBalls', 'deathTeamWickets',
                    'overallTeamRuns', 'overallTeamBalls', 'overallTeamWickets']

    global runsRangeColumns
    runsRangeColumns.sort()
    runsRangeColumns = [*set(runsRangeColumns)]
    if statMode == 'batting':
        sumColumns.extend(runsRangeColumns)
    
    for column in sumColumns:

        if column in df.columns:
            tempDict[column] = int(df[column].astype(int).sum())

    tempDf = pd.DataFrame([tempDict])

    df = pd.concat([df, tempDf])

    if statMode == 'batting':
        tempDf = df[df['striker'] == label]

    if statMode == 'bowling':
        tempDf = df[df['bowler'] == label]

    #tempDf = calculatePhaseInnings(tempDf)
    tempDf = calculateOverallTotals(tempDf, pd.DataFrame())

    df = pd.concat([df, tempDf])

    if statMode == 'batting':
        if matchupPlot != 'Matchups':
            df = df.drop_duplicates(subset=['striker'], keep='last')

    if statMode == 'bowling':
        if matchupPlot != 'Matchups':
            df = df.drop_duplicates(subset=['bowler'], keep='last')

    return df

def processBatterStatistics(batterTotals, venueDf, batterNames):
    for batter in batterNames:
        playerDf = venueDf[venueDf['striker'] == batter]
        playerDf.sort_values(by=['start_date'], inplace=True)

        if playerDf['runsScored'].sum() > 200 and not playerDf.empty:
            playerTotal = calculatePhaseInnings(playerDf)
            playerTotal = calculateOverallTotals(playerTotal, venueDf)
            batterTotals = pd.concat([batterTotals, playerTotal])

    return batterTotals

def processBowlerStatistics(bowlerTotals, venueDf, bowlerNames):
    for bowler in bowlerNames:
        playerDf = venueDf[venueDf['bowler'] == bowler]
        playerDf.sort_values(by=['start_date'], inplace=True)

        if playerDf['ballsFaced'].sum() > 1 and not playerDf.empty:
            playerTotal = calculatePhaseInnings(playerDf)
            playerTotal = calculateOverallTotals(playerTotal, venueDf)
            bowlerTotals = pd.concat([bowlerTotals, playerTotal])

    return bowlerTotals

def calculatePhaseInnings(playerTotal):
    phases = ['pp', 'mo', 'death', 'overall', 'mo1', 'mo2', 'mo3']

    for phase in phases:
        phaseBallsLabel = phase + 'Balls'
        phaseInnsLabel = phase + 'Inns'

        if phaseBallsLabel in playerTotal.columns:
            playerTotal[phaseInnsLabel] = playerTotal[phaseBallsLabel].gt(0).cumsum()

    return playerTotal

def plotDifferences(df, group):
    plotDf = df.copy()

    teams = ['New Zealand', 'England', 'Bangladesh', 'India', 'Pakistan', 'Australia', 'Afghanistan', 'South Africa', 'Netherlands', 'Sri Lanka', '']

    teamColumn = 'bowling_team'
    playerColumn = 'bowler'

    if statMode == 'batting':
        teamColumn = 'batting_team'
        playerColumn = 'striker'

    #tempDf = plotDf[plotDf[playerColumn] == 'Player Average']
    #plotDf = plotDf[plotDf[teamColumn].isin(teams)]

    #plotDf = pd.concat([plotDf, tempDf])

    phases = ['pp', 'mo', 'death', 'overall']
    #phases = ['overall']
    labels = ['Power Play', 'Middle Overs', 'Death Overs', 'Overall']
    #labels = ['Overall']

    phaseAvgBallsFaced = []
    phaseAvgBallsBowled = []
    playerAvgDf = pd.DataFrame()

    if statMode == 'batting':
        if 'Player Average' in df['striker'].values:
            playerAvgDf = df[df['striker'] == 'Player Average']
            phaseAvgBallsFaced = [25, 25, 12, 30]
            #phaseAvgBallsFaced = [15]
        elif 'Team Average' in df['striker'].values:
            playerAvgDf = df[df['striker'] == 'Team Average']
            phaseAvgBallsFaced = [30, 50, 20, 100]
            #phaseAvgBallsFaced = [100]

        plotDf = plotDf[plotDf['striker'] != 'Team Average']
    if statMode == 'bowling':
        if 'Player Average' in df['bowler'].values:
            playerAvgDf = df[df['bowler'] == 'Player Average']
            phaseAvgBallsBowled = [25, 25, 12, 30]
            #phaseAvgBallsBowled = [18]
        elif 'Team Average' in df['bowler'].values:
            playerAvgDf = df[df['bowler'] == 'Team Average']
            phaseAvgBallsBowled = [30, 50, 20, 100]
            #phaseAvgBallsBowled = [100]

        plotDf = plotDf[plotDf['bowler'] != 'Team Average']

    ballsFaced = []

    for phase in phases:

        if not playerAvgDf.empty:
            ballsFaced.append(math.floor(0.75*playerAvgDf[phase + 'BPI'][0]))  

    phaseAvgBallsBowled = ballsFaced
    phaseAvgBallsFaced = ballsFaced

    for i, phase in enumerate(phases):

        phaseBallsFacedLabel = phase + 'BPI'
        phaseInningsLabel = phase + 'Inns'

        phaseAvgLabel = phases[i] + 'Avg'
        phaseSRLabel = phases[i] + 'SR'
        phaseRPILabel = phases[i] + 'RPI'

        if statMode == 'batting':
            avgBallsFaced = phaseAvgBallsFaced[i]

        if statMode == 'bowling':
            avgBallsFaced = phaseAvgBallsBowled[i]

        phaseDf = plotDf.copy()
        #phaseDf = phaseDf[phaseDf[phaseBallsFacedLabel] >= avgBallsFaced]

        tempDf = plotDf.copy()

        if statMode == 'batting':
            tempDf = tempDf[tempDf['striker'] != 'Player Average']
        if statMode == 'bowling':
            tempDf = tempDf[tempDf['bowler'] != 'Player Average']

        avgRunsScored = tempDf[phase + 'Runs'].mean()
        avgBPI = tempDf[phase + 'BPI'].mean()
        avgWPI = tempDf[phase + 'WPI'].mean()
        avgWickets = tempDf[phase + 'Wickets'].mean()

        if statMode == 'batting':
            phaseDf = phaseDf[phaseDf[phase + 'Runs'] >= avgRunsScored]
        if statMode == 'bowling':
            phaseDf = phaseDf[phaseDf[phase + 'Wickets'] >= avgWickets]

        avgInnsFaced = math.floor(phaseDf[phaseInningsLabel].mean()/3)
        #avgInnsFaced = 1

        #phaseDf = phaseDf[phaseDf[phaseInningsLabel] >= avgInnsFaced]

        phaseDf.to_excel(phase + statMode + '.xlsx')
            
        #phaseDf = phaseDf[~phaseDf['batting_team'].isin(['Namibia', 'Hong Kong', 'United Arab Emirates', 'Netherlands', 'Oman', 'Kenya', 'ICC World XI', 'Papua New Guinea', 'Canada', 'Nepal', 'Uganda', 'Spain', 'Zimbabwe', 'Ireland', 'Scotland', 'Afghanistan'])]
        #phaseDf = phaseDf[phaseDf['batting_team'].isin(['New Zealand', 'England', 'Bangladesh', 'India', 'Pakistan', 'Australia', 'Afghanistan', 'South Africa', 'West Indies', 'Sri Lanka', 'Ireland', 'Zimbabwe', 'Netherlands'])]

        #title = f"{statMode}{group} {labels[i]} (Min {avgInnsFaced} Innings, {avgBallsFaced} Balls Per Innings)"
        #title = f"{statMode} {labels[i]} (Min {avgInnsFaced} Innings, {avgBallsFaced} Balls Per Innings)"

        #title = f"{statMode} {group} {labels[i]} (Min {avgInnsFaced} Innings)"
        #title = f"{statMode} {labels[i]} (Min {avgInnsFaced} Innings)"

        if venueFilter != '':
            title = f"{venueTitle} {matchupPlot} {statMode} {group} {labels[i]} (Min {avgInnsFaced} Innings)"
        else:
            title = f"{statMode} {matchupPlot} {group} {labels[i]} (Min {avgInnsFaced} Innings)"

        title = f"{statMode} {matchupPlot} {group} {labels[i]} "

        global batterScatter
        global bowlerScatter

        if statMode == 'batting':
            colors = ['yellow', 'green', 'red', 'yellow']
            buildPlot(phaseDf[phase + 'dotPercent'].tolist(), phaseDf[phase + 'boundaryPercent'].tolist(), 0, operator.le, 0, operator.ge, 'or', phase + 'DotPercent', phase + 'BoundaryPercent', phaseDf, title, phase, colors)

            colors = ['green', 'yellow', 'yellow', 'red']
            if 'avgDiff' in phaseDf.columns:
                buildPlot(phaseDf['avgDiff'].tolist(), phaseDf['srDiff'].tolist(), -40, operator.ge, -100, operator.ge, 'or', 'Avg Diff (Player Avg - Team Avg Excluding Player)', 'SR Diff (Player SR - Team SR Excluding Player)', phaseDf, title, phase, colors)
            #buildPlot(phaseDf[phaseAvgLabel].tolist(), phaseDf[phaseSRLabel].tolist(), playerAvgDf[phaseAvgLabel][0], operator.ge, playerAvgDf[phaseSRLabel][0], operator.ge, 'or', 'Average', 'Strike Rate', phaseDf, title, phase)

            colors = ['green', 'yellow', 'yellow', 'red']
            batterScatter = buildPlot(phaseDf[phaseAvgLabel].tolist(), phaseDf[phaseSRLabel].tolist(), 0, operator.ge, 0, operator.ge, 'or', 'Average', 'Strike Rate', phaseDf, title, phase, colors)
            #buildPlot(phaseDf[phaseAvgLabel].tolist(), phaseDf[phaseSRLabel].tolist(), 0, operator.ge, 0, operator.ge, 'or', 'Average', 'Strike Rate', phaseDf, title, phase, colors)

        elif statMode == 'bowling':
            #phaseDf = phaseDf[phaseDf[phase + 'Avg'] < 50]
            phaseDf = phaseDf[phaseDf[phase + 'WPI'] > 0]
            
            colors = ['yellow', 'red', 'green', 'yellow']
            buildPlot(phaseDf[phase + 'dotPercent'].tolist(), phaseDf[phase + 'boundaryPercent'].tolist(), 0, operator.ge, 0, operator.le, 'or', phase + 'DotPercent', phase + 'BoundaryPercent', phaseDf, title, phase, colors)

            colors = ['red', 'yellow', 'yellow', 'green']
            #buildPlot(phaseDf[phaseAvgLabel].tolist(), phaseDf[phase + 'ER'].tolist(), 50, operator.le, 36, operator.le, 'or', 'Average', 'Economy Rate', phaseDf, title, phase, colors)

            colors = ['red', 'yellow', 'yellow', 'green']
            #if 'avgDiff' in phaseDf.columns:
                #buildPlot(phaseDf['avgDiff'].tolist(), phaseDf['srDiff'].tolist(), -50, operator.ge, -10, operator.ge, 'or', 'Avg Diff (Player Avg - Team Avg Excluding Player)', 'SR Diff (Player SR - Team SR Excluding Player)', phaseDf, title, phase, colors)

            colors = ['red', 'yellow', 'yellow', 'green']
            bowlerScatter = buildPlot(phaseDf[phaseAvgLabel].tolist(), phaseDf[phase + 'SR'].tolist(), 50, operator.le, 150, operator.le, 'or', 'Average', 'Strike Rate', phaseDf, title, phase, colors)
            #buildPlot(phaseDf['avgDiff'].tolist(), phaseDf['srDiff'].tolist(), playerAvgDf['avgDiff'][0], operator.le, playerAvgDf['srDiff'][0], operator.le, 'or', 'Avg Diff (Player Avg - Team Avg Excluding Player)', 'SR Diff (Player SR - Team SR Excluding Player)', phaseDf, title, phase)
            #buildPlot(phaseDf[phase + 'WPI'].tolist(), phaseDf[phase + 'ER'].tolist(), playerAvgDf[phase + 'WPI'][0], operator.ge, playerAvgDf[phase + 'ER'][0], operator.le, 'or', 'Wickets Per Innings', 'Economy Rate', phaseDf, title, phase)
            #buildPlot(phaseDf[phase + 'WPIDiff'].tolist(), phaseDf[phase + 'ERDiff'].tolist(), playerAvgDf[phase + 'WPIDiff'][0], operator.ge, playerAvgDf[phase + 'ERDiff'][0], operator.le, 'or', 'Wickets Per Innings Diff', 'Economy Rate Diff', phaseDf, title, phase)

def readFile(fileName, nbsrDf, startDate, endDate, inningsTotals):
    matchDf = pd.read_csv(fileName)
    matchDf = matchDf.fillna('')

    matchStartDate = matchDf['start_date']
    battingTeam = matchDf['batting_team'][0]
    bowlingTeam = matchDf['bowling_team'][0]

    #teams = ['New Zealand', 'England', 'Bangladesh', 'India', 'Pakistan', 'Australia', 'Afghanistan', 'South Africa', 'West Indies', 'Sri Lanka', 'Ireland', 'Zimbabwe', 'Netherlands']
    #teams = ['New Zealand', 'England', 'Bangladesh', 'India', 'Pakistan', 'Australia', 'South Africa', 'West Indies', 'Sri Lanka']
    teams = ['New Zealand', 'England', 'Bangladesh', 'India', 'Pakistan', 'Australia', 'Afghanistan', 'South Africa', 'Netherlands', 'Sri Lanka']

    startDateValue = startDate
    endDateValue = endDate

    filterResult = matchStartDate[0] >= startDateValue and matchStartDate[0] <= endDateValue
    #filterResult = True

    global filterTeams
    #filterTeams = ['New Zealand', 'England', 'Bangladesh', 'India', 'Pakistan', 'Australia', 'Afghanistan', 'South Africa', 'West Indies', 'Sri Lanka', 'Ireland', 'Zimbabwe', 'Netherlands']
    print(filterTeams)

    if len(filterTeams) > 0:
        filterResult = matchStartDate[0] >= startDateValue and matchStartDate[0] <= endDateValue and battingTeam in filterTeams and bowlingTeam in filterTeams

    # and (battingTeam in teams or bowlingTeam in teams)

    if filterResult:

        matchDf.replace(teams_mapping, inplace=True)
        
        allColumns = ['match_id', 'season', 'start_date', 'venue', 'innings', 'ball',
        'batting_team', 'bowling_team', 'striker', 'non_striker', 'bowler',
        'runs_off_bat', 'extras', 'wides', 'noballs', 'byes', 'legbyes',
        'penalty', 'wicket_type', 'player_dismissed', 'other_wicket_type',
        'other_player_dismissed']
        
        matchColumns = ['match_id', 'season', 'start_date', 'venue', 'innings',
        'batting_team', 'bowling_team', 'striker', 'wicket_type', 'player_dismissed', 'other_wicket_type',
        'other_player_dismissed']
        
        bowlingColumns = allColumns
        
        integerColumns = ['runs_off_bat', 'extras', 'wides', 'noballs', 'byes', 'legbyes', 'penalty', 'innings']
        decimalColumns = ['ball']
        
        matchDf['ball'] = matchDf['ball'].astype(float)
        
        for column in integerColumns:
            matchDf[column] = matchDf[column].replace('', 0)
        
        teams = matchDf['batting_team'].unique()
        check = True

        masterPlayers = pd.read_excel('masterPlayers.xlsx')

        playerTypeColumns = ['striker', 'non_striker', 'bowler']
        prefixes = ['s', 'ns', 'b']

        for i in range(0, len(playerTypeColumns)):

            column = playerTypeColumns[i]
            prefix = prefixes[i]

            tempDf = masterPlayers.copy()
            tempDf.rename(columns={"Player": column, 'batterType': prefix+'_batterType', 'bowlerType': prefix+'_bowlerType',
                                    'bowlHand': prefix+'_bowlHand', 'bowlType': prefix+'_bowlType'}, inplace=True)
            
            matchDf = pd.merge(matchDf, tempDf, on=column, how='outer')

        inningsTotalDf = pd.DataFrame()

        matchDf = buildMatchupColumns(matchDf)
        matchDf = matchDf[matchDf['ball'] >= 0.0]
        matchDf.to_excel('matchDf.xlsx')
        
        if check:
            matchTotals, inningsTotalDf = buildMatchTotals(matchDf, inningsTotalDf) 
            inningsTotals = pd.concat([inningsTotals, inningsTotalDf])

            if calculateNBSRFlag == True:
                nbsrDf = calculateNBSR(matchDf, nbsrDf, 'player') #
                nbsrDf = calculateNBSR(matchDf, nbsrDf, 'team') #

        else:
            matchTotals = pd.DataFrame()
        
        return [matchTotals, nbsrDf, inningsTotals]

def buildMatchupColumns(matchDf):

    batterTypeColumns = ['striker', 's_batterType']
    bowlerTypeColumns = ['bowler', 'b_bowlerType']

    batterTypeColumns = []
    bowlerTypeColumns = []

    for batterType in batterTypeColumns:

        for bowlerType in bowlerTypeColumns:

            columnName = batterType + '_vs_' + bowlerType
            matchDf[columnName] = matchDf[batterType] + ' vs ' + matchDf[bowlerType] 
            
            matchupColumns.append(columnName)

    return matchDf

def calculateNBSR(df, nbsrDf, group):
    tempDf = df.copy()
    
    if group == 'player':
        filter = 'striker' if statMode == 'batting' else 'bowler'
    elif group == 'team':
        filter = 'batting_team' if statMode == 'batting' else 'bowling_team'

    strikers = tempDf[filter].unique()
    
    for striker in strikers:
        strikerDf = df[df[filter] == striker].copy()
        strikerDf.sort_values(by='ball', inplace=True)
        
        if statMode == 'batting':
            strikerDf = strikerDf[strikerDf['wides'] == 0]

        strikerDf.set_index('ball', inplace=True)
        strikerDf = strikerDf.fillna(0)

        nbsrDf = nbsrDf.fillna(0)
        
        ballsFaced = len(strikerDf)
        
        tempDict = {'playerName': striker}
        
        if not nbsrDf.empty:
            existingPlayers = nbsrDf['playerName'].tolist()
            
            if striker in existingPlayers:
                tempDict = nbsrDf[nbsrDf['playerName'] == striker].iloc[0].to_dict()
        
        ballCounter = 1
        
        for i in strikerDf.index:
            runsColumnName = f'ball{ballCounter}Runs'
            ballsFacedColumnName = f'ball{ballCounter}BallsFaced'
            nbsrColumnName = f'ball{ballCounter}SR'
            
            prevRuns = prevBalls = 0
            
            if ballCounter > 1:
                prevrunsColumnName = f'ball{ballCounter-1}Runs'
                prevballsFacedColumnName = f'ball{ballCounter-1}BallsFaced'
                prevnbsrColumnName = f'ball{ballCounter-1}SR'
                
                prevRuns = int(tempDict[prevrunsColumnName])
                prevBalls = int(tempDict[prevballsFacedColumnName])
            
            strikerDict = strikerDf.loc[i].to_dict()
            currentRuns = 0

            #if isinstance(strikerDict['runs_off_bat'], Mapping):
             #   currentRuns = int(sum(strikerDict['runs_off_bat'].values()))
            #else:
             #   currentRuns = int(strikerDict['runs_off_bat'])

            currentRuns = int(tempDict.get(runsColumnName, currentRuns))
            
            if isinstance(strikerDict['runs_off_bat'], Mapping):
                runsToAdd = int(sum(strikerDict['runs_off_bat'].values()))
            else:
                runsToAdd = int(strikerDict['runs_off_bat'])

            tempDict[runsColumnName] = currentRuns + runsToAdd
            tempDict[ballsFacedColumnName] = tempDict.get(ballsFacedColumnName, 0) + 1
            tempDict[nbsrColumnName] = calcSR(tempDict[runsColumnName], tempDict[ballsFacedColumnName])
            
            ballCounter += 1
        
        if not nbsrDf.empty:
            if striker in existingPlayers:
                nbsrDf = nbsrDf[nbsrDf['playerName'] != striker]
            
            nbsrDf = nbsrDf.append(tempDict, ignore_index=True)
        else:
            nbsrDf = nbsrDf.append(tempDict, ignore_index=True)
        
        nbsrDf = nbsrDf.drop_duplicates(subset=['playerName'], keep='last').fillna(0)
    
    return nbsrDf    

def buildMatchTotals(df, inningsTotalDf):

    allColumns = ['match_id', 'season', 'start_date', 'venue', 'innings', 'ball',
       'batting_team', 'bowling_team', 'striker', 'non_striker', 'bowler',
       'runs_off_bat', 'extras', 'wides', 'noballs', 'byes', 'legbyes',
       'penalty', 'wicket_type', 'player_dismissed', 'other_wicket_type',
       'other_player_dismissed']

    matchColumns = ['match_id', 'season', 'start_date', 'venue', 'innings',
       'batting_team', 'bowling_team', 'striker', 'bowler', 'wicket_type', 'player_dismissed', 'other_wicket_type',
       'other_player_dismissed']

    global matchupTotals

    if (statMode == 'batting'):

        matchTotals = pd.DataFrame()
        matchInningsTotals = pd.DataFrame()
        typeTotals = pd.DataFrame()

        df = df[df['innings'].notna()]

        matchColumns.append('s_batterType')
        matchColumns.append('b_bowlerType')
        matchColumns.append('b_bowlType')
        matchColumns.append('b_bowlHand')

        allColumns.append('b_bowlerType')
        allColumns.append('b_bowlType')
        allColumns.append('b_bowlHand')

        for innings in df['innings'].unique():

            tempDf = df.copy()
            tempDf = tempDf[tempDf['innings'] == innings]

            tempDf.to_excel(f"TempInningsDf {statMode} {venueTitle} {timePeriod}.xlsx")

            inningsTotal = pd.DataFrame()
            inningsTotal = calculateGroupTotals(tempDf, matchColumns, 'batting_team', inningsTotal)
            matchInningsTotals = pd.concat([matchInningsTotals, inningsTotal])

            batterTotals = calculateGroupTotals(tempDf, matchColumns, 'striker', inningsTotal)
            batterTotals = calculateDiffs(inningsTotal, batterTotals)

            batterTypeTotals = calculateGroupTotals(tempDf, matchColumns, 's_batterType', inningsTotal)
            typeTotals = pd.concat([typeTotals, batterTypeTotals])

            for column in matchupColumns:

                matchupTotal = calculateGroupTotals(tempDf, matchColumns, column, inningsTotal)
                matchupTotals = pd.concat([matchupTotals, matchupTotal])

                #matchupTotals = matchupTotals.drop_duplicates(subset = ['match_id', 'matchup'], keep = 'last').reset_index(drop = True)

            for index, row in batterTotals.iterrows():

                row['matchInnings'] = innings

            tempMatchTotals = pd.concat([inningsTotal, batterTotals])
            tempMatchTotals = tempMatchTotals.fillna(0)

            matchTotals = pd.concat([matchTotals, tempMatchTotals])

        matchInningsTotals = matchInningsTotals.sort_values(by='innings')

        typeTotals.to_excel(f"Type Totals {statMode} {venueTitle} {timePeriod}.xlsx")
        typeTotals['innings'] = typeTotals['innings'].astype(int)
        typeTotals = typeTotals.sort_values(by='innings')

        if not matchupTotals.empty:
            matchupTotals['innings'] = matchupTotals['innings'].astype(int)
            matchupTotals = matchupTotals.sort_values(by='innings')

            matchupTotals.to_excel('tempMatchupTotals.xlsx')

        inningsTotalDict = buildInnsTotalDict(matchInningsTotals, typeTotals)

        matchInningsTotals.to_excel(f"Temp Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")
        inningsTotalDf = inningsTotalDf.append(inningsTotalDict, ignore_index=True)


    if (statMode == 'bowling'):

        matchTotals = pd.DataFrame()
        matchInningsTotals = pd.DataFrame()
        typeTotals = pd.DataFrame()

        df = df[df['innings'].notna()]

        matchColumns.append('s_batterType')
        matchColumns.append('b_bowlerType')
        matchColumns.append('b_bowlType')
        matchColumns.append('b_bowlHand')

        allColumns.append('b_bowlerType')
        allColumns.append('b_bowlType')
        allColumns.append('b_bowlHand')

        for innings in df['innings'].unique():

            tempDf = df.copy()
            tempDf = tempDf[tempDf['innings'] == innings]

            inningsTotal = pd.DataFrame()
            inningsTotal = calculateGroupTotals(tempDf, allColumns, 'bowling_team', inningsTotal)
            matchInningsTotals = pd.concat([matchInningsTotals, inningsTotal])
            matchInningsTotals.to_excel(f"Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")

            bowlerTotals = calculateGroupTotals(tempDf, allColumns, 'bowler', inningsTotal)
            bowlerTotals = calculateDiffs(inningsTotal, bowlerTotals)

            bowlerTypeTotals = calculateGroupTotals(tempDf, matchColumns, 'b_bowlerType', inningsTotal)
            typeTotals = pd.concat([typeTotals, bowlerTypeTotals])

            bowlerTypeTotals = calculateGroupTotals(tempDf, matchColumns, 'b_bowlType', inningsTotal)
            typeTotals = pd.concat([typeTotals, bowlerTypeTotals])

            for column in matchupColumns:

                matchupTotal = calculateGroupTotals(tempDf, matchColumns, column, inningsTotal)
                matchupTotals = pd.concat([matchupTotals, matchupTotal])

                #matchupTotals = matchupTotals.drop_duplicates(subset = ['match_id', 'striker'],keep = 'last').reset_index(drop = True)

            for index, row in bowlerTotals.iterrows():

                row['matchInnings'] = innings

            tempMatchTotals = pd.concat([inningsTotal, bowlerTotals])
            tempMatchTotals = tempMatchTotals.fillna(0)

            matchTotals = pd.concat([matchTotals, tempMatchTotals])

        matchInningsTotals = matchInningsTotals.sort_values(by='innings')
        typeTotals['innings'] = typeTotals['innings'].astype(int)
        typeTotals = typeTotals.sort_values(by='innings')
        typeTotals.to_excel(f"Type Totals {statMode} {venueTitle} {timePeriod}.xlsx")

        if not matchupTotals.empty:
            matchupTotals['innings'] = matchupTotals['innings'].astype(int)
            matchupTotals = matchupTotals.sort_values(by='innings')

        matchInningsTotals.to_excel(f"Temp Match Innings Totals {statMode} {venueTitle} {timePeriod}.xlsx")

        inningsTotalDict = buildInnsTotalDict(matchInningsTotals, typeTotals)
        inningsTotalDf = inningsTotalDf.append(inningsTotalDict, ignore_index=True)

    return matchTotals, inningsTotalDf

def buildInnsTotalDict(matchInningsTotals, typeTotals):

    inningsTotalDict = {}

    for index, row in matchInningsTotals.iterrows():
        
        inningsTotalDict['matchId'] = row['match_id']
        inningsNumber = int(row['innings'])

        inningsTeamLabel = 'innings' + str(inningsNumber) + 'Team'
        inningsTotalDict[inningsTeamLabel] = row['bowler']

        inningsTotalLabel = 'innings' + str(inningsNumber) + 'Runs'
        inningsTotalDict[inningsTotalLabel] = int(row['runs'])

        inningsTotalLabel = 'innings' + str(inningsNumber) + 'Balls'
        inningsTotalDict[inningsTotalLabel] = int(row['ballsFaced'])

        inningsWicketsLabel = 'innings' + str(inningsNumber) + 'Wickets'
        inningsTotalDict[inningsWicketsLabel] = int(row['wickets'])

    phases = ['pp', 'mo', 'death', 'overall', 'mo1', 'mo2', 'mo3']

    for phase in phases:

        for index, row in matchInningsTotals.iterrows():

            inningsNumber = int(row['innings'])

            innsRunsLabel = 'innings' + str(inningsNumber) + str(phase) + 'Runs'
            inningsTotalDict[innsRunsLabel] = int(row[str(phase) + 'Runs'])

            innsBallsLabel = 'innings' + str(inningsNumber) + str(phase) + 'Balls'
            inningsTotalDict[innsBallsLabel] = int(row[str(phase) + 'Balls'])

            innsWicketsLabel = 'innings' + str(inningsNumber) + str(phase) + 'Wickets'
            inningsTotalDict[innsWicketsLabel] = int(row[str(phase) + 'Wickets'])

    for innings in typeTotals['innings'].unique().tolist():

        tempDf = typeTotals.copy()
        tempDf = tempDf[tempDf['innings'] == innings]

        for index, row in tempDf.iterrows():

            inningsNumber = int(row['innings'])

            label = row['bowler']

            if statMode == 'batting':
                label = row['striker']

            inningsTotalLabel = 'innings' + str(inningsNumber) + str(label) + 'Runs'
            inningsTotalDict[inningsTotalLabel] = int(row['runs'])

            inningsTotalLabel = 'innings' + str(inningsNumber) + str(label) + 'Balls'
            inningsTotalDict[inningsTotalLabel] = int(row['ballsFaced'])

            inningsWicketsLabel = 'innings' + str(inningsNumber) + str(label) + 'Wickets'
            inningsTotalDict[inningsWicketsLabel] = int(row['wickets'])

    return inningsTotalDict

def calculateOverallTotals(batterTotals, masterDf):

    overallBatterDf = pd.DataFrame()

    totalDict = {}

    batterDf = batterTotals.iloc[len(batterTotals.index) - 1]

    #if statMode == 'batting':
        #battingTeam = batterDf['batting_team']

    #if statMode == 'bowling':
        #battingTeam = batterDf['bowling_team']

    allColumns = ['innings', 'striker', 'bowler', 'matchup', 'batting_team', 'bowling_team', 'runs', 'wickets',
       'ballsFaced', 'inningsAvg', 'inningsSR', 'dots', '1s', '2s', '3s', '4s',
       '6s', 'dotPercent', 'boundaryPercent', 'ppInns', 'ppRuns', 'ppBalls', 'ppWickets',
       'ppAvg', 'ppSR', 'ppdots', 'pp1s', 'pp2s', 'pp3s', 'pp4s', 'pp6s', 'ppExtras', 'ppER', 
       'ppdotPercent', 'ppboundaryPercent', 'moInns', 'moRuns', 'moBalls', 'moWickets',
       'moAvg', 'moSR', 'modots', 'mo1s', 'mo2s', 'mo3s', 'mo4s', 'mo6s', 'moExtras', 'moER',
       'modotPercent', 'moboundaryPercent','deathInns', 'deathRuns', 'deathBalls',
       'deathWickets', 'deathAvg', 'deathSR', 'deathdots', 'death1s',
       'death2s', 'death3s', 'death4s', 'death6s', 'deathExtras', 'deathER', 'deathdotPercent',
       'deathboundaryPercent', 'overallInns', 'overallRuns', 'overallBalls',
       'overallWickets', 'overallAvg', 'overallSR', 'overalldots', 'overall1s',
       'overall2s', 'overall3s', 'overall4s', 'overall6s', 'overallExtras', 'overallER', 'overalldotPercent',
       'overallboundaryPercent', 'teamRunsExclBatter', 'teamBallsExclBatter',
       'avgDiff', 'srDiff', 'teamAvgExclBatter', 'teamSRExclBatter', 'ppTeamAvg', 'ppTeamSR', 'ppAvgDiff', 'ppSRDiff',
       'moTeamAvg', 'moTeamSR', 'moAvgDiff', 'moSRDiff', 'deathTeamAvg', 'deathTeamSR', 'deathAvgDiff', 'deathSRDiff',
       'ppTeamRuns', 'ppTeamBalls', 'ppTeamWickets', 'moTeamRuns', 'moTeamBalls', 'moTeamWickets', 'deathTeamRuns', 'deathTeamBalls', 'deathTeamWickets',
       'overallTeamRuns', 'overallTeamBalls', 'overallTeamWickets']

    phases = ['mo1', 'mo2', 'mo3']
    columns = ['Inns', 'Runs', 'Balls', 'Wickets', 'Avg', 'SR', 'dots', '1s', '2s', '3s', '4s', '6s', 'Extras', 'ER', 'dotPercent', 'boundaryPercent']

    for phase in phases:

        for column in columns:

            allColumns.append(phase + column)

            if column in ['Inns', 'Runs', 'Balls', 'Wickets', 'dots', '1s', '2s', '3s', '4s', '6s', 'Extras']:
                sumColumns.append(phase + column)

    global runsRangeColumns
    runsRangeColumns.sort()
    runsRangeColumns = [*set(runsRangeColumns)]
    if statMode == 'batting':
        sumColumns.extend(runsRangeColumns)

    for column in allColumns:

        if column in batterTotals.columns:
            totalDict[column] = batterDf[column]

    for column in sumColumns:
        
        if column in batterTotals.columns:
            totalDict[column] = batterTotals[column].sum()

    phases = ['pp', 'mo', 'death', 'overall', 'mo1', 'mo2', 'mo3']

    for phase in phases:
        
        phaseInns = totalDict[phase + 'Inns']
        phaseRuns = totalDict[phase + 'Runs']
        phaseBalls = totalDict[phase + 'Balls']
        phaseWickets = totalDict[phase + 'Wickets']
        phaseDots = totalDict[phase + 'dots']
        phaseBoundaries = totalDict[phase + '4s'] + totalDict[phase + '6s']
        totalBallsFaced = totalDict['ballsFaced']

        if (phase + 'TeamRuns') in totalDict:
            phaseTeamRuns = totalDict[phase + 'TeamRuns']
            phaseTeamBalls = totalDict[phase + 'TeamBalls']
            phaseTeamWickets = totalDict[phase + 'TeamWickets']

        totalDict[phase + 'BPI'] = calcAvg(phaseBalls, phaseInns)
        totalDict[phase + 'Avg'] = calcAvg(phaseRuns, phaseWickets)
        totalDict[phase + 'WPI'] = calcAvg(phaseWickets, phaseInns)

        if statMode == 'batting':
            totalDict[phase + 'SR'] = calcSR(phaseRuns, phaseBalls)

        if statMode == 'bowling':
            totalDict[phase + 'SR'] = calcSR(phaseWickets, phaseBalls)
            
            if phaseInns > 0:

                totalDict[phase + 'EPI'] = round(totalDict[phase + 'Extras']/phaseInns, 2)

        totalDict[phase + '4PI'] = calcAvg(totalDict[phase + '4s'], phaseInns)
        totalDict[phase + '6PI'] = calcAvg(totalDict[phase + '6s'], phaseInns)
        totalDict[phase + 'BP4'] = calcAvg(phaseBalls, totalDict[phase + '4s'])
        totalDict[phase + 'BP6'] = calcAvg(phaseBalls, totalDict[phase + '6s'])
        totalDict[phase + 'BPB'] = calcAvg(phaseBalls, phaseBoundaries)

        if statMode == 'batting':
            totalDict[phase + 'RPI'] = totalDict[phase + 'BPI']*totalDict[phase + 'SR']/100
        
        phaseER = 0

        if phaseBalls > 0:
            phaseER = 6*phaseRuns/phaseBalls

        totalDict[phase + 'ER'] = phaseER

        if statMode == 'bowling':
            totalDict[phase + 'RPI'] = totalDict[phase + 'BPI']*totalDict[phase + 'ER']/6

        if statMode == 'batting':
            totalDict[phase + 'AvgScore'] = str(math.ceil(totalDict[phase + 'RPI'])) + '-' + str(math.ceil(totalDict[phase + 'WPI'])) + ' (' + str(math.ceil(totalDict[phase + 'BPI'])) + ')'
        if statMode == 'bowling' and phaseInns > 0:
            totalDict[phase + 'AvgScore'] = str(math.ceil(phaseBalls/phaseInns)) + '-' + str(math.ceil(totalDict[phase + 'dots']/phaseInns)) + '-' + str(math.ceil(phaseRuns/phaseInns)) + '-' + str(round(phaseWickets/phaseInns, 2))

        if phaseBalls > 0:
            totalDict[phase + 'dotPercent'] = 100*phaseDots/phaseBalls
            totalDict[phase + 'boundaryPercent'] = 100*phaseBoundaries/phaseBalls
        else:
            totalDict[phase + 'dotPercent'] = 0
            totalDict[phase + 'boundaryPercent'] = 0

        if phase != 'overall':

            if (phase + 'TeamRuns') in totalDict:
                phaseTeamRuns = totalDict[phase + 'TeamRuns']
                phaseTeamBalls = totalDict[phase + 'TeamBalls']
                phaseTeamWickets = totalDict[phase + 'TeamWickets']

                totalDict[phase + 'TeamAvg'] = calcAvg(phaseTeamRuns, phaseTeamWickets)

                if statMode == 'batting':
                    totalDict[phase + 'TeamSR'] = calcSR(phaseTeamRuns, phaseTeamBalls)

                if statMode == 'bowling':
                    totalDict[phase + 'TeamSR'] = calcSR(phaseTeamWickets, phaseTeamBalls)
                
                totalDict[phase + 'AvgDiff'] = totalDict[phase + 'Avg'] - totalDict[phase + 'TeamAvg']
                totalDict[phase + 'SRDiff'] = totalDict[phase + 'SR'] - totalDict[phase + 'TeamSR']

            totalDict[phase + '%BallsFaced'] = round(100*phaseBalls/totalBallsFaced, 2)

        if (phase + 'TeamRuns') in totalDict:
            phaseTeamRunsExclBatter = phaseTeamRuns
            phaseTeamBallsExclBatter = phaseTeamBalls
            phaseTeamWktsExclBatter = phaseTeamWickets
        
            totalDict[phase + 'ERDiff'] = 6*round(calcAvg(phaseRuns, phaseBalls), 2) - 6*round(calcAvg(phaseTeamRunsExclBatter, phaseTeamBallsExclBatter), 2)

            if phaseWickets > 0 and phaseBalls > 0:
                totalDict[phase + 'WPIDiff'] = totalDict[phase + 'BPI']*(calcAvg(phaseWickets, phaseBalls) - calcAvg(phaseTeamWktsExclBatter, phaseTeamBallsExclBatter))
            else:
                totalDict[phase + 'WPIDiff'] = 0

        if phaseWickets > 0:
            totalDict[phase + 'BPD'] = math.floor(phaseBalls/phaseWickets)
        else:
            totalDict[phase + 'BPD'] = phaseBalls

    totalDict['inningsAvg'] = calcAvg(totalDict['runs'], totalDict['wickets'])

    if statMode == 'batting':
        totalDict['inningsSR'] = calcSR(totalDict['runs'], totalDict['ballsFaced'])

    if statMode == 'bowling':
        totalDict['inningsSR'] = calcSR(totalDict['wickets'], totalDict['ballsFaced'])

    if ('teamRunsExclBatter') in totalDict:

        totalDict['teamAvgExclBatter'] = calcAvg(totalDict['teamRunsExclBatter'], totalDict['teamWicketsExclBatter'])

        if statMode == 'batting':
            totalDict['teamSRExclBatter'] = calcSR(totalDict['teamRunsExclBatter'], totalDict['teamBallsExclBatter'])

        if statMode == 'bowling':
            totalDict['teamSRExclBatter'] = calcSR(totalDict['teamWicketsExclBatter'], totalDict['teamBallsExclBatter'])

        totalDict['avgDiff'] = totalDict['inningsAvg'] - totalDict['teamAvgExclBatter']
        totalDict['srDiff'] = totalDict['inningsSR'] - totalDict['teamSRExclBatter']

    totalDict['dotPercent'] = totalDict['dots']/totalDict['ballsFaced']
    totalDict['boundaryPercent'] = (totalDict['4s'] + totalDict['6s'])/totalDict['ballsFaced']

    if ('avgDiff') in batterTotals.columns:

        aboveAvgDf = batterTotals[batterTotals['avgDiff'] >= 0]
        pctAboveAvg = 100*len(aboveAvgDf.index)/len(batterTotals.index)

        aboveSRDf = batterTotals[batterTotals['srDiff'] >= 0]
        pctAboveSR = 100*len(aboveSRDf.index)/len(batterTotals.index)

        totalDict['overall' + 'AboveAvgPct'] = pctAboveAvg
        totalDict['overall' + 'AboveSRPct'] = pctAboveSR

    overallBatterDf = overallBatterDf.append(totalDict, ignore_index=True)

    #(overallBatterDf)

    return overallBatterDf
    
def calculateDiffs(inningsTotal, batterTotals):
    lstAvgDiffs = []
    lstSRDiffs = []
    lstTeamAvgBatterExcl = []
    lstTeamSRBatterExcl = []
    lstTeamRunsExclBatter = []
    lstTeamBallsExclBatter = []
    lstTeamWktsExclBatter = []

    lstWPIDiffs = []
    lstERDiffs = []

    for index, row in batterTotals.iterrows():

        filter = 'striker' if statMode == 'batting' else 'bowler'
        batter = row[filter]

        batterDf = batterTotals.loc[batterTotals[filter] == batter].iloc[-1]

        batterRuns = batterDf['runs']
        batterBalls = batterDf['ballsFaced']
        batterWickets = batterDf['wickets']
        batterAvg = batterDf['inningsAvg']
        batterSR = batterDf['inningsSR']

        teamFilter = batterDf['batting_team'] if statMode == 'batting' else batterDf['bowling_team']
        teamDf = inningsTotal.loc[inningsTotal[filter] == teamFilter].iloc[-1]

        teamRuns = teamDf['runs']
        teamBalls = teamDf['ballsFaced']
        teamWickets = teamDf['wickets']
        teamAvg = teamDf['inningsAvg']
        teamSR = teamDf['inningsSR']

        teamRunsWoBatter = teamRuns - batterRuns
        teamBallsWoBatter = teamBalls - batterBalls
        teamWicketsWoBatter = teamWickets - batterWickets

        lstTeamRunsExclBatter.append(teamRunsWoBatter)
        lstTeamBallsExclBatter.append(teamBallsWoBatter)
        lstTeamWktsExclBatter.append(teamWicketsWoBatter)

        teamAvgWoBatter = teamRunsWoBatter / teamWicketsWoBatter
        teamSRWoBatter = 100 * teamRunsWoBatter / teamBallsWoBatter

        lstTeamAvgBatterExcl.append(teamAvgWoBatter)
        lstTeamSRBatterExcl.append(teamSRWoBatter)

        batterAvgDiff = batterAvg - teamAvgWoBatter
        batterSRDiff = batterSR - teamSRWoBatter

        lstAvgDiffs.append(batterAvgDiff)
        lstSRDiffs.append(batterSRDiff)

    batterTotals['teamRunsExclBatter'] = lstTeamRunsExclBatter
    batterTotals['teamBallsExclBatter'] = lstTeamBallsExclBatter
    batterTotals['teamWicketsExclBatter'] = lstTeamWktsExclBatter
    batterTotals['avgDiff'] = lstAvgDiffs
    batterTotals['srDiff'] = lstSRDiffs
    batterTotals['teamAvgExclBatter'] = lstTeamAvgBatterExcl
    batterTotals['teamSRExclBatter'] = lstTeamSRBatterExcl

    return batterTotals

def calcAvg(runs, wickets):

    if wickets > 0:
        return runs/wickets
    else:
        return runs

def calcSR(runs, balls):

    if statMode == 'batting':

        if balls > 0:
            return round(100*runs/balls, 2)
        else:
            return 0

    if statMode == 'bowling':

        if runs > 0:
            return round(balls/runs, 2)
        else:
            return 0

def calculatePhaseWise(groupDf, tempDict, group, groupColumn, inningsTotal):

    startOvers = [ppStart, ppStart, moStart, deathStart]
    endOvers = [deathEnd, ppEnd, moEnd, deathEnd]
    labels = ['overall', 'pp', 'mo', 'death']
    bowlerDismissals = ['caught', 'lbw', 'caught and bowled', 'bowled', 'stumped', 'hit wicket']

    startOvers = startOvers + [0.0, 30.0, 60.0]
    endOvers = endOvers + [30.0, 60.0, 450.0]
    labels = labels + ['mo1', 'mo2', 'mo3']

    for index in range(0, len(startOvers)):

        groupDfCopy = groupDf.copy()

        startOver = startOvers[index]
        endOver = endOvers[index]
        label = labels[index]

        ppDf = groupDfCopy[(groupDfCopy['ball'] >= startOver)] 
        ppDf = ppDf[(ppDf['ball'] < endOver)] 

        ppDict = groupDf.iloc[0]

        ppRuns = 0
        ppExtras = 0

        if statMode == 'batting':
            ppRuns = ppDf['runs_off_bat'].astype(int).sum()
        if statMode == 'bowling':
            runsScored = ppDf['runs_off_bat'].astype(int).sum()
            extras = ppDf['extras'].astype(int).to_numpy().sum()
            penalties = ppDf['penalty'].astype(int).to_numpy().sum()
            ppRuns = runsScored + extras + penalties
            ppExtras = extras + penalties

        ppBalls = len(ppDf.index)

        if groupColumn == 'striker':
            widesDf = ppDf[ppDf['wides'] >= 1]
            wides = len(widesDf['wides'].tolist())
            ppBalls = ppBalls - wides

        if statMode == 'batting':
            if groupColumn in ['batting_team', 's_batterType']:
                playersDismissed = ppDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            elif groupColumn in matchupColumns:
                matchups = groupColumn.split('_vs_')
                print('#### MATCHUPS ####')
                print(matchups)
                print(tempDict['striker'])

                """
                if (' vs ' + tempDict[matchups[1]]) in tempDict[matchups[0]]:
                    tempDict['striker'] = tempDict[matchups[0]]
                else:
                    tempDict['striker'] = tempDict[matchups[0]] + ' vs ' + tempDict[matchups[1]]
                """

                tempDict['matchup'] = group

                playersDismissed = groupDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            else:
                playersDismissed = ppDf[ppDf['player_dismissed'] == group]

        if statMode == 'bowling':

            ppDf = ppDf[ppDf['wicket_type'] != 'run out']

            if groupColumn == 'bowling_team':
                playersDismissed = ppDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            elif groupColumn in ['bowler', 'b_bowlerType', 'b_bowlType']:
                tempDf = ppDf.copy()
                tempDf = ppDf[ppDf['wicket_type'].isin(bowlerDismissals)]
                playersDismissed = tempDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            elif groupColumn in matchupColumns:
                matchups = groupColumn.split('_vs_')
                tempDict['matchup'] = group

                tempDf = ppDf.copy()
                tempDf = ppDf[ppDf['wicket_type'].isin(bowlerDismissals)]
                playersDismissed = tempDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            else:
                playersDismissed = ppDf[ppDf['player_dismissed'].str.len() > 0]

        ppWickets = len(playersDismissed)

        if not inningsTotal.empty:

            teamFilter = ''

            if statMode == 'batting':
                teamFilter = ppDict['batting_team']
                inningsTotal = inningsTotal[inningsTotal['striker'] == teamFilter]

            if statMode == 'bowling':
                teamFilter = ppDict['bowling_team']
                inningsTotal = inningsTotal[inningsTotal['bowler'] == teamFilter]

            inningsDict = inningsTotal.iloc[0]
            ppTeamRuns = inningsDict[label + 'Runs'] - ppRuns
            ppTeamBalls =  inningsDict[label + 'Balls'] - ppBalls  
            ppTeamWickets = inningsDict[label + 'Wickets'] - ppWickets  
            
            tempDict[label + 'TeamRuns'] = ppTeamRuns
            tempDict[label + 'TeamBalls'] = ppTeamBalls
            tempDict[label + 'TeamWickets'] = ppTeamWickets
            tempDict[label + 'TeamAvg'] = calcAvg(ppTeamRuns, ppTeamWickets)

            if statMode == 'batting':
                tempDict[label + 'TeamSR'] = calcSR(ppTeamRuns, ppTeamBalls)

            if statMode == 'bowling':
                tempDict[label + 'TeamSR'] = calcSR(ppTeamWickets, ppTeamBalls)

        ppAvg = calcAvg(ppRuns, ppWickets)

        if statMode == 'batting':
            ppSR = calcSR(ppRuns, ppBalls)

        if statMode == 'bowling':
            ppSR = calcSR(ppBalls, ppWickets)

        dots = len(ppDf[ppDf['runs_off_bat'] == 0])
        ones = len(ppDf[ppDf['runs_off_bat'] == 1])
        twos = len(ppDf[ppDf['runs_off_bat'] == 2])
        threes = len(ppDf[ppDf['runs_off_bat'] == 3])
        fours = len(ppDf[ppDf['runs_off_bat'] == 4])
        sixes = len(ppDf[ppDf['runs_off_bat'] == 6])

        tempDict[label + 'Runs'] = ppRuns
        tempDict[label + 'Balls'] = ppBalls
        tempDict[label + 'Wickets'] = ppWickets
        tempDict[label + 'Avg'] = ppAvg
        tempDict[label + 'SR'] = ppSR
        tempDict[label +'dots'] = dots
        tempDict[label +'1s'] = ones
        tempDict[label +'2s'] = twos
        tempDict[label +'3s'] = threes
        tempDict[label +'4s'] = fours
        tempDict[label +'6s'] = sixes
        tempDict[label + 'Extras'] = ppExtras
        tempDict[label + 'ER'] = 0

        if not inningsTotal.empty:
            tempDict[label + 'AvgDiff'] = ppAvg - tempDict[label + 'TeamAvg']
            tempDict[label + 'SRDiff'] = ppSR - tempDict[label + 'TeamSR']

        if ppBalls > 0:
            tempDict[label +'dotPercent'] = 100*dots/ppBalls
            tempDict[label +'boundaryPercent'] = 100*(fours+sixes)/ppBalls
        else:
            tempDict[label +'dotPercent'] = 0
            tempDict[label +'boundaryPercent'] = 0

        if groupColumn == 'striker':
            assignRunsRange(tempDict, ppRuns, label)

def assignRunsRange(tempDict, runsScored, label):

    """
    floorValue = 10*math.floor(runsScored/10)
    ceilValue = 10*math.ceil(runsScored/10)

    if floorValue == ceilValue:
        ceilValue = ceilValue + 10

    key = label + str(floorValue) + '-' + str(ceilValue) + 'Runs'

    tempDict[key] = tempDict.get(key, 0) + 1
    runsRangeColumns.append(key)
    """

    if runsScored in range(0, 31):

        key = label + str(0) + '-' + str(30) + 'Runs'

        tempDict[key] = tempDict.get(key, 0) + 1
        runsRangeColumns.append(key)

    milestones = [30, 50, 100, 150, 200]

    for milestone in milestones:

        if runsScored > milestone:
            key = label + str(milestone) + 'PlusRuns'
            tempDict[key] = tempDict.get(key, 0) + 1
            runsRangeColumns.append(key)

def calculateGroupTotals(df, columns, groupColumn, inningsTotal):

    groupedDf = pd.DataFrame()

    groups = df[groupColumn].dropna().unique()

    bowlerDismissals = ['caught', 'lbw', 'caught and bowled', 'bowled', 'stumped', 'hit wicket']

    for group in groups:

        groupDf = df.copy()
        groupDf = groupDf[groupDf[groupColumn] == group]

        tempDict = {}

        inningsInfo = groupDf.iloc[len(groupDf.index) - 1]

        for column in columns:

            tempDict[column] = inningsInfo[column]

        if groupColumn == 'b_bowlerType':
            tempDict['bowler'] = group

        if groupColumn == 'b_bowlType':
            tempDict['bowler'] = group

        if groupColumn == 's_batterType':
            tempDict['striker'] = group

        ballsFaced = len(groupDf.index)
        runsOffBat = groupDf['runs_off_bat'].astype(int).to_numpy().sum()
        runsScored = runsOffBat
        inningsAvg = runsScored

        if statMode == 'batting':
            if (groupColumn == 'batting_team'):
                extras = groupDf['extras'].astype(int).to_numpy().sum()
                penalties = groupDf['penalty'].astype(int).to_numpy().sum()

                print('#### ' + groupColumn + group + ' ####')
                print('#### runsScored #### ' + str(runsScored))
                print('#### extras #### ' + str(extras))
                print('#### penalties #### ' + str(penalties))

                print('#### groupDf ####')
                print(groupDf[[groupColumn, 'runs_off_bat']])

                runsScored = runsScored + extras + penalties
                tempDict['striker'] = tempDict['batting_team']
                tempDict['non_striker'] = tempDict['batting_team']
                playersDismissed = groupDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))

                print('#### RUNS SCORED #### ' + str(runsScored))
            elif groupColumn == 's_batterType':
                playersDismissed = groupDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            elif groupColumn in matchupColumns:
                #tempDict['striker'] = group
                tempDict['matchup'] = group
                playersDismissed = groupDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            else:
                playersDismissed = groupDf[groupDf['player_dismissed'] == group]

        if statMode == 'bowling':

            extras = groupDf['extras'].astype(int).to_numpy().sum()
            penalties = groupDf['penalty'].astype(int).to_numpy().sum()
            runsScored = runsScored + extras + penalties

            if (groupColumn == 'bowling_team'):
                tempDict['bowler'] = tempDict['bowling_team']
                playersDismissed = groupDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            elif groupColumn in ['bowler', 'b_bowlerType', 'b_bowlType']:
                tempDf = groupDf[groupDf['wicket_type'].isin(bowlerDismissals)]
                playersDismissed = tempDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            elif groupColumn in matchupColumns:
                #tempDict['bowler'] = group
                tempDict['matchup'] = group
                tempDf = groupDf[groupDf['wicket_type'].isin(bowlerDismissals)]
                playersDismissed = tempDf['player_dismissed']
                playersDismissed = playersDismissed.unique().tolist()
                playersDismissed = list(filter(None, playersDismissed))
            else:
                playersDismissed = groupDf[groupDf['player_dismissed'].str.len() > 0]

        wickets = len(playersDismissed)

        if wickets > 0:
            inningsAvg = runsOffBat/wickets

        if statMode == 'batting':
            inningsSR = calcSR(runsOffBat, ballsFaced)

        if statMode == 'bowling':
            inningsSR = calcSR(wickets, ballsFaced)

        dots = len(groupDf[groupDf['runs_off_bat'] == 0])
        ones = len(groupDf[groupDf['runs_off_bat'] == 1])
        twos = len(groupDf[groupDf['runs_off_bat'] == 2])
        threes = len(groupDf[groupDf['runs_off_bat'] == 3])
        fours = len(groupDf[groupDf['runs_off_bat'] == 4])
        sixes = len(groupDf[groupDf['runs_off_bat'] == 6])

        tempDict['matchInnings'] = df['innings'].unique()[0]
        tempDict['runs'] = runsScored
        tempDict['wickets'] = wickets
        tempDict['ballsFaced'] = ballsFaced
        tempDict['inningsAvg'] = inningsAvg
        tempDict['inningsSR'] = inningsSR
        tempDict['dots'] = dots
        tempDict['1s'] = ones
        tempDict['2s'] = twos
        tempDict['3s'] = threes
        tempDict['4s'] = fours
        tempDict['6s'] = sixes
        tempDict['dotPercent'] = 100*dots/ballsFaced
        tempDict['boundaryPercent'] = 100*(fours+sixes)/ballsFaced

        calculatePhaseWise(groupDf, tempDict, group, groupColumn, inningsTotal)

        groupedDf = groupedDf.append(tempDict, ignore_index=True)

    return groupedDf  

def get_truth(inp, op, cut):
    return op(inp, cut)

def buildPlot (xValues, yValues, xValue, xOperator, yValue, yOperator, eqOperator, xLabel, yLabel, df, title, phase, colors):

    if 'striker' in df.columns:
        df = df[df['striker'] != 'Team Average']

    if 'bowler' in df.columns:
        df = df[df['bowler'] != 'Team Average']

    if statMode == 'batting':
        playerNames = df['striker'].tolist()
        tempDf = df.copy()

        if 'batting_team' in tempDf.columns:
            tempDf = tempDf[['striker', 'batting_team']]
            tempDf.rename(columns = {'batting_team':'teamName'}, inplace = True)

        tempDf.drop_duplicates(subset=['striker'], keep='last', inplace=True)
        tempDf = tempDf.set_index('striker')

    if statMode == 'bowling':
        playerNames = df['bowler'].tolist()
        tempDf = df.copy()

        if 'bowling_team' in tempDf.columns:
            tempDf = tempDf[['bowler', 'bowling_team']]
            tempDf.rename(columns = {'bowling_team':'teamName'}, inplace = True)

        tempDf.drop_duplicates(subset=['bowler'], keep='last', inplace=True)
        tempDf = tempDf.set_index('bowler')

    noOfRows = len(df.index) - 1

    if phase + 'AvgScore' in df.columns:
        phaseAvgScores = df[phase + 'AvgScore'].tolist()

    innsLabel = phase + 'Inns'
    phasePlayerLabel = phase + 'PlayerLabel'

    if innsLabel in df.columns:

        if statMode == 'batting':
            df[phasePlayerLabel] = df['striker'].astype(str) + ' ' + df[phase + 'Runs'].astype(str) + ' (' + df[phase + 'Inns'].astype(str) + ')'

        if statMode == 'bowling':
            df[phasePlayerLabel] = df['bowler'].astype(str) + ' ' + df[phase + 'Wickets'].astype(str) + ' (' + df[phase + 'Inns'].astype(str) + ')'

    subplotX = []
    subplotY = []
    subplotPlayers = []

    figureTitle = title + ' ' + xLabel + ' vs ' + yLabel
    htmlTitle = figureTitle + '.html'
    pngTitle = figureTitle + '.png'

    if saveHtml:
        output_file(filename = htmlTitle)

    p = figure(width = 1200, height = 800, x_axis_label=xLabel, y_axis_label=yLabel, title=figureTitle)

    for i, txt in enumerate(playerNames):

        textColor = 'black'

        xTruth = get_truth(xValues[i], xOperator, xValue)
        yTruth = get_truth(yValues[i], yOperator, yValue)

        overallTruth = False

        if eqOperator == 'and':
            overallTruth = xTruth and yTruth

        if eqOperator == 'or':
            overallTruth = xTruth or yTruth

        if (overallTruth):
            
            if phasePlayerLabel in df.columns:
                phaseLabels = df[phasePlayerLabel].tolist()
                tempStr = phaseLabels[i]
            elif phase + 'AvgScore' in df.columns:
                tempStr = phaseAvgScores[i]
            else:
                tempStr = txt

            if txt == 'Player Average' or txt == 'Team Average':
                dst_start = Span(location=xValues[i], dimension='height', line_color='black', line_width=1)
                p.add_layout(dst_start)

                dst_end = Span(location=yValues[i], dimension='width', line_color='black', line_width=1)
                p.add_layout(dst_end)

                p.add_layout(BoxAnnotation(bottom=yValues[i], left=xValues[i], fill_alpha=0.1, fill_color=colors[0]))
                p.add_layout(BoxAnnotation(bottom=yValues[i], right=xValues[i], fill_alpha=0.1, fill_color=colors[1]))
                p.add_layout(BoxAnnotation(top=yValues[i], left=xValues[i], fill_alpha=0.1, fill_color=colors[2]))
                p.add_layout(BoxAnnotation(top=yValues[i], right=xValues[i], fill_alpha=0.1, fill_color=colors[3]))
                
                tempStr = ''
                    

            subplotX.append(xValues[i])
            subplotY.append(yValues[i])
            
            subplotPlayers.append(tempStr)

            if 'teamName' in tempDf.columns:
                color = returnColorHex(txt, tempDf)
            elif 'Medium' in txt or 'Fast' in txt or 'Slow' in txt:
                color = 'red'
            elif 'Orthodox' in txt or 'Chinaman' in txt or 'Off' in txt or 'Leg' in txt:
                color = 'blue'
            else:
                color = 'black'

            p.circle(xValues[i], yValues[i], size=10, fill_color=color, line_color=color)
    
    plotColors = np.array(colors, dtype="str")

    source = pd.DataFrame(
        dict(
            x=subplotX,
            y=subplotY,
            names=subplotPlayers
        )
    )

    labels = LabelSet(
            x='x',
            y='y',
            text='names',
            level='glyph',
            x_offset=-30, 
            y_offset=-20, 
            text_color=textColor,
            source=ColumnDataSource(source))

    p.add_layout(labels)

    if showImages:
        show(p)
    #export_png(p, filename=pngTitle, width=1200, height=800)

    return p

def returnColorHex(playerName, playerCountries):

    #colorHex = '#4287f5'
    colorHex = 'black'

    if playerName in playerCountries.index:

        playerCountry = playerCountries.loc[playerName, 'teamName']

        if playerCountry in ['Chennai Super Kings', 'CSK']:
            colorHex = '#eff542'
            #colorHex = 'yellow'
        elif playerCountry in ['Royal Challengers Bangalore', 'RCB']:
            colorHex = '#f54242'
            #colorHex = 'red'
        elif playerCountry in ['Mumbai Indians', 'MI']:
            colorHex = '#42a7f5'
            #colorHex = 'blue'
        elif playerCountry in ['Rajasthan Royals', 'Rising Pune Supergiants', 'RR']:
            colorHex = '#FF2AA8'
            #colorHex = 'pink'
        elif playerCountry in ['Kolkata Knight Riders', 'KKR']:
            colorHex = '#610048'
            #colorHex = 'purple'
        elif playerCountry in ['Kings XI Punjab', 'Punjab Kings', 'PBKS']:
            colorHex = '#FF004D'
            #colorHex = 'brown'
        elif playerCountry in ['Sunrisers Hyderabad', 'SRH', 'Netherlands', 'Zimbabwe']:
            colorHex = '#FF7C01'
            #colorHex = 'black'
        elif playerCountry in ['Lucknow Super Giants', 'Pune Warriors', 'LSG']:
            colorHex = '#00BBB3'
            #colorHex = 'green'
        elif playerCountry in ['Delhi Capitals', 'Delhi Daredevils', 'DC']:
            colorHex = '#004BC5'
            #colorHex = 'cyan'
        elif playerCountry == 'Deccan Chargers':
            colorHex = '#04378C'
            #colorHex = 'blue'
        elif playerCountry == 'Gujarat Lions' :
            colorHex = '#FF5814'
            #colorHex = 'blue'
        elif playerCountry in ['Gujarat Titans', 'GT'] :
            colorHex = '#01295B'
            #colorHex = 'blue'
        elif playerCountry == 'Australia':
            colorHex = '#eff542'
            #colorHex = 'yellow'
        elif playerCountry == 'England':
            colorHex = '#f54242'
            #colorHex = 'red'
        elif playerCountry == 'India':
            colorHex = '#42a7f5'
            #colorHex = 'blue'
        elif playerCountry == 'South Africa':
            colorHex = '#1cba2e'
            #colorHex = 'green'
        elif playerCountry == 'Pakistan':
            colorHex = '#02450a'
            #colorHex = 'green'
        elif playerCountry == 'West Indies':
            colorHex = '#450202'
            #colorHex = 'brown'
        elif playerCountry == 'New Zealand':
            colorHex = '#050505'
            #colorHex = 'black'
        elif playerCountry == 'Bangladesh':
            colorHex = '#022b07'
            #colorHex = 'green'
        elif playerCountry == 'Afghanistan':
            colorHex = '#058bf2'
            #colorHex = 'cyan'
        elif playerCountry == 'Sri Lanka':
            colorHex = '#031459'
            #colorHex = 'blue'
        elif playerCountry == 'Ireland':
            colorHex = '#90EE90'
        else:
            print(playerCountry)

    return colorHex

def allRoundInnsProgression(battingTeamInnsProgression, bowlingTeamInnsProgression, type):

    totalTeamInnsProgression = pd.merge(battingTeamInnsProgression, bowlingTeamInnsProgression, on='striker', how='inner')

    rpiColumns = ['overallRPI', 'ppRPI', 'moRPI', 'deathRPI']
    wpiColumns = ['overallWPI', 'ppWPI', 'moWPI', 'deathWPI']
    erColumns = ['overallER', 'ppER', 'moER', 'deathER']

    # initializing append_str
    append_str = 'bat_'
    
    # Append suffix / prefix to strings in list
    batRpiColumns = [append_str + sub for sub in rpiColumns]
    batWpiColumns = [append_str + sub for sub in wpiColumns]
    batErColumns = [append_str + sub for sub in erColumns]

    # initializing append_str
    append_str = 'bowl_'
    
    # Append suffix / prefix to strings in list
    bowlRpiColumns = [append_str + sub for sub in rpiColumns]
    bowlWpiColumns = [append_str + sub for sub in wpiColumns]
    bowlErColumns = [append_str + sub for sub in erColumns]

    allBatColumns = []
    allBowlColumns = []

    for i in range (0, 4):

        allBatColumns.append(batRpiColumns[i])
        allBatColumns.append(batWpiColumns[i])
        allBatColumns.append(batErColumns[i])

        allBowlColumns.append(bowlRpiColumns[i])
        allBowlColumns.append(bowlWpiColumns[i])
        allBowlColumns.append(bowlErColumns[i])

    allColumns = allBatColumns + allBowlColumns

    rgColumns = []
    grColumns = []

    cmRG = sns.color_palette("RdYlGn", as_cmap=True)
    cmGR = sns.color_palette("RdYlGn_r", as_cmap=True)

    rgColumns = batRpiColumns + batErColumns
    grColumns = batWpiColumns 

    rgColumns += bowlWpiColumns
    grColumns += bowlRpiColumns + bowlErColumns

    statMode = type + ' Bat Bowl '

    totalTeamInnsProgression = totalTeamInnsProgression[allColumns]

    if type == 'team':
        totalTeamInnsProgression.rename(index=teams_mapping,inplace=True)

    totalTeamInnsProgression['bat-ball'] = totalTeamInnsProgression['bat_overallRPI'] - totalTeamInnsProgression['bowl_overallRPI']

    totalTeamInnsProgression = totalTeamInnsProgression.sort_values(by='bat-ball', ascending=False)
    totalTeamInnsProgression = totalTeamInnsProgression.drop('bat-ball', axis=1)

    styleColumns(totalTeamInnsProgression, cmRG, rgColumns, cmGR, grColumns, 'All Round' + type)

    return totalTeamInnsProgression, rgColumns, grColumns

def rankTeamInnsProgression(df, rgColumns, grColumns):

    columns = df.columns
    columnLabels = []

    for column in columns:

        columnRankLabel = column + '_rank' 
        values = df[column].tolist()
        
        if column in rgColumns:
            ranks = [sorted(values, reverse=True).index(x) for x in values]
            ranks = [x + 1 for x in ranks]
        
        if column in grColumns:
            ranks = [sorted(values).index(x) for x in values]
            ranks = [x + 1 for x in ranks]

        df[columnRankLabel] = ranks

        columnLabels.append(column)
        columnLabels.append(columnRankLabel)

    df = df[columnLabels]

    return df

def performCalculations(startDate, endDate):

    global matchupTotals

    matchupTotals = pd.DataFrame()
    battingTeamInnsProgression, battersInnsProgression, batterTotals, batterMatchTotals = processMultipleFiles('batting', startDate, endDate)
    #battingTeamInnsProgression = battingTeamInnsProgression.add_prefix('bat_')
    #battersInnsProgression = battersInnsProgression.add_prefix('bat_')
    if not matchupTotals.empty:
        matchupTotals.drop_duplicates(subset=['match_id', 'matchup'], inplace=True)
        matchupTotals.to_excel(f"Matchup Totals {statMode} {venueTitle} {timePeriod}.xlsx")

    matchupTotals = pd.DataFrame()
    bowlingTeamInnsProgression, bowlersInnsProgression, bowlerTotals, bowlerMatchTotals = processMultipleFiles('bowling', startDate, endDate)
    #bowlingTeamInnsProgression = bowlingTeamInnsProgression.add_prefix('bowl_')
    #bowlersInnsProgression = bowlersInnsProgression.add_prefix('bowl_')
    if not matchupTotals.empty:
        matchupTotals.drop_duplicates(subset=['match_id', 'matchup'], inplace=True)
        matchupTotals.to_excel(f"Matchup Totals {statMode} {venueTitle} {timePeriod}.xlsx")

    """
    teamInnsProgression, rgColumns, grColumns = allRoundInnsProgression(battingTeamInnsProgression, bowlingTeamInnsProgression, 'team')
    rankedTeamInnsProgression = rankTeamInnsProgression(teamInnsProgression, rgColumns, grColumns)
    rankedTeamInnsProgression.to_excel(str(timePeriod) + 'Ranked All Round Team Stats.xlsx')
    allRoundInnsProgression(battersInnsProgression, bowlersInnsProgression, 'player')
    """

    matchTotals = pd.merge(batterMatchTotals, bowlerMatchTotals, on='matchId', how='outer', suffixes=(None, '_y'))
    matchTotals = bowlerMatchTotals.copy()

    columns = matchTotals.columns
    renamedColumnDict = {}

    for column in columns:
        
        if '_y' in column:
            renamedColumnDict[column] = column.replace('_y', '')

        if '.0' in column:
            renamedColumnDict[column] = column.replace('.0', '')

    matchTotals.rename(columns=renamedColumnDict, inplace=True)

    columns = matchTotals.columns.values.tolist()
    tempDf = pd.DataFrame()
    tempDf['columns'] = columns

    print('#### columns ####')
    print(columns)

    columns = tempDf['columns'].unique().tolist()
    matchTotals = matchTotals[columns]

    print('#### columns unique ####')
    print(columns)

    #matchTotals = matchTotals.T.drop_duplicates().T

    matchTotals.to_excel(f"Temp Match Totals {statMode} {venueTitle} {timePeriod}.xlsx")

    return batterTotals, bowlerTotals, matchTotals

def calculatePlayerAverage(overallBatterTotals, playerName, startYear, endYear, mode, fileName):

    global statMode
    statMode = mode

    global timePeriod
    timePeriod = str(startYear) + '-' + str(endYear-1)

    if statMode == 'batting':
        filterColumn = 'striker'

    if statMode == 'bowling':
        filterColumn = 'bowler'
    
    overallAverageBatter = overallBatterTotals[overallBatterTotals[filterColumn] == playerName]
    averageBatterColumns = ['year', filterColumn]

    avgColumns = ['overallAvg', 'ppAvg', 'moAvg', 'deathAvg']
    srColumns = ['overallSR', 'ppSR', 'moSR', 'deathSR']
    erColumns = ['overallER', 'ppER', 'moER', 'deathER']
    dotPercentColumns = ['overalldotPercent', 'ppdotPercent', 'modotPercent', 'deathdotPercent']
    boundaryPercentColumns = ['overallboundaryPercent', 'ppboundaryPercent', 'moboundaryPercent', 'deathboundaryPercent']

    for i in range (0, 4):

        averageBatterColumns.append(avgColumns[i])

        if statMode == 'batting':
            averageBatterColumns.append(srColumns[i])

        if statMode == 'bowling':
            averageBatterColumns.append(erColumns[i])

        averageBatterColumns.append(dotPercentColumns[i])
        averageBatterColumns.append(boundaryPercentColumns[i])

    if statMode == 'batting':
        rgColumns = avgColumns + srColumns + boundaryPercentColumns
        grColumns = dotPercentColumns

    if statMode == 'bowling':
        grColumns = avgColumns + erColumns + boundaryPercentColumns
        rgColumns = dotPercentColumns

    overallAverageBatter = overallAverageBatter[averageBatterColumns]
    overallAverageBatter = overallAverageBatter.drop(filterColumn, axis=1)
    overallAverageBatter = overallAverageBatter.sort_values(by='year', ascending=True)
    overallAverageBatter = overallAverageBatter.set_index('year')
    overallAverageBatter.to_excel('Average ' + fileName)

    cmRG = sns.color_palette("RdYlGn", as_cmap=True)
    cmGR = sns.color_palette("RdYlGn_r", as_cmap=True)

    styleColumns(overallAverageBatter, cmRG, rgColumns, cmGR, grColumns, playerName + ' ')

def invokeAllFunctions():

    overallBatterTotals = pd.DataFrame()
    overallBowlerTotals = pd.DataFrame()

    startYear = 2022
    endYear = 2023

    for year in range(startYear, endYear):

        #startDate = str(year) + '-01-01'
        #endDate = str(year) + '-12-31'
        startDate = '2018-01-01'
        endDate = '2023-12-31'
        batterTotals, bowlerTotals, matchTotals = performCalculations(startDate, endDate)
        createVenueNotes(matchTotals, batterTotals, bowlerTotals)

        overallBatterTotals = pd.concat([overallBatterTotals, batterTotals])
        overallBowlerTotals = pd.concat([overallBowlerTotals, bowlerTotals])

    startyear = 2008
    endYear = 2023

    batterTotalsFileName = str(startYear) + '-' + str(endYear-1) + ' Overall Batter Totals.xlsx'
    bowlerTotalsFileName = str(startYear) + '-' + str(endYear-1) + ' Overall Bowler Totals.xlsx'
    overallBatterTotals.to_excel(batterTotalsFileName)
    overallBowlerTotals.to_excel(bowlerTotalsFileName) 

    #overallBatterTotals = pd.read_excel(batterTotalsFileName)
    #overallBowlerTotals = pd.read_excel(bowlerTotalsFileName)

    calculatePlayerAverage(overallBatterTotals, 'Player Average', startYear, endYear, 'batting', batterTotalsFileName)
    calculatePlayerAverage(overallBowlerTotals, 'Player Average', startYear, endYear, 'bowling', bowlerTotalsFileName) 

def getVenueTeams(city):

    filterVenues = []
    venueTeams = []

    if city == 'Ahmedabad':
        filterVenues = ['Narendra Modi Stadium', 'Sardar Patel Stadium']
        venueTeams = ['England', 'New Zealand', 'India', 'Pakistan', 'Australia', 'Afghanistan', 'South Africa']

    if city == 'Hyderabad':
        filterVenues = ['Rajiv Gandhi International Stadium']
        venueTeams = ['Netherlands', 'Pakistan', 'New Zealand', 'Sri Lanka']

    if city == 'Dharamsala':
        filterVenues = ['HPCA Stadium', 'Himachal Pradesh Cricket Association Stadium']
        venueTeams = ['Afghanistan', 'Bangladesh', 'England', 'Netherlands', 'South Africa', 'India', 'New Zealand', 'Australia']

    if city == 'Chennai':
        filterVenues = ['MA Chidambaram Stadium']
        venueTeams = ['India', 'Australia', 'Bangladesh', 'New Zealand', 'Afghanistan', 'Pakistan', 'South Africa']

    if city == 'Lucknow':
        filterVenues = ['BRSABV Ekana Cricket Stadium', 'Ekana Cricket Stadium', 'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium']
        venueTeams = ['Australia', 'South Africa', 'Sri Lanka', 'Netherlands', 'India', 'England', 'Afghanistan']

    if city == 'Pune':
        filterVenues = ['MCA Stadium', 'Maharashtra Cricket Association Stadium']
        venueTeams = ['India', 'Bangladesh', 'Afghanistan', 'Sri Lanka', 'New Zealand', 'South Africa', 'England', 'Netherlands', 'Australia']

    if city == 'Bangalore':
        filterVenues = ['M Chinnaswamy Stadium', 'M.Chinnaswamy Stadium']
        venueTeams = ['Australia', 'Pakistan', 'England', 'Sri Lanka', 'New Zealand', 'India', 'Netherlands']

    if city == 'Mumbai':
        filterVenues = ['Wankhede Stadium']
        venueTeams = ['England', 'South Africa', 'Bangladesh', 'India', 'Sri Lanka', 'Afghanistan']

    if city == 'Kolkata':
        filterVenues = ['Eden Gardens']
        venueTeams = ['Bangladesh', 'Netherlands', 'Pakistan', 'India', 'South Africa', 'England']

    if city == 'Delhi':
        filterVenues = ['Feroz Shah Kotla']
        venueTeams = ['South Africa', 'Sri Lanka', 'India', 'Afghanistan', 'England', 'Australia', 'Netherlands', 'Bangladesh']

    if city == 'Visakhapatnam':
        filterVenues = ['Dr Y S  Rajasekhara Reddy ACA-VDCA Cricket Stadium Visakhapatnam', 'Dr Y S  Rajasekhara Reddy ACA-VDCA Cricket Stadium', 'Dr Y S  Rajasekhara Reddy ACA-VDCA Cricket Stadium Visakhapatnam Visakhapatnam',
                        'Dr  Y S  Rajasekhara Reddy ACA-VDCA Cricket Stadium Visakhapatnam', 'Dr  Y S  Rajasekhara Reddy ACA-VDCA Cricket Stadium', 'Dr  Y S  Rajasekhara Reddy ACA-VDCA Cricket Stadium Visakhapatnam Visakhapatnam',
                        'Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium Visakhapatnam', 'Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium']
        venueTeams = ['India', 'Australia']

    if city == 'Windhoek':
        filterVenues = ['United Cricket Club Ground Windhoek', 'United Cricket Club Ground, Windhoek']
        venueTeams = ['Kenya', 'Rwanda']

    if city == 'Thiruvananthapuram':
        filterVenues = ['Greenfield International Stadium', 'Greenfield International Stadium Thiruvananthapuram']
        venueTeams = ['India', 'Australia']

    if city == 'Guwahati':
        filterVenues = ['Barsapara Cricket Stadium']
        venueTeams = ['India', 'Australia']

    if city == 'Port of Spain':
        filterVenues = ['Queen\'s Park Oval Port of Spain Trinidad', 'Queen\'s Park Oval Port of Spain']
        venueTeams = ['India', 'West Indies']

    if city == 'London':
        filterVenues = ['Kennington Oval London']
        filterVenues = ['Lord\'s', 'Lord\'s London']
        venueTeams = ['England', 'West Indies']

    if city == 'Centurion':
        filterVenues = ['SuperSport Park Centurion', 'SuperSport Park']
        venueTeams = ['India', 'South Africa']

    if city == 'Perth':
        filterVenues = ['Perth Stadium']
        venueTeams = ['Australia', 'Pakistan']

    if city == 'Melbourne':
        filterVenues = ['Melbourne Cricket Ground']
        venueTeams = ['Australia', 'Pakistan']

    if city == 'Cape Town':
        filterVenues = ['Newlands', 'Newlands Cape Town']
        venueTeams = ['India', 'South Africa']

    if city == 'Sydney':
        filterVenues = ['Sydney Cricket Ground']
        venueTeams = ['Australia', 'Pakistan']

    if city == 'Colombo':
        filterVenues = ['R Premadasa Stadium', 'R.Premadasa Stadium', 'R.Premadasa Stadium Khettarama', 'R Premadasa Stadium Colombo', 'R Premadasa Stadium Khettarama']
        venueTeams = ['Sri Lanka', 'Zimbabwe']

    if city == 'Adelaide':
        filterVenues = ['Adelaide Oval']
        venueTeams = ['Australia', 'West Indies']

    if city == 'Ranchi':
        filterVenues = ['JSCA International Stadium Complex']
        venueTeams = ['India', 'England']

    if city == 'Wellington':
        filterVenues = ['Basin Reserve', 'Basin Reserve Wellington']
        venueTeams = ['New Zealand', 'Australia']

    if city == 'Christchurch':
        filterVenues = ['Hagley Oval', 'Hagley Oval Christchurch']
        venueTeams = ['New Zealand', 'Australia']

    return filterVenues, venueTeams

def init():

    global filterVenues
    filterVenues = ['Edgbaston Birmingham', 'Headingley Leeds', 'Kennington Oval London', "Lord's London", 'Old Trafford Manchester', 'Sophia Gardens Cardiff', 'The Rose Bowl Southampton', 'Trent Bridge Nottingham']
    #filterVenues = ['Edgbaston Birmingham', 'Headingley Leeds']
    #filterVenues = ['Brian Lara Stadium Tarouba']
    filterVenues = ['Providence Stadium']
    filterVenues = []

    global venueFilter
    global venueTitle

    for venue in filterVenues:

        venueFilter = venue
        venueTitle = venue

        #invokeAllFunctions()

    venueFilter = ''
    filterVenues = ['Mahinda Rajapaksa International Cricket Stadium Sooriyawewa Hambantota', 'Mahinda Rajapaksa International Cricket Stadium Sooriyawewa']
    filterVenues = ['The Village Malahide Dublin', 'The Village Malahide']
    filterVenues = ['R Premadasa Stadium', 'R.Premadasa Stadium', 'R.Premadasa Stadium Khettarama', 'R Premadasa Stadium Colombo', 'R Premadasa Stadium Khettarama']
    #filterVenues = ['Multan Cricket Stadium']
    #filterVenues = ['Pallekele International Cricket Stadium']
    #filterVenues = ['Mangaung Oval Bloemfontein', 'Goodyear Park', 'OUTsurance Oval', 'Chevrolet Park', 'Mangaung Oval']
    #filterVenues = ['Gaddafi Stadium Lahore', 'Gaddafi Stadium']
    #filterVenues = ['Punjab Cricket Association IS Bindra Stadium']
    filterVenues = []

    cities = ['Kolkata', 'Mumbai', 'Bangalore', 'Pune', 'Lucknow', 'Chennai', 'Dharamsala', 'Ahmedabad', 'Hyderabad', 'Delhi']
    #cities = ['Kolkata', 'Mumbai']
    cities = ['Hyderabad', 'Dharamsala', 'Delhi', 'Chennai', 'Lucknow', 'Pune', 'Bangalore', 'Mumbai', 'Kolkata', 'Ahmedabad']
    cities = ['Dharamsala', 'Delhi', 'Chennai', 'Lucknow', 'Pune', 'Bangalore', 'Mumbai', 'Kolkata', 'Ahmedabad']
    cities = ['Pune']
    cities = ['Visakhapatnam']
    cities = ['Windhoek']
    cities = ['Bangalore']
    cities = ['Port of Spain']
    cities = ['Adelaide']
    cities = ['Christchurch']
    cities = ['London']

    global saveHtml
    saveHtml = False

    global showImages
    showImages = False

    global calculateNBSRFlag
    calculateNBSRFlag = False

    global filterTeams

    if len(cities) > 0:
        for city in cities:
            filterVenues, venueTeams = getVenueTeams(city)

            #venueTeams = ['Australia', 'Pakistan']
            #filterVenues = []
            #venueTitle = 'Edgbaston, Headingley'
            venueTitle = filterVenues[0] + ' ' + city
            global bestPlayerTeams
            bestPlayerTeams.extend(venueTeams)
            invokeAllFunctions()

            venueFilter = ''
            filterVenues = []
            #venueTitle = 'Edgbaston, Headingley'
            filterTeams = venueTeams
            bestPlayerTeams = []
            bestPlayerTeams.extend(filterTeams)
            venueTitle = 'World Cup @ ' + city
            getFilterPlayers(filterTeams)
            filterTeams = []
            #invokeAllFunctions()
    else:
        filterTeams = ['India', 'South Africa', 'Australia', 'New Zealand', 'Afghanistan', 'Pakistan', 'Bangladesh', 'England', 'Netherlands', 'Sri Lanka']
        venueTitle = 'World Cup 2023 '
        invokeAllFunctions()

def justScatter():

    overallBatterTotals = pd.DataFrame()
    overallBowlerTotals = pd.DataFrame()

    startYear = 2022
    endYear = 2023

    global saveHtml
    saveHtml = True

    global showImages
    showImages = True

    global calculateNBSRFlag
    calculateNBSRFlag = True

    for year in range(startYear, endYear):

        #startDate = str(year) + '-01-01'
        #endDate = str(year) + '-12-31'
        startDate = '2017-01-01'
        endDate = '2023-12-31'
        batterTotals, bowlerTotals, matchTotals = performCalculations(startDate, endDate)
        #createVenueNotes(matchTotals, batterTotals, bowlerTotals)

        overallBatterTotals = pd.concat([overallBatterTotals, batterTotals])
        overallBowlerTotals = pd.concat([overallBowlerTotals, bowlerTotals])

    startyear = 2008
    endYear = 2023

    batterTotalsFileName = str(startYear) + '-' + str(endYear-1) + ' Overall Batter Totals.xlsx'
    bowlerTotalsFileName = str(startYear) + '-' + str(endYear-1) + ' Overall Bowler Totals.xlsx'
    overallBatterTotals.to_excel(batterTotalsFileName)
    overallBowlerTotals.to_excel(bowlerTotalsFileName) 

    #overallBatterTotals = pd.read_excel(batterTotalsFileName)
    #overallBowlerTotals = pd.read_excel(bowlerTotalsFileName)

    calculatePlayerAverage(overallBatterTotals, 'Player Average', startYear, endYear, 'batting', batterTotalsFileName)
    calculatePlayerAverage(overallBowlerTotals, 'Player Average', startYear, endYear, 'bowling', bowlerTotalsFileName) 

init()
#justScatter()

#venuesDf = pd.read_excel('venueNotes bowling SuperSport Park Centurion Centurion 2018-2023.xlsx')
#show(buildHbarStackTests(venuesDf))

#tempDf = pd.read_excel('tempDF bowling Sydney Cricket Ground Sydney 2013-2023.xlsx')
#buildHLineChartStacked(tempDf)