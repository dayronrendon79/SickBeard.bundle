####################################################################################################

PREFIX = "/video/sickbeard"

NAME = 'SickBeard'

ART         = 'art-default.jpg'
ICON        = 'icon-default.png'
SEARCH_ICON = 'icon-search.png'
PREFS_ICON  = 'icon-prefs.png'
HISTORY_ICON= 'icon-history.png'
COMING_ICON = 'icon-coming.png'


####################################################################################################

def Start():

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    DirectoryObject.thumb = R(ICON)
    PopupDirectoryObject.thumb = R(ICON)
    HTTP.CacheTime=3600*3


####################################################################################################
def IndexerField():
    if Prefs['Fork'] == 'SickRage':
        return 'indexerid'
    else:
        return 'tvdbid'

####################################################################################################
@handler(PREFIX, NAME, ICON, ART)
def MainMenu():
    oc = ObjectContainer(no_cache=True)

    if Prefs['sbAPI']:
        oc.add(DirectoryObject(key=Callback(ShowList), title="Manage Your TV Shows",
            summary="View and edit your existing TV Shows",thumb=R(ICON)))
        oc.add(DirectoryObject(key=Callback(Future), title="Coming Episodes",
            summary="See which shows that you follow have episodes airing soon",thumb=R(COMING_ICON)))
        oc.add(InputDirectoryObject(key=Callback(Search), title="Search for TV Shows", summary="Find TV Shows to add to SickBeard",
            prompt="Search for", thumb=R(SEARCH_ICON)))
        oc.add(DirectoryObject(key=Callback(History), title="History",
            summary="See which shows have been snatched/downloaded recently",thumb=R(HISTORY_ICON)))
        oc.add(PrefsObject(title="Preferences", summary="Set SickBeard plugin preferences to allow it to connect to SickBeard app",thumb=R(PREFS_ICON)))
    else:
        oc.add(PrefsObject(title="Preferences", summary="PLUGIN IS CURRENTLY UNABLE TO CONNECT TO SICKBEARD.\nSet SickBeard plugin preferences to allow it to connect to SickBeard app",
            thumb=R(PREFS_ICON)))

    return oc

####################################################################################################
@route(PREFIX + '/validate')
def ValidatePrefs():
    Log("Storing SickBeard URL for future reference: %s" % Get_SB_URL(reset=True))
    Log("Storing SickBeard API Key for future reference: %s" % Prefs['sbAPI'])
    return ObjectContainer(header=NAME, message="Please restart your Plex client for pref changes to take effect.")

####################################################################################################
@route(PREFIX +'/future')
def Future():
    
    oc = ObjectContainer(title2='Coming Episodes')
    
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="all"), title="All",
        summary="All episodes which are scheduled to air."))
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="today"), title="Airing Today",
        summary="Episodes which are scheduled to air today."))
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="soon"), title="Airing Soon",
        summary="Episodes which are scheduled to air this week."))
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="later"), title="Airing Later",
        summary="Episodes which are scheduled to air after this week."))
    oc.add(DirectoryObject(key=Callback(ComingEpisodes, timeframe="missed"), title="Missed Episodes",
        summary="Episodes which aired prior to today's date."))

    
    return oc

####################################################################################################
@route(PREFIX + '/coming')
def ComingEpisodes(timeframe=""):
    
    oc = ObjectContainer(title1='Coming Episodes', title2=String.CapitalizeWords(timeframe), no_cache=True)
    
    if timeframe == 'all':
        timeframe = ['today','soon','later']
    else:
        timeframe = [timeframe]
    
    for i in range(len(timeframe)):
        coming_Eps = API_Request([{'key':'cmd', 'value':'future'}])['data'][timeframe[i]]
    
        for episode in coming_Eps:
            title = FutureEpisodeTitle(episode)
            summary = FutureEpisodeSummary(episode)
            oc.add(PopupDirectoryObject(key=Callback(EpisodePopup, episode=episode, tvdbid=episode[IndexerField()], season=episode['season']),
                title=title, summary=summary, thumb=Callback(GetThumb, tvdbid=episode[IndexerField()])))

    if len(oc) == 0:
            return ObjectContainer(header=NAME, message="No episodes found.")   
    return oc

