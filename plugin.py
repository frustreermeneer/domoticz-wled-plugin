# WLED Plugin for Domoticz
#
# Author: Frustreermeneer
#
"""
<plugin key="WLED" name="WLED" author="frustreermeneer" version="0.0.1" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://github.com/frustreermeneer/domoticz-wled-plugin">
    <description>
        <h2>WLED Plugin</h2><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Switching WLED on/off</li>
            <li>Setting brightness</li>
            <li>Setting effect from list</li>
            <li>Setting effect speed & intensity</li>
            <li>Setting presets from list</li>
            <li>Setting pallette from list</li>
        </ul>
        <!--h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Device Type - What it does...</li>
        </ul-->
        <h3>Configuration</h3>
    </description>
    <params>
	<param field="Address" label="WLED IP Address" width="200px" required="true" default=""/>
	<param field="Mode1" label="FX and pallettes update interval (every x*10 secs)" width="200px" required="true" default="6"/>
    </params>
</plugin>
"""
import Domoticz
import json
import requests

ipaddress = ""
jsonArray = None
getWLEDStatusConn = None

class BasePlugin:
    enabled = True
    counter = 0

    def onStart(self):
        self.counter = 0
        self.Color = {}
        self.Level = 100

        global ipaddress
        global updateInterval

        ipaddress = Parameters["Address"].strip()
        updateInterval = int(Parameters["Mode1"].strip())

        
        if (len(Devices) == 0):
            Domoticz.Log("creating devices")

            Options = {"LevelActions": "",
                  "LevelNames": "Loading...",
                  "LevelOffHidden": "true",
                  "SelectorStyle": "1"}

            Domoticz.Device(Name="Palettes", Unit=1, TypeName="Selector Switch", Options=Options, Image=0).Create()
            Domoticz.Device(Name="Effects", Unit=2, TypeName="Selector Switch", Options=Options).Create()
            Domoticz.Device(Name="Color & Brightness", Unit=3, Type=241,Subtype=2,Switchtype=7,Options=Options).Create()
            Domoticz.Device(Name="Presets", Unit=4, TypeName="Selector Switch", Options=Options).Create()
            Domoticz.Device(Name="FX Speed", Unit=5, Type=244,Subtype=62,Switchtype=7,Options=Options).Create()
            Domoticz.Device(Name="FX Intensity", Unit=6, Type=244,Subtype=62,Switchtype=7,Options=Options).Create()
        else:
            Domoticz.Log("devices existed already")

        UpdatePresetsInDomoticz()
        getWLEDStatus()

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        global ipaddress
 
        # er is een externe verbinding gemaakt
        # json request doen
        if( Connection.Name == "getWLEDStatusConn" ):
            sendData = { 'Verb' : 'GET',
                         'URL'  : '/json',
                         'Headers' : { 'Content-Type': 'application/json; charset=utf-8', 
                                       'Connection': 'keep-alive', 
                                       'Accept': 'Content-Type: text/plain; charset=UTF-8', 
                                       'Host': ipaddress+":80",
                                       'User-Agent':'Domoticz/1.0' }
                       }
            Connection.Send(sendData)

    def onMessage(self, Connection, Data):
        global jsonArray
        global updateInterval
        
        # we krijgen antwoord terug op onze request
        # json update request afhandelen
        if( Connection.Name == "getWLEDStatusConn" ):
            Connection.Disconnect()
            
            Status = int(Data["Status"])
            
            if( Status == 200 ):
                strData = Data["Data"].decode("utf-8", "ignore")

                jsonArray = json.loads( str(strData) ) 

                if( len( jsonArray ) ):
                    UpdateStatusInDomoticz()
                    if( self.counter == 0 ):
                        UpdateEffectsInDomoticz()
                        UpdatePalettesInDomoticz()

            self.counter = self.counter + 1

            if( self.counter >= updateInterval ):
                self.counter = 0

    def onCommand(self, Unit, Command, Level, Color):
