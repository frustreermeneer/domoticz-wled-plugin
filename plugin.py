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
            <li>Setting palette from list</li>
            <li>Fast updating with UDP</li>
        </ul>
        <!--h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Device Type - What it does...</li>
        </ul-->
        <h3>Configuration</h3>
    </description>
    <params>
	<param field="Address" label="WLED IP Address" width="200px" required="true" default=""/>
	<param field="Port" label="WLED UDP Sync Port" width="200px" required="true" default="21324"/>
	<param field="Mode1" label="FX and palettes update interval (every x*10 secs)" width="200px" required="true" default="30"/>
	<param field="Mode6" label="Debug" width="200px">
	    <options>
		<option label="None" value="0"  default="true" />
		<option label="Python Only" value="2"/>
		<option label="Basic Debugging" value="62"/>
		<option label="Basic+Messages" value="126"/>
		<option label="Connections Only" value="16"/>
		<option label="Connections+Queue" value="144"/>
		<option label="All" value="-1"/>
	    </options>
	</param>
    </params>
</plugin>
"""
import Domoticz
import json
import requests

ipaddress = ""
jsonArray = None
wledData = {}

class BasePlugin:
    enabled = True
    counter = 0

    JSONConn = None
    UDPConn = None

    def onStart(self):
        self.counter = 0
        self.Color = {}
        self.Level = 100

        global ipaddress
        global updateInterval

        if Parameters["Mode6"] != "0":
            Domoticz.Debugging(int(Parameters["Mode6"]))
            DumpConfigToLog()

        ipaddress = Parameters["Address"].strip()
        updateInterval = int(Parameters["Mode1"].strip())

        self.UDPConn = Domoticz.Connection(Name="UDPConn", Transport="UDP/IP", Address=ipaddress, Port=str(Parameters["Port"]))
        self.UDPConn.Listen()

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

        getWLEDJSON( self.JSONConn )

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        global ipaddress

        # Get JSON from WLED after it connects
        if( Connection.Name == "JSONConn" ):
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
        global wledData
        global updateInterval

        try:

            # we get answer back from our json request
            # start update from json data
            if( Connection.Name == "JSONConn" ):
                Connection.Disconnect()

                Status = int(Data["Status"])

                if( Status == 200 ):
                    strData = Data["Data"].decode("utf-8", "ignore")

                    if( len( strData ) ):
                        jsonArray = json.loads( str(strData) ) 

                    if( len( jsonArray ) ):
                        # only update Domoticz from JSON on plugin start
                        if( self.counter == 0 ):
                            #wled data comes from json
                            Domoticz.Log("Updating Domoticz from JSON")
                            wledData["red"] = int(jsonArray['state']['seg'][0]["col"][0][0])
                            wledData["green"] = int(jsonArray['state']['seg'][0]["col"][0][1])
                            wledData["blue"] = int(jsonArray['state']['seg'][0]["col"][0][2])
                            wledData["bri"] = jsonArray['state']['bri']
                            wledData["preset"] = jsonArray['state']['ps']
                            if( wledData["preset"] < 0 ): wledData["preset"] = 0
                            wledData["effectCurrent"] = jsonArray['state']['seg'][0]['fx']
                            wledData["effectIntensity"] = jsonArray['state']['seg'][0]['ix']
                            wledData["effectSpeed"] = jsonArray['state']['seg'][0]['sx']
                            wledData["effectPalette"] = jsonArray['state']['seg'][0]['pal'];

                            # update domoticz wleddata from json
                            UpdateStatusInDomoticz()

                        # every time JSON data is retrieved update effects and palettes in Domoticz
                        UpdateEffectsInDomoticz()
                        UpdatePalettesInDomoticz()


            if( Connection.Name == "UDPConn" ):
                # Is it notifier protocol?
                if ( Data[0] == 0x00 and Data[21] == 0x00 and Data[22] == 0x00 and Data[23] == 0x00 and Data[24] == 0x00):
                    wledData = {
                        "callMode": Data[1],
                        "bri": Data[2],
                        "red": Data[3],
                        "green": Data[4],
                        "blue": Data[5],
                        "nightlightActive": Data[6],
                        "nightlightDelayMins": Data[7],
                        "effectCurrent": Data[8],
                        "effectSpeed": Data[9],
                        "white": Data[10],
                        "redSec": Data[12],
                        "greenSec": Data[13],
                        "blueSec": Data[14],
                        "whiteSec": Data[15],
                        "effectIntensity": Data[16],
                        "transitionDelayHi": Data[17],
                        "transitionDelayLow": Data[18],
                        "effectPalette": Data[19]
                    }

                    # update domoticz with wleddata from UDP
                    Domoticz.Log("Updating Domoticz from UDP")
                    UpdateStatusInDomoticz()

        except Exception as inst:
            Domoticz.Error("Exception detail: '"+str(inst)+"'")
            raise

    def onCommand(self, Unit, Command, Level, Color):
        # palette picked
        if( Unit == 1 ):
            if( Command == "Set Level" ):
                doWLEDRequest( "&FP="+str(int(Level/10)-1) )
                #UpdateDevice(1, 1, Level )

        # effect picked
        if( Unit == 2 ):
            if( Command == "Set Level" ):
                doWLEDRequest( "&T=1&FX="+str(int(Level/10)-1) )
                #UpdateDevice(2, 1, Level )

            if( Command == "Off" ):
                doWLEDRequest( "&T=0" )
                #UpdateDevice(2, 0,  0 )

        # color picked
        if( Unit == 3 ):
            if( Command == "Set Level" ):
                self.Level = Level if Level < 100 else 100
                UpdateDevice(3,1,self.Level) 		#,self.Color)
                doWLEDRequest( "/win&A="+str(int(self.Level*2.55)) )

            if( Command == "Set Color" ):		#set color and level
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

        # preset picked
        if( Unit == 4 ):
            if( Command == "Set Level" ):
                Domoticz.Log( "Switching to preset" + str(int(Level/10)))
                #UpdateDevice(4,1,int(Level))
                doWLEDRequest( "/win&PL="+str(int(Level/10)) )

        # fx speed set
        if( Unit == 5 ):
            if( Command == "Set Level" ):
                Domoticz.Log( "FX Speed: " + str(int(Level*2.55)))
                #UpdateDevice(5,1,int(Level))
                doWLEDRequest( "/win&SX="+str(int(Level*2.55)) )

        # fx intensity set
        if( Unit == 6 ):
            if( Command == "Set Level" ):
                Domoticz.Log( "FX Intensity: " + str(int(Level*2.55)))
                #UpdateDevice(6,1,int(Level))
                doWLEDRequest( "/win&IX="+str(int(Level*2.55)) )

    def onHeartbeat(self):
        global updateInterval
        self.counter = self.counter + 1
        #Domoticz.Log("counter:" + str(self.counter))

        if( self.counter > updateInterval ):
            self.counter = 1
            getWLEDJSON( self.JSONConn )

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
    Domoticz.Log("Updating effects")

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
    Domoticz.Log("Updating palettes")

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
    Domoticz.Log("Updating presets")

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
    global wledData

#    Domoticz.Log( str(jsonArray['state']) )
    wledData["color"] = json.dumps({ "b": wledData["blue"],
                                     "cw": 0,
                                     "g": wledData["green"],
                                     "m": 3,
                                     "r": wledData["red"],
                                     "t": 0,
                                     "ww": 0 })
    
    # brightness and color
    if( wledData["bri"] == 0 ):
        UpdateDevice(3,0,int(wledData["bri"]/2.55),wledData["color"]) #Devices[3].sValue)
    else:
        UpdateDevice(3,1,int(wledData["bri"]/2.55),wledData["color"]) #Devices[3].sValue)

    # effect Intensity
    UpdateDevice(6,1,int(wledData["effectIntensity"]/2.55))

    # effect Speed
    UpdateDevice(5,1,int(wledData["effectSpeed"]/2.55))

    # current Effect
    UpdateDevice(2,1,(int(wledData["effectCurrent"])+1)*10)

    # Palette
    UpdateDevice(1,1,(int(wledData["effectPalette"])+1)*10 )

    # preset (not implemented in WLED yet)
#   Domoticz.Log( "preset:" + str(preset) )
#   UpdateDevice(4,1,int(wledData["preset"]*10)) 

def getWLEDJSON( JSONConn ):
    #Domoticz.Log("getWLEDJSON")
    JSONConn = Domoticz.Connection(Name="JSONConn", Transport="TCP/IP", Protocol="HTTP", Address=ipaddress, Port="80" )
    JSONConn.Connect()

def doWLEDRequest( parameters ):
    global ipaddress
    url = "http://"+ipaddress+"/win"+parameters
    resp = requests.get(url=url)
#    Domoticz.Log( url )
#    Domoticz.Log(str(resp.status_code))
#    Domoticz.Log(str(resp))