####################################################################################################
@route(PREFIX + '/history')
def History():
    
    oc = ObjectContainer(title1='History', no_cache=True)
    
    for episode in API_Request([{'key':'cmd', 'value':'history'}])['data']:
        title = HistoryEpisodeTitle(episode)
        summary = HistoryEpisodeSummary(episode)
        oc.add(PopupDirectoryObject(key=Callback(EpisodePopup, episode=episode['episode'], tvdbid=episode[IndexerField()], season=episode['season']),
            title=title, summary=summary, thumb=Callback(GetThumb, tvdbid=episode[IndexerField()])))

    if len(oc) == 0:
            return ObjectContainer(header=NAME, message="No episodes found.")   
    return oc

####################################################################################################
@route(PREFIX + '/search')
def Search(query):
    
    oc = ObjectContainer(title2="TVDB Results", no_cache=True)
    
    search_results = API_Request([{'key':'cmd', 'value':'sb.searchtvdb'},{'key':'name', 'value':String.Quote(query, usePlus=True)}])
    if len(search_results['data']['results']) == 0:
        return ObjectContainer(header=NAME, message="No search results found for %s" % query)

    for result in search_results['data']['results']:
        oc.add(PopupDirectoryObject(
            key=Callback(AddShowMenu, show=result),
            title = result['name'],
            summary = "TVDB ID: %s\nFirst Aired: %s" % (result['tvdbid'], result['first_aired']), # Still uses tvbdbid
            thumb = Callback(GetThumb, tvdbid=result['tvdbid'])))
    
    return oc
    
####################################################################################################  
@route(PREFIX +'/shows', offset=int)
def ShowList(offset=0):
    '''List all shows that SickBeard manages, and relevant info about each show'''
    
    oc = ObjectContainer(title2="All Shows", no_cache=True)
    
    shows = API_Request([{'key':'cmd', 'value':'shows'},{'key':'sort', 'value':'name'}])['data']
    show_list = sorted(shows.items(), key = lambda item: item[0])
    
    for entry in show_list[offset:offset+20]:
        show_name = entry[0]
        show = entry[1]
        if len(show['tvrage_name']) > 0:
            show_name = show['tvrage_name']
        
        if show['paused']:
            paused = "True"
        else:
            paused = "False"

        tvdbid = show[IndexerField()]
        episodes = GetEpisodes(tvdbid)
        title = "%s   %s" % (show_name, episodes)
        summary = "Next Episode: %s\nNetwork: %s\nDownload Quality: %s\nStatus: %s\nPaused: %s" % (
            show['next_ep_airdate'], show['network'], show['quality'], show['status'], paused, )
            
        oc.add(PopupDirectoryObject(key=Callback(SeriesPopup, tvdbid=tvdbid, show=title), title=title, summary=summary,
            thumb=Callback(GetThumb, tvdbid=tvdbid)))
    
    if offset+20 < len(show_list):
        oc.add(NextPageObject(key=Callback(ShowList, offset=offset+20)))
    
    return oc
    
####################################################################################################
@route(PREFIX + '/series')
def SeriesPopup(tvdbid, show):
    '''display a popup menu with the option to force a search for the selected series'''
    oc = ObjectContainer()
    
    oc.add(DirectoryObject(key=Callback(SeasonList, tvdbid=tvdbid, show=show), title="View Season List"))
    oc.add(DirectoryObject(key=Callback(EditSeries, tvdbid=tvdbid), title="Edit SickBeard series options"))
    
    return oc
    