#        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Command '" + str(Command) + "', Level: " + str(Level) + "', Color: " + str(Color) )

        # palettes keuze
        if( Unit == 1 ):
            if( Command == "Set Level" ):
                doWLEDRequest( "&FP="+str(int(Level/10)-1) )
                UpdateDevice(1, 1, Level )
    
        # effect keuze

        if( Unit == 2 ):
            if( Command == "Set Level" ):
                doWLEDRequest( "&T=1&FX="+str(int(Level/10)-1) )
                UpdateDevice(2, 1, Level )

            if( Command == "Off" ):
                doWLEDRequest( "&T=0" )
                UpdateDevice(2, 0,  0 )

        # kleurkeuze 

        if( Unit == 3 ):
            if( Command == "Set Level" ):
                self.Level = Level if Level < 100 else 100
                UpdateDevice(3,1,self.Level) 		#,self.Color)
                doWLEDRequest( "/win&A="+str(int(self.Level*2.55)) )

            if( Command == "Set Color" ):		#set kleur en level
                self.Color = Color;
                self.Level = Level
                Domoticz.Log( "Color:" + str(self.Color) )
                parsedColor = json.loads(self.Color)
                UpdateDevice(3,1,self.Level,self.Color)
                doWLEDRequest( "/win&FX=0&A="+str(int(self.Level*2.55))+"&R="+str(parsedColor["r"])+"&G="+str(parsedColor["g"])+"&B="+str(parsedColor["b"] ) )

            if( Command == "On" ):
                UpdateDevice(3,1,self.Level) 		#,self.Color)
                doWLEDRequest( "/win&T=1&A="+str(int(self.Level*2.55)) )

            if( Command == "Off" ):
                UpdateDevice(3,0, self.Level) 		#,self.Color)
                doWLEDRequest( "/win&T=0&A="+str(int(self.Level*2.55)) )

        # preset keuze
        if( Unit == 4 ):
            if( Command == "Set Level" ):
                Domoticz.Log( "Switching to preset" + str(int(Level/10)))
                UpdateDevice(4,1,int(Level))
                doWLEDRequest( "/win&PL="+str(int(Level/10)) )

        # fx speed
        if( Unit == 5 ):
            if( Command == "Set Level" ):
                Domoticz.Log( "FX Speed: " + str(int(Level*2.55)))
                UpdateDevice(5,1,int(Level))
                doWLEDRequest( "/win&SX="+str(int(Level*2.55)) )

        # fx intensity
        if( Unit == 6 ):
            if( Command == "Set Level" ):
                Domoticz.Log( "FX Intensity: " + str(int(Level*2.55)))
                UpdateDevice(6,1,int(Level))
                doWLEDRequest( "/win&IX="+str(int(Level*2.55)) )

    def onHeartbeat(self):
        getWLEDStatus()


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def UpdateDevice(Unit, nValue, sValue, Color=""):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it.
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (Devices[Unit].Color != Color):
            if( Color ):
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue), Color=str(Color) )
            else:
                Devices[Unit].Update(nValue=nValue, sValue=str(sValue) )
    return

def UpdateEffectsInDomoticz():
    global jsonArray

#    Domoticz.Log("updateEffects")

    LevelNames = "Off|"
    LevelActions = "|"

    effectsArray = jsonArray["effects"]

    for idx,effect in enumerate(effectsArray):
        LevelNames = LevelNames + str(idx+1) + " - " + str(effect)
        if( idx < len(effectsArray)-1 ):
           LevelNames = LevelNames + "|"
           LevelActions = LevelActions + "|"

    dictOptions = Devices[2].Options
    dictOptions["LevelNames"] = LevelNames
    dictOptions["LevelActions"] = LevelActions
    nValue = Devices[2].nValue;
    sValue = Devices[2].sValue;
    Devices[2].Update(nValue = nValue, sValue = sValue, Options = dictOptions)