####################################################################################################
@route(PREFIX + '/episode', episode=dict)
def EpisodePopup(episode={}, tvdbid=None, season=None):
    '''display a popup menu with the option to force a search for the selected episode/series'''
    oc = ObjectContainer()
    if not season:
        episode = API_Request([{'key':'cmd','value':'episode'},{'key':IndexerField(),'value':tvdbid},
            {'key':'episode','value':episode}])['data']
        season=episode['season']
    else:
        pass
    
    episode=episode['episode']
    
    oc.add(DirectoryObject(key=Callback(EpisodeRefresh, tvdbid=tvdbid, season=season, episode=episode),
        title="Force search for this episode"))
    for status in API_Request([{"key":"cmd", "value":"show.addnew"},{"key":"help", "value":"1"}])['data']['optionalParameters']['status']['allowedValues']:
        oc.add(DirectoryObject(key=Callback(SetEpisodeStatus, tvdbid=tvdbid, season=season,
            episode=episode, status=status),title="Mark this episode as '%s'" % String.CapitalizeWords(status)))
    
    return oc

####################################################################################################
@route(PREFIX + '/addmenu', show=dict)
def AddShowMenu(show={}):
    '''offer the option to add the given show to sickbeard with default settings or with custom settings'''
    
    oc = ObjectContainer()
    
    oc.add(DirectoryObject(key=Callback(AddShow, tvdbid=show['tvdbid']), title="Add with default settings"))
    oc.add(DirectoryObject(key=Callback(CustomAddShow, tvdbid=show['tvdbid']), title="Add with custom settings"))
    
    return oc
    
####################################################################################################
@route(PREFIX + '/addshow')
def AddShow(tvdbid, useCustomSettings=False):
    '''add the given show to the SickBeard database with the SickBeard's default settings,
        or with custom settings'''
    
    params = [{"key":"cmd", "value":"show.addnew"},{"key":"tvdbid","value":tvdbid}]
    if useCustomSettings:
        for key, value in Dict['DefaultSettings'].iteritems():
            if key in ['lang','location','season_folders','status','future_show_paused','location']:
                params.append({'key':key,'value':value})
            else:
                params.append({'key':key,'value':'|'.join(value)})
        
    return API_Request(params, return_message=True)

####################################################################################################
@route(PREFIX + '/addcustom')
def CustomAddShow(tvdbid):
    '''retrieve the user's default settings from SickBeard and use them as a starting point to allow
        modifications before adding a show with custom settings'''
    
    oc = ObjectContainer(title2="Add Show Settings...", no_cache=True)
    
    if not Dict['settings_modified']:
        GetQualityDefaults(group="DefaultSettings")
        GetSickBeardRootDirs()
    
    '''Offer separate menu options for each default setting'''
    oc.add(PopupDirectoryObject(key=Callback(QualitySetting, group="DefaultSettings", category="initial"), title="Initial Quality", summary=str(Dict['DefaultSettings']['initial'])))
    oc.add(PopupDirectoryObject(key=Callback(QualitySetting, group="DefaultSettings", category="archive"), title="Archive Quality", summary=str(Dict['DefaultSettings']['archive'])))
    oc.add(PopupDirectoryObject(key=Callback(LanguageSetting), title="TVDB Language: [%s]" % Dict['DefaultSettings']['lang']))
    oc.add(PopupDirectoryObject(key=Callback(StatusSetting), title="Status of previous episodes: [%s]" % Dict['DefaultSettings']['status']))
    oc.add(PopupDirectoryObject(key=Callback(RootDirSetting), title="Root Directory"))
    try:
        if Dict['DefaultSettings']['season_folders'] == 1:
            season_folders = "Yes"
        else:
            season_folders = "No"
    except:
        season_folders = "?"
    oc.add(PopupDirectoryObject(key=Callback(SeasonFolderSetting), title="Use season Folders [%s]" % season_folders))
            
    oc.add(DirectoryObject(key=Callback(AddShow, tvdbid=tvdbid, useCustomSettings=True), title="Add show with these settings"))
    
    return oc

####################################################################################################
@route(PREFIX + '/qualitydefaults')
def GetQualityDefaults(group="", tvdbid=None):
    if not Dict[group]:
        Dict[group] = {}
    if group == "DefaultSettings":
        settings = API_Request([{"key":"cmd", "value":"sb.getdefaults"}])
        Dict[group]['lang'] = Prefs['TVDBlang']
    else:
        settings = API_Request([{"key":"cmd", "value":"show.getquality"},{"key":IndexerField(), "value":tvdbid}])
        Dict[group] = {}
    
    for key, value in settings['data'].iteritems():
        Dict[group][key] = value
    
    return
    
####################################################################################################
@route(PREFIX + '/getrootdirs')
def GetSickBeardRootDirs():
    Dict['RootDirs'] = API_Request([{"key":"cmd", "value":"sb.getrootdirs"}])['data']
    for dir in Dict['RootDirs']:
        if dir["default"]:
            Dict["DefaultSettings"]["location"] = dir['location']
            Dict.Save()
    return

####################################################################################################
@route(PREFIX + '/rootdir')
def RootDirSetting():
    oc = ObjectContainer()
    for dir in Dict['RootDirs']:
        if dir["valid"]:
            if dir["location"] == Dict["DefaultSettings"]["location"]:
                oc.add(DirectoryObject(key=Callback(SetRootDir, location=dir['location']), title="%s [*]" % dir['location']))
            else:
                oc.add(DirectoryObject(key=Callback(SetRootDir, location=dir['location']), title="%s [ ]" % dir['location']))
    return oc

####################################################################################################
@route(PREFIX +'/setrootdir')
def SetRootDir(location):
    Dict["DefaultSettings"]["location"] = location
    Dict['settings_modified'] = True
    Dict.Save()
    return

####################################################################################################
@route(PREFIX + '/quality')
def QualitySetting(group, category):
    oc = ObjectContainer(no_cache=True, title2="%s Quality" % String.CapitalizeWords(category))
    for quality in API_Request([{"key":"cmd", "value":"show.addnew"},{"key":"help", "value":"1"}])['data']['optionalParameters'][category]['allowedValues']:
        if quality in Dict[group][category]:
            oc.add(DirectoryObject(key=Callback(ChangeQualities, group=group, quality=quality, category=category, action="remove"), title = "%s [*]" % quality))
        else:
            oc.add(DirectoryObject(key=Callback(ChangeQualities, group=group, quality=quality, category=category, action="add"), title = "%s [ ]" % quality))
    return oc

####################################################################################################
@route(PREFIX + '/changequalities')
def ChangeQualities(group, quality, category, action):
    qualities = Dict[group][category]
    if action == "remove":
        qualities.remove(quality)
    elif action == "add":
        qualities.append(quality)
    else:
        pass
    Dict[group][category] = qualities
    Dict['settings_modified'] = True
    Dict.Save()
    return

####################################################################################################
@route(PREFIX + '/language')
def LanguageSetting():
    oc = ObjectContainer(title2="tvdb Language", no_cache=True)
    for lang in API_Request([{"key":"cmd", "value":"show.addnew"},{"key":"help", "value":"1"}])['data']['optionalParameters']['lang']['allowedValues']:
        if lang in Dict['DefaultSettings']['lang']:
            oc.add(DirectoryObject(key=Callback(ChangeLanguage, lang=lang, value="False"), title = "%s [*]" % lang))
            Dict['DefaultSettings']['lang'] = lang
        else:
            oc.add(DirectoryObject(key=Callback(ChangeLanguage, lang=lang, value="True"), title = "%s [ ]" % lang))
    return oc
    
####################################################################################################
@route(PREFIX + '/changelanguage')
def ChangeLanguage(lang, value):
    if value == "True":
        Dict['DefaultSettings']['lang'] = lang
    else:
        Dict['DefaultSettings']['lang'] = ''
    Dict['settings_modified'] = True
    Dict.Save()
    return