def UpdatePalettesInDomoticz():
    global jsonArray

#    Domoticz.Log("updatePallettes")

    LevelNames = "Off|"
    LevelActions = "|"

    palettesArray = jsonArray["palettes"]

    for idx,palette in enumerate(palettesArray):
        LevelNames = LevelNames + str(idx+1) + " - " + str(palette)
        if( idx < len(palettesArray)-1 ):
           LevelNames = LevelNames + "|"
           LevelActions = LevelActions + "|"

    dictOptions = Devices[1].Options
    dictOptions["LevelNames"] = LevelNames
    dictOptions["LevelActions"] = LevelActions
    nValue = Devices[1].nValue;
    sValue = Devices[1].sValue;
    Devices[1].Update(nValue = nValue, sValue = sValue, Options = dictOptions)


def UpdatePresetsInDomoticz():
#    Domoticz.Log("updatePresets")

    LevelNames = "None|"
    LevelActions = "|"

    for i in range(1,25):
        LevelNames = LevelNames + str(i)
        if( i < 24 ):
           LevelNames = LevelNames + "|"
           LevelActions = LevelActions + "|"

#    Domoticz.Log( LevelNames )

    dictOptions = Devices[4].Options
    dictOptions["LevelNames"] = LevelNames
    dictOptions["LevelActions"] = LevelActions
    dictOptions["LevelOffHidden"] = "false"
    nValue = Devices[4].nValue;
    sValue = Devices[4].sValue;
    Devices[4].Update(nValue = nValue, sValue = sValue, Options = dictOptions)

def UpdateStatusInDomoticz():
    global jsonArray
#    Domoticz.Log("updateStatus")

    brightness = jsonArray['state']['bri']
#    Domoticz.Log( "brightness:" + str(brightness) )
#    Domoticz.Log( "col:" + str(jsonArray['state']['seg'][0]["col"][0]) )
    r = int(jsonArray['state']['seg'][0]["col"][0][0])
    g = int(jsonArray['state']['seg'][0]["col"][0][1])
    b = int(jsonArray['state']['seg'][0]["col"][0][2])
    color = json.dumps({ "b":b, "cw":0, "g":g, "m":3, "r":r, "t":0, "ww":0 })

    UpdateDevice(3,1,int(brightness/2.55),color) #Devices[3].sValue)

    preset = jsonArray['state']['ps']
    if( preset <= 0 ): preset = 0
#    Domoticz.Log( "preset:" + str(preset) )
    #UpdateDevice(4,1,int(preset*10)) #not working in 0.8.5 yet

#    Domoticz.Log( "ix:" + str(jsonArray['state']['seg'][0]['ix']) )
    UpdateDevice(6,1,int(jsonArray['state']['seg'][0]['ix']/2.55))

#    Domoticz.Log( "sx:" + str(jsonArray['state']['seg'][0]['sx']) )
    UpdateDevice(5,1,int(jsonArray['state']['seg'][0]['sx']/2.55))

#    Domoticz.Log( "fx:" + str(jsonArray['state']['seg'][0]['fx']) )
    effect = int(jsonArray['state']['seg'][0]['fx'])
    UpdateDevice(2,1,(effect+1)*10)
    
#    Domoticz.Log( "pal:" + str(jsonArray['state']['seg'][0]['pal']) )
    UpdateDevice(1, 1, (int(jsonArray['state']['seg'][0]['pal'])+1)*10 )


def getWLEDStatus():
    getWLEDStatusConn = Domoticz.Connection(Name="getWLEDStatusConn", Transport="TCP/IP", Protocol="HTTP", Address=ipaddress, Port="80" )
    getWLEDStatusConn.Connect()

def doWLEDRequest( parameters ):
    global ipaddress
    url = "http://"+ipaddress+"/win"+parameters
#    Domoticz.Log( url )
    resp = requests.get(url=url)
#    Domoticz.Log(str(resp.status_code))
#    Domoticz.Log(str(resp))