####################################################################################################
@route(PREFIX + '/status')
def StatusSetting():
    oc = ObjectContainer(title2="Status", no_cache=True)
    for status in API_Request([{"key":"cmd", "value":"show.addnew"},{"key":"help", "value":"1"}])['data']['optionalParameters']['status']['allowedValues']:
        if status in Dict['DefaultSettings']['status']:
            oc.add(DirectoryObject(key=Callback(ChangeStatus, status=status, value="False"), title = "%s [*]" % status))
        else:
            oc.add(DirectoryObject(key=Callback(ChangeStatus, status=status, value="True"), title = "%s [ ]" % status))
    return oc

####################################################################################################
@route(PREFIX + '/changestatus')
def ChangeStatus(status, value):
    if value == "True":
        Dict['DefaultSettings']['status'] = status
    else:
        Dict['DefaultSettings']['status'] = ''
    Dict['settings_modified'] = True
    Dict.Save()
    return

####################################################################################################
@route(PREFIX + '/seasonfolder')
def SeasonFolderSetting():
    oc = ObjectContainer(title2="Status", no_cache=True)
    for option in API_Request([{"key":"cmd", "value":"show.addnew"},{"key":"help", "value":"1"}])['data']['optionalParameters']['season_folder']['allowedValues']:
        if option:
            label = "Yes"
        else:
            label = "No"
        try:
            if option in Dict['DefaultSettings']['season_folder']:
                oc.add(DirectoryObject(key=Callback(ChangeSeasonFolder, option=option, value="False"), title = "%s [*]" % label))
            else:
                oc.add(DirectoryObject(key=Callback(ChangeSeasonFolder, option=option, value="True"), title = "%s [ ]" % label))
        except:
            oc.add(DirectoryObject(key=Callback(ChangeSeasonFolder, option=option, value="True"), title = "%s [ ]" % label))
    return oc
    
####################################################################################################
@route(PREFIX + '/changeseasonfolder')
def ChangeSeasonFolder(option, value):
    if value == "True":
        Dict['DefaultSettings']['season_folder'] = option
    else:
        Dict['DefaultSettings']['season_folder'] = ''
    Dict['settings_modified'] = True
    Dict.Save()
    return

####################################################################################################
@route(PREFIX + '/seasonlist')
def SeasonList(tvdbid, show):
    '''Display a list of all season of the given TV series in SickBeard'''
    oc = ObjectContainer(title1=show, title2="Seasons")
    seasons = API_Request([{"key":"cmd","value":"show.seasonlist"},{"key":IndexerField(),"value":tvdbid}])['data']
    for season in seasons:
        oc.add(PopupDirectoryObject(key=Callback(SeasonPopup, season=season, tvdbid=tvdbid, show=show),
            title="Season %s" % season, thumb=Callback(GetThumb, tvdbid=tvdbid)))
    
    return oc

####################################################################################################
@route(PREFIX + '/season')
def SeasonPopup(tvdbid, season, show):
    '''display a popup menu with options for the selected season'''
    oc = ObjectContainer()
    
    oc.add(DirectoryObject(key=Callback(EpisodeList, tvdbid=tvdbid, season=season, show=show), title="View Episode List"))
    
    for status in API_Request([{"key":"cmd", "value":"show.addnew"},{"key":"help", "value":"1"}])['data']['optionalParameters']['status']['allowedValues']:
        oc.add(DirectoryObject(key=Callback(SetSeasonStatus, tvdbid=tvdbid, season=season, status=status),
            title="Mark all episodes as '%s'" % String.CapitalizeWords(status)))
    
    return oc
    
####################################################################################################
@route(PREFIX + '/episodes')
def EpisodeList(tvdbid, season, show):
    '''Display a list of all episodes of the given TV series including the SickBeard state of each'''
    oc = ObjectContainer(title1=show, title2="Season %s" % season)
    episodes = API_Request([{"key":"cmd","value":"show.seasons"},{"key":IndexerField(),"value":tvdbid},
        {"key":"season","value":season}])['data']
    for key, value in episodes.iteritems():
        summary = "Airdate: %s\nQuality: %s\nStatus: %s" % (value['airdate'], value['quality'], value['status'])
        oc.add(PopupDirectoryObject(key=Callback(EpisodePopup, tvdbid=tvdbid, season=season, episode=key),
            title="%s. %s" %(key, value['name']), summary=summary, thumb=Callback(GetThumb, tvdbid=tvdbid)))
    
    #Attempt to sort the list using only the int value of the episode number
    oc.objects.sort(key = lambda obj: int(obj.title.split('. ')[0]))
    
    return oc

####################################################################################################
@route(PREFIX + '/editseries')
def EditSeries(tvdbid):
    '''display a menu of options for editing SickBeard functions for the given series'''

    show = API_Request([{"key":"cmd","value":"show"},{"key":IndexerField(),"value":tvdbid}])['data']

    oc = ObjectContainer(title2=show['show_name'], no_cache=True)

    oc.add(DirectoryObject(key=Callback(API_Request, params=[{"key":"cmd","value":"show.refresh"},{"key":IndexerField(),"value":tvdbid}],
        return_message=True), title='Re-Scan Files', summary="Refresh a show in SickBeard by rescanning local files", thumb=Callback(GetThumb, tvdbid=tvdbid)))
    oc.add(DirectoryObject(key=Callback(API_Request, params=[{"key":"cmd","value":"show.update"},{"key":IndexerField(),"value":tvdbid}],
        return_message=True), title='Force Full Update', summary="Update a show in SickBeard by pulling down information from TVDB and rescan local files",
        thumb=Callback(GetThumb, tvdbid=tvdbid)))
    oc.add(DirectoryObject(key=Callback(API_Request, params=[{"key":"cmd","value":"show.delete"},{"key":IndexerField(),"value":tvdbid}],
        return_message=True), title='Delete Series', summary="Delete a show from SickBeard", thumb=Callback(GetThumb, tvdbid=tvdbid)))
    
    if not show['paused']:
        oc.add(DirectoryObject(key=Callback(API_Request, params=[{"key":"cmd","value":"show.pause"},{"key":IndexerField(),"value":tvdbid},
            {"key":"pause","value":"1"}], return_message=True), title='Pause Series', thumb=Callback(GetThumb, tvdbid=tvdbid)))
    else:
        oc.add(DirectoryObject(key=Callback(API_Request, params=[{"key":"cmd","value":"show.pause"},{"key":IndexerField(),"value":tvdbid},
            {"key":"pause","value":"0"}], return_message=True), title='Unpause Series', thumb=Callback(GetThumb, tvdbid=tvdbid)))
    
    oc.add(DirectoryObject(key=Callback(SeriesQuality, tvdbid=tvdbid, show=show['show_name']), title="Download Quality: [%s]" % show['quality'],
        summary="Initial: %s \nArchive: %s" % (show['quality_details']['initial'],show['quality_details']['archive']), thumb=Callback(GetThumb, tvdbid=tvdbid)))
        
    return oc

####################################################################################################
@route(PREFIX + '/seriesquality')
def SeriesQuality(tvdbid, show):
    '''allow option to change quality setting for individual series'''
    
    oc = ObjectContainer(title1=show, title2='Quality Settings', no_cache=True)
    
    if not Dict['settings_modified']:
        GetQualityDefaults(group="Series", tvdbid=tvdbid)
    
    oc.add(PopupDirectoryObject(key=Callback(QualitySetting, group="Series", category="initial"), title="Initial Quality", 
        summary='Selected Qualities: %s' % Dict['Series']['initial'], thumb=Callback(GetThumb, tvdbid=tvdbid)))
    oc.add(PopupDirectoryObject(key=Callback(QualitySetting, group="Series", category="archive"), title="Archive Quality",
        summary='Selected Qualities: %s' % Dict['Series']['archive'], thumb=Callback(GetThumb, tvdbid=tvdbid)))
    oc.add(DirectoryObject(key=Callback(ApplyQualitySettings, tvdbid=tvdbid), title="Apply quality settings",
        summary="Tell SickBeard to apply these quality settings to %s" % show, thumb=Callback(GetThumb, tvdbid=tvdbid)))
    return oc
    
####################################################################################################    
@route(PREFIX + '/applyquality')
def ApplyQualitySettings(tvdbid):
    '''send modified quality settings for the given series to SickBeard'''
    settings = {}
    for key, value in Dict['Series'].iteritems():
        if range(len(value)) > 1:
            settings[key] = '|'.join(value)
        else:
            settings[key] = value
    
    Dict['settings_modified'] = False

    return API_Request([{"key":"cmd","value":"show.setquality"},{"key":IndexerField(),"value":tvdbid},
        {"key":"initial","value":settings['initial']},{"key":"archive","value":settings['archive']}], return_message=True)
    
####################################################################################################
@route(PREFIX + '/episoderefresh')
def EpisodeRefresh(tvdbid, season, episode):
    '''tell SickBeard to do a force search for the given episode'''

    return API_Request([{"key":"cmd","value":"episode.search"},{"key":IndexerField(),"value":tvdbid},
        {"key":"season","value":season},{"key":"episode","value":episode}], return_message=True)

####################################################################################################
@route(PREFIX + '/episodestatus', entire_season=bool)
def SetEpisodeStatus(tvdbid, season, episode, status, entire_season=False):
    '''tell SickBeard to do mark the given episode(s) with the given status'''

    data = API_Request([{'key':'cmd','value':'episode.setstatus'},{'key':IndexerField(),'value':tvdbid},
        {'key':'season','value':season},{'key':'episode','value':episode},{'key':'status','value':status}])
    message = data['message']
    
    if entire_season:
        if data['result'] == 'success':
            return True
        else:
            Log.Error("TVDBID: %s S%sE%s -- %s" % (tvdbid, data['data'][0]['season'], data['data'][0]['episode'], data['data'][0]['message']))
            return False
    else:
        return ObjectContainer(header=NAME, message=message)
    
####################################################################################################
@route(PREFIX + '/seasonstatus')
def SetSeasonStatus(tvdbid, season, status):
    '''iterate through the given season and tell SickBeard to mark each episode as wanted'''
    
    count = 0
    episodes = API_Request([{'key':'cmd','value':'show.seasons'},{'key':IndexerField(),'value':tvdbid},
        {'key':'season','value':season}])['data']
    for key, value in episodes.iteritems():
        if SetEpisodeStatus(tvdbid, season, episode=key, status=status, entire_season=True):
            count = count +1
    
    return ObjectContainer(header=NAME, message="%s marked as '%s'" % (count, String.CapitalizeWords(status)))

####################################################################################################
@route(PREFIX + '/getepisodes')
def GetEpisodes(tvdbid):
    '''determine the number of downloaded (or snatched) episodes out of the total number of episodes
        for the given series'''
    show = API_Request([{'key':'cmd','value':'show.stats'},{'key':IndexerField(),'value':tvdbid}])['data']

    try:
        downloaded = int(show['downloaded']['total']) + int(show['archived'])
        total = show['total']
        episodes = "[%s / %s]" % (downloaded, total)
    except:
        episodes = "[? / ?]"
    
    
    return episodes

####################################################################################################
@route(PREFIX + '/sburl', reset=bool)
def Get_SB_URL(reset=False):
    ''' include a hack to set the SickBeard URL in the plugin Dict since saving prefs seems unreliable'''
    if reset:
        webroot = Prefs['webroot']
        if webroot:
            if webroot[0] == '/':
                pass
            else:
                webroot = '/'+webroot
        else:
            webroot = ''
        if Prefs['sbIP'].startswith("http"):
            Dict['SB_URL'] = '%s:%s%s' % (Prefs['sbIP'], Prefs['sbPort'], webroot)
        else:
            if Prefs['https']:
                Dict['SB_URL'] = 'https://%s:%s%s' % (Prefs['sbIP'], Prefs['sbPort'], webroot)
            else:
                Dict['SB_URL'] = 'http://%s:%s%s' % (Prefs['sbIP'], Prefs['sbPort'], webroot)
    else:
        pass
    
    return Dict['SB_URL']
    
####################################################################################################
@route(PREFIX + '/apiurl')
def API_URL():
    '''build and return the base url for all SickBeard API requests'''
    return Get_SB_URL() + '/api/%s/?' % Prefs['sbAPI']

####################################################################################################
@route(PREFIX + '/api', params=list, return_message=bool)
def API_Request(params=[], return_message=False):
    '''use the given args to make an API request and return the JSON'''
    
    '''start with the base API url'''
    request_url = API_URL()
    '''build the request url with the given parameters'''
    if len(params) > 1:
        for i in range(len(params)):
            request_url = request_url + "%s=%s&" % (params[i]['key'], params[i]['value'])
    else:
        request_url = request_url + "%s=%s" % (params[0]['key'], params[0]['value'])
    '''strip the trailing "&" from the request_url'''
    request_url = request_url.strip('&')
    '''send the request and confirm success'''
    data = JSON.ObjectFromURL(request_url, timeout=30, cacheTime=0)
    
    if return_message:
        return ObjectContainer(header=NAME, message=data['message'])
    else:
        pass
    
    if data['result'] == "denied":
        return ObjectContainer(header=NAME, message="The API request: %s\n was denied. Do you need to update your API key?" % request_url)
    elif data['result'] == 'success' or 'failure':
        return data
    elif data['result'] == 'fatal':
        Log.Error("SickBeard threw an error:\n" + data)
        return data
    else:
        return ObjectContainer(header=NAME, message="The API request: %s\n was unsuccessful. Please try again." % request_url)
    
####################################################################################################
@route(PREFIX + '/futuretitle', episode=dict)
def FutureEpisodeTitle(episode={}):
    '''build a string for the episode's title using the show name, season #, episode #, and episode title'''
    episode_title = "%s - S%sE%s - %s" % (episode['show_name'], episode['season'], episode['episode'], episode['ep_name'])
    return episode_title
    
####################################################################################################
@route(PREFIX + '/futuresummary', episode=dict)
def FutureEpisodeSummary(episode={}):
    '''build a string for the episode's summary using the episode's airdate, airs, network, paused(if true), quality, show_status,
        and ep_plot'''
    if episode['paused']:
        paused = 'Paused: True\n'
    else:
        paused = ''
    episode_summary = "Episode Airdate: %s\nTimeslot: %s\nNetwork: %s\nQuality: %s\nStatus: %s\n%s\nSynopsis: %s" % (
        episode['airdate'], episode['airs'], episode['network'], episode['quality'], episode['show_status'], paused, episode['ep_plot'])
    return episode_summary
    
####################################################################################################
@route(PREFIX + '/historytitle', episode=dict)
def HistoryEpisodeTitle(episode={}):
    '''build a string for the episode's title using the show name, season #, episode #'''
    episode_title = "%s - S%sE%s - %s" % (episode['show_name'], episode['season'], episode['episode'], episode['status'])
    return episode_title
    
####################################################################################################
@route(PREFIX + '/historysummary', episode=dict)
def HistoryEpisodeSummary(episode={}):
    '''build a string for the episode's summary using the episode's airdate, airs, network, paused(if true), quality, show_status,
        and ep_plot'''
    episode_summary = "Date: %s\nEpisode: %s\nProvider: %s\nQuality: %s\nStatus: %s\n" % (
        episode['date'], episode['episode'], episode['provider'], episode['quality'], episode['status'])
    return episode_summary
    
####################################################################################################
@route(PREFIX + '/thumb')
def GetThumb(tvdbid):
    thumb_url = API_URL() + "cmd=show.getposter&%s=%s" % (IndexerField(), tvdbid)
    MAX_RETRIES = 2
    i = 0
    while i < MAX_RETRIES: 
        try:
            data = HTTP.Request(thumb_url).content
            break
        except:
            i+=1
            Log.Error('Failed to retrieve image from SickBeard. Retrying... Attempt #%d of %d' % (i+1, MAX_RETRIES+1))
            continue
    return DataObject(data, 'image/jpeg')